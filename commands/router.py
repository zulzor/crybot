# Obsolete compatibility entry-point for older bot_vk.py

def configure_router() -> None:
    """Инициализирует реестр команд. Совместимость со старым bot_vk.py."""
    # Инициализация уже происходит при импорте в конце файла вызовом
    # _register_builtin_commands(). Оставляем функцию-пустышку для совместимости.
    return None