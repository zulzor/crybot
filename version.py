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


def get_build() -> str:
    """Возвращает строку сборки бота.
    Приоритет:
    1) BOT_BUILD из окружения
    2) дата последнего коммита + короткий хеш (YYYY-mm-dd-HHMMSS-<sha7>)
    3) fallback: UTC timestamp YYYY-mm-dd-HHMMSS
    """
    env_build = os.getenv("BOT_BUILD")
    if env_build:
        return env_build

    try:
        date_str = subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%cd",
                "--date=format:%Y-%m-%d-%H%M%S",
                "HEAD",
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if date_str and short:
            return f"{date_str}-{short}"
    except Exception:
        pass

    return datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")