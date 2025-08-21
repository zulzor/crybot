from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
import time
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import os
from i18n import t


# -------- Типы --------


@dataclass
class RouterContext:
    vk: object
    peer_id: int
    user_id: int
    text: str
    is_dm: bool


Handler = Callable[[RouterContext], Optional[str]]


@dataclass
class Command:
    name: str
    aliases: List[str]
    description: str
    handler: Handler
    admin_required: bool = False
    dm_only: bool = False
    chat_only: bool = False


# -------- Глобальное состояние роутера --------


_commands_by_alias: Dict[str, Command] = {}
_is_admin_check: Callable[[int], bool] = lambda _uid: False

# Базовый rate limit: на пользователя и на peer (чат/ЛС)
_user_limit = 10
_user_window_sec = 60
_peer_limit = 30
_peer_window_sec = 60

_user_hits: Dict[int, List[float]] = {}
_peer_hits: Dict[int, List[float]] = {}


def configure_router(
    is_admin: Optional[Callable[[int], bool]] = None,
    user_limit: Optional[int] = None,
    user_window_sec: Optional[int] = None,
    peer_limit: Optional[int] = None,
    peer_window_sec: Optional[int] = None,
) -> None:
    global _is_admin_check, _user_limit, _user_window_sec, _peer_limit, _peer_window_sec
    if is_admin is not None:
        _is_admin_check = is_admin
    if user_limit is not None:
        _user_limit = int(user_limit)
    if user_window_sec is not None:
        _user_window_sec = int(user_window_sec)
    if peer_limit is not None:
        _peer_limit = int(peer_limit)
    if peer_window_sec is not None:
        _peer_window_sec = int(peer_window_sec)


def register_command(cmd: Command) -> None:
    # Регистрируем основное имя и алиасы в нижнем регистре
    keys = [cmd.name] + list(cmd.aliases)
    for key in keys:
        _commands_by_alias[key.strip().lower()] = cmd


def require_admin(handler: Handler) -> Handler:
    def wrapper(ctx: RouterContext) -> Optional[str]:
        if not _is_admin_check(ctx.user_id):
            return "❌ Недостаточно прав"
        return handler(ctx)

    return wrapper


# -------- Вспомогательные функции отправки и клавиатур --------


def _send_with_keyboard(ctx: RouterContext, text: str, keyboard_json: Optional[str] = None) -> None:
    try:
        if keyboard_json:
            ctx.vk.messages.send(peer_id=ctx.peer_id, message=text, keyboard=keyboard_json, random_id=0)
        else:
            ctx.vk.messages.send(peer_id=ctx.peer_id, message=text, random_id=0)
    except Exception:
        # игнорируем ошибки отправки в роутере, чтобы не падать
        pass


def _build_inline_keyboard(button_rows: List[List[Tuple[str, Dict]]]) -> str:
    """Строит inline-клавиатуру. button_rows: [[(label, payload_dict), ...], ...]"""
    kb = VkKeyboard(one_time=False, inline=True)
    first = True
    for row in button_rows:
        if not first:
            kb.add_line()
        first = False
        for label, payload in row:
            kb.add_button(label, color=VkKeyboardColor.PRIMARY, payload=payload)
    return kb.get_keyboard()


# ---------- Админка: inline меню ----------


def _build_admin_main_inline_keyboard() -> str:
    rows = [
        [("⚙️ Хранилище", {"action": "admin_storage"}), ("🌐 Язык", {"action": "admin_lang"})],
        [("📈 Мониторинг", {"action": "admin_monitoring"}), ("🛒 Экономика", {"action": "admin_economy"})],
        [("💾 Бэкапы", {"action": "admin_backups"})],
    ]
    return _build_inline_keyboard(rows)


def _build_storage_inline_keyboard() -> str:
    rows = [
        [("SQLite", {"action": "set_storage", "value": "sqlite"}), ("JSON", {"action": "set_storage", "value": "json"})],
        [("Hybrid", {"action": "set_storage", "value": "hybrid"})],
        [("⬅️ Назад", {"action": "admin_menu"})],
    ]
    return _build_inline_keyboard(rows)


def _build_lang_inline_keyboard() -> str:
    rows = [
        [("Русский", {"action": "set_lang", "value": "ru"}), ("English", {"action": "set_lang", "value": "en"})],
        [("⬅️ Назад", {"action": "admin_menu"})],
    ]
    return _build_inline_keyboard(rows)


def _build_conductor_inline_keyboard() -> str:
    rows = [
        [("Проверить билеты", {"action": "conductor_action", "value": "проверить билеты"}),
         ("Помочь пассажирам", {"action": "conductor_action", "value": "помочь пассажирам"})],
        [("Решить проблемы", {"action": "conductor_action", "value": "решить проблемы"}),
         ("Следующий поезд", {"action": "conductor_action", "value": "следующий поезд"})],
        [("Завершить смену", {"action": "conductor_action", "value": "завершить смену"})]
    ]
    # На случай, если payload не обрабатывается как callback, используем текстовые подписи кнопок как команду
    # Клиент VK всё равно отправит текст кнопки как сообщение, что подхватят команды ниже
    return _build_inline_keyboard(rows)


def _build_shop_inline_keyboard(economy: object) -> str:
    # Кнопки с текстом вида "/buy <item_id>", чтобы не зависеть от payload
    items = list(getattr(economy, "shop_items", {}).values())
    rows: List[List[Tuple[str, Dict]]] = []
    row: List[Tuple[str, Dict]] = []
    for item in items:
        label = f"/buy {item.id}"
        row.append((label, {"action": "text", "value": label}))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if not rows:
        rows = [[("Обновить магазин", {"action": "text", "value": "/shop"})]]
    return _build_inline_keyboard(rows)


# ---------- Бизнес: inline меню ----------


def _build_business_inline_keyboard() -> str:
    rows = [
        [("💳 Баланс", {"action": "business_action", "value": "balance"}), ("🎁 Ежедневный", {"action": "business_action", "value": "daily"})],
        [("🏪 Магазин", {"action": "business_action", "value": "shop"}), ("📦 Инвентарь", {"action": "business_action", "value": "inventory"})],
        [("🏬 Активы", {"action": "business_action", "value": "assets"}), ("🔧 Улучшить", {"action": "business_action", "value": "upgrade"})],
        [("🌟 Престиж", {"action": "business_action", "value": "prestige"})],
    ]
    return _build_inline_keyboard(rows)


def _handle_business(ctx: RouterContext) -> Optional[str]:
    from economy_social import economy_manager
    text = t(ctx.user_id, "shop_title")
    kb = _build_business_inline_keyboard()
    _send_with_keyboard(ctx, text, kb)
    return None


