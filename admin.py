"""
Админ модуль для управления ботом
"""
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from ai import runtime_settings, export_ai_settings, import_ai_settings, reset_ai_settings
from config import (
    export_config,
    import_config,
    backup_config_file,
    list_config_backups,
    restore_config_from_backup,
)

# ---------- Система ролей ----------
class UserRole(Enum):
    USER = "user"
    EDITOR = "editor"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

@dataclass
class UserProfile:
    user_id: int
    role: UserRole
    ai_provider: str = "AUTO"
    ai_model: str = ""
    temperature: float = 0.6
    top_p: float = 1.0
    max_tokens: int = 80
    max_chars: int = 380
    max_history: int = 8
    created_at: float = 0.0
    last_activity: float = 0.0

# ---------- Per-chat настройки ----------
@dataclass
class ChatSettings:
    chat_id: int
    ai_provider: str = "AUTO"
    ai_model: str = ""
    temperature: float = 0.6
    top_p: float = 1.0
    max_tokens: int = 80
    max_chars: int = 380
    max_history: int = 8
    rate_limit: int = 10
    rate_window: int = 60
    created_at: float = 0.0
    updated_at: float = 0.0

# ---------- Пресеты настроек ----------
class AIPresets:
    PRESETS = {
        "Коротко": {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 50,
            "max_chars": 200,
            "max_history": 4
        },
        "Детально": {
            "temperature": 0.8,
            "top_p": 1.0,
            "max_tokens": 200,
            "max_chars": 600,
            "max_history": 12
        },
        "Дешево": {
            "temperature": 0.5,
            "top_p": 0.8,
            "max_tokens": 30,
            "max_chars": 150,
            "max_history": 3
        },
        "Креативно": {
            "temperature": 1.2,
            "top_p": 1.0,
            "max_tokens": 150,
            "max_chars": 500,
            "max_history": 8
        }
    }
    
    @classmethod
    def get_preset(cls, name: str) -> Optional[Dict]:
        return cls.PRESETS.get(name)
    
    @classmethod
    def list_presets(cls) -> List[str]:
        return list(cls.PRESETS.keys())
    
    @classmethod
    def apply_preset(cls, name: str) -> bool:
        preset = cls.get_preset(name)
        if not preset:
            return False
            
        for key, value in preset.items():
            if hasattr(runtime_settings, key):
                setattr(runtime_settings, key, value)
        return True

# ---------- Пагинация и поиск ----------
class Paginator:
    def __init__(self, items: List, page_size: int = 10):
        self.items = items
        self.page_size = page_size
        self.current_page = 0
        
    def get_page(self, page: int) -> Tuple[List, int, int, int]:
        """Возвращает страницу, текущую страницу, общее количество страниц"""
        if page < 0:
            page = 0
        if page >= self.total_pages:
            page = self.total_pages - 1
            
        start = page * self.page_size
        end = start + self.page_size
        page_items = self.items[start:end]
        
        return page_items, page, self.total_pages, len(self.items)
    
    @property
    def total_pages(self) -> int:
        return (len(self.items) + self.page_size - 1) // self.page_size
    
    def next_page(self) -> int:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        return self.current_page
    
    def prev_page(self) -> int:
        if self.current_page > 0:
            self.current_page -= 1
        return self.current_page

class ModelSearch:
    def __init__(self):
        self.models = [
            "deepseek/deepseek-chat-v3-0324:free",
            "deepseek/deepseek-r1-distill-llama-70b:free",
            "deepseek/deepseek-r1-0528:free",
            "qwen/qwen3-coder:free",
            "deepseek/deepseek-r1:free",
            "gpt-5-nano",
            "gpt-3.5-turbo",
            "deepseek-chat",
            "gemini-flash-1.5-8b"
        ]
    
    def search(self, query: str) -> List[str]:
        """Поиск моделей по запросу"""
        query = query.lower()
        results = []
        
        for model in self.models:
            if query in model.lower():
                results.append(model)
        
        return results
    
    def get_all(self) -> List[str]:
        return self.models.copy()

