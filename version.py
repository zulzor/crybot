import os
import subprocess
from datetime import datetime


def get_version() -> str:
    """Возвращает строку версии бота.
    Приоритет:
    1) BOT_VERSION из окружения
    2) git describe --tags/--always
    3) короткий commit (git rev-parse --short HEAD)
    4) fallback: dev-YYYYmmDDHHMM
    """
    env_ver = os.getenv("BOT_VERSION")
    if env_ver:
        return env_ver

    # Попытка получить версию из git
    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty", "--abbrev=7"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if out:
            return out
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if out:
            return out
    except Exception:
        pass

    return "dev-" + datetime.utcnow().strftime("%Y%m%d%H%M")