def _handle_business_action(ctx: RouterContext) -> Optional[str]:
    from economy_social import economy_manager, Currency
    action = ctx.text.strip().lower()
    if action == "balance":
        wallet = economy_manager.get_wallet(ctx.user_id)
        bal = wallet.balance.get(Currency.CRYCOIN, 0)
        _send_with_keyboard(ctx, f"💰 Баланс: {bal} 🪙", _build_business_inline_keyboard())
        return None
    if action == "daily":
        msg = economy_manager.daily_bonus(ctx.user_id)
        _send_with_keyboard(ctx, msg, _build_business_inline_keyboard())
        return None
    if action == "shop":
        msg = economy_manager.get_shop()
        _send_with_keyboard(ctx, msg, _build_shop_inline_keyboard(economy_manager))
        return None
    if action == "inventory":
        inv = economy_manager.get_inventory(ctx.user_id)
        if not inv.items:
            _send_with_keyboard(ctx, "📦 Инвентарь пуст", _build_business_inline_keyboard())
            return None
        lines = ["📦 Инвентарь:"]
        for iid, qty in inv.items.items():
            lines.append(f"• {iid}: x{qty}")
        _send_with_keyboard(ctx, "\n".join(lines), _build_business_inline_keyboard())
        return None
    if action == "assets":
        # Показ магазина активов из bot_vk
        try:
            from bot_vk import get_business_shop
            msg = get_business_shop()
        except Exception:
            msg = "🏪 Магазин активов недоступен"
        kb_rows = []
        try:
            from bot_vk import BUSINESS_ASSETS  # dict of asset_key -> BusinessAsset
            row = []
            for key in BUSINESS_ASSETS.keys():
                label = f"/buy_asset {key}"
                row.append((label, {"action": "text", "value": f"buy_asset {key}"}))
                if len(row) == 2:
                    kb_rows.append(row)
                    row = []
            if row:
                kb_rows.append(row)
        except Exception:
            pass
        kb = _build_inline_keyboard(kb_rows) if kb_rows else _build_business_inline_keyboard()
        _send_with_keyboard(ctx, msg, kb)
        return None
    if action == "upgrade":
        # Показ улучшений доступных активов пользователя
        try:
            from bot_vk import get_business_profile
            prof = get_business_profile(ctx.user_id)
            if not prof.assets:
                _send_with_keyboard(ctx, "❌ Нет активов для улучшения", _build_business_inline_keyboard())
                return None
            lines = ["🔧 Доступные для улучшения:"]
            kb_rows = []
            row = []
            for k, a in prof.assets.items():
                lines.append(f"• {a.name} (ур.{a.level})")
                label = f"/upgrade_asset {k}"
                row.append((label, {"action": "text", "value": f"upgrade_asset {k}"}))
                if len(row) == 2:
                    kb_rows.append(row)
                    row = []
            if row:
                kb_rows.append(row)
            kb = _build_inline_keyboard(kb_rows)
            _send_with_keyboard(ctx, "\n".join(lines), kb)
        except Exception:
            _send_with_keyboard(ctx, "❌ Не удалось получить данные", _build_business_inline_keyboard())
        return None
    if action == "prestige":
        try:
            from bot_vk import prestige_reset
            msg = prestige_reset(ctx.user_id)
            _send_with_keyboard(ctx, msg, _build_business_inline_keyboard())
        except Exception:
            _send_with_keyboard(ctx, "❌ Престиж недоступен", _build_business_inline_keyboard())
        return None
    return None

def _cleanup_hits(hits: List[float], now_ts: float, window_sec: int) -> None:
    # Удаляем старые записи
    cutoff = now_ts - window_sec
    while hits and hits[0] < cutoff:
        hits.pop(0)


def _rate_limited(user_id: int, peer_id: int, now_ts: float) -> Optional[str]:
    user_hits = _user_hits.setdefault(user_id, [])
    _cleanup_hits(user_hits, now_ts, _user_window_sec)
    if len(user_hits) >= _user_limit:
        wait_sec = max(1, int(user_hits[0] + _user_window_sec - now_ts))
        return f"⏳ Слишком часто. Подожди {wait_sec} сек."

    peer_hits = _peer_hits.setdefault(peer_id, [])
    _cleanup_hits(peer_hits, now_ts, _peer_window_sec)
    if len(peer_hits) >= _peer_limit:
        wait_sec = max(1, int(peer_hits[0] + _peer_window_sec - now_ts))
        return f"⏳ Чат перегружен. Подожди {wait_sec} сек."

    # Записываем текущий хит
    user_hits.append(now_ts)
    peer_hits.append(now_ts)
    return None


