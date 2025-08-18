import os
import sys
import json
import logging
import random
import ctypes
import atexit
import requests
import difflib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List, Tuple

from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


# ---------- Система ролей и привилегий ----------
class UserRole(Enum):
	USER = "user"
	EDITOR = "editor"      # Может редактировать контент
	MODERATOR = "moderator" # Может модерировать чат
	ADMIN = "admin"        # Полный доступ
	SUPER_ADMIN = "super_admin" # Создатель бота

# Привилегии для каждой роли
ROLE_PRIVILEGES = {
	UserRole.USER: set(),
	UserRole.EDITOR: {"edit_content", "view_stats"},
	UserRole.MODERATOR: {"edit_content", "view_stats", "warn_users", "delete_messages", "kick_users"},
	UserRole.ADMIN: {"edit_content", "view_stats", "warn_users", "delete_messages", "kick_users", "ban_users", "manage_roles", "ai_control"},
	UserRole.SUPER_ADMIN: {"*"}  # Все привилегии
}

# Роли пользователей (user_id -> role)
USER_ROLES: Dict[int, UserRole] = {}

# 2FA коды для админов (user_id -> {"code": "123456", "expires": timestamp})
ADMIN_2FA_CODES: Dict[int, Dict] = {}

# Ранний загрузчик .env до чтения переменных окружения в константах ниже
load_dotenv()

# ---------- Настройки OpenRouter (DeepSeek) ----------
DEEPSEEK_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
OPENROUTER_MODELS = os.getenv("OPENROUTER_MODELS", "deepseek/deepseek-chat-v3-0324:free,deepseek/deepseek-r1-0528:free,qwen/qwen3-coder:free,deepseek/deepseek-r1:free").strip()
MAX_HISTORY_MESSAGES = 8
MAX_AI_CHARS = 380
AI_REFERER = os.getenv("OPENROUTER_REFERER", "https://vk.com/crycat_memes")
AI_TITLE = os.getenv("OPENROUTER_TITLE", "Cry Cat Bot")

# ---------- Настройки AITunnel ----------
AITUNNEL_API_URL = os.getenv("AITUNNEL_API_URL", "").strip()
AITUNNEL_MODEL = os.getenv("AITUNNEL_MODEL", "deepseek-r1-fast").strip()
AITUNNEL_MODELS = os.getenv("AITUNNEL_MODELS", "").strip()

# Провайдер ИИ: OPENROUTER, AITUNNEL, AUTO
AI_PROVIDER = os.getenv("AI_PROVIDER", "AITUNNEL").strip().upper()

# Администраторы (через запятую: user_id)
def _parse_admin_ids(csv: str) -> Set[int]:
	ids: Set[int] = set()
	for part in (csv or "").split(","):
		part = part.strip()
		if part.isdigit():
			ids.add(int(part))
	return ids

ADMIN_USER_IDS: Set[int] = _parse_admin_ids(os.getenv("ADMIN_USER_IDS", "").strip())

# Текущее имя модели AITunnel (может быть изменено админом в рантайме)
RUNTIME_AITUNNEL_MODEL: str = AITUNNEL_MODEL

# Текущий провайдер ИИ (может быть изменён админом в рантайме)
RUNTIME_AI_PROVIDER: str = AI_PROVIDER

# Текущая модель OpenRouter (может быть изменена админом в рантайме)
RUNTIME_OPENROUTER_MODEL: str = DEEPSEEK_MODEL

# ---------- Не даём Windows уснуть ----------
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

def prevent_sleep() -> None:
	try:
		if os.name == "nt":
			ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
	except Exception:
		pass

def allow_sleep() -> None:
	try:
		if os.name == "nt":
			ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
	except Exception:
		pass

atexit.register(allow_sleep)


def configure_logging() -> None:
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)


def load_config() -> Tuple[str, int, str, str, str, str]:
	load_dotenv()
	token = os.getenv("VK_GROUP_TOKEN", "").strip()
	group_id_str = os.getenv("VK_GROUP_ID", "").strip()
	openrouter_key = os.getenv("DEEPSEEK_API_KEY", "").strip()  # ключ OpenRouter
	aitunnel_key = os.getenv("AITUNNEL_API_KEY", "").strip()
	ai_provider = os.getenv("AI_PROVIDER", AI_PROVIDER).strip().upper()
	system_prompt = (
		os.getenv("AI_SYSTEM_PROMPT", "").strip()
		or "Ты КиберКусь. Пиши по-русски, дружелюбно, до 380 символов. По запросу кратко упоминай: Мафия, Угадай число, Викторина, Кальмар, ИИ‑чат."
	)
	if not token:
		raise RuntimeError("VK_GROUP_TOKEN is not set in .env")
	if not group_id_str.isdigit():
		raise RuntimeError("VK_GROUP_ID must be a number (без минуса)")
	return token, int(group_id_str), openrouter_key, system_prompt, aitunnel_key, ai_provider


# ---------- Мафия: лобби ----------
@dataclass
class Lobby:
	leader_id: int
	player_ids: Set[int] = field(default_factory=set)

	def add_player(self, user_id: int) -> None:
		self.player_ids.add(user_id)

	def remove_player(self, user_id: int) -> None:
		self.player_ids.discard(user_id)


# peer_id -> Lobby
LOBBIES: Dict[int, Lobby] = {}


# ---------- Угадай число (2 игрока) ----------
@dataclass
class GuessNumberSession:
	creator_id: int
	joined_ids: Set[int] = field(default_factory=set)  # лобби
	player_order: List[int] = field(default_factory=list)  # двое игроков при старте
	started: bool = False
	secret_number: int = 0
	current_turn_index: int = 0
	min_value: int = 1
	max_value: int = 100
	attempts: Dict[int, int] = field(default_factory=dict)

	def add_player(self, user_id: int) -> bool:
		if self.started:
			return False
		if len(self.joined_ids) >= 2 and user_id not in self.joined_ids:
			return False
		self.joined_ids.add(user_id)
		return True

	def remove_player(self, user_id: int) -> None:
		self.joined_ids.discard(user_id)

	def can_start(self) -> bool:
		return not self.started and len(self.joined_ids) == 2

	def start(self) -> None:
		self.started = True
		self.player_order = list(self.joined_ids)[:2]
		random.shuffle(self.player_order)
		self.secret_number = random.randint(self.min_value, self.max_value)
		self.current_turn_index = 0
		self.attempts = {self.player_order[0]: 0, self.player_order[1]: 0}

	def current_player_id(self) -> int:
		return self.player_order[self.current_turn_index]

	def other_player_id(self) -> int:
		return self.player_order[1 - self.current_turn_index]

	def switch_turn(self) -> None:
		self.current_turn_index = 1 - self.current_turn_index


# peer_id -> GuessNumberSession
GUESS_SESSIONS: Dict[int, GuessNumberSession] = {}


# ---------- ИИ‑чат состояния ----------
# В личных сообщениях ИИ всегда активен; в беседах — только после кнопки «ИИ‑чат»
AI_ACTIVE_CHATS: Set[int] = set()
AI_HISTORY: Dict[int, List[Dict[str, str]]] = {}  # peer_id -> [{"role": "...", "content": "..."}]

# ---------- Профили игроков и топы ----------
@dataclass
class UserProfile:
	user_id: int
	name: str = ""
	stats: Dict[str, int] = field(default_factory=dict)  # game_key -> points
	privacy_accepted: bool = False  # Принятие политики конфиденциальности
	privacy_accepted_at: str = ""   # Дата принятия
	gdpr_consent: bool = False      # Согласие на обработку персональных данных
	gdpr_consent_at: str = ""       # Дата согласия

PROFILES: Dict[int, UserProfile] = {}
PROFILES_FILE = os.getenv("PROFILES_FILE", "profiles.json").strip() or "profiles.json"

def load_profiles() -> None:
	try:
		if not os.path.exists(PROFILES_FILE):
			return
		with open(PROFILES_FILE, "r", encoding="utf-8") as f:
			data = json.load(f)
		for uid_str, prof in data.items():
			try:
				uid = int(uid_str)
				PROFILES[uid] = UserProfile(
					user_id=uid, 
					name=prof.get("name", ""), 
					stats=dict(prof.get("stats", {})),
					privacy_accepted=prof.get("privacy_accepted", False),
					privacy_accepted_at=prof.get("privacy_accepted_at", ""),
					gdpr_consent=prof.get("gdpr_consent", False),
					gdpr_consent_at=prof.get("gdpr_consent_at", "")
				)
			except Exception:
				continue
	except Exception:
		pass

def save_profiles() -> None:
	try:
		os.makedirs(os.path.dirname(PROFILES_FILE) or ".", exist_ok=True)
		out = {
			str(uid): {
				"name": p.name, 
				"stats": p.stats,
				"privacy_accepted": p.privacy_accepted,
				"privacy_accepted_at": p.privacy_accepted_at,
				"gdpr_consent": p.gdpr_consent,
				"gdpr_consent_at": p.gdpr_consent_at
			} for uid, p in PROFILES.items()
		}
		with open(PROFILES_FILE, "w", encoding="utf-8") as f:
			json.dump(out, f, ensure_ascii=False, indent=2)
	except Exception:
		pass

def get_profile(vk, user_id: int) -> UserProfile:
	prof = PROFILES.get(user_id)
	if not prof:
		prof = UserProfile(user_id=user_id)
		PROFILES[user_id] = prof
		# попытаться подтянуть имя
		try:
			users = vk.users.get(user_ids=str(user_id), name_case="Nom")
			if users:
				prof.name = f"{users[0]['first_name']} {users[0]['last_name']}"
		except Exception:
			pass
		save_profiles()
	return prof

def increment_stat(vk, user_id: int, game_key: str, inc: int = 1) -> None:
	prof = get_profile(vk, user_id)
	prof.stats[game_key] = prof.stats.get(game_key, 0) + inc
	save_profiles()

