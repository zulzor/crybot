"""
Простой i18n слой: ru/en с выбором языка для пользователя
"""
from __future__ import annotations

from typing import Dict
from economy_social import social_manager


RU: Dict[str, str] = {
    "help_title": "CryBot — команды:",
    "shop_title": "🛒 Магазин:",
    "business_title": "🏢 Космический бизнес",
    "admin_menu": "Админ‑меню:",
    "select_storage": "Выберите бэкенд хранилища:",
    "select_lang": "Выберите язык интерфейса:",
    "lang_set": "✅ Язык интерфейса: {lang}.",
}

EN: Dict[str, str] = {
    "help_title": "CryBot — commands:",
    "shop_title": "🛒 Shop:",
    "business_title": "🏢 Cosmic Business",
    "admin_menu": "Admin menu:",
    "select_storage": "Select storage backend:",
    "select_lang": "Choose interface language:",
    "lang_set": "✅ Language set: {lang}.",
}


def get_lang_for_user(user_id: int) -> str:
    try:
        profile = social_manager.get_profile(user_id)
        lang = getattr(profile, "preferred_language", "ru") or "ru"
        return lang if lang in ("ru", "en") else "ru"
    except Exception:
        return "ru"


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_lang_for_user(user_id)
    table = RU if lang == "ru" else EN
    text = table.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