def dispatch_command(
    text: str,
    vk: object,
    peer_id: int,
    user_id: int,
    is_dm: bool,
) -> Tuple[bool, Optional[str]]:
    """
    Пытается обработать команду. Возвращает (handled, reply_text).
    Если handler сам отправляет ответ, reply_text = None.
    """
    if not text:
        return False, None

    raw = text.strip()
    lower = raw.lower()

    def _map_label_to_action(s: str) -> str:
        s = s.strip().lower()
        mapping = {
            "/admin": "admin_menu", "admin": "admin_menu", "админ": "admin_menu", "админ-меню": "admin_menu",
            "хранилище": "admin_storage", "storage": "admin_storage", "⚙️ хранилище": "admin_storage",
            "язык": "admin_lang", "language": "admin_lang", "🌐 язык": "admin_lang",
            "мониторинг": "admin_monitoring", "monitoring": "admin_monitoring", "📈 мониторинг": "admin_monitoring",
            "бизнес": "business", "business": "business", "🏢 космический бизнес": "business",
            "баланс": "set_business balance", "balance": "set_business balance",
            "ежедневный": "set_business daily", "daily": "set_business daily",
            "магазин": "set_business shop", "shop": "set_business shop",
            "инвентарь": "set_business inventory", "inventory": "set_business inventory",
            "русский": "set_lang ru", "russian": "set_lang ru",
            "english": "set_lang en", "английский": "set_lang en",
            "sqlite": "set_storage sqlite", "json": "set_storage json", "hybrid": "set_storage hybrid",
        }
        return mapping.get(s, s)

    mapped = _map_label_to_action(lower)
    if mapped != lower:
        lower = mapped
        raw = mapped

    # Специальный случай: /config restore N — парсинг с аргументом
    if lower.startswith("/config restore ") or lower.startswith("config restore "):
        cmd = _commands_by_alias.get("/config restore")
        if not cmd:
            return False, None
        parts = raw.split(" ", 2)
        if len(parts) < 3:
            return True, "❌ Использование: /config restore <номер> (см. /config list)"
        idx_str = parts[2].strip()
        ctx = RouterContext(vk=vk, peer_id=peer_id, user_id=user_id, text=idx_str, is_dm=is_dm)
        # Проверка контекста/прав и RL
        if cmd.dm_only and not is_dm:
            return True, "❌ Команда доступна только в ЛС"
        if cmd.chat_only and is_dm:
            return True, "❌ Команда доступна только в беседах"
        if cmd.admin_required and not _is_admin_check(user_id):
            return True, "❌ Недостаточно прав"
        rl = _rate_limited(user_id, peer_id, time.time())
        if rl:
            return True, rl
        return True, cmd.handler(ctx)

    # Прямое сопоставление по алиасам
    cmd = _commands_by_alias.get(lower)
    if not cmd:
        return False, None

    ctx = RouterContext(vk=vk, peer_id=peer_id, user_id=user_id, text=raw, is_dm=is_dm)

    # Админские inline действия
    if lower == "admin_menu" and _is_admin_check(user_id):
        _send_with_keyboard(ctx, t(user_id, "admin_menu"), _build_admin_main_inline_keyboard())
        return True, None
    if lower == "admin_storage" and _is_admin_check(user_id):
        _send_with_keyboard(ctx, t(user_id, "select_storage"), _build_storage_inline_keyboard())
        return True, None
    if lower == "admin_lang" and _is_admin_check(user_id):
        _send_with_keyboard(ctx, t(user_id, "select_lang"), _build_lang_inline_keyboard())
        return True, None
    if lower == "admin_monitoring" and _is_admin_check(user_id):
        try:
            from monitoring import health_checker, metrics_collector, START_TIME
            import time
            
            # Получаем краткую статистику
            overall_status = health_checker.get_overall_status()
            
            # Основные метрики
            total_requests = metrics_collector.get_counter("ai_requests_total")
            successful_requests = metrics_collector.get_counter("ai_success_total")
            failed_requests = metrics_collector.get_counter("ai_errors_total")
            
            # Uptime
            uptime_hours = (time.time() - START_TIME) / 3600
            
            # Активные пользователи
            from storage import get_storage_from_env
            storage = get_storage_from_env()
            profiles = storage.get_all("profiles")
            current_time = time.time()
            one_hour_ago = current_time - 3600
            active_users = sum(1 for profile in profiles.values() 
                              if isinstance(profile, dict) and 
                              profile.get('last_activity', 0) > one_hour_ago)
            
            # Формируем ответ
            status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(overall_status, "❓")
            
            text = f"""📊 Мониторинг системы

🏥 Статус: {status_emoji} {overall_status}
⏱️ Время работы: {uptime_hours:.1f} ч
📈 Запросов ИИ: {total_requests}
✅ Успешных: {successful_requests}
❌ Ошибок: {failed_requests}
👥 Активных пользователей: {active_users}"""
            
            # Inline-кнопки для мониторинга
            keyboard = VkKeyboard(inline=True)
            keyboard.add_button("📊 Подробная статистика", color=VkKeyboardColor.PRIMARY)
            keyboard.add_line()
            keyboard.add_button("🏥 Состояние системы", color=VkKeyboardColor.SECONDARY)
            keyboard.add_button("🗑️ Очистить кеш", color=VkKeyboardColor.NEGATIVE)
            keyboard.add_line()
            keyboard.add_button("🔙 Назад в админ-меню", color=VkKeyboardColor.SECONDARY)
            
            _send_with_keyboard(ctx, text, keyboard.get_keyboard())
            return True, None
            
        except Exception as e:
            return True, f"❌ Ошибка мониторинга: {str(e)}"
    if lower.startswith("set_storage") and _is_admin_check(user_id):
        parts = raw.split()
        value = parts[-1].strip().lower() if len(parts) > 1 else "sqlite"
        if value not in {"sqlite", "json", "hybrid"}:
            return True, "❌ Недопустимое значение: sqlite|json|hybrid"
        
        # Сохраняем в .env файл
        try:
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Ищем и заменяем STORAGE_BACKEND
                found = False
                for i, line in enumerate(lines):
                    if line.startswith("STORAGE_BACKEND="):
                        lines[i] = f"STORAGE_BACKEND={value}\n"
                        found = True
                        break
                
                if not found:
                    lines.append(f"STORAGE_BACKEND={value}\n")
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            else:
                # Создаем .env если не существует
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write(f"STORAGE_BACKEND={value}\n")
            
            os.environ["STORAGE_BACKEND"] = value
            _send_with_keyboard(ctx, f"✅ STORAGE_BACKEND={value}. Изменение сохранено в .env и вступит в силу после перезапуска.", _build_storage_inline_keyboard())
            return True, None
        except Exception as e:
            return True, f"❌ Ошибка сохранения: {str(e)}"
    if lower.startswith("set_lang") and _is_admin_check(user_id):
        parts = raw.split()
        value = parts[-1].strip().lower() if len(parts) > 1 else "ru"
        if value not in {"ru", "en"}:
            return True, "❌ Язык поддерживается: ru|en"
        os.environ["DEFAULT_LANGUAGE"] = "ru" if value == "ru" else "en"
        _send_with_keyboard(ctx, t(user_id, "lang_set", lang=value), _build_lang_inline_keyboard())
        return True, None

    # Язык для любого пользователя: /lang
    if lower in {"/lang", "lang", "язык"}:
        _send_with_keyboard(ctx, t(user_id, "select_lang"), _build_lang_inline_keyboard())
        return True, None
    if lower.startswith("set_lang "):
        value = raw.split(" ", 1)[1].strip().lower()
        if value not in {"ru", "en"}:
            return True, "❌ ru|en"
        # сохранить в профиль
        try:
            from economy_social import social_manager
            profile = social_manager.get_profile(user_id)
            profile.preferred_language = value
            social_manager.update_profile(user_id, preferred_language=value)
            _send_with_keyboard(ctx, t(user_id, "lang_set", lang=value), _build_lang_inline_keyboard())
            return True, None
        except Exception:
            return True, "❌ Не удалось сохранить язык"

    # Бизнес: обрабатываем mapped set_business <action>
    if lower.startswith("set_business "):
        action = raw.split(" ", 1)[1].strip()
        ctx2 = RouterContext(vk=vk, peer_id=peer_id, user_id=user_id, text=action, is_dm=is_dm)
        return True, _handle_business_action(ctx2)
    if lower.startswith("buy_asset "):
        asset_key = raw.split(" ", 1)[1].strip()
        try:
            from bot_vk import buy_asset
            msg = buy_asset(user_id, asset_key)
            _send_with_keyboard(ctx, msg, _build_business_inline_keyboard())
            return True, None
        except Exception:
            return True, "❌ Покупка недоступна"
    if lower.startswith("upgrade_asset "):
        asset_key = raw.split(" ", 1)[1].strip()
        try:
            from bot_vk import upgrade_asset
            msg = upgrade_asset(user_id, asset_key)
            _send_with_keyboard(ctx, msg, _build_business_inline_keyboard())
            return True, None
        except Exception:
            return True, "❌ Улучшение недоступно"

    # Контекст/права
    if cmd.dm_only and not is_dm:
        return True, "❌ Команда доступна только в ЛС"
    if cmd.chat_only and is_dm:
        return True, "❌ Команда доступна только в беседах"
    if cmd.admin_required and not _is_admin_check(user_id):
        return True, "❌ Недостаточно прав"

    rl = _rate_limited(user_id, peer_id, time.time())
    if rl:
        return True, rl

    return True, cmd.handler(ctx)