# ---------- Клавиатуры админки ----------
def build_admin_keyboard() -> Dict:
    """Основная админ клавиатура"""
    keyboard = VkKeyboard(one_time=False, inline=False)
    
    # AI модели
    keyboard.add_button("🤖 AI модели", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_ai_models"})
    keyboard.add_button("⚙️ AI настройки", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_ai_settings"})
    keyboard.add_line()
    
    # Игры и статистика
    keyboard.add_button("🎮 Игры", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_games"})
    keyboard.add_button("📊 Статистика", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_stats"})
    keyboard.add_line()
    
    # Система
    keyboard.add_button("🔧 Система", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_system"})
    keyboard.add_button("👥 Пользователи", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_users"})
    keyboard.add_line()
    
    # Мониторинг
    keyboard.add_button("📈 Мониторинг", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_monitoring"})
    keyboard.add_button("🚨 Логи", color=VkKeyboardColor.NEGATIVE, payload={"action": "admin_logs"})
    
    return keyboard.get_keyboard()

def build_ai_settings_keyboard() -> Dict:
    """Клавиатура AI настроек"""
    keyboard = VkKeyboard(one_time=False, inline=False)
    
    # Ряд 1: температура
    keyboard.add_button("🌡️ -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_temp_down"})
    keyboard.add_button("🌡️ Температура", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_temp_info"})
    keyboard.add_button("🌡️ +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_temp_up"})
    keyboard.add_line()
    
    # Ряд 2: top-p
    keyboard.add_button("📊 -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_top_p_down"})
    keyboard.add_button("📊 Top-P", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_top_p_info"})
    keyboard.add_button("📊 +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_top_p_up"})
    keyboard.add_line()
    
    # Ряд 3: max tokens OpenRouter
    keyboard.add_button("🔢 -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_max_or_down"})
    keyboard.add_button("🔢 Max OR", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_max_or_info"})
    keyboard.add_button("🔢 +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_max_or_up"})
    keyboard.add_line()
    
    # Ряд 4: max tokens AITunnel
    keyboard.add_button("🔢 -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_max_at_down"})
    keyboard.add_button("🔢 Max AT", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_max_at_info"})
    keyboard.add_button("🔢 +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_max_at_up"})
    keyboard.add_line()
    
    # Ряд 5: reasoning
    keyboard.add_button("🧠 Вкл/Выкл", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_reason_toggle"})
    keyboard.add_button("🧠 Токены -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_reason_tokens_down"})
    keyboard.add_button("🧠 Токены +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_reason_tokens_up"})
    keyboard.add_line()
    
    # Ряд 6: reasoning depth
    keyboard.add_button("🧠 Глубина", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_reason_depth_cycle"})
    keyboard.add_button("📚 История -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_hist_down"})
    keyboard.add_button("📚 История +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_hist_up"})
    keyboard.add_line()
    
    # Ряд 7: символы и fallback
    keyboard.add_button("🔤 Символы -", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_chars_down"})
    keyboard.add_button("🔤 Символы +", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_chars_up"})
    keyboard.add_button("Fallback on/off", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_fallback_toggle"})
    keyboard.add_line()
    
    # Ряд 8: провайдер и показать
    keyboard.add_button("Провайдер", color=VkKeyboardColor.PRIMARY, payload={"action": "admin_ai_provider"})
    keyboard.add_button("Показать", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_current"})
    keyboard.add_line()
    
    # Ряд 9: экспорт/импорт
    keyboard.add_button("📤 Экспорт", color=VkKeyboardColor.POSITIVE, payload={"action": "ai_export_settings"})
    keyboard.add_button("📥 Импорт", color=VkKeyboardColor.POSITIVE, payload={"action": "ai_import_settings"})
    keyboard.add_line()
    
    # Ряд 10: сброс и назад
    keyboard.add_button("🔄 Сброс", color=VkKeyboardColor.NEGATIVE, payload={"action": "ai_reset_settings"})
    keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
    
    return keyboard.get_keyboard()

def build_ai_models_keyboard(page: int = 0, search_query: str = "") -> Dict:
    """Клавиатура AI моделей с пагинацией"""
    keyboard = VkKeyboard(one_time=False, inline=False)
    
    model_search = ModelSearch()
    if search_query:
        models = model_search.search(search_query)
    else:
        models = model_search.get_all()
    
    paginator = Paginator(models, page_size=5)
    page_items, current_page, total_pages, total_items = paginator.get_page(page)
    
    # Показываем модели на текущей странице
    for model in page_items:
        keyboard.add_button(f"🤖 {model[:30]}...", color=VkKeyboardColor.PRIMARY, 
                           payload={"action": "ai_model_select", "model": model})
        keyboard.add_line()
    
    # Навигация по страницам
    if total_pages > 1:
        if current_page > 0:
            keyboard.add_button("⬅️ Назад", color=VkKeyboardColor.SECONDARY, 
                               payload={"action": "ai_models_page", "page": current_page - 1})
        
        keyboard.add_button(f"📄 {current_page + 1}/{total_pages}", color=VkKeyboardColor.PRIMARY, 
                           payload={"action": "ai_models_info"})
        
        if current_page < total_pages - 1:
            keyboard.add_button("Вперед ➡️", color=VkKeyboardColor.SECONDARY, 
                               payload={"action": "ai_models_page", "page": current_page + 1})
        keyboard.add_line()
    
    # Поиск
    keyboard.add_button("🔍 Поиск", color=VkKeyboardColor.PRIMARY, payload={"action": "ai_models_search"})
    keyboard.add_button("📋 Все модели", color=VkKeyboardColor.SECONDARY, payload={"action": "ai_models_all"})
    keyboard.add_line()
    
    # Назад
    keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
    
    return keyboard.get_keyboard()

def build_presets_keyboard() -> Dict:
    """Клавиатура пресетов"""
    keyboard = VkKeyboard(one_time=False, inline=False)
    
    presets = AIPresets.list_presets()
    for i, preset in enumerate(presets):
        color = VkKeyboardColor.PRIMARY if i % 2 == 0 else VkKeyboardColor.SECONDARY
        keyboard.add_button(f"⚙️ {preset}", color=color, payload={"action": "ai_preset_apply", "preset": preset})
        if i % 2 == 1:
            keyboard.add_line()
    
    if len(presets) % 2 == 1:
        keyboard.add_line()
    
    keyboard.add_button("← Назад", color=VkKeyboardColor.SECONDARY, payload={"action": "admin_back"})
    
    return keyboard.get_keyboard()

# ---------- Админ функции ----------
def handle_admin_ai_settings(vk, peer_id: int, user_id: int) -> None:
    """Показывает AI настройки"""
    text = (
        f"⚙️ AI настройки:\n\n"
        f"Провайдер: {runtime_settings.or_to_at_fallback}\n"
        f"Температура: {runtime_settings.temperature}\n"
        f"Top-P: {runtime_settings.top_p}\n"
        f"Макс. токены OR: {runtime_settings.max_tokens_or}\n"
        f"Макс. токены AT: {runtime_settings.max_tokens_at}\n"
        f"Макс. символы: {runtime_settings.max_ai_chars}\n"
        f"История: {runtime_settings.max_history}\n"
        f"Ретраи OR: {runtime_settings.or_retries}\n"
        f"Ретраи AT: {runtime_settings.at_retries}\n"
        f"Таймаут OR: {runtime_settings.or_timeout}s\n"
        f"Таймаут AT: {runtime_settings.at_timeout}s\n"
        f"Reasoning: {'Вкл' if runtime_settings.reasoning_enabled else 'Выкл'}\n"
        f"Fallback OR→AT: {'Вкл' if runtime_settings.or_to_at_fallback else 'Выкл'}"
    )
    send_message(vk, peer_id, text, keyboard=build_ai_settings_keyboard())

def handle_admin_ai_models(vk, peer_id: int, user_id: int, page: int = 0) -> None:
    """Показывает AI модели с пагинацией"""
    text = "🤖 Доступные AI модели:\n\n"
    text += "Выберите модель для настройки или используйте поиск."
    
    send_message(vk, peer_id, text, keyboard=build_ai_models_keyboard(page))

def handle_admin_presets(vk, peer_id: int, user_id: int) -> None:
    """Показывает пресеты настроек"""
    text = "⚙️ Пресеты AI настроек:\n\n"
    presets = AIPresets.list_presets()
    for preset in presets:
        text += f"• {preset}\n"
    text += "\nВыберите пресет для применения."
    
    send_message(vk, peer_id, text, keyboard=build_presets_keyboard())

def handle_admin_export_ai_settings(vk, peer_id: int, user_id: int) -> None:
    """Экспортирует AI настройки"""
    settings_json = export_ai_settings()
    text = f"📤 AI настройки экспортированы:\n\n```json\n{settings_json}\n```"
    send_message(vk, peer_id, text, keyboard=build_ai_settings_keyboard())

def handle_admin_import_ai_settings(vk, peer_id: int, user_id: int, settings_json: str) -> None:
    """Импортирует AI настройки"""
    if import_ai_settings(settings_json):
        text = "✅ AI настройки успешно импортированы!"
    else:
        text = "❌ Ошибка при импорте настроек. Проверьте формат JSON."
    
    send_message(vk, peer_id, text, keyboard=build_ai_settings_keyboard())

def handle_admin_reset_ai_settings(vk, peer_id: int, user_id: int) -> None:
    """Сбрасывает AI настройки"""
    reset_ai_settings()
    text = "🔄 AI настройки сброшены к значениям по умолчанию."
    send_message(vk, peer_id, text, keyboard=build_ai_settings_keyboard())

def handle_admin_apply_preset(vk, peer_id: int, user_id: int, preset_name: str) -> None:
    """Применяет пресет настроек"""
    if AIPresets.apply_preset(preset_name):
        text = f"✅ Пресет '{preset_name}' применен!"
    else:
        text = f"❌ Пресет '{preset_name}' не найден."
    
    send_message(vk, peer_id, text, keyboard=build_presets_keyboard())

# ---------- Конфигурация бота: бэкап/лист/восстановление ----------
def handle_admin_config_backup(vk, peer_id: int, user_id: int) -> None:
    """Создает резервную копию config.json"""
    path = backup_config_file()
    if path:
        text = f"✅ Бэкап конфигурации создан: {path}"
    else:
        text = "❌ Не удалось создать бэкап (возможно, config.json отсутствует)."
    send_message(vk, peer_id, text)

def handle_admin_config_list(vk, peer_id: int, user_id: int) -> None:
    """Показывает список доступных бэкапов"""
    backups = list_config_backups()
    if not backups:
        text = "ℹ️ Бэкапы не найдены."
    else:
        lines = "\n".join(f"{idx+1}. {p}" for idx, p in enumerate(backups))
        text = f"📚 Доступные бэкапы:\n\n{lines}\n\nВосстановление: /config restore <номер>"
    send_message(vk, peer_id, text)

def handle_admin_config_restore(vk, peer_id: int, user_id: int, idx_str: str) -> None:
    """Восстанавливает конфигурацию из бэкапа по индексу из списка"""
    try:
        idx = int(idx_str) - 1
    except Exception:
        send_message(vk, peer_id, "❌ Использование: /config restore <номер> (см. /config list)")
        return
    backups = list_config_backups()
    if idx < 0 or idx >= len(backups):
        send_message(vk, peer_id, "❌ Неверный номер бэкапа")
        return
    ok = restore_config_from_backup(backups[idx])
    if ok:
        text = f"✅ Конфигурация восстановлена из: {backups[idx]}"
    else:
        text = "❌ Не удалось восстановить конфигурацию"
    send_message(vk, peer_id, text)

# ---------- Вспомогательные функции ----------
def send_message(vk, peer_id: int, text: str, keyboard: Optional[Dict] = None) -> None:
    """Отправляет сообщение с клавиатурой"""
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=text,
            keyboard=keyboard,
            random_id=0
        )
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def is_admin(user_id: int, admin_ids: set) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in admin_ids

def get_user_role(user_id: int) -> UserRole:
    """Получает роль пользователя"""
    # TODO: Реализовать систему ролей
    return UserRole.USER

def create_user_profile(user_id: int) -> UserProfile:
    """Создает профиль пользователя"""
    return UserProfile(
        user_id=user_id,
        role=UserRole.USER,
        created_at=time.time()
    )

def create_chat_settings(chat_id: int) -> ChatSettings:
    """Создает настройки чата"""
    return ChatSettings(
        chat_id=chat_id,
        created_at=time.time()
    )