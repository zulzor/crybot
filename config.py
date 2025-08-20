"""
Конфигурация бота
"""
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# ---------- Базовые настройки ----------
@dataclass
class BotConfig:
    """Основная конфигурация бота"""
    
    # Основные настройки
    bot_name: str = "CryCat Bot"
    bot_version: str = "2.0.0"
    bot_description: str = "AI-powered VK bot with games and content"
    
    # VK настройки
    vk_group_token: str = ""
    vk_group_id: int = 0
    vk_api_version: str = "5.131"
    
    # AI настройки
    ai_provider: str = "AUTO"  # AUTO, OPENROUTER, AITUNNEL
    openrouter_api_key: str = ""
    openrouter_models: List[str] = field(default_factory=lambda: [
        "deepseek/deepseek-chat-v3-0324:free",
        "deepseek/deepseek-r1-distill-llama-70b:free",
        "deepseek/deepseek-r1-0528:free",
        "qwen/qwen3-coder:free",
        "deepseek/deepseek-r1:free"
    ])
    aitunnel_api_url: str = "https://api.aitunnel.ru/v1"
    aitunnel_api_key: str = ""
    aitunnel_models: List[str] = field(default_factory=lambda: [
        "deepseek-r1-fast",
        "gpt-5-nano",
        "gpt-3.5-turbo",
        "deepseek-chat",
        "gemini-flash-1.5-8b"
    ])
    
    # Runtime AI параметры
    runtime_temperature: float = 0.6
    runtime_top_p: float = 1.0
    runtime_max_tokens_or: int = 80
    runtime_max_tokens_at: int = 5000
    runtime_reasoning_enabled: bool = False
    runtime_reasoning_tokens: int = 100
    runtime_reasoning_depth: str = "medium"
    runtime_max_history: int = 8
    runtime_max_ai_chars: int = 380
    runtime_or_retries: int = 2
    runtime_at_retries: int = 2
    runtime_or_timeout: int = 60
    runtime_at_timeout: int = 60
    runtime_or_to_at_fallback: bool = True
    
    # Админ настройки
    admin_user_ids: List[int] = field(default_factory=list)
    admin_commands_enabled: bool = True
    admin_logging_enabled: bool = True
    
    # Игры
    games_enabled: bool = True
    max_games_per_chat: int = 3
    game_timeout_hours: int = 24
    
    # Мониторинг
    monitoring_enabled: bool = True
    metrics_collection: bool = True
    health_checks: bool = True
    log_level: str = "INFO"
    log_file: Optional[str] = "bot.log"
    
    # Стриминг
    streaming_enabled: bool = True
    chunk_delay: float = 0.1
    max_streaming_time: int = 300
    
    # Контент и монетизация
    content_enabled: bool = True
    daily_tasks_enabled: bool = True
    seasonal_events_enabled: bool = True
    boosters_enabled: bool = True
    
    # Безопасность
    content_filtering: bool = True
    rate_limiting: bool = True
    max_requests_per_minute: int = 10
    
    # Webhook
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_port: int = 8080
    
    # YooMoney
    yoomoney_enabled: bool = False
    yoomoney_secret: str = ""
    
    # Локализация
    default_language: str = "ru"
    supported_languages: List[str] = field(default_factory=lambda: ["ru", "en"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует конфигурацию в словарь"""
        return {
            "bot_name": self.bot_name,
            "bot_version": self.bot_version,
            "bot_description": self.bot_description,
            "vk_group_token": self.vk_group_token,
            "vk_group_id": self.vk_group_id,
            "vk_api_version": self.vk_api_version,
            "ai_provider": self.ai_provider,
            "openrouter_api_key": self.openrouter_api_key,
            "openrouter_models": self.openrouter_models,
            "aitunnel_api_url": self.aitunnel_api_url,
            "aitunnel_api_key": self.aitunnel_api_key,
            "aitunnel_models": self.aitunnel_models,
            "runtime_temperature": self.runtime_temperature,
            "runtime_top_p": self.runtime_top_p,
            "runtime_max_tokens_or": self.runtime_max_tokens_or,
            "runtime_max_tokens_at": self.runtime_max_tokens_at,
            "runtime_reasoning_enabled": self.runtime_reasoning_enabled,
            "runtime_reasoning_tokens": self.runtime_reasoning_tokens,
            "runtime_reasoning_depth": self.runtime_reasoning_depth,
            "runtime_max_history": self.runtime_max_history,
            "runtime_max_ai_chars": self.runtime_max_ai_chars,
            "runtime_or_retries": self.runtime_or_retries,
            "runtime_at_retries": self.runtime_at_retries,
            "runtime_or_timeout": self.runtime_or_timeout,
            "runtime_at_timeout": self.runtime_at_timeout,
            "runtime_or_to_at_fallback": self.runtime_or_to_at_fallback,
            "admin_user_ids": self.admin_user_ids,
            "admin_commands_enabled": self.admin_commands_enabled,
            "admin_logging_enabled": self.admin_logging_enabled,
            "games_enabled": self.games_enabled,
            "max_games_per_chat": self.max_games_per_chat,
            "game_timeout_hours": self.game_timeout_hours,
            "monitoring_enabled": self.monitoring_enabled,
            "metrics_collection": self.metrics_collection,
            "health_checks": self.health_checks,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "streaming_enabled": self.streaming_enabled,
            "chunk_delay": self.chunk_delay,
            "max_streaming_time": self.max_streaming_time,
            "content_enabled": self.content_enabled,
            "daily_tasks_enabled": self.daily_tasks_enabled,
            "seasonal_events_enabled": self.seasonal_events_enabled,
            "boosters_enabled": self.boosters_enabled,
            "content_filtering": self.content_filtering,
            "rate_limiting": self.rate_limiting,
            "max_requests_per_minute": self.max_requests_per_minute,
            "webhook_enabled": self.webhook_enabled,
            "webhook_url": self.webhook_url,
            "webhook_secret": self.webhook_secret,
            "webhook_port": self.webhook_port,
            "yoomoney_enabled": self.yoomoney_enabled,
            "yoomoney_secret": self.yoomoney_secret,
            "default_language": self.default_language,
            "supported_languages": self.supported_languages
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Загружает конфигурацию из словаря"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def save_to_file(self, filename: str = "config.json") -> bool:
        """Сохраняет конфигурацию в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def load_from_file(self, filename: str = "config.json") -> bool:
        """Загружает конфигурацию из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.from_dict(data)
            return True
        except FileNotFoundError:
            print(f"Config file {filename} not found")
            return False
        except Exception as e:
            print(f"Error loading config: {e}")
            return False

# ---------- Загрузка конфигурации из переменных окружения ----------
def load_config_from_env(config: BotConfig):
    """Загружает конфигурацию из переменных окружения"""
    
    # VK настройки
    if os.getenv("VK_GROUP_TOKEN"):
        config.vk_group_token = os.getenv("VK_GROUP_TOKEN")
    
    if os.getenv("VK_GROUP_ID"):
        try:
            config.vk_group_id = int(os.getenv("VK_GROUP_ID"))
        except ValueError:
            print("Warning: Invalid VK_GROUP_ID")
    
    # AI настройки
    if os.getenv("AI_PROVIDER"):
        config.ai_provider = os.getenv("AI_PROVIDER")
    
    if os.getenv("OPENROUTER_API_KEY"):
        config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if os.getenv("AITUNNEL_API_KEY"):
        config.aitunnel_api_key = os.getenv("AITUNNEL_API_KEY")
    
    # Runtime AI параметры
    if os.getenv("RUNTIME_TEMPERATURE"):
        try:
            config.runtime_temperature = float(os.getenv("RUNTIME_TEMPERATURE"))
        except ValueError:
            print("Warning: Invalid RUNTIME_TEMPERATURE")
    
    if os.getenv("RUNTIME_TOP_P"):
        try:
            config.runtime_top_p = float(os.getenv("RUNTIME_TOP_P"))
        except ValueError:
            print("Warning: Invalid RUNTIME_TOP_P")
    
    if os.getenv("RUNTIME_MAX_TOKENS_OR"):
        try:
            config.runtime_max_tokens_or = int(os.getenv("RUNTIME_MAX_TOKENS_OR"))
        except ValueError:
            print("Warning: Invalid RUNTIME_MAX_TOKENS_OR")
    
    if os.getenv("RUNTIME_MAX_TOKENS_AT"):
        try:
            config.runtime_max_tokens_at = int(os.getenv("RUNTIME_MAX_TOKENS_AT"))
        except ValueError:
            print("Warning: Invalid RUNTIME_MAX_TOKENS_AT")
    
    if os.getenv("RUNTIME_MAX_HISTORY"):
        try:
            config.runtime_max_history = int(os.getenv("RUNTIME_MAX_HISTORY"))
        except ValueError:
            print("Warning: Invalid RUNTIME_MAX_HISTORY")
    
    if os.getenv("RUNTIME_MAX_AI_CHARS"):
        try:
            config.runtime_max_ai_chars = int(os.getenv("RUNTIME_MAX_AI_CHARS"))
        except ValueError:
            print("Warning: Invalid RUNTIME_MAX_AI_CHARS")
    
    # Админ настройки
    if os.getenv("ADMIN_USER_IDS"):
        try:
            config.admin_user_ids = [int(x.strip()) for x in os.getenv("ADMIN_USER_IDS").split(",")]
        except ValueError:
            print("Warning: Invalid ADMIN_USER_IDS")
    
    # Логирование
    if os.getenv("LOG_LEVEL"):
        config.log_level = os.getenv("LOG_LEVEL")
    
    if os.getenv("LOG_FILE"):
        config.log_file = os.getenv("LOG_FILE")
    
    # Webhook
    if os.getenv("WEBHOOK_ENABLED"):
        config.webhook_enabled = os.getenv("WEBHOOK_ENABLED").lower() == "true"
    
    if os.getenv("WEBHOOK_URL"):
        config.webhook_url = os.getenv("WEBHOOK_URL")
    
    if os.getenv("WEBHOOK_SECRET"):
        config.webhook_secret = os.getenv("WEBHOOK_SECRET")
    
    if os.getenv("WEBHOOK_PORT"):
        try:
            config.webhook_port = int(os.getenv("WEBHOOK_PORT"))
        except ValueError:
            print("Warning: Invalid WEBHOOK_PORT")
    
    # YooMoney
    if os.getenv("YOOMONEY_SECRET"):
        config.yoomoney_secret = os.getenv("YOOMONEY_SECRET")
        config.yoomoney_enabled = True
    
    # Локализация
    if os.getenv("DEFAULT_LANGUAGE"):
        config.default_language = os.getenv("DEFAULT_LANGUAGE")

# ---------- Создание конфигурации по умолчанию ----------
def create_default_config() -> BotConfig:
    """Создает конфигурацию по умолчанию"""
    config = BotConfig()
    
    # Загружаем из переменных окружения
    load_config_from_env(config)
    
    # Загружаем из файла если существует
    config_file = Path("config.json")
    if config_file.exists():
        config.load_from_file("config.json")
    
    return config

# ---------- Валидация конфигурации ----------
def validate_config(config: BotConfig) -> List[str]:
    """Валидирует конфигурацию и возвращает список ошибок"""
    errors = []
    
    # Проверяем обязательные поля
    if not config.vk_group_token:
        errors.append("VK_GROUP_TOKEN is required")
    
    if config.vk_group_id <= 0:
        errors.append("VK_GROUP_ID must be positive")
    
    # Проверяем AI настройки
    if config.ai_provider not in ["AUTO", "OPENROUTER", "AITUNNEL"]:
        errors.append("AI_PROVIDER must be AUTO, OPENROUTER, or AITUNNEL")
    
    if config.ai_provider == "OPENROUTER" and not config.openrouter_api_key:
        errors.append("OPENROUTER_API_KEY is required when AI_PROVIDER is OPENROUTER")
    
    if config.ai_provider == "AITUNNEL" and not config.aitunnel_api_key:
        errors.append("AITUNNEL_API_KEY is required when AI_PROVIDER is AITUNNEL")
    
    # Проверяем runtime параметры
    if not (0.0 <= config.runtime_temperature <= 2.0):
        errors.append("RUNTIME_TEMPERATURE must be between 0.0 and 2.0")
    
    if not (0.0 <= config.runtime_top_p <= 1.0):
        errors.append("RUNTIME_TOP_P must be between 0.0 and 1.0")
    
    if config.runtime_max_tokens_or <= 0:
        errors.append("RUNTIME_MAX_TOKENS_OR must be positive")
    
    if config.runtime_max_tokens_at <= 0:
        errors.append("RUNTIME_MAX_TOKENS_AT must be positive")
    
    if config.runtime_max_history <= 0:
        errors.append("RUNTIME_MAX_HISTORY must be positive")
    
    if config.runtime_max_ai_chars <= 0:
        errors.append("RUNTIME_MAX_AI_CHARS must be positive")
    
    if config.runtime_or_retries <= 0:
        errors.append("RUNTIME_OR_RETRIES must be positive")
    
    if config.runtime_at_retries <= 0:
        errors.append("RUNTIME_AT_RETRIES must be positive")
    
    if config.runtime_or_timeout <= 0:
        errors.append("RUNTIME_OR_TIMEOUT must be positive")
    
    if config.runtime_at_timeout <= 0:
        errors.append("RUNTIME_AT_TIMEOUT must be positive")
    
    # Проверяем админ настройки
    if not config.admin_user_ids:
        errors.append("At least one admin user ID must be specified")
    
    # Проверяем логирование
    if config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        errors.append("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    
    # Проверяем webhook
    if config.webhook_enabled:
        if not config.webhook_url:
            errors.append("WEBHOOK_URL is required when webhook is enabled")
        if not config.webhook_secret:
            errors.append("WEBHOOK_SECRET is required when webhook is enabled")
        if config.webhook_port <= 0 or config.webhook_port > 65535:
            errors.append("WEBHOOK_PORT must be between 1 and 65535")
    
    # Проверяем локализацию
    if config.default_language not in config.supported_languages:
        errors.append("DEFAULT_LANGUAGE must be in SUPPORTED_LANGUAGES")
    
    return errors

# ---------- Глобальная конфигурация ----------
# Создаем глобальную конфигурацию
bot_config = create_default_config()

# Валидируем конфигурацию
config_errors = validate_config(bot_config)
if config_errors:
    print("Configuration errors:")
    for error in config_errors:
        print(f"  - {error}")
    print("Please fix these errors before running the bot.")

# ---------- Функции для работы с конфигурацией ----------
def get_config() -> BotConfig:
    """Возвращает глобальную конфигурацию"""
    return bot_config

def reload_config() -> bool:
    """Перезагружает конфигурацию"""
    global bot_config
    
    # Создаем новую конфигурацию
    new_config = create_default_config()
    
    # Валидируем
    errors = validate_config(new_config)
    if errors:
        print("Configuration errors during reload:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    # Обновляем глобальную конфигурацию
    bot_config = new_config
    return True

def save_config() -> bool:
    """Сохраняет текущую конфигурацию в файл"""
    return bot_config.save_to_file("config.json")

def export_config() -> str:
    """Экспортирует конфигурацию в JSON строку"""
    return json.dumps(bot_config.to_dict(), ensure_ascii=False, indent=2)

def import_config(config_json: str) -> bool:
    """Импортирует конфигурацию из JSON строки"""
    try:
        data = json.loads(config_json)
        bot_config.from_dict(data)
        
        # Валидируем
        errors = validate_config(bot_config)
        if errors:
            print("Configuration errors during import:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    except Exception as e:
        print(f"Error importing config: {e}")
        return False