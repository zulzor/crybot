import os
import sys
import json
import logging
import random
import atexit
import requests
import time
import signal
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List, Tuple

from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


# ---------- Настройки OpenRouter (DeepSeek) ----------
DEEPSEEK_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
OPENROUTER_MODELS = os.getenv("OPENROUTER_MODELS", "").strip()
MAX_HISTORY_MESSAGES = 12
MAX_AI_CHARS = 380
AI_REFERER = os.getenv("OPENROUTER_REFERER", "https://vk.com/crycat_memes")
AI_TITLE = os.getenv("OPENROUTER_TITLE", "Cry Cat Bot")

# ---------- Graceful shutdown ----------
shutdown_requested = False

def signal_handler(signum, frame):
	global shutdown_requested
	logging.getLogger("vk-mafia-bot").info(f"Received signal {signum}, shutting down gracefully...")
	shutdown_requested = True

def setup_signal_handlers():
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)


def configure_logging() -> None:
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)


def load_config() -> Tuple[str, int, str, str]:
	load_dotenv()
	
	token = os.getenv("VK_GROUP_TOKEN", "").strip()
	if not token:
		raise RuntimeError("VK_GROUP_TOKEN is not set in .env")
	
	group_id_str = os.getenv("VK_GROUP_ID", "").strip()
	if not group_id_str:
		raise RuntimeError("VK_GROUP_ID is not set in .env")
	if not group_id_str.isdigit():
		raise RuntimeError("VK_GROUP_ID must be a number (без минуса)")
	
	openrouter_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
	if not openrouter_key:
		logging.warning("DEEPSEEK_API_KEY is not set - AI chat will be disabled")
	
	system_prompt = (
		os.getenv("AI_SYSTEM_PROMPT", "").strip()
		or "Ты дружелюбный нейросотрудник сообщества Cry Cat. Отвечай кратко (до 380 символов) и по делу на русском. Если спрашивают про бота — есть игры «Мафия», «Угадай число» и режим «ИИ‑чат»."
	)
	
	return token, int(group_id_str), openrouter_key, system_prompt


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
AI_CONFIRMATION_MODE: Dict[int, bool] = {}  # peer_id -> True если ждет подтверждения "привет"


# ---------- Клавиатуры ----------
def build_main_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Мафия", color=VkKeyboardColor.PRIMARY, payload={"action": "start_mafia"})
	keyboard.add_button("Угадай число", color=VkKeyboardColor.SECONDARY, payload={"action": "start_guess"})
	keyboard.add_line()
	keyboard.add_button("ИИ‑чат", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_on"})
	keyboard.add_button("Выключить ИИ", color=VkKeyboardColor.NEGATIVE, payload={"action": "ai_off"})
	return keyboard.get_keyboard()


def build_dm_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Выключить ИИ", color=VkKeyboardColor.NEGATIVE, payload={"action": "ai_off"})
	return keyboard.get_keyboard()


def build_ai_confirmation_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Да, к ИИ", color=VkKeyboardColor.POSITIVE, payload={"action": "ai_confirm_yes"})
	keyboard.add_button("Нет, не к ИИ", color=VkKeyboardColor.NEGATIVE, payload={"action": "ai_confirm_no"})
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


def build_empty_keyboard() -> str:
	return json.dumps({"one_time": True, "buttons": []}, ensure_ascii=False)


# ---------- Вспомогательные ----------
def send_message(vk, peer_id: int, text: str, keyboard: Optional[str] = None) -> None:
	if not text.strip():
		return
		
	params: dict[str, object] = {
		"peer_id": peer_id,
		"random_id": 0,
		"message": text,
	}
	if keyboard is not None:
		params["keyboard"] = keyboard
	
	try:
		vk.messages.send(**params)
	except Exception as e:
		logger = logging.getLogger("vk-mafia-bot")
		logger.error(f"Failed to send message to {peer_id}: {e}")
		# Don't crash the bot on send errors


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


# ---------- DeepSeek через OpenRouter (с авто‑переключением моделей) ----------
def deepseek_reply(api_key: str, system_prompt: str, history: List[Dict[str, str]], user_text: str) -> str:
	if not api_key:
		return "ИИ не настроен. Добавьте DEEPSEEK_API_KEY в .env."
	
	if not user_text.strip():
		return "Пожалуйста, напишите что-нибудь."
	
	messages = [{"role": "system", "content": system_prompt}]
	messages.extend(history[-MAX_HISTORY_MESSAGES:])
	messages.append({"role": "user", "content": user_text})

	logger = logging.getLogger("vk-mafia-bot")
	last_err = "unknown"
	
	for model in get_model_candidates():
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
						"max_tokens": 180,
					},
					timeout=45,
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
				logger.info(f"AI OK model={model} attempt={attempt+1}")
				return text
			except requests.HTTPError as e:
				code = e.response.status_code if e.response else None
				last_err = f"HTTP {code}"
				# На 429/5xx пробуем ещё раз и/или другую модель
				if code in (429, 500, 502, 503, 504):
					time.sleep(1 + attempt * 2)
					continue
				break
			except requests.RequestException as e:
				last_err = f"Request error: {e}"
				break
			except Exception as e:
				last_err = str(e)
				break
		logger.info(f"AI fallback: {last_err} on model={model}")
	
	return f"ИИ временно недоступен ({last_err}). Попробуйте позже."


def ai_enabled_for_peer(peer_id: int, is_dm: bool) -> bool:
	if is_dm:
		return True
	return peer_id in AI_ACTIVE_CHATS


def add_history(peer_id: int, role: str, content: str) -> None:
	h = AI_HISTORY.setdefault(peer_id, [])
	h.append({"role": role, "content": content})
	if len(h) > MAX_HISTORY_MESSAGES:
		del h[: len(h) - MAX_HISTORY_MESSAGES]