# -------- Хендлеры по умолчанию --------


def _handle_help(ctx: RouterContext) -> Optional[str]:
    # Генерация справки из реестра с фильтром прав/контекста
    visible: Dict[str, Command] = {}
    for alias, cmd in _commands_by_alias.items():
        # Показываем только основное имя команды в списке
        if alias != cmd.name:
            continue
        if cmd.dm_only and not ctx.is_dm:
            continue
        if cmd.chat_only and ctx.is_dm:
            continue
        if cmd.admin_required and not _is_admin_check(ctx.user_id):
            continue
        visible[cmd.name] = cmd

    if not visible:
        return "Доступные команды не найдены"

    lines: List[str] = [
        "CryBot — команды:",
    ]
    for _, cmd in sorted(visible.items(), key=lambda kv: kv[0]):
        aliases = ", ".join(a for a in cmd.aliases if a)
        if aliases:
            lines.append(f"{cmd.name} ({aliases}) — {cmd.description}")
        else:
            lines.append(f"{cmd.name} — {cmd.description}")

    return "\n".join(lines)


# -------- Новые команды для игр --------
def _handle_game(ctx: RouterContext) -> Optional[str]:
    """Универсальный обработчик игр"""
    from games_extended import game_engine
    
    parts = ctx.text.strip().split()
    if len(parts) < 2:
        return "❌ Использование: /game <тип> <действие>\n\nДоступные игры:\n• conductor - Проводница РЖД\n• hangman - Виселица\n• poker - Покер"
    
    game_type = parts[0]
    command = parts[1]
    
    if game_type not in ["conductor", "hangman", "poker"]:
        return "❌ Неизвестная игра. Доступные: conductor, hangman, poker"
    
    # Обрабатываем действие
    message, buttons = game_engine.handle_action(ctx.user_id, ctx.peer_id, game_type, command)
    
    # Отправляем сообщение с inline-кнопками
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:  # Переход на новую строку каждые 2 кнопки
                keyboard.add_line()
        
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    
    return None

def _handle_conductor(ctx: RouterContext) -> Optional[str]:
    """Обработчик игры 'Проводница РЖД'"""
    from games_extended import game_engine
    
    message, buttons = game_engine.start_game(ctx.user_id, ctx.peer_id, "conductor")
    
    # Отправляем сообщение с inline-кнопками
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:  # Переход на новую строку каждые 2 кнопки
                keyboard.add_line()
        
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    
    return None

def _handle_hangman(ctx: RouterContext) -> Optional[str]:
    """Обработчик игры 'Виселица'"""
    from games_extended import game_engine
    
    message, buttons = game_engine.start_game(ctx.user_id, ctx.peer_id, "hangman")
    
    # Отправляем сообщение с inline-кнопками
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:  # Переход на новую строку каждые 2 кнопки
                keyboard.add_line()
        
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    
    return None

def _handle_poker(ctx: RouterContext) -> Optional[str]:
    """Обработчик игры 'Покер'"""
    from games_extended import game_engine
    
    message, buttons = game_engine.start_game(ctx.user_id, ctx.peer_id, "poker")
    
    # Отправляем сообщение с inline-кнопками
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:  # Переход на новую строку каждые 2 кнопки
                keyboard.add_line()
        
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    
    return None

def _handle_conductor_action(ctx: RouterContext) -> Optional[str]:
    """Обработчик действий в игре Проводница РЖД"""
    from games_extended import conductor_game
    action = ctx.text.strip()
    text = conductor_game.handle_action(ctx.peer_id, action)
    _send_with_keyboard(ctx, text, _build_conductor_inline_keyboard())
    return None

def _handle_hangman_guess(ctx: RouterContext) -> Optional[str]:
    """Обработчик угадывания букв в Виселице"""
    from games_extended import hangman_manager
    letter = ctx.text.strip()
    return hangman_manager.guess_letter(ctx.peer_id, letter)

def _handle_chess(ctx: RouterContext) -> Optional[str]:
    """Обработчик создания шахматной партии"""
    from games_extended import chess_manager
    
    # Простая реализация: создаем игру с ботом
    bot_player = 999999  # ID бота
    return chess_manager.create_game(ctx.user_id, bot_player)

def _handle_chess_move(ctx: RouterContext) -> Optional[str]:
    """Обработчик хода в шахматах"""
    from games_extended import chess_manager
    
    parts = ctx.text.split()
    if len(parts) < 2:
        return "❌ Использование: /chess move <game_id> <move>"
    
    game_id = parts[0]
    move = parts[1]
    
    return chess_manager.make_move(game_id, ctx.user_id, move)

def _handle_crossword(ctx: RouterContext) -> Optional[str]:
    """Обработчик начала кроссворда"""
    from games_extended import crossword_manager
    return crossword_manager.start_game(ctx.user_id)

def _handle_crossword_guess(ctx: RouterContext) -> Optional[str]:
    """Обработчик угадывания слова в кроссворде"""
    from games_extended import crossword_manager
    return crossword_manager.guess_word(ctx.user_id, ctx.text)

def _handle_poker_create(ctx: RouterContext) -> Optional[str]:
    """Создание покер-стола"""
    from games_extended import poker_manager
    # Используем имя по умолчанию, чтобы не зависеть от bot_vk
    name = f"Игрок {ctx.user_id}"
    return poker_manager.create_game(ctx.peer_id, ctx.user_id, name)

def _handle_poker_join(ctx: RouterContext) -> Optional[str]:
    """Присоединение к покер-столу"""
    from games_extended import poker_manager
    from bot_vk import get_user_name
    name = get_user_name(ctx.vk, ctx.user_id)
    return poker_manager.join_game(ctx.peer_id, ctx.user_id, name)