def format_top(vk, game_key: str, limit: int = 10) -> str:
	items = sorted(((uid, p.stats.get(game_key, 0)) for uid, p in PROFILES.items()), key=lambda x: x[1], reverse=True)
	items = [it for it in items if it[1] > 0][:limit]
	if not items:
		return "Пока нет результатов."
	lines: List[str] = []
	for idx, (uid, pts) in enumerate(items, start=1):
		name = PROFILES.get(uid).name or "игрок"
		lines.append(f"{idx}. {mention(uid, name)} — {pts}")
	return "\n".join(lines)


def check_user_consents(user_id: int) -> Tuple[bool, bool]:
	"""Проверяет, принял ли пользователь необходимые согласия"""
	prof = PROFILES.get(user_id)
	if not prof:
		return False, False
	return prof.privacy_accepted, prof.gdpr_consent


def accept_privacy_policy(user_id: int) -> None:
	"""Пользователь принимает политику конфиденциальности"""
	prof = PROFILES.get(user_id)
	if prof:
		prof.privacy_accepted = True
		prof.privacy_accepted_at = datetime.now().isoformat()
		save_profiles()


def accept_gdpr_consent(user_id: int) -> None:
	"""Пользователь принимает согласие на обработку персональных данных"""
	prof = PROFILES.get(user_id)
	if prof:
		prof.gdpr_consent = True
		prof.gdpr_consent_at = datetime.now().isoformat()
		save_profiles()


# ---------- Система ролей и привилегий ----------
def get_user_role(user_id: int) -> UserRole:
	"""Получить роль пользователя"""
	return USER_ROLES.get(user_id, UserRole.USER)


def has_privilege(user_id: int, privilege: str) -> bool:
	"""Проверить, есть ли у пользователя привилегия"""
	role = get_user_role(user_id)
	if role == UserRole.SUPER_ADMIN:
		return True
	return privilege in ROLE_PRIVILEGES.get(role, set())


def set_user_role(user_id: int, role: UserRole) -> None:
	"""Установить роль пользователя (только для админов)"""
	USER_ROLES[user_id] = role


def generate_2fa_code(user_id: int) -> str:
	"""Генерирует 6-значный код для 2FA"""
	code = str(random.randint(100000, 999999))
	expires = time.time() + 300  # 5 минут
	ADMIN_2FA_CODES[user_id] = {"code": code, "expires": time.time() + 300}
	return code


def verify_2fa_code(user_id: int, code: str) -> bool:
	"""Проверяет 2FA код"""
	if user_id not in ADMIN_2FA_CODES:
		return False
	
	code_data = ADMIN_2FA_CODES[user_id]
	if time.time() > code_data["expires"]:
		del ADMIN_2FA_CODES[user_id]
		return False
	
	if code_data["code"] == code:
		del ADMIN_2FA_CODES[user_id]
		return True
	
	return False


def require_2fa_for_admin(user_id: int, action: str) -> bool:
	"""Требует 2FA для критических админ-действий"""
	critical_actions = {"manage_roles", "ban_users", "delete_messages", "kick_users"}
	return action in critical_actions and has_privilege(user_id, "admin")


# ---------- Система мониторинга активности ----------
@dataclass
class UserActivity:
	user_id: int
	last_action: str = ""
	last_action_time: float = 0
	action_count: int = 0
	suspicious_actions: List[str] = field(default_factory=list)
	warnings: int = 0
	last_warning_time: float = 0

# Отслеживание активности пользователей
USER_ACTIVITY: Dict[int, UserActivity] = {}

# Подозрительные паттерны
SUSPICIOUS_PATTERNS = [
	"spam",           # Спам сообщения
	"flood",          # Флуд
	"inappropriate",  # Неподобающий контент
	"bot_abuse",      # Злоупотребление ботом
	"admin_impersonation"  # Подделка админа
]

# Запрещённые слова и паттерны
FORBIDDEN_WORDS = [
	"спам", "реклама", "купить", "продать", "заработок", "криптовалюта",
	"биткоин", "майнинг", "инвестиции", "лохотрон", "развод"
]

# Паттерны спама
SPAM_PATTERNS = [
	r"https?://[^\s]+",  # Ссылки
	r"\d{10,}",          # Длинные числа (телефоны)
	r"[A-Z]{5,}",        # Капс
	r"(\w)\1{3,}"        # Повторяющиеся символы
]


def track_user_activity(user_id: int, action: str, context: str = "") -> None:
	"""Отслеживает активность пользователя"""
	if user_id not in USER_ACTIVITY:
		USER_ACTIVITY[user_id] = UserActivity(user_id=user_id)
	
	activity = USER_ACTIVITY[user_id]
	current_time = time.time()
	
	# Обновляем статистику
	activity.last_action = action
	activity.last_action_time = current_time
	activity.action_count += 1
	
	# Проверяем на подозрительную активность
	if _is_suspicious_action(user_id, action, context):
		activity.suspicious_actions.append(f"{action}:{context}:{current_time}")
		logger.warning(f"Suspicious activity detected: user={user_id}, action={action}, context={context}")


def _is_suspicious_action(user_id: int, action: str, context: str) -> bool:
	"""Определяет, является ли действие подозрительным"""
	activity = USER_ACTIVITY.get(user_id)
	if not activity:
		return False
	
	current_time = time.time()
	
	# Спам: много действий за короткое время
	if current_time - activity.last_action_time < 1 and activity.action_count > 10:
		return True
	
	# Флуд: повторяющиеся действия
	if len(activity.suspicious_actions) > 5:
		recent_actions = [a for a in activity.suspicious_actions if current_time - float(a.split(":")[-1]) < 60]
		if len(recent_actions) > 10:
			return True
	
	return False


def warn_user(user_id: int, reason: str, moderator_id: int) -> str:
	"""Выносит предупреждение пользователю"""
	if not has_privilege(moderator_id, "warn_users"):
		return "❌ У вас нет прав для вынесения предупреждений"
	
	activity = USER_ACTIVITY.get(user_id)
	if not activity:
		activity = UserActivity(user_id=user_id)
		USER_ACTIVITY[user_id] = activity
	
	current_time = time.time()
	activity.warnings += 1
	activity.last_warning_time = current_time
	
	# Автоматические действия при предупреждениях
	if activity.warnings >= 3:
		# Временный бан на 1 час
		return f"⚠️ Пользователь {user_id} получил 3 предупреждения. Автоматический бан на 1 час."
	elif activity.warnings >= 2:
		return f"⚠️ Пользователь {user_id} получил 2-е предупреждение. Следующее = бан."
	else:
		return f"⚠️ Пользователь {user_id} получил предупреждение: {reason}"


def get_user_activity_report(user_id: int) -> str:
	"""Получить отчёт об активности пользователя"""
	activity = USER_ACTIVITY.get(user_id)
	if not activity:
		return "Активность не найдена"
	
	return (
		f"📊 Активность пользователя {user_id}:\n"
		f"Действий: {activity.action_count}\n"
		f"Последнее: {activity.last_action}\n"
		f"Предупреждений: {activity.warnings}\n"
		f"Подозрительных действий: {len(activity.suspicious_actions)}"
	)


# ---------- Автоматическая модерация ----------
def auto_moderate_message(text: str, user_id: int) -> Tuple[bool, str, str]:
	"""
	Автоматическая модерация сообщения
	Возвращает: (is_violation, action, reason)
	"""
	text_lower = text.lower()
	
	# Проверка на запрещённые слова
	for word in FORBIDDEN_WORDS:
		if word in text_lower:
			return True, "warn", f"Запрещённое слово: {word}"
	
	# Проверка на спам-паттерны
	for pattern in SPAM_PATTERNS:
		if re.search(pattern, text, re.IGNORECASE):
			return True, "delete", f"Спам-паттерн: {pattern}"
	
	# Проверка на капс (больше 70% заглавных букв)
	upper_count = sum(1 for c in text if c.isupper())
	if len(text) > 10 and upper_count / len(text) > 0.7:
		return True, "warn", "Слишком много заглавных букв"
	
	# Проверка на повторяющиеся символы
	if re.search(r"(.)\1{4,}", text):
		return True, "warn", "Повторяющиеся символы"
	
	return False, "", ""


def auto_delete_message(vk, peer_id: int, message_id: int, reason: str) -> None:
	"""Автоматически удаляет сообщение"""
	try:
		vk.method("messages.delete", {
			"peer_id": peer_id,
			"message_id": message_id,
			"delete_for_all": True
		})
		logger.info(f"Auto-deleted message {message_id} in {peer_id}: {reason}")
	except Exception as e:
		logger.error(f"Failed to auto-delete message: {e}")


def auto_warn_user(user_id: int, reason: str) -> str:
	"""Автоматически выносит предупреждение"""
	return warn_user(user_id, f"Автоматически: {reason}", 0)  # 0 = система


# ---------- Система репортов ----------
@dataclass
class UserReport:
	reporter_id: int
	reported_id: int
	reason: str
	timestamp: float
	status: str = "pending"  # pending, reviewed, resolved
	moderator_id: Optional[int] = None
	resolution: str = ""

# База репортов
USER_REPORTS: List[UserReport] = []


def report_user(reporter_id: int, reported_id: int, reason: str) -> str:
	"""Пользователь жалуется на другого пользователя"""
	# Проверяем, не жаловался ли уже
	for report in USER_REPORTS:
		if (report.reporter_id == reporter_id and 
			report.reported_id == reported_id and 
			report.status == "pending"):
			return "❌ Вы уже жаловались на этого пользователя"
	
	# Создаём репорт
	report = UserReport(
		reporter_id=reporter_id,
		reported_id=reported_id,
		reason=reason,
		timestamp=time.time()
	)
	USER_REPORTS.append(report)
	
	# Уведомляем модераторов
	notify_moderators_of_report(report)
	
	return "✅ Жалоба отправлена модераторам"


def notify_moderators_of_report(report: UserReport) -> None:
	"""Уведомляет модераторов о новом репорте"""
	# Находим всех модераторов и админов
	moderators = [uid for uid, role in USER_ROLES.items() 
				 if role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]]
	
	# Отправляем уведомление (в реальности нужно реализовать отправку)
	logger.info(f"New report: {report.reporter_id} -> {report.reported_id}: {report.reason}")
	logger.info(f"Notifying moderators: {moderators}")