# ---------- Команды ----------
def handle_start(vk, peer_id: int, is_dm: bool = False) -> None:
	send_message(vk, peer_id, "Старые кнопки убраны.", keyboard=build_empty_keyboard())
	
	if is_dm:
		# В личных сообщениях - только ИИ-чат
		send_message(
			vk,
			peer_id,
			"Привет! Я ИИ-помощник. Просто напиши мне сообщение, и я отвечу. Чтобы выключить ИИ, нажми кнопку или напиши 'выключись'.",
			keyboard=build_dm_keyboard(),
		)
	else:
		# В групповых чатах - игры и ИИ
		send_message(
			vk,
			peer_id,
			"Привет! Выбери игру: «Мафия», «Угадай число», либо включи «ИИ‑чат». Также можешь написать 'привет' для быстрого вызова ИИ.",
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
	send_message(vk, peer_id, "ИИ‑чат включён для этой беседы. Пишите сообщения — я отвечу. Чтобы выключить, нажмите «Выключить ИИ» или напишите 'выключись'.", keyboard=build_main_keyboard())

def handle_ai_off(vk, peer_id: int) -> None:
	AI_ACTIVE_CHATS.discard(peer_id)
	AI_CONFIRMATION_MODE.pop(peer_id, None)  # Убираем режим подтверждения
	send_message(vk, peer_id, "ИИ‑чат выключен для этой беседы.", keyboard=build_main_keyboard())

def handle_ai_confirm_yes(vk, peer_id: int) -> None:
	AI_ACTIVE_CHATS.add(peer_id)
	AI_CONFIRMATION_MODE.pop(peer_id, None)
	send_message(vk, peer_id, "ИИ‑чат включён! Пишите сообщения — я отвечу.", keyboard=build_main_keyboard())

def handle_ai_confirm_no(vk, peer_id: int) -> None:
	AI_CONFIRMATION_MODE.pop(peer_id, None)
	send_message(vk, peer_id, "Понял, ИИ не нужен. Выберите игру или напишите 'привет' для вызова ИИ.", keyboard=build_main_keyboard())

def handle_ai_message(vk, peer_id: int, user_text: str, api_key: str, system_prompt: str) -> None:
	# Проверяем команды выключения ИИ
	if user_text.lower().strip() in {"выключись", "выключить ии", "выключить ии-чат", "стоп ии", "отключись"}:
		handle_ai_off(vk, peer_id)
		return
	
	add_history(peer_id, "user", user_text)
	reply = deepseek_reply(api_key, system_prompt, AI_HISTORY.get(peer_id, []), user_text)
	reply = clamp_text(reply, MAX_AI_CHARS)
	add_history(peer_id, "assistant", reply)
	send_message(vk, peer_id, reply)

def handle_hello_trigger(vk, peer_id: int, is_dm: bool) -> bool:
	"""Обработка слова 'привет' для вызова ИИ"""
	if is_dm:
		# В личных сообщениях ИИ всегда активен
		return False  # Продолжаем обычную обработку
	
	if peer_id in AI_ACTIVE_CHATS:
		# ИИ уже активен
		return False
	
	# Запрашиваем подтверждение
	AI_CONFIRMATION_MODE[peer_id] = True
	send_message(
		vk, 
		peer_id, 
		"Вы обращаетесь ко мне (ИИ)?", 
		keyboard=build_ai_confirmation_keyboard()
	)
	return True  # Обработано, не продолжаем


# ---------- Основной цикл ----------
def main() -> None:
	configure_logging()
	load_dotenv()
	setup_signal_handlers()
	logger = logging.getLogger("vk-mafia-bot")
	logger.info(f"AI endpoint: {DEEPSEEK_API_URL}")
	logger.info(f"AI models: {get_model_candidates()}")
	try:
		token, group_id, openrouter_key, system_prompt = load_config()
	except Exception as exc:
		logger.error("Config error: %s", exc)
		sys.exit(1)

	vk_session = vk_api.VkApi(token=token)
	vk = vk_session.get_api()
	longpoll = VkBotLongPoll(vk_session, group_id)

	logger.info("Bot started. Listening for events...")

	while not shutdown_requested:
		try:
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
					handle_start(vk, peer_id, is_dm)
					continue

				# Текстовые синонимы для кнопок
				if text in {"мафия"}:
					handle_start_mafia(vk, peer_id, user_id)
					continue
				if text in {"угадай число", "угадай", "число"}:
					handle_start_guess(vk, peer_id, user_id)
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
				if action == "ai_confirm_yes":
					handle_ai_confirm_yes(vk, peer_id)
					continue
				if action == "ai_confirm_no":
					handle_ai_confirm_no(vk, peer_id)
					continue

				# Обработка слова "привет" для вызова ИИ
				if text == "привет" and not is_dm:
					if handle_hello_trigger(vk, peer_id, is_dm):
						continue

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

				# ИИ‑чат: в личке — всегда; в беседе — только если включён или в режиме подтверждения
				if text_raw and (ai_enabled_for_peer(peer_id, is_dm) or peer_id in AI_CONFIRMATION_MODE):
					handle_ai_message(vk, peer_id, text_raw, openrouter_key, system_prompt)
					continue

				# Ответ о неизвестной команде — только если сообщение похоже на команду
				if text.startswith("/") or text in {"help", "помощь", "команды"}:
					send_message(vk, peer_id, "Команда не распознана. Напиши /start, чтобы выбрать игру.")

		except Exception as e:
			logger.exception("Error during longpoll listen: %s", e)
			if not shutdown_requested:
				time.sleep(1) # Retry after a short delay

	logger.info("Bot shutting down gracefully.")

if __name__ == "__main__":
	main()