def _handle_poker_start(ctx: RouterContext) -> Optional[str]:
    """Начало покер-игры"""
    from games_extended import poker_manager
    return poker_manager.start_game(ctx.peer_id)

def _handle_poker_bet(ctx: RouterContext) -> Optional[str]:
    """Ставка в покере"""
    from games_extended import poker_manager
    try:
        amount = int(ctx.text.strip())
        return poker_manager.make_action(ctx.peer_id, ctx.user_id, "bet", amount)
    except ValueError:
        return "❌ Укажите сумму ставки: /poker bet <amount>"

def _handle_poker_call(ctx: RouterContext) -> Optional[str]:
    """Уравнять ставку в покере"""
    from games_extended import poker_manager
    return poker_manager.make_action(ctx.peer_id, ctx.user_id, "call")

def _handle_poker_fold(ctx: RouterContext) -> Optional[str]:
    """Сбросить карты в покере"""
    from games_extended import poker_manager
    return poker_manager.make_action(ctx.peer_id, ctx.user_id, "fold")

def _handle_poker_check(ctx: RouterContext) -> Optional[str]:
    """Пасовать в покере"""
    from games_extended import poker_manager
    return poker_manager.make_action(ctx.peer_id, ctx.user_id, "check")

# -------- Команды экономики --------
def _handle_daily(ctx: RouterContext) -> Optional[str]:
    """Ежедневный бонус"""
    from economy_social import economy_manager
    return economy_manager.daily_bonus(ctx.user_id)

def _handle_balance(ctx: RouterContext) -> Optional[str]:
    """Показать баланс"""
    from economy_social import economy_manager, Currency
    wallet = economy_manager.get_wallet(ctx.user_id)
    balance = wallet.balance.get(Currency.CRYCOIN, 0)
    return f"💰 Баланс: {balance} 🪙"

def _handle_shop(ctx: RouterContext) -> Optional[str]:
    """Показать магазин"""
    from economy_social import economy_manager
    text = economy_manager.get_shop()
    kb = _build_shop_inline_keyboard(economy_manager)
    _send_with_keyboard(ctx, text, kb)
    return None

def _handle_buy(ctx: RouterContext) -> Optional[str]:
    """Покупка предмета"""
    from economy_social import economy_manager
    item_id = ctx.text.strip()
    return economy_manager.buy_item(ctx.user_id, item_id)

def _handle_craft(ctx: RouterContext) -> Optional[str]:
    """Крафтинг предмета"""
    from economy_social import economy_manager
    recipe = ctx.text.strip()
    return economy_manager.craft_item(ctx.user_id, recipe)

def _handle_auction_create(ctx: RouterContext) -> Optional[str]:
    """Создание аукциона"""
    from economy_social import economy_manager
    parts = ctx.text.strip().split()
    if len(parts) < 3:
        return "❌ Использование: /auction create <item_id> <quantity> <price>"
    
    item_id = parts[0]
    quantity = int(parts[1])
    price = int(parts[2])
    
    return economy_manager.create_auction(ctx.user_id, item_id, quantity, price)

def _handle_auction_bid(ctx: RouterContext) -> Optional[str]:
    """Ставка на аукцион"""
    from economy_social import economy_manager
    parts = ctx.text.strip().split()
    if len(parts) < 2:
        return "❌ Использование: /auction bid <auction_id> <amount>"
    
    auction_id = parts[0]
    amount = int(parts[1])
    
    return economy_manager.bid_on_auction(ctx.user_id, auction_id, amount)

def _handle_auction_list(ctx: RouterContext) -> Optional[str]:
    """Список активных аукционов"""
    from economy_social import economy_manager
    return economy_manager.get_active_auctions()

def _handle_tournament_create(ctx: RouterContext) -> Optional[str]:
    """Создание турнира"""
    from economy_social import economy_manager
    parts = ctx.text.strip().split()
    if len(parts) < 3:
        return "❌ Использование: /tournament create <name> <game_type> <entry_fee>"
    
    name = parts[0]
    game_type = parts[1]
    try:
        entry_fee = int(parts[2])
    except ValueError:
        return "❌ Взнос должен быть числом"
    
    return economy_manager.create_tournament(name, game_type, entry_fee)

def _handle_tournament_join(ctx: RouterContext) -> Optional[str]:
    """Присоединение к турниру"""
    from economy_social import economy_manager
    tournament_id = ctx.text.strip()
    return economy_manager.join_tournament(ctx.user_id, tournament_id)

def _handle_tournament_list(ctx: RouterContext) -> Optional[str]:
    """Список активных турниров"""
    from economy_social import economy_manager
    return economy_manager.get_tournaments()

def _handle_leaderboard(ctx: RouterContext) -> Optional[str]:
    """Рейтинг по игре"""
    from economy_social import economy_manager
    game_type = ctx.text.strip() if ctx.text.strip() else "chess"
    return economy_manager.get_leaderboard(game_type)

def _handle_achievements(ctx: RouterContext) -> Optional[str]:
    """Показать достижения"""
    from economy_social import economy_manager
    return economy_manager.get_user_achievements(ctx.user_id)

# -------- Социальные команды --------
def _handle_profile(ctx: RouterContext) -> Optional[str]:
    """Показать профиль"""
    from economy_social import social_manager
    profile = social_manager.get_profile(ctx.user_id)
    return (
        f"👤 Профиль {profile.name}\n"
        f"📊 Уровень: {profile.level}\n"
        f"💕 Статус: {profile.relationship_status.value}\n"
        f"👥 Друзей: {len(profile.friends)}\n"
        f"🏰 Клан: {'Да' if profile.clan_id else 'Нет'}"
    )

def _handle_clan_create(ctx: RouterContext) -> Optional[str]:
    """Создание клана"""
    from economy_social import social_manager
    parts = ctx.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "❌ Использование: /clan create <название> <описание>"
    
    name = parts[0]
    description = parts[1] if len(parts) > 1 else "Новый клан"
    return social_manager.create_clan(ctx.user_id, name, description)

def _handle_clan_join(ctx: RouterContext) -> Optional[str]:
    """Присоединение к клану"""
    from economy_social import social_manager
    clan_id = ctx.text.strip()
    if not clan_id.isdigit():
        return "❌ ID клана должен быть числом"
    return social_manager.join_clan(ctx.user_id, int(clan_id))

def _handle_marry(ctx: RouterContext) -> Optional[str]:
    """Предложение брака"""
    from economy_social import social_manager
    partner_id = ctx.text.strip()
    if not partner_id.isdigit():
        return "❌ ID партнёра должен быть числом"
    return social_manager.propose_marriage(ctx.user_id, int(partner_id))

