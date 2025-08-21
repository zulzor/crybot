# Obsolete compatibility entry-point for older bot_vk.py

from typing import Optional, Tuple
from version import get_version
from storage import get_storage_from_env

# Состояние ожидания имени в памяти процесса
_awaiting_name = set()


def _get_profile(storage, user_id: int) -> dict:
    prof = storage.get("profiles", str(user_id)) or {}
    if "created_at" not in prof:
        import time as _t
        prof["created_at"] = _t.time()
    return prof


def _save_profile(storage, user_id: int, prof: dict) -> None:
    storage.set("profiles", str(user_id), prof)


def _inline_keyboard(vk, peer_id: int, rows: list[list[str]]) -> None:
    from vk_api.keyboard import VkKeyboard, VkKeyboardColor
    kb = VkKeyboard(inline=True)
    first = True
    for row in rows:
        if not first:
            kb.add_line()
        first = False
        for label in row:
            kb.add_button(label, color=VkKeyboardColor.PRIMARY)
    vk.messages.send(peer_id=peer_id, message=" ", random_id=0, keyboard=kb.get_keyboard())


def configure_router() -> None:
    """Инициализирует реестр команд. Совместимость со старым bot_vk.py."""
    # Инициализация уже происходит при импорте в конце файла вызовом
    # _register_builtin_commands(). Оставляем функцию-пустышку для совместимости.
    return None


def dispatch_command(
    text: str,
    vk: object,
    peer_id: int,
    user_id: int,
    is_dm: bool,
) -> Tuple[bool, Optional[str]]:
    if not text:
        return False, None

    storage = get_storage_from_env()
    lower = text.strip().lower()

    # Ловушка ввода имени
    if user_id in _awaiting_name and lower not in {"/start", "/games", "/help"}:
        name = text.strip()
        prof = _get_profile(storage, user_id)
        prof["name"] = name
        prof["privacy_accept"] = True
        _save_profile(storage, user_id, prof)
        _awaiting_name.discard(user_id)
        return True, f"✅ Спасибо, {name}! Доступ к играм открыт. Откройте 🎮 Игры."

    if lower in {"/start", "start", "начать"}:
        ver = get_version()
        msg = (
            f"🎮 CryBot\n\nВерсия: `{ver}`\n\nВыберите раздел:" if is_dm else f"👋 CryBot (версия `{ver}`)"
        )
        if is_dm:
            from vk_api.keyboard import VkKeyboard, VkKeyboardColor
            kb = VkKeyboard(inline=True)
            for label in ["🛒 Экономика", "👥 Социальное"]:
                kb.add_button(label, color=VkKeyboardColor.PRIMARY)
            kb.add_line()
            for label in ["🎮 Игры", "🤖 ИИ-чат"]:
                kb.add_button(label, color=VkKeyboardColor.PRIMARY)
            kb.add_line()
            for label in ["🌐 Язык", "🔐 Админ"]:
                kb.add_button(label, color=VkKeyboardColor.SECONDARY)
            kb.add_line()
            for label in ["📖 Инструкция", "🗺️ Карта бота"]:
                kb.add_button(label, color=VkKeyboardColor.SECONDARY)
            vk.messages.send(peer_id=peer_id, message=msg, random_id=0, keyboard=kb.get_keyboard())
            return True, None
        return True, msg

    if lower in {"/games", "🎮 игры"}:
        prof = _get_profile(storage, user_id)
        if not prof.get("privacy_accept") or not prof.get("name"):
            # показать регистрацию
            msg = (
                "📝 Регистрация\n\nДля доступа к играм примите политику и введите имя."
            )
            from vk_api.keyboard import VkKeyboard, VkKeyboardColor
            kb = VkKeyboard(inline=True)
            kb.add_button("✅ Принять политику", color=VkKeyboardColor.PRIMARY)
            kb.add_line()
            kb.add_button("📄 Политика", color=VkKeyboardColor.SECONDARY)
            vk.messages.send(peer_id=peer_id, message=msg, random_id=0, keyboard=kb.get_keyboard())
            return True, None
        # меню игр
        return True, "🎮 Игры: 🚂 Проводница, 🎯 Виселица, 🃏 Покер (кнопки далее)."

    if lower in {"✅ принять политику", "accept_privacy"}:
        prof = _get_profile(storage, user_id)
        prof["privacy_accept"] = True
        _save_profile(storage, user_id, prof)
        _awaiting_name.add(user_id)
        return True, "✍️ Введите имя (одной строкой):"

    if lower in {"📄 политика", "show_privacy"}:
        return True, "Политика: см. файл PRIVACY_POLICY.md или /privacy"

    if lower in {"/help", "help", "помощь"}:
        return True, "Доступно: /start, /games. Для начала — /start."

    return False, None