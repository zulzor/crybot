# Obsolete compatibility entry-point for older bot_vk.py

from typing import Optional, Tuple
from version import get_version


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
    """Минимальная совместимая реализация маршрутизатора команд.
    Возвращает (handled, reply). Если reply is None, отправка вне роутера.
    """
    if not text:
        return False, None

    lower = text.strip().lower()

    if lower in {"/start", "start", "начать"}:
        ver = get_version()
        if is_dm:
            msg = (
                f"🎮 CryBot\n\n"
                f"Версия: `{ver}`\n\n"
                f"Доступно:\n"
                f"• 🎮 Игры\n"
                f"• 🤖 ИИ-чат\n"
                f"• 🌐 Язык\n"
                f"• 🔐 Админ\n"
            )
        else:
            msg = (
                f"👋 CryBot (версия: `{ver}`)\n\n"
                f"В этом чате доступны: 🎮 Игры, 🤖 ИИ-чат, 🆘 Помощь, 🌐 Язык, 📖 Инструкция, 🗺️ Карта бота."
            )
        return True, msg

    if lower in {"/help", "help", "помощь"}:
        return True, "Доступно: /start, /help. Остальные команды временно недоступны."

    # Необработанная команда
    return False, None