@require_admin
def _handle_config_backup(ctx: RouterContext) -> Optional[str]:
    if not ctx.is_dm:
        return "❌ Команда доступна только в ЛС"
    from admin import handle_admin_config_backup

    handle_admin_config_backup(ctx.vk, ctx.peer_id, ctx.user_id)
    return None


@require_admin
def _handle_config_list(ctx: RouterContext) -> Optional[str]:
    if not ctx.is_dm:
        return "❌ Команда доступна только в ЛС"
    from admin import handle_admin_config_list

    handle_admin_config_list(ctx.vk, ctx.peer_id, ctx.user_id)
    return None


@require_admin
def _handle_config_restore(ctx: RouterContext) -> Optional[str]:
    if not ctx.is_dm:
        return "❌ Команда доступна только в ЛС"
    from admin import handle_admin_config_restore

    idx_str = ctx.text.strip()
    handle_admin_config_restore(ctx.vk, ctx.peer_id, ctx.user_id, idx_str)
    return None

# -------- Команды управления ролями --------
def _handle_role_info(ctx: RouterContext) -> Optional[str]:
    """Показать информацию о роли пользователя"""
    from admin import get_user_role, get_user_privileges
    role = get_user_role(ctx.user_id)
    privileges = get_user_privileges(ctx.user_id)
    
    privilege_names = {
        "edit_content": "Редактирование контента",
        "view_stats": "Просмотр статистики", 
        "warn_users": "Предупреждение пользователей",
        "delete_messages": "Удаление сообщений",
        "kick_users": "Исключение пользователей",
        "ban_users": "Бан пользователей",
        "manage_roles": "Управление ролями",
        "ai_control": "Управление ИИ"
    }
    
    privilege_list = []
    for priv in privileges:
        if priv == "*":
            privilege_list.append("Все привилегии")
            break
        privilege_list.append(privilege_names.get(priv, priv))
    
    return f"👤 Ваша роль: {role.value}\n🔑 Привилегии:\n" + "\n".join(f"• {priv}" for priv in privilege_list)

@require_admin
def _handle_role_set(ctx: RouterContext) -> Optional[str]:
    """Установить роль пользователя (только для админов)"""
    from admin import can_manage_roles, UserRole
    from storage import set_user_profile, get_user_profile
    
    if not can_manage_roles(ctx.user_id):
        return "❌ Недостаточно прав для управления ролями"
    
    parts = ctx.text.split()
    if len(parts) < 3:
        return "Использование: /role set <user_id> <role>"
    
    try:
        target_id = int(parts[1])
        role_name = parts[2].lower()
        
        # Проверяем существование роли
        try:
            role = UserRole(role_name)
        except ValueError:
            return f"❌ Неизвестная роль: {role_name}. Доступные: {', '.join(r.value for r in UserRole)}"
        
        # Получаем текущий профиль
        profile = get_user_profile(target_id) or {}
        profile["role"] = role.value
        set_user_profile(target_id, profile)
        
        return f"✅ Роль пользователя {target_id} изменена на {role.value}"
    except ValueError:
        return "❌ Неверный ID пользователя"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

def _handle_role_list(ctx: RouterContext) -> Optional[str]:
    """Показать список ролей"""
    from admin import UserRole
    
    roles_info = []
    for role in UserRole:
        roles_info.append(f"• {role.value} - {_get_role_description(role)}")
    
    return "📋 Доступные роли:\n" + "\n".join(roles_info)

def _get_role_description(role) -> str:
    """Получить описание роли"""
    descriptions = {
        "user": "Обычный пользователь",
        "editor": "Может редактировать контент",
        "moderator": "Может модерировать чат", 
        "admin": "Полный доступ к функциям",
        "super_admin": "Создатель бота"
    }
    return descriptions.get(role.value, "Описание отсутствует")

# -------- Команды мониторинга и статистики --------
@require_admin
def _handle_stats(ctx: RouterContext) -> Optional[str]:
    """Показать статистику бота"""
    from admin import can_view_stats
    from monitoring import health_checker, metrics_collector
    
    if not can_view_stats(ctx.user_id):
        return "❌ Недостаточно прав для просмотра статистики"
    
    try:
        # Получаем статус здоровья
        health_status = health_checker.get_overall_status()
        
        # Получаем метрики
        total_requests = metrics_collector.get_counter("ai_requests_total")
        successful_requests = metrics_collector.get_counter("ai_success_total")
        failed_requests = metrics_collector.get_counter("ai_errors_total")
        
        # Вычисляем процент успешных запросов
        success_rate = 0.0
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
        
        # Получаем статистику кеша
        from cache_monitoring import cache_manager
        cache_stats = cache_manager.get_stats()
        cache_hit_rate = cache_stats.get("hit_rate", 0.0)
        
        # Получаем количество активных пользователей
        from storage import get_storage_from_env
        storage = get_storage_from_env()
        profiles = storage.get_all("profiles")
        active_users = 0
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        for user_id, profile in profiles.items():
            if isinstance(profile, dict) and 'last_activity' in profile:
                last_activity = profile.get('last_activity', 0)
                if last_activity > one_hour_ago:
                    active_users += 1
        
        stats_text = f"""📊 Статистика бота:

🏥 Статус: {health_status}
📈 Всего запросов ИИ: {total_requests}
✅ Успешных: {successful_requests}
❌ Ошибок: {failed_requests}
📊 Процент успеха: {success_rate:.1f}%
💾 Кеш (попадания): {cache_hit_rate:.1f}%
👥 Активных пользователей: {active_users}
"""
        
        return stats_text
    except Exception as e:
        return f"❌ Ошибка получения статистики: {str(e)}"

@require_admin
def _handle_health(ctx: RouterContext) -> Optional[str]:
    """Показать состояние здоровья системы"""
    from admin import can_view_stats
    from monitoring import health_checker
    
    if not can_view_stats(ctx.user_id):
        return "❌ Недостаточно прав для просмотра состояния системы"
    
    try:
        health_status = health_checker.check_health()
        overall_status = health_checker.get_overall_status()
        
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️", 
            "unhealthy": "❌"
        }
        
        health_text = f"🏥 Общее состояние: {status_emoji.get(overall_status, '❓')} {overall_status}\n\n"
        
        for service_name, status in health_status.items():
            emoji = status_emoji.get(status.status, "❓")
            health_text += f"{emoji} {service_name}: {status.message}\n"
        
        return health_text
    except Exception as e:
        return f"❌ Ошибка получения состояния: {str(e)}"