def get_pending_reports() -> List[UserReport]:
	"""Получить все необработанные репорты"""
	return [r for r in USER_REPORTS if r.status == "pending"]


def resolve_report(report_index: int, moderator_id: int, resolution: str) -> str:
	"""Модератор обрабатывает репорт"""
	if not has_privilege(moderator_id, "warn_users"):
		return "❌ У вас нет прав для обработки репортов"
	
	if report_index >= len(USER_REPORTS):
		return "❌ Репорт не найден"
	
	report = USER_REPORTS[report_index]
	if report.status != "pending":
		return "❌ Репорт уже обработан"
	
	report.status = "resolved"
	report.moderator_id = moderator_id
	report.resolution = resolution
	
	return f"✅ Репорт обработан: {resolution}"


# ---------- Система временных банов ----------
@dataclass
class UserBan:
	user_id: int
	reason: str
	banned_by: int
	banned_at: float
	expires_at: float
	active: bool = True

# База банов
USER_BANS: Dict[int, UserBan] = {}


def ban_user(user_id: int, duration_hours: int, reason: str, moderator_id: int) -> str:
	"""Банит пользователя на определённое время"""
	if not has_privilege(moderator_id, "ban_users"):
		return "❌ У вас нет прав для бана пользователей"
	
	current_time = time.time()
	expires_at = current_time + (duration_hours * 3600)
	
	ban = UserBan(
		user_id=user_id,
		reason=reason,
		banned_by=moderator_id,
		banned_at=current_time,
		expires_at=expires_at
	)
	
	USER_BANS[user_id] = ban
	
	# Автоматически снимаем бан по истечении времени
	schedule_unban(user_id, expires_at)
	
	return f"🚫 Пользователь {user_id} забанен на {duration_hours} часов. Причина: {reason}"


def unban_user(user_id: int, moderator_id: int) -> str:
	"""Снимает бан с пользователя"""
	if not has_privilege(moderator_id, "ban_users"):
		return "❌ У вас нет прав для снятия бана"
	
	if user_id not in USER_BANS:
		return "❌ Пользователь не забанен"
	
	ban = USER_BANS[user_id]
	ban.active = False
	del USER_BANS[user_id]
	
	return f"✅ Бан с пользователя {user_id} снят"


def is_user_banned(user_id: int) -> Tuple[bool, Optional[UserBan]]:
	"""Проверяет, забанен ли пользователь"""
	if user_id not in USER_BANS:
		return False, None
	
	ban = USER_BANS[user_id]
	current_time = time.time()
	
	# Проверяем, не истёк ли бан
	if current_time > ban.expires_at:
		ban.active = False
		del USER_BANS[user_id]
		return False, None
	
	return ban.active, ban


def schedule_unban(user_id: int, expires_at: float) -> None:
	"""Планирует автоматическое снятие бана"""
	# В реальности здесь должна быть система планировщика
	# Пока просто логируем
	logger.info(f"Ban scheduled for user {user_id}, expires at {expires_at}")


def get_active_bans() -> List[UserBan]:
	"""Получить все активные баны"""
	return [ban for ban in USER_BANS.values() if ban.active]


# ---------- Аналитика безопасности ----------
@dataclass
class SecurityIncident:
	incident_type: str
	user_id: int
	description: str
	timestamp: float
	severity: str = "low"  # low, medium, high, critical
	resolved: bool = False

# База инцидентов безопасности
SECURITY_INCIDENTS: List[SecurityIncident] = []


def log_security_incident(incident_type: str, user_id: int, description: str, severity: str = "medium") -> None:
	"""Логирует инцидент безопасности"""
	incident = SecurityIncident(
		incident_type=incident_type,
		user_id=user_id,
		description=description,
		timestamp=time.time(),
		severity=severity
	)
	SECURITY_INCIDENTS.append(incident)
	
	# Логируем в основной лог
	logger.warning(f"Security incident: {incident_type} by user {user_id}: {description}")


def generate_security_report() -> str:
	"""Генерирует отчёт по безопасности"""
	total_incidents = len(SECURITY_INCIDENTS)
	resolved_incidents = len([i for i in SECURITY_INCIDENTS if i.resolved])
	active_incidents = total_incidents - resolved_incidents
	
	# Статистика по типам инцидентов
	incident_types = {}
	for incident in SECURITY_INCIDENTS:
		incident_types[incident.incident_type] = incident_types.get(incident.incident_type, 0) + 1
	
	# Статистика по серьёзности
	severity_stats = {}
	for incident in SECURITY_INCIDENTS:
		severity_stats[incident.severity] = severity_stats.get(incident.severity, 0) + 1
	
	# Топ подозрительных пользователей
	user_incidents = {}
	for incident in SECURITY_INCIDENTS:
		user_incidents[incident.user_id] = user_incidents.get(incident.user_id, 0) + 1
	
	top_suspicious = sorted(user_incidents.items(), key=lambda x: x[1], reverse=True)[:5]
	
	report = (
		f"🛡️ Отчёт по безопасности:\n\n"
		f"📊 Общая статистика:\n"
		f"• Всего инцидентов: {total_incidents}\n"
		f"• Решено: {resolved_incidents}\n"
		f"• Активно: {active_incidents}\n\n"
		f"🚨 По типам:\n"
	)
	
	for incident_type, count in incident_types.items():
		report += f"• {incident_type}: {count}\n"
	
	report += f"\n⚠️ По серьёзности:\n"
	for severity, count in severity_stats.items():
		report += f"• {severity}: {count}\n"
	
	report += f"\n👤 Топ подозрительных:\n"
	for user_id, count in top_suspicious:
		report += f"• {user_id}: {count} инцидентов\n"
	
	return report


def get_suspicious_patterns_report() -> str:
	"""Анализирует подозрительные паттерны"""
	# Анализ активности пользователей
	suspicious_users = []
	
	for user_id, activity in USER_ACTIVITY.items():
		if activity.warnings >= 2 or len(activity.suspicious_actions) >= 3:
			suspicious_users.append((user_id, activity))
	
	if not suspicious_users:
		return "✅ Подозрительных паттернов не обнаружено"
	
	report = "🔍 Подозрительные паттерны:\n\n"
	
	for user_id, activity in suspicious_users:
		report += f"👤 Пользователь {user_id}:\n"
		report += f"• Предупреждений: {activity.warnings}\n"
		report += f"• Подозрительных действий: {len(activity.suspicious_actions)}\n"
		report += f"• Последнее действие: {activity.last_action}\n\n"
	
	return report


def cleanup_old_incidents(days: int = 30) -> int:
	"""Очищает старые инциденты"""
	current_time = time.time()
	cutoff_time = current_time - (days * 24 * 3600)
	
	old_incidents = [i for i in SECURITY_INCIDENTS if i.timestamp < cutoff_time]
	SECURITY_INCIDENTS[:] = [i for i in SECURITY_INCIDENTS if i.timestamp >= cutoff_time]
	
	return len(old_incidents)

# ---------- Викторина состояния ----------
@dataclass
class QuizState:
	question: str
	answers: List[str]
	active: bool = True
	score: Dict[int, int] = field(default_factory=dict)  # user_id -> points
	attempts: int = 0

# Простейший пул вопросов (можно расширять)
QUIZ_QUESTIONS: List[Tuple[str, List[str]]] = [
	("Столица Франции?", ["париж"]),
	("2+2?", ["4", "четыре"]),
	("Цвет неба днём?", ["синий", "синее", "голубой", "голубое"]),
	("Автор 'Война и мир'?", ["толстой", "лев толстой", "лев николаевич толстой"]),
]

MAX_QUIZ_ATTEMPTS = 6

# peer_id -> QuizState
QUIZZES: Dict[int, QuizState] = {}


# ---------- Кальмар (Squid Game) ----------
@dataclass
class SquidGameSession:
	players: Set[int] = field(default_factory=set)  # user_id
	active_players: Set[int] = field(default_factory=set)  # выжившие
	round_num: int = 0
	game_type: str = ""  # тип мини-игры
	started: bool = False
	waiting_for: Set[int] = field(default_factory=set)  # кто ещё не ответил
	round_data: Dict = field(default_factory=dict)  # данные раунда

# peer_id -> SquidGameSession
SQUID_GAMES: Dict[int, SquidGameSession] = {}

# Мини-игры
SQUID_MINIGAMES = [
	"Сахарные соты",  # угадать число
	"Перетягивание каната",  # команды
	"Мраморные шарики",  # чёт/нечет
	"Стеклянные мосты"  # лево/право
]

# peer_id -> SquidGameSession
SQUID_GAMES: Dict[int, SquidGameSession] = {}


