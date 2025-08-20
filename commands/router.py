from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
import time


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


# Инициализация регистра при импорте модуля
_register_builtin_commands()