@require_admin
def _handle_cache_clear(ctx: RouterContext) -> Optional[str]:
    """Очистить кеш"""
    from admin import can_view_stats
    from cache_monitoring import cache_manager
    
    if not can_view_stats(ctx.user_id):
        return "❌ Недостаточно прав для управления кешем"
    
    try:
        # Получаем статистику до очистки
        stats_before = cache_manager.get_stats()
        items_before = stats_before.get("size", 0)
        
        # Очищаем кеш
        cache_manager.clear()
        
        return f"✅ Кеш очищен! Удалено {items_before} элементов."
    except Exception as e:
        return f"❌ Ошибка очистки кеша: {str(e)}"


# -------- Регистрация builtin-команд --------


def _register_builtin_commands() -> None:
    register_command(
        Command(
            name="/help",
            aliases=["help", "помощь", "halp", "команды"],
            description="Показать список команд",
            handler=_handle_help,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/admin",
            aliases=["admin", "админ"],
            description="Админ-меню (inline)",
            handler=lambda ctx: (_send_with_keyboard(ctx, t(ctx.user_id, "admin_menu"), _build_admin_main_inline_keyboard()) or None),
            admin_required=True,
            dm_only=True,
        )
    )

    # Основные команды
    register_command(
        Command(
            name="/start",
            aliases=["start", "начать"],
            description="Главное меню бота",
            handler=_handle_start,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/help",
            aliases=["help", "помощь"],
            description="Справка по командам",
            handler=_handle_help,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/menu",
            aliases=["menu", "меню"],
            description="Главное меню",
            handler=_handle_start,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/games",
            aliases=["games", "игры"],
            description="Меню игр",
            handler=_handle_games_menu,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/economy",
            aliases=["economy", "экономика"],
            description="Меню экономики",
            handler=_handle_economy_menu,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/social",
            aliases=["social", "социальное"],
            description="Меню социальных функций",
            handler=_handle_social_menu,
            admin_required=False,
        )
    )

    # Новые игры
    register_command(
        Command(
            name="/game",
            aliases=["game", "игра"],
            description="Универсальная команда для игр: /game <тип> <действие>",
            handler=_handle_game,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/conductor",
            aliases=["conductor", "проводница"],
            description="Игра 'Проводница РЖД'",
            handler=_handle_conductor,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/hangman",
            aliases=["hangman", "виселица"],
            description="Игра 'Виселица'",
            handler=_handle_hangman,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker",
            aliases=["poker", "покер"],
            description="Игра 'Покер'",
            handler=_handle_poker,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/conductor action",
            aliases=["conductor action", "проводница действие"],
            description="Действие в игре 'Проводница РЖД'",
            handler=_handle_conductor_action,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/hangman",
            aliases=["hangman", "виселица"],
            description="Игра 'Виселица'",
            handler=_handle_hangman,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker create",
            aliases=["poker create", "покер создать"],
            description="Создать покер-стол",
            handler=_handle_poker_create,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker join",
            aliases=["poker join", "покер присоединиться"],
            description="Присоединиться к покер-столу",
            handler=_handle_poker_join,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker start",
            aliases=["poker start", "покер начать"],
            description="Начать покер-игру",
            handler=_handle_poker_start,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker bet",
            aliases=["poker bet", "покер ставка"],
            description="Сделать ставку: /poker bet <amount>",
            handler=_handle_poker_bet,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker call",
            aliases=["poker call", "покер уравнять"],
            description="Уравнять ставку",
            handler=_handle_poker_call,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker fold",
            aliases=["poker fold", "покер сбросить"],
            description="Сбросить карты",
            handler=_handle_poker_fold,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/poker check",
            aliases=["poker check", "покер пас"],
            description="Пасовать (если нет ставок)",
            handler=_handle_poker_check,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/chess",
            aliases=["chess", "шахматы"],
            description="Игра 'Шахматы'",
            handler=_handle_chess,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/crossword",
            aliases=["crossword", "кроссворд"],
            description="Игра 'Кроссворды'",
            handler=_handle_crossword,
            admin_required=False,
        )
    )

    # Экономика
    register_command(
        Command(
            name="/daily",
            aliases=["daily", "бонус", "ежедневный"],
            description="Получить ежедневный бонус",
            handler=_handle_daily,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/balance",
            aliases=["balance", "баланс", "деньги"],
            description="Показать баланс",
            handler=_handle_balance,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/shop",
            aliases=["shop", "магазин"],
            description="Показать магазин",
            handler=_handle_shop,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/business",
            aliases=["business", "бизнес"],
            description="Космический бизнес — меню",
            handler=_handle_business,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/buy",
            aliases=["buy", "купить"],
            description="Купить предмет: /buy <id>",
            handler=_handle_buy,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/craft",
            aliases=["craft", "крафт"],
            description="Крафтинг предмета: /craft <recipe>",
            handler=_handle_craft,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/auction create",
            aliases=["auction create", "аукцион создать"],
            description="Создать аукцион: /auction create <item_id> <quantity> <price>",
            handler=_handle_auction_create,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/auction bid",
            aliases=["auction bid", "аукцион ставка"],
            description="Ставка на аукцион: /auction bid <auction_id> <amount>",
            handler=_handle_auction_bid,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/auction list",
            aliases=["auction list", "аукцион список"],
            description="Список активных аукционов",
            handler=_handle_auction_list,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/tournament create",
            aliases=["tournament create", "турнир создать"],
            description="Создать турнир: /tournament create <name> <game_type> <entry_fee>",
            handler=_handle_tournament_create,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/tournament join",
            aliases=["tournament join", "турнир присоединиться"],
            description="Присоединиться к турниру: /tournament join <tournament_id>",
            handler=_handle_tournament_join,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/tournament list",
            aliases=["tournament list", "турнир список"],
            description="Список активных турниров",
            handler=_handle_tournament_list,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/leaderboard",
            aliases=["leaderboard", "рейтинг"],
            description="Рейтинг по игре: /leaderboard <game_type>",
            handler=_handle_leaderboard,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/achievements",
            aliases=["achievements", "достижения"],
            description="Показать ваши достижения",
            handler=_handle_achievements,
            admin_required=False,
        )
    )

    # Социальное
    register_command(
        Command(
            name="/profile",
            aliases=["profile", "профиль"],
            description="Показать профиль",
            handler=_handle_profile,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/clan create",
            aliases=["clan create", "клан создать"],
            description="Создать клан: /clan create <название> <описание>",
            handler=_handle_clan_create,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/clan join",
            aliases=["clan join", "клан присоединиться"],
            description="Присоединиться к клану: /clan join <id>",
            handler=_handle_clan_join,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/marry",
            aliases=["marry", "жениться"],
            description="Предложить брак: /marry <user_id>",
            handler=_handle_marry,
            admin_required=False,
        )
    )

    # /config backup|list|restore — только ЛС и только админам
    register_command(
        Command(
            name="/config backup",
            aliases=["config backup"],
            description="Создать бэкап конфигурации",
            handler=_handle_config_backup,
            admin_required=True,
            dm_only=True,
        )
    )
    register_command(
        Command(
            name="/config list",
            aliases=["config list"],
            description="Список бэкапов конфигурации",
            handler=_handle_config_list,
            admin_required=True,
            dm_only=True,
        )
    )
    register_command(
        Command(
            name="/config restore",
            aliases=["config restore"],
            description="Восстановить конфиг из бэкапа: /config restore <номер>",
            handler=_handle_config_restore,
            admin_required=True,
            dm_only=True,
        )
    )

    # Команды управления ролями
    register_command(
        Command(
            name="/role info",
            aliases=["role info", "роль инфо"],
            description="Показать информацию о своей роли",
            handler=_handle_role_info,
            admin_required=False,
        )
    )
    register_command(
        Command(
            name="/role set",
            aliases=["role set", "роль установить"],
            description="Установить роль пользователя: /role set <user_id> <role>",
            handler=_handle_role_set,
            admin_required=True,
        )
    )
    register_command(
        Command(
            name="/role list",
            aliases=["role list", "роль список"],
            description="Показать список доступных ролей",
            handler=_handle_role_list,
            admin_required=False,
        )
    )

    # Команды мониторинга
    register_command(
        Command(
            name="/stats",
            aliases=["stats", "статистика"],
            description="Показать статистику бота",
            handler=_handle_stats,
            admin_required=True,
        )
    )
    register_command(
        Command(
            name="/health",
            aliases=["health", "здоровье"],
            description="Показать состояние системы",
            handler=_handle_health,
            admin_required=True,
        )
    )
    register_command(
        Command(
            name="/cache clear",
            aliases=["cache clear", "кеш очистить"],
            description="Очистить кеш",
            handler=_handle_cache_clear,
            admin_required=True,
        )
    )