# ---------- Клавиатуры ----------
def build_main_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Мафия", color=VkKeyboardColor.PRIMARY, payload={"action": "start_mafia"})
	keyboard.add_button("Угадай число", color=VkKeyboardColor.SECONDARY, payload={"action": "start_guess"})
	keyboard.add_button("Викторина", color=VkKeyboardColor.SECONDARY, payload={"action": "start_quiz"})
	keyboard.add_button("Кальмар", color=VkKeyboardColor.PRIMARY, payload={"action": "start_squid"})
	keyboard.add_line()
	keyboard.add_button("ИИ‑чат", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_on"})
	keyboard.add_button("Выключить ИИ", color=VkKeyboardColor.NEGATIVE, payload={"action": "ai_off"})
	keyboard.add_line()
	keyboard.add_button("Описание", color=VkKeyboardColor.SECONDARY, payload={"action": "show_help"})
	return keyboard.get_keyboard()


def build_admin_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	
	# AI модели
	keyboard.add_button("🤖 AI модели", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_ai_models"})
	keyboard.add_line()
	
	# Управление пользователями
	keyboard.add_button("👥 Пользователи", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_users"})
	keyboard.add_line()
	
	# Модерация
	keyboard.add_button("🛡️ Модерация", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_moderation"})
	keyboard.add_line()
	
	# Система
	keyboard.add_button("⚙️ Система", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_system"})
	keyboard.add_line()
	
	keyboard.add_button("Закрыть", color=VkKeyboardColor.NEGATIVE, payload={"action": "admin_close"})
	return keyboard.get_keyboard()


def build_ai_models_keyboard() -> str:
	"""Клавиатура для выбора AI моделей"""
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("gpt-5-nano", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_model", "model": "gpt-5-nano"})
	keyboard.add_button("gemini-flash-8b", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_model", "model": "gemini-flash-1.5-8b"})
	keyboard.add_line()
	keyboard.add_button("deepseek-chat", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_set_model", "model": "deepseek-chat"})
	keyboard.add_line()
	keyboard.add_button("deepseek-chat-v3", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_model", "model": "deepseek/deepseek-chat-v3-0324:free"})
	keyboard.add_button("deepseek-r1-0528", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_model", "model": "deepseek/deepseek-r1-0528:free"})
	keyboard.add_line()
	keyboard.add_button("qwen3-coder", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_set_model", "model": "qwen/qwen3-coder:free"})
	keyboard.add_button("deepseek-r1-free", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_set_model", "model": "deepseek/deepseek-r1:free"})
	keyboard.add_line()
	keyboard.add_button("deepseek-r1", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_model", "model": "deepseek-r1"})
	keyboard.add_line()
	keyboard.add_button("Текущая модель", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_current"})
	keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
	return keyboard.get_keyboard()


def build_users_management_keyboard() -> str:
	"""Клавиатура для управления пользователями"""
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("👤 Назначить роль", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_set_role"})
	keyboard.add_button("📊 Активность", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_user_activity"})
	keyboard.add_line()
	keyboard.add_button("⚠️ Предупреждение", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_warn_user"})
	keyboard.add_button("🚫 Бан", color=VkKeyboardColor.NEGATIVE, payload={"action": "admin_ban_user"})
	keyboard.add_line()
	keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
	return keyboard.get_keyboard()


def build_moderation_keyboard() -> str:
	"""Клавиатура для модерации"""
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("🔍 Проверить чат", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_scan_chat"})
	keyboard.add_button("📝 Логи", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_view_logs"})
	keyboard.add_line()
	keyboard.add_button("🧹 Очистить спам", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_clean_spam"})
	keyboard.add_button("📊 Статистика", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_mod_stats"})
	keyboard.add_line()
	keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
	return keyboard.get_keyboard()


def build_dm_info_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Описание", color=VkKeyboardColor.SECONDARY, payload={"action": "show_help"})
	return keyboard.get_keyboard()


def build_privacy_consent_keyboard() -> str:
	"""Клавиатура для принятия политики конфиденциальности"""
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Принять политику конфиденциальности", color=VkKeyboardColor.POSITIVE, payload={"action": "accept_privacy"})
	keyboard.add_line()
	keyboard.add_button("Принять согласие на обработку данных", color=VkKeyboardColor.POSITIVE, payload={"action": "accept_gdpr"})
	keyboard.add_line()
	keyboard.add_button("Отказаться", color=VkKeyboardColor.NEGATIVE, payload={"action": "decline_privacy"})
	return keyboard.get_keyboard()


def build_mafia_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Присоединиться", color=VkKeyboardColor.PRIMARY, payload={"action": "maf_join"})
	keyboard.add_button("Выйти", color=VkKeyboardColor.SECONDARY, payload={"action": "maf_leave"})
	keyboard.add_line()
	keyboard.add_button("Старт", color=VkKeyboardColor.POSITIVE, payload={"action": "maf_begin"})
	keyboard.add_button("Отмена", color=VkKeyboardColor.NEGATIVE, payload={"action": "maf_cancel"})
	return keyboard.get_keyboard()


def build_guess_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Присоединиться", color=VkKeyboardColor.PRIMARY, payload={"action": "g_join"})
	keyboard.add_button("Выйти", color=VkKeyboardColor.SECONDARY, payload={"action": "g_leave"})
	keyboard.add_line()
	keyboard.add_button("Старт (2 игрока)", color=VkKeyboardColor.POSITIVE, payload={"action": "g_begin"})
	keyboard.add_button("Отмена", color=VkKeyboardColor.NEGATIVE, payload={"action": "g_cancel"})
	return keyboard.get_keyboard()


def build_quiz_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Начать вопрос", color=VkKeyboardColor.POSITIVE, payload={"action": "quiz_begin"})
	keyboard.add_button("Завершить", color=VkKeyboardColor.NEGATIVE, payload={"action": "quiz_end"})
	keyboard.add_line()
	keyboard.add_button("Новый вопрос", color=VkKeyboardColor.PRIMARY, payload={"action": "quiz_next"})
	return keyboard.get_keyboard()


def build_squid_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Присоединиться", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_join"})
	keyboard.add_button("Выйти", color=VkKeyboardColor.SECONDARY, payload={"action": "squid_leave"})
	keyboard.add_line()
	keyboard.add_button("Старт", color=VkKeyboardColor.POSITIVE, payload={"action": "squid_begin"})
	keyboard.add_button("Отмена", color=VkKeyboardColor.NEGATIVE, payload={"action": "squid_cancel"})
	return keyboard.get_keyboard()


def build_squid_game_keyboard(game_type: str) -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	
	if game_type == "Сахарные соты":
		keyboard.add_button("1", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "1"})
		keyboard.add_button("2", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "2"})
		keyboard.add_button("3", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "3"})
		keyboard.add_line()
		keyboard.add_button("4", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "4"})
		keyboard.add_button("5", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "5"})
		keyboard.add_button("6", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "6"})
		keyboard.add_line()
		keyboard.add_button("7", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "7"})
		keyboard.add_button("8", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "8"})
		keyboard.add_button("9", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "9"})
		keyboard.add_line()
		keyboard.add_button("10", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "number": "10"})
	elif game_type == "Мраморные шарики":
		keyboard.add_button("Чёт", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "parity": "even"})
		keyboard.add_line()
		keyboard.add_button("Нечет", color=VkKeyboardColor.SECONDARY, payload={"action": "squid_guess", "parity": "odd"})
	elif game_type == "Стеклянные мосты":
		keyboard.add_button("Лево", color=VkKeyboardColor.PRIMARY, payload={"action": "squid_guess", "direction": "left"})
		keyboard.add_line()
		keyboard.add_button("Право", color=VkKeyboardColor.SECONDARY, payload={"action": "squid_guess", "direction": "right"})
	
	return keyboard.get_keyboard()


def build_empty_keyboard() -> str:
	return json.dumps({"one_time": True, "buttons": []}, ensure_ascii=False)


# ---------- Вспомогательные ----------
def send_message(vk, peer_id: int, text: str, keyboard: Optional[str] = None) -> None:
	params: dict[str, object] = {
		"peer_id": peer_id,
		"random_id": 0,
		"message": text,
	}
	if keyboard is not None:
		params["keyboard"] = keyboard
	vk.messages.send(**params)


def mention(user_id: int, name: str = "игрок") -> str:
	return f"[id{user_id}|{name}]"


def format_players(vk, user_ids: Set[int]) -> str:
	if not user_ids:
		return "(никого)"
	try:
		users = vk.users.get(user_ids=",".join(str(u) for u in user_ids), name_case="Nom")
		parts = [mention(u["id"], f"{u['first_name']} {u['last_name']}") for u in users]
	except Exception:
		parts = [mention(u) for u in user_ids]
	return ", ".join(parts)


def format_players_list(vk, ids_list: List[int]) -> str:
	return format_players(vk, set(ids_list))


def clamp_text(text: str, max_chars: int = MAX_AI_CHARS) -> str:
	t = (text or "").strip()
	if len(t) <= max_chars:
		return t
	cut = t.rfind(" ", 0, max_chars)
	if cut < max_chars // 2:
		cut = max_chars
	return t[:cut].rstrip() + "…"


def get_model_candidates() -> List[str]:
	models_csv = os.getenv("OPENROUTER_MODELS", "").strip()
	if models_csv:
		return [m.strip() for m in models_csv.split(",") if m.strip()]
	model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free").strip()
	return [model]


def get_aitunnel_model_candidates() -> List[str]:
	# Приоритет ручного выбора модели админом
	if RUNTIME_AITUNNEL_MODEL:
		return [RUNTIME_AITUNNEL_MODEL]
	models_csv = AITUNNEL_MODELS
	if models_csv:
		return [m.strip() for m in models_csv.split(",") if m.strip()]
	return [AITUNNEL_MODEL]


# ---------- DeepSeek через OpenRouter (с авто‑переключением моделей) ----------
def deepseek_reply(api_key: str, system_prompt: str, history: List[Dict[str, str]], user_text: str) -> str:
	if not api_key:
		return "ИИ не настроен. Добавьте DEEPSEEK_API_KEY в .env."
	messages = [{"role": "system", "content": system_prompt}]
	messages.extend(history[-MAX_HISTORY_MESSAGES:])
	messages.append({"role": "user", "content": user_text})

	logger = logging.getLogger("vk-mafia-bot")
	last_err = "unknown"
	
	# Используем runtime модель или fallback на список
	models_to_try = [RUNTIME_OPENROUTER_MODEL] if RUNTIME_OPENROUTER_MODEL else get_model_candidates()
	
	for model in models_to_try:
		for attempt in range(2):  # до 2 попыток на модель
			try:
				resp = requests.post(
					DEEPSEEK_API_URL,
					headers={
						"Authorization": f"Bearer {api_key}",
						"Content-Type": "application/json",
						"HTTP-Referer": AI_REFERER,
						"X-Title": AI_TITLE,
					},
					json={
						"model": model,
						"messages": messages,
						"temperature": 0.6,
						"max_tokens": 80,
					},
					timeout=60,  # Увеличиваем timeout для стабильности
				)
				resp.raise_for_status()
				data = resp.json()
				if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
					last_err = "invalid response (no choices)"
					break
				msg = data["choices"][0].get("message", {})
				text = (msg.get("content") or "").strip()
				if not text:
					last_err = "empty content"
					break
				usage = data.get("usage") or {}
				logger.info(f"AI OK model={model} attempt={attempt+1} usage={usage}")
				return text
			except requests.HTTPError as e:
				code = e.response.status_code if e.response else None
				last_err = f"HTTP {code}"
				# На 429/5xx пробуем ещё раз и/или другую модель
				if code in (429, 500, 502, 503, 504):
					time.sleep(1 + attempt * 2)
					continue
				break
			except Exception as e:
				last_err = str(e)
				break
		logger.info(f"AI fallback: {last_err} on model={model}")
	
	# Если все модели OpenRouter недоступны, пробуем AITunnel как fallback
	if aitunnel_key and AITUNNEL_API_URL:
		logger.info("Trying AITunnel as fallback...")
		return aitunnel_reply(aitunnel_key, system_prompt, history, user_text)
	
	return f"ИИ временно недоступен ({last_err}). Попробуйте позже."


def aitunnel_reply(api_key: str, system_prompt: str, history: List[Dict[str, str]], user_text: str) -> str:
	if not api_key:
		return "ИИ не настроен. Добавьте AITUNNEL_API_KEY в .env."
	if not AITUNNEL_API_URL:
		return "ИИ не настроен. Добавьте AITUNNEL_API_URL в .env."

	messages = [{"role": "system", "content": system_prompt}]
	messages.extend(history[-MAX_HISTORY_MESSAGES:])
	messages.append({"role": "user", "content": user_text})

	logger = logging.getLogger("vk-mafia-bot")
	last_err = "unknown"
	
		# Умный выбор модели: сначала runtime, потом по стоимости
	models_to_try = []
	if RUNTIME_AITUNNEL_MODEL:
		models_to_try.append(RUNTIME_AITUNNEL_MODEL)
	
	# Добавляем остальные модели по стоимости (от дешёвых к дорогим)
	fallback_models = get_aitunnel_model_candidates()
	for model in fallback_models:
		if model not in models_to_try:
			models_to_try.append(model)
	
	for model in models_to_try:
		for attempt in range(2):
			try:
				# Формируем JSON данные в зависимости от модели
				json_data = {
					"model": model,
					"messages": messages,
					"temperature": 2.0,  # Как на сайте AITunnel
					"max_tokens": 5000,  # Как на сайте AITunnel
				}
				
				# Для gpt-5-nano используем оптимизированные параметры
				if model == "gpt-5-nano":
					json_data["max_tokens"] = 200  # Ограничиваем для экономии
					json_data["reasoning_tokens"] = 50  # Ограничиваем reasoning
					json_data["reasoning_depth"] = "low"
				else:
					# Для других моделей используем стандартные параметры
					json_data["max_tokens"] = 5000
					json_data["reasoning"] = {"exclude": True}
				
				resp = requests.post(
					AITUNNEL_API_URL,
					headers={
						"Authorization": f"Bearer {api_key}",
						"Content-Type": "application/json",
					},
					json=json_data,
					timeout=60,  # Увеличиваем timeout для стабильности
				)
				resp.raise_for_status()
				data = resp.json()
				if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
					last_err = "invalid response (no choices)"
					break
				msg = data["choices"][0].get("message", {})
				text = (msg.get("content") or "").strip()
				if not text:
					last_err = "empty content"
					# при пустом ответе пробуем ещё раз (до 2 попыток)
					continue
				usage = data.get("usage") or {}
				logger.info(f"AI OK (AITunnel) model={model} attempt={attempt+1} usage={usage}")
				return text
			except requests.HTTPError as e:
				code = e.response.status_code if e.response else None
				last_err = f"HTTP {code}"
				if code in (429, 500, 502, 503, 504):
					time.sleep(1 + attempt * 2)
					continue
				break
			except Exception as e:
				last_err = str(e)
				break
		logger.info(f"AI fallback (AITunnel): {last_err} on model={model}")
	# дружелюбный ответ вместо технической ошибки
	return "Хм, не расслышала. Скажи иначе, пожалуйста."


def generate_ai_reply(user_text: str, system_prompt: str, history: List[Dict[str, str]],
					  openrouter_key: str, aitunnel_key: str, provider: str) -> str:
	# Используем runtime переменные для переключения в админке
	prov = (RUNTIME_AI_PROVIDER or provider or "AUTO").upper()
	is_aitunnel_ready = bool(aitunnel_key and AITUNNEL_API_URL)
	is_openrouter_ready = bool(openrouter_key)

	if prov == "AITUNNEL":
		return aitunnel_reply(aitunnel_key, system_prompt, history, user_text)
	if prov == "OPENROUTER":
		return deepseek_reply(openrouter_key, system_prompt, history, user_text)

	# AUTO
	if is_aitunnel_ready:
		reply = aitunnel_reply(aitunnel_key, system_prompt, history, user_text)
		if not reply.startswith("ИИ временно недоступен"):
			return reply
	if is_openrouter_ready:
		return deepseek_reply(openrouter_key, system_prompt, history, user_text)
	return "ИИ не настроен. Добавьте AITUNNEL_API_KEY/AITUNNEL_API_URL или DEEPSEEK_API_KEY в .env."


# ---------- Команды ----------
def handle_start(vk, peer_id: int) -> None:
	send_message(
		vk,
		peer_id,
		"Привет! Выбери игру: «Мафия», «Угадай число», «Викторина», либо включи «ИИ‑чат».",
		keyboard=build_main_keyboard(),
	)


# ----- Мафия -----
def handle_start_mafia(vk, peer_id: int, user_id: int) -> None:
	if peer_id in LOBBIES:
		lobby = LOBBIES[peer_id]
		text = (
			"Лобби уже создано. Участники: "
			+ format_players(vk, lobby.player_ids)
			+ "\nНажмите «Присоединиться», чтобы войти."
		)
		send_message(vk, peer_id, text, keyboard=build_mafia_keyboard())
		return
	lobby = Lobby(leader_id=user_id)
	lobby.add_player(user_id)
	LOBBIES[peer_id] = lobby
	text = (
		f"Лобби «Мафия» создано лидером {mention(user_id)}.\n"
		f"Игроки: {format_players(vk, lobby.player_ids)}\n"
		"Нажмите «Присоединиться», чтобы войти. Лидер может нажать «Старт»."
	)
	send_message(vk, peer_id, text, keyboard=build_mafia_keyboard())


def handle_mafia_join(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби ещё не создано. Нажмите «Мафия».", keyboard=build_main_keyboard())
		return
	if user_id in lobby.player_ids:
		send_message(vk, peer_id, f"{mention(user_id)} уже в лобби.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_mafia_keyboard())
		return
	lobby.add_player(user_id)
	send_message(vk, peer_id, f"{mention(user_id)} присоединился.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_mafia_keyboard())


def handle_mafia_leave(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби ещё не создано.")
		return
	lobby.remove_player(user_id)
	if not lobby.player_ids:
		LOBBIES.pop(peer_id, None)
		send_message(vk, peer_id, "Лобби закрыто: игроков не осталось.", keyboard=build_main_keyboard())
		return
	send_message(vk, peer_id, f"{mention(user_id)} вышел.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_mafia_keyboard())


def handle_mafia_cancel(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби уже отсутствует.")
		return
	if user_id != lobby.leader_id:
		send_message(vk, peer_id, "Отменить может только лидер лобби.")
		return
	LOBBIES.pop(peer_id, None)
	send_message(vk, peer_id, "Лобби отменено лидером.", keyboard=build_main_keyboard())


def handle_mafia_begin(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби не найдено.")
		return
	if user_id != lobby.leader_id:
		send_message(vk, peer_id, "Запускать игру может только лидер лобби.")
		return
	min_players = 4
	if len(lobby.player_ids) < min_players:
		send_message(vk, peer_id, f"Недостаточно игроков для старта. Нужно минимум {min_players}. Сейчас: {len(lobby.player_ids)}.")
		return
	send_message(vk, peer_id, "Мафия: демо-старт (логика ролей будет добавлена).")
	LOBBIES.pop(peer_id, None)


# ----- Угадай число -----
def handle_start_guess(vk, peer_id: int, user_id: int) -> None:
	if peer_id in GUESS_SESSIONS:
		sess = GUESS_SESSIONS[peer_id]
		text = (
			"Лобби «Угадай число». Участники: "
			+ format_players(vk, sess.joined_ids)
			+ "\nНужно ровно 2 игрока. Нажмите «Присоединиться»."
		)
		send_message(vk, peer_id, text, keyboard=build_guess_keyboard())
		return
	sess = GuessNumberSession(creator_id=user_id)
	sess.add_player(user_id)
	GUESS_SESSIONS[peer_id] = sess
	text = (
		f"Создано лобби «Угадай число» создателем {mention(user_id)}.\n"
		f"Игроки: {format_players(vk, sess.joined_ids)}\n"
		"Требуется 2 игрока. Присоединяйтесь!"
	)
	send_message(vk, peer_id, text, keyboard=build_guess_keyboard())


def handle_guess_join(vk, peer_id: int, user_id: int) -> None:
	sess = GUESS_SESSIONS.get(peer_id)
	if not sess:
		send_message(vk, peer_id, "Лобби ещё не создано. Нажмите «Угадай число».", keyboard=build_main_keyboard())
		return
	if user_id in sess.joined_ids:
		send_message(vk, peer_id, f"{mention(user_id)} уже в лобби.\nИгроки: {format_players(vk, sess.joined_ids)}", keyboard=build_guess_keyboard())
		return
	if len(sess.joined_ids) >= 2:
		send_message(vk, peer_id, "В этой игре максимум 2 игрока.", keyboard=build_guess_keyboard())
		return
	sess.add_player(user_id)
	send_message(vk, peer_id, f"{mention(user_id)} присоединился.\nИгроки: {format_players(vk, sess.joined_ids)}", keyboard=build_guess_keyboard())


def handle_guess_leave(vk, peer_id: int, user_id: int) -> None:
	sess = GUESS_SESSIONS.get(peer_id)
	if not sess:
		send_message(vk, peer_id, "Лобби ещё не создано.")
		return
	sess.remove_player(user_id)
	if not sess.joined_ids:
		GUESS_SESSIONS.pop(peer_id, None)
		send_message(vk, peer_id, "Лобби закрыто: игроков не осталось.", keyboard=build_main_keyboard())
		return
	send_message(vk, peer_id, f"{mention(user_id)} вышел.\nИгроки: {format_players(vk, sess.joined_ids)}", keyboard=build_guess_keyboard())


def handle_guess_cancel(vk, peer_id: int, user_id: int) -> None:
	sess = GUESS_SESSIONS.get(peer_id)
	if not sess:
		send_message(vk, peer_id, "Лобби уже отсутствует.")
		return
	if user_id != sess.creator_id:
		send_message(vk, peer_id, "Отменить может только создатель лобби.")
		return
	GUESS_SESSIONS.pop(peer_id, None)
	send_message(vk, peer_id, "Лобби «Угадай число» отменено.", keyboard=build_main_keyboard())


def handle_guess_begin(vk, peer_id: int, user_id: int) -> None:
	sess = GUESS_SESSIONS.get(peer_id)
	if not sess:
		send_message(vk, peer_id, "Лобби не найдено.")
		return
	if user_id != sess.creator_id:
		send_message(vk, peer_id, "Стартовать может только создатель лобби.")
		return
	if not sess.can_start():
		send_message(vk, peer_id, "Нужно ровно 2 игрока для старта.", keyboard=build_guess_keyboard())
		return
	sess.start()
	msg = (
		f"Игра началась! Я загадал число от {sess.min_value} до {sess.max_value}.\n"
		f"Игроки: {format_players_list(vk, sess.player_order)}\n"
		f"Ходит {mention(sess.current_player_id())}. Отправь число."
	)
	send_message(vk, peer_id, msg)


def handle_guess_attempt(vk, peer_id: int, user_id: int, guess_value: int) -> None:
	sess = GUESS_SESSIONS.get(peer_id)
	if not sess or not sess.started:
		return
	if user_id not in sess.player_order:
		return
	current = sess.current_player_id()
	if user_id != current:
		send_message(vk, peer_id, f"Сейчас ходит {mention(current)}.")
		return
	sess.attempts[user_id] = sess.attempts.get(user_id, 0) + 1

	if guess_value == sess.secret_number:
		msg = (
			f"{mention(user_id)} угадал число {sess.secret_number}! 🎉\n"
			f"Попытки: {', '.join(f'{mention(pid)}: {sess.attempts.get(pid,0)}' for pid in sess.player_order)}"
		)
		send_message(vk, peer_id, msg, keyboard=build_main_keyboard())
		# стат для угадай-число
		increment_stat(vk, user_id, "guess_wins", 1)
		GUESS_SESSIONS.pop(peer_id, None)
		return

	if guess_value < sess.secret_number:
		send_message(vk, peer_id, f"Мало. Ходит {mention(sess.other_player_id())}.")
	else:
		send_message(vk, peer_id, f"Много. Ходит {mention(sess.other_player_id())}.")
	sess.switch_turn()


# ----- ИИ‑чат -----
def handle_ai_on(vk, peer_id: int) -> None:
	AI_ACTIVE_CHATS.add(peer_id)
	send_message(vk, peer_id, "ИИ‑чат включён для этой беседы. Пишите сообщения — я отвечу. Чтобы выключить, нажмите «Выключить ИИ».", keyboard=build_main_keyboard())

def handle_ai_off(vk, peer_id: int) -> None:
	AI_ACTIVE_CHATS.discard(peer_id)
	send_message(vk, peer_id, "ИИ‑чат выключен для этой беседы.", keyboard=build_main_keyboard())

def handle_ai_message(vk, peer_id: int, user_text: str,
					  openrouter_key: str, aitunnel_key: str, provider: str,
					  system_prompt: str) -> None:
	add_history(peer_id, "user", user_text)
	reply = generate_ai_reply(user_text, system_prompt, AI_HISTORY.get(peer_id, []),
							  openrouter_key, aitunnel_key, provider)
	reply = clamp_text(reply, MAX_AI_CHARS)
	add_history(peer_id, "assistant", reply)
	send_message(vk, peer_id, reply)


# ----- Админ: выбор модели AITunnel -----
def handle_admin_panel(vk, peer_id: int, user_id: int) -> None:
	if user_id not in ADMIN_USER_IDS:
		return
	send_message(vk, peer_id, "Админ‑панель: выбери модель для AITunnel.", keyboard=build_admin_keyboard())


def handle_admin_set_model(vk, peer_id: int, user_id: int, model_name: str) -> None:
	global RUNTIME_AITUNNEL_MODEL, RUNTIME_AI_PROVIDER, RUNTIME_OPENROUTER_MODEL
	if user_id not in ADMIN_USER_IDS:
		return
	model = (model_name or "").strip()
	if not model:
		send_message(vk, peer_id, "Модель не указана.")
		return
	
	# Определяем провайдера по названию модели
	if model.startswith(("deepseek/", "qwen/")) or model == "deepseek-r1":
		# OpenRouter модели: deepseek/deepseek-chat-v3-0324:free, qwen/qwen3-coder:free, deepseek-r1
		RUNTIME_AI_PROVIDER = "OPENROUTER"
		RUNTIME_OPENROUTER_MODEL = model
		send_message(vk, peer_id, f"OK. Переключился на OpenRouter, модель: {model}", keyboard=build_admin_keyboard())
	else:
		# AITunnel модели: gpt-5-nano, gemini-flash-1.5-8b, deepseek-chat
		RUNTIME_AI_PROVIDER = "AITUNNEL"
		RUNTIME_AITUNNEL_MODEL = model
		send_message(vk, peer_id, f"OK. Переключился на AITunnel, модель: {model}", keyboard=build_admin_keyboard())


def handle_admin_current(vk, peer_id: int, user_id: int) -> None:
	if user_id not in ADMIN_USER_IDS:
		return
	
	if RUNTIME_AI_PROVIDER == "OPENROUTER":
		# Показываем текущую модель OpenRouter
		current = RUNTIME_OPENROUTER_MODEL or DEEPSEEK_MODEL
		send_message(vk, peer_id, f"Текущий провайдер: OpenRouter\nМодель: {current}", keyboard=build_admin_keyboard())
	else:
		# Показываем текущую модель AITunnel
		current = RUNTIME_AITUNNEL_MODEL or AITUNNEL_MODEL
		send_message(vk, peer_id, f"Текущий провайдер: AITunnel\nМодель: {current}", keyboard=build_admin_keyboard())


# ----- Викторина -----
def handle_start_quiz(vk, peer_id: int) -> None:
	QUIZZES.pop(peer_id, None)
	send_message(vk, peer_id, "Викторина! Нажмите 'Начать вопрос' для первого вопроса.", keyboard=build_quiz_keyboard())


def handle_quiz_begin(vk, peer_id: int) -> None:
	# Берём случайный вопрос
	if not QUIZ_QUESTIONS:
		send_message(vk, peer_id, "Нет доступных вопросов.")
		return
	q, answers = random.choice(QUIZ_QUESTIONS)
	answers_norm = [a.lower().strip() for a in answers]
	QUIZZES[peer_id] = QuizState(question=q, answers=answers_norm)
	send_message(vk, peer_id, f"Вопрос: {q}\nОтвет напишите текстом.")


def handle_quiz_answer(vk, peer_id: int, user_id: int, text: str) -> None:
	state = QUIZZES.get(peer_id)
	if not state or not state.active:
		return
	answer_raw = (text or "").strip()
	if not answer_raw:
		return

	# спец-команды
	answer_low = answer_raw.lower()
	if answer_low in {"подсказка", "hint"}:
		hint = state.answer[:1] + "*" * max(0, len(state.answer) - 1)
		send_message(vk, peer_id, f"Подсказка: {hint}")
		return
	if answer_low in {"сдаюсь", "pass"}:
		send_message(vk, peer_id, f"Ответ: {state.answer}", keyboard=build_quiz_keyboard())
		QUIZZES.pop(peer_id, None)
		return

	# нормализация: нижний регистр, ё->е, убрать пунктуацию
	def normalize(s: str) -> str:
		res = s.lower().replace("ё", "е")
		allowed = []
		for ch in res:
			if ch.isalnum() or ch.isspace():
				allowed.append(ch)
		return " ".join("".join(allowed).split())

	user_norm = normalize(answer_raw)
	gold_norms = [normalize(a) for a in state.answers]
	user_words = set(user_norm.split())

	# Совпадение по слову, подстроке или фаззи-метч
	def is_match(g: str, u: str) -> bool:
		if g in u or g in user_words:
			return True
		score = difflib.SequenceMatcher(None, g, u).ratio()
		return score >= 0.8

	correct = any(is_match(g, user_norm) for g in gold_norms)

	if correct:
		state.score[user_id] = state.score.get(user_id, 0) + 1
		send_message(vk, peer_id, f"Верно! +1 очко {mention(user_id)}.\nСчёт: " + ", ".join(f"{mention(uid)}: {pts}" for uid, pts in state.score.items()), keyboard=build_quiz_keyboard())
		# стат для викторины
		increment_stat(vk, user_id, "quiz_points", 1)
		QUIZZES.pop(peer_id, None)
	else:
		state.attempts += 1
		if state.attempts % 3 == 0:
			g = gold_norms[0] if gold_norms else ""
			hint = g[:2] + "*" * max(0, len(g) - 2)
			send_message(vk, peer_id, f"Неверно. Подсказка: {hint}")
		elif state.attempts >= MAX_QUIZ_ATTEMPTS:
			correct_text = ", ".join(state.answers)
			send_message(vk, peer_id, f"Правильный ответ: {correct_text}", keyboard=build_quiz_keyboard())
			QUIZZES.pop(peer_id, None)
		else:
			send_message(vk, peer_id, "Неверно. Попробуйте ещё!")


def handle_quiz_end(vk, peer_id: int) -> None:
	state = QUIZZES.pop(peer_id, None)
	if not state:
		send_message(vk, peer_id, "Викторина уже завершена.", keyboard=build_main_keyboard())
		return
	send_message(vk, peer_id, "Викторина завершена.", keyboard=build_main_keyboard())


# ---------- Кальмар (Squid Game) ----------
def handle_start_squid(vk, peer_id: int) -> None:
	SQUID_GAMES.pop(peer_id, None)
	send_message(vk, peer_id, "🎮 Игра в Кальмара! Присоединяйтесь к игре.", keyboard=build_squid_keyboard())


def handle_squid_join(vk, peer_id: int, user_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game:
		game = SquidGameSession()
		SQUID_GAMES[peer_id] = game
	
	if user_id in game.players:
		send_message(vk, peer_id, f"{mention(user_id)} уже в игре!")
		return
	
	game.players.add(user_id)
	game.active_players.add(user_id)
	
	players_list = ", ".join(mention(uid) for uid in game.players)
	send_message(vk, peer_id, f"{mention(user_id)} присоединился! Игроки: {players_list}", keyboard=build_squid_keyboard())


def handle_squid_leave(vk, peer_id: int, user_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game:
		return
	
	if user_id in game.players:
		game.players.discard(user_id)
		game.active_players.discard(user_id)
		
		if not game.players:
			SQUID_GAMES.pop(peer_id, None)
			send_message(vk, peer_id, "Все игроки вышли. Игра отменена.", keyboard=build_main_keyboard())
		else:
			players_list = ", ".join(mention(uid) for uid in game.players)
			send_message(vk, peer_id, f"{mention(user_id)} вышел! Игроки: {players_list}", keyboard=build_squid_keyboard())


def handle_squid_begin(vk, peer_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game or len(game.players) < 2:
		send_message(vk, peer_id, "Нужно минимум 2 игрока для начала игры!")
		return
	
	game.started = True
	game.round_num = 1
	game.active_players = game.players.copy()
	start_squid_round(vk, peer_id)


def start_squid_round(vk, peer_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game or not game.started:
		return
	
	if len(game.active_players) <= 1:
		end_squid_game(vk, peer_id)
		return
	
	# Выбираем случайную мини-игру
	game.game_type = random.choice(SQUID_MINIGAMES)
	game.waiting_for = game.active_players.copy()
	
	round_msg = f"🎮 Раунд {game.round_num}: {game.game_type}\n"
	round_msg += f"Игроки: {', '.join(mention(uid) for uid in game.active_players)}\n"
	
	if game.game_type == "Сахарные соты":
		round_msg += "Угадайте число от 1 до 10. Кто ближе к загаданному - выживает!"
		game.round_data = {"target": random.randint(1, 10)}
	elif game.game_type == "Перетягивание каната":
		players_list = list(game.active_players)
		random.shuffle(players_list)
		mid = len(players_list) // 2
		team1 = set(players_list[:mid])
		team2 = set(players_list[mid:])
		game.round_data = {"team1": team1, "team2": team2}
		round_msg += f"Команда 1: {', '.join(mention(uid) for uid in team1)}\n"
		round_msg += f"Команда 2: {', '.join(mention(uid) for uid in team2)}\n"
		round_msg += "Проигравшая команда выбывает!"
	elif game.game_type == "Мраморные шарики":
		round_msg += "Угадайте чёт или нечет. Неправильные выбывают!"
		game.round_data = {"target": random.choice(["even", "odd"])}
	elif game.game_type == "Стеклянные мосты":
		round_msg += "Выберите лево или право. Неправильный выбор = выбывание!"
		game.round_data = {"target": random.choice(["left", "right"])}
	
	send_message(vk, peer_id, round_msg, keyboard=build_squid_game_keyboard(game.game_type))


def handle_squid_guess(vk, peer_id: int, user_id: int, payload: Dict) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game or not game.started or user_id not in game.waiting_for:
		return
	
	game.waiting_for.discard(user_id)
	
	if game.game_type == "Сахарные соты":
		guess = int(payload.get("number", "1"))
		target = game.round_data.get("target", 5)
		distance = abs(guess - target)
		game.round_data.setdefault("guesses", {})[user_id] = distance
		
		if not game.waiting_for:  # все ответили
			end_squid_round(vk, peer_id)
	
	elif game.game_type == "Мраморные шарики":
		guess = payload.get("parity", "even")
		target = game.round_data.get("target", "even")
		
		if guess == target:
			send_message(vk, peer_id, f"✅ {mention(user_id)} выжил!")
		else:
			game.active_players.discard(user_id)
			send_message(vk, peer_id, f"❌ {mention(user_id)} выбыл!")
		
		if not game.waiting_for:  # все ответили
			end_squid_round(vk, peer_id)
	
	elif game.game_type == "Стеклянные мосты":
		guess = payload.get("direction", "left")
		target = game.round_data.get("target", "left")
		
		if guess == target:
			send_message(vk, peer_id, f"✅ {mention(user_id)} выжил!")
		else:
			game.active_players.discard(user_id)
			send_message(vk, peer_id, f"❌ {mention(user_id)} выбыл!")
		
		if not game.waiting_for:  # все ответили
			end_squid_round(vk, peer_id)


def end_squid_round(vk, peer_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game or not game.started:
		return
	
	if game.game_type == "Сахарные соты":
		guesses = game.round_data.get("guesses", {})
		if guesses:
			best_player = min(guesses.items(), key=lambda x: x[1])[0]
			losers = set(guesses.keys()) - {best_player}
			
			for loser in losers:
				game.active_players.discard(loser)
				send_message(vk, peer_id, f"❌ {mention(loser)} выбыл!")
			
			send_message(vk, peer_id, f"✅ {mention(best_player)} выжил! Загаданное число: {game.round_data.get('target')}")
	
	elif game.game_type == "Перетягивание каната":
		# Случайно выбираем проигравшую команду
		loser_team = random.choice([game.round_data["team1"], game.round_data["team2"]])
		for loser in loser_team:
			game.active_players.discard(loser)
			send_message(vk, peer_id, f"❌ {mention(loser)} выбыл!")
		
		winner_team = game.round_data["team1"] if loser_team == game.round_data["team2"] else game.round_data["team2"]
		survivors = ", ".join(mention(uid) for uid in winner_team)
		send_message(vk, peer_id, f"✅ Выжили: {survivors}")
	
	# Проверяем, нужно ли продолжать
	if len(game.active_players) <= 1:
		end_squid_game(vk, peer_id)
	else:
		game.round_num += 1
		time.sleep(3)  # пауза между раундами
		start_squid_round(vk, peer_id)


def end_squid_game(vk, peer_id: int) -> None:
	game = SQUID_GAMES.get(peer_id)
	if not game:
		return
	
	if len(game.active_players) == 1:
		winner = list(game.active_players)[0]
		send_message(vk, peer_id, f"🏆 Победитель: {mention(winner)}!", keyboard=build_main_keyboard())
		increment_stat(vk, winner, "squid_wins", 1)
	else:
		send_message(vk, peer_id, "Игра завершена без победителя.", keyboard=build_main_keyboard())
	
	SQUID_GAMES.pop(peer_id, None)


def handle_squid_cancel(vk, peer_id: int) -> None:
	SQUID_GAMES.pop(peer_id, None)
	send_message(vk, peer_id, "Игра в Кальмара отменена.", keyboard=build_main_keyboard())


# ---------- ИИ‑чат утилиты ----------
def ai_enabled_for_peer(peer_id: int, is_dm: bool) -> bool:
	# ИИ включается только вручную и для ЛС, и для бесед
	return peer_id in AI_ACTIVE_CHATS


def add_history(peer_id: int, role: str, content: str) -> None:
	h = AI_HISTORY.setdefault(peer_id, [])
	h.append({"role": role, "content": content})
	if len(h) > MAX_HISTORY_MESSAGES:
		del h[: len(h) - MAX_HISTORY_MESSAGES]


# ---------- Основной цикл ----------
def main() -> None:
	configure_logging()
	load_dotenv()
	load_profiles()
	prevent_sleep()
	logger = logging.getLogger("vk-mafia-bot")
	logger.info(f"OpenRouter endpoint: {DEEPSEEK_API_URL}")
	logger.info(f"AITunnel endpoint: {AITUNNEL_API_URL or '(not set)'}")
	try:
		token, group_id, openrouter_key, system_prompt, aitunnel_key, ai_provider = load_config()
	except Exception as exc:
		logger.error("Config error: %s", exc)
		sys.exit(1)

	vk_session = vk_api.VkApi(token=token)
	vk = vk_session.get_api()
	longpoll = VkBotLongPoll(vk_session, group_id)

	logger.info(f"AI provider: {ai_provider}")
	logger.info(f"OpenRouter models: {get_model_candidates()}")
	logger.info(f"AITunnel models: {get_aitunnel_model_candidates()}")
	logger.info("Bot started. Listening for events...")

	for event in longpoll.listen():
		if event.type != VkBotEventType.MESSAGE_NEW:
			continue

		message = event.message
		peer_id = message.peer_id
		is_dm = peer_id < 2000000000  # личка
		text_raw = (message.text or "").strip()
		text = text_raw.lower()
		user_id = message.from_id

		payload = {}
		if message.payload:
			try:
				payload = json.loads(message.payload)
			except Exception:
				payload = {}

		# Команды
		if text == "/start":
			send_message(vk, peer_id, "Привет! Выбери игру или включи «ИИ‑чат».", keyboard=build_main_keyboard())
			continue

		# Текстовые синонимы для кнопок
		if text in {"мафия"}:
			handle_start_mafia(vk, peer_id, user_id)
			continue
		if text in {"угадай число", "угадай", "число"}:
			handle_start_guess(vk, peer_id, user_id)
			continue
		if text in {"викторина"}:
			handle_start_quiz(vk, peer_id)
			continue
		if text in {"кальмар", "squid", "squid game"}:
			handle_start_squid(vk, peer_id)
			continue
		if text in {"/me", "профиль", "профиль мой"}:
			# Проверяем согласия перед показом профиля
			privacy_accepted, gdpr_consent = check_user_consents(user_id)
			if not privacy_accepted or not gdpr_consent:
				msg = "⚠️ Для использования бота необходимо принять политику конфиденциальности и согласие на обработку персональных данных."
				send_message(vk, peer_id, msg, keyboard=build_privacy_consent_keyboard())
				continue
			
			prof = get_profile(vk, user_id)
			s = prof.stats
			msg = (
				f"Профиль {mention(user_id, prof.name or 'игрок')}:\n"
				f"Викторина очков: {s.get('quiz_points', 0)}\n"
				f"Угадай число побед: {s.get('guess_wins', 0)}\n"
				f"Кальмар побед: {s.get('squid_wins', 0)}\n"
				f"✅ Политика конфиденциальности: принята\n"
				f"✅ GDPR согласие: принято"
			)
			send_message(vk, peer_id, msg)
			continue
		if text in {"/top quiz", "/top викторина", "топ викторина"}:
			msg = "Топ викторины:\n" + format_top(vk, "quiz_points")
			send_message(vk, peer_id, msg)
			continue
		if text in {"/top guess", "/top угадай", "топ угадай"}:
			msg = "Топ угадай число:\n" + format_top(vk, "guess_wins")
			send_message(vk, peer_id, msg)
			continue
		if text in {"/top squid", "/top кальмар", "топ кальмар"}:
			msg = "Топ 'Кальмар':\n" + format_top(vk, "squid_wins")
			send_message(vk, peer_id, msg)
			continue
		
		# Команды безопасности для пользователей
		if text.startswith("/report "):
			# Формат: /report @user_id причина
			parts = text.split(" ", 2)
			if len(parts) >= 3:
				try:
					reported_id = int(parts[1])
					reason = parts[2]
					result = report_user(user_id, reported_id, reason)
					send_message(vk, peer_id, result)
				except ValueError:
					send_message(vk, peer_id, "❌ Неверный формат. Используйте: /report user_id причина")
			else:
				send_message(vk, peer_id, "❌ Неверный формат. Используйте: /report user_id причина")
			continue
		
		if text in {"/security", "безопасность", "security"}:
			# Показываем пользователю его статус безопасности
			privacy_accepted, gdpr_consent = check_user_consents(user_id)
			is_banned, ban_info = is_user_banned(user_id)
			activity = USER_ACTIVITY.get(user_id)
			
			status_msg = "🛡️ Ваш статус безопасности:\n\n"
			status_msg += f"✅ Политика конфиденциальности: {'Принята' if privacy_accepted else 'Не принята'}\n"
			status_msg += f"✅ GDPR согласие: {'Принято' if gdpr_consent else 'Не принято'}\n"
			
			if is_banned:
				remaining_time = int((ban_info.expires_at - time.time()) / 3600)
				status_msg += f"🚫 Статус: Забанен (осталось {remaining_time} часов)\n"
				status_msg += f"🚫 Причина: {ban_info.reason}\n"
			else:
				status_msg += "✅ Статус: Активен\n"
			
			if activity:
				status_msg += f"⚠️ Предупреждений: {activity.warnings}\n"
				status_msg += f"📊 Подозрительных действий: {len(activity.suspicious_actions)}"
			
			send_message(vk, peer_id, status_msg)
			continue
		# Админ-панель по команде в ЛС
		if is_dm and text in {"/admin", "админ", "admin"}:
			handle_admin_panel(vk, peer_id, user_id)
			continue

		action = payload.get("action") if isinstance(payload, dict) else None

		# Мафия
		if action == "start_mafia":
			handle_start_mafia(vk, peer_id, user_id)
			continue
		if action == "maf_join":
			handle_mafia_join(vk, peer_id, user_id)
			continue
		if action == "maf_leave":
			handle_mafia_leave(vk, peer_id, user_id)
			continue
		if action == "maf_cancel":
			handle_mafia_cancel(vk, peer_id, user_id)
			continue
		if action == "maf_begin":
			handle_mafia_begin(vk, peer_id, user_id)
			continue

		# Угадай число
		if action == "start_guess":
			handle_start_guess(vk, peer_id, user_id)
			continue
		# Викторина
		if action == "start_quiz":
			handle_start_quiz(vk, peer_id)
			continue
		if action == "quiz_begin":
			handle_quiz_begin(vk, peer_id)
			continue
		if action == "quiz_next":
			handle_quiz_begin(vk, peer_id)
			continue
		if action == "quiz_end":
			handle_quiz_end(vk, peer_id)
			continue
		
		# Кальмар (Squid Game)
		if action == "start_squid":
			handle_start_squid(vk, peer_id)
			continue
		if action == "squid_join":
			handle_squid_join(vk, peer_id, user_id)
			continue
		if action == "squid_leave":
			handle_squid_leave(vk, peer_id, user_id)
			continue
		if action == "squid_begin":
			handle_squid_begin(vk, peer_id)
			continue
		if action == "squid_cancel":
			handle_squid_cancel(vk, peer_id)
			continue
		if action == "squid_guess":
			handle_squid_guess(vk, peer_id, user_id, payload)
			continue
		if action == "g_join":
			handle_guess_join(vk, peer_id, user_id)
			continue
		if action == "g_leave":
			handle_guess_leave(vk, peer_id, user_id)
			continue
		if action == "g_cancel":
			handle_guess_cancel(vk, peer_id, user_id)
			continue
		if action == "g_begin":
			handle_guess_begin(vk, peer_id, user_id)
			continue

		# ИИ‑чат управление (в беседах)
		if action == "ai_on":
			handle_ai_on(vk, peer_id)
			continue
		if action == "ai_off":
			handle_ai_off(vk, peer_id)
			continue
		if action == "show_help":
			help_msg = (
				"Cry Cat — игры и ИИ:\n"
				"— Мафия: лобби и старт\n"
				"— Угадай число: 2 игрока, по очереди\n"
				"— Викторина: отвечай текстом, есть подсказка/сдаюсь\n"
				"— Кальмар: мини-игры с элиминацией\n"
				"— ИИ‑чат: включай кнопкой. В ЛС /admin — выбор модели ИИ (gpt-5-nano / gemini-flash-1.5-8b / deepseek-chat)\n"
				"Команды: /start, /me, /top quiz, /top guess, /top squid"
			)
			send_message(vk, peer_id, help_msg)
			continue

		# Админ-панель: выбор модели
		if action == "admin_set_model":
			model_name = payload.get("model") if isinstance(payload, dict) else None
			handle_admin_set_model(vk, peer_id, user_id, model_name or "")
			continue
		if action == "admin_current":
			handle_admin_current(vk, peer_id, user_id)
			continue
		if action == "admin_close":
			if user_id in ADMIN_USER_IDS:
				send_message(vk, peer_id, "Админ‑панель закрыта.", keyboard=build_main_keyboard())
			continue
		
		# Обработка согласий на конфиденциальность
		if action == "accept_privacy":
			track_user_activity(user_id, "accept_privacy", "privacy_consent")
			accept_privacy_policy(user_id)
			send_message(vk, peer_id, "✅ Политика конфиденциальности принята!", keyboard=build_main_keyboard())
			continue
		if action == "accept_gdpr":
			track_user_activity(user_id, "accept_gdpr", "gdpr_consent")
			accept_gdpr_consent(user_id)
			send_message(vk, peer_id, "✅ Согласие на обработку персональных данных принято!", keyboard=build_main_keyboard())
			continue
		if action == "decline_privacy":
			track_user_activity(user_id, "decline_privacy", "privacy_declined")
			send_message(vk, peer_id, "❌ Без принятия политики конфиденциальности использование бота невозможно.", keyboard=build_privacy_consent_keyboard())
			continue
		
		# Отслеживание активности для всех действий
		track_user_activity(user_id, action or "message", text[:50])
		
		# Проверка на бан
		is_banned, ban_info = is_user_banned(user_id)
		if is_banned:
			remaining_time = int((ban_info.expires_at - time.time()) / 3600)
			send_message(vk, peer_id, f"🚫 Вы забанены. Причина: {ban_info.reason}. Осталось: {remaining_time} часов")
			continue
		
		# Автоматическая модерация сообщений
		if text and not action:  # Только текстовые сообщения, не действия
			is_violation, action_type, reason = auto_moderate_message(text, user_id)
			if is_violation:
				# Логируем инцидент
				log_security_incident("content_violation", user_id, f"Text: {text[:100]}, Reason: {reason}")
				
				if action_type == "delete":
					# Автоматически удаляем сообщение
					try:
						vk.method("messages.delete", {
							"peer_id": peer_id,
							"message_id": event.message.id,
							"delete_for_all": True
						})
						send_message(vk, peer_id, f"🚫 Сообщение удалено автоматически. Причина: {reason}")
					except Exception as e:
						logger.error(f"Failed to auto-delete message: {e}")
				
				elif action_type == "warn":
					# Автоматически выносим предупреждение
					warning_msg = auto_warn_user(user_id, reason)
					send_message(vk, peer_id, f"⚠️ {warning_msg}")
				
				continue  # Прерываем обработку сообщения

		# Ход в игре «Угадай число»: любое сообщение с числом
		if peer_id in GUESS_SESSIONS and GUESS_SESSIONS[peer_id].started:
			if text.isdigit():
				guess = int(text)
				sess = GUESS_SESSIONS[peer_id]
				if sess.min_value <= guess <= sess.max_value:
					handle_guess_attempt(vk, peer_id, user_id, guess)
					continue
				else:
					send_message(vk, peer_id, f"Введи число от {sess.min_value} до {sess.max_value}.")
					continue

		# Викторина: перехват ответа текстом
		if peer_id in QUIZZES and text_raw:
			handle_quiz_answer(vk, peer_id, user_id, text_raw)
			continue

		# ИИ‑чат: в личке и беседе — только если включён явно
		if text_raw and ai_enabled_for_peer(peer_id, False):
			handle_ai_message(vk, peer_id, text_raw, openrouter_key, aitunnel_key, ai_provider, system_prompt)
			continue

		# Ответ о неизвестной команде — только если сообщение похоже на команду
		if text.startswith("/") or text in {"help", "помощь", "команды"}:
			send_message(vk, peer_id, "Команда не распознана. Напиши /start, чтобы выбрать игру.")

if __name__ == "__main__":
	main()