# Инициализация регистра при импорте модуля
_register_builtin_commands()


def _handle_start(ctx: RouterContext) -> Optional[str]:
    """Главное меню бота"""
    message = """🎮 **CryBot** — игровой бот для ВКонтакте

Привет! Я бот с играми, экономикой и социальными функциями.

**🎯 Что умею:**
• 🚂 Проводница РЖД — помоги пассажирам
• 🎯 Виселица — угадай слово по буквам  
• 🃏 Покер — карточная игра
• 💰 Экономика — магазин, крафтинг, аукционы
• 👥 Социальное — друзья, кланы, браки

Выбери, что хочешь сделать:"""

    # Создаем inline-клавиатуру
    keyboard = VkKeyboard(inline=True)
    
    # Первый ряд: Игры
    keyboard.add_button("🎮 Игры", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("💰 Экономика", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    
    # Второй ряд: Социальное и Профиль
    keyboard.add_button("👥 Социальное", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("👤 Профиль", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    
    # Третий ряд: Помощь и Настройки
    keyboard.add_button("❓ Помощь", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("⚙️ Настройки", color=VkKeyboardColor.SECONDARY)
    
    _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    return None

def _handle_games_menu(ctx: RouterContext) -> Optional[str]:
    """Меню игр"""
    message = """🎮 **Игры**

Выбери игру для начала:

**🚂 Проводница РЖД**
Помоги пассажирам и проверь билеты. 5 поездов за смену!

**🎯 Виселица**  
Угадай слово по буквам. Максимум 6 ошибок!

**🃏 Покер**
Карточная игра с фишками и ставками."""

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🚂 Проводница РЖД", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🎯 Виселица", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🃏 Покер", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Назад", color=VkKeyboardColor.SECONDARY)
    
    _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    return None

def _handle_economy_menu(ctx: RouterContext) -> Optional[str]:
    """Меню экономики"""
    from economy_social import economy_manager, Currency
    
    wallet = economy_manager.get_wallet(ctx.user_id)
    balance = wallet.balance.get(Currency.CRYCOIN, 0)
    
    message = f"""💰 **Экономика**

Твой баланс: **{balance} 🪙**

**🛒 Магазин** — покупай предметы и бустеры
**🔨 Крафтинг** — создавай предметы из материалов  
**🏷️ Аукционы** — торгуйся за редкие вещи
**🏆 Турниры** — участвуй в соревнованиях
**📊 Рейтинги** — смотри топ игроков"""

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🛒 Магазин", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🔨 Крафтинг", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🏷️ Аукционы", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🏆 Турниры", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("📊 Рейтинги", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("💰 Баланс", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Назад", color=VkKeyboardColor.SECONDARY)
    
    _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    return None

def _handle_social_menu(ctx: RouterContext) -> Optional[str]:
    """Меню социальных функций"""
    from economy_social import social_manager
    
    profile = social_manager.get_profile(ctx.user_id)
    
    message = f"""👥 **Социальное**

**👤 Профиль:** {profile.name}
**💕 Статус:** {profile.relationship_status.value}
**👥 Друзей:** {len(profile.friends)}
**🏰 Клан:** {'Да' if profile.clan_id else 'Нет'}

**👥 Друзья** — добавляй и общайся
**🏰 Кланы** — создавай и присоединяйся
**💍 Браки** — предложи руку и сердце
**🏆 Достижения** — смотри свои награды"""

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("👥 Друзья", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🏰 Кланы", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("💍 Браки", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🏆 Достижения", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔙 Назад", color=VkKeyboardColor.SECONDARY)
    
    _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    return None

def _handle_chess(ctx: RouterContext) -> Optional[str]:
    from games_extended import game_engine
    message, buttons = game_engine.start_game(ctx.user_id, ctx.peer_id, "chess")
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:
                keyboard.add_line()
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    return None

def _handle_crossword(ctx: RouterContext) -> Optional[str]:
    from games_extended import game_engine
    message, buttons = game_engine.start_game(ctx.user_id, ctx.peer_id, "crossword")
    if buttons:
        keyboard = VkKeyboard(inline=True)
        for i, button in enumerate(buttons):
            keyboard.add_button(button["label"], color=VkKeyboardColor.PRIMARY)
            if i % 2 == 1:
                keyboard.add_line()
        _send_with_keyboard(ctx, message, keyboard.get_keyboard())
    else:
        _send_with_keyboard(ctx, message, None)
    return None

