"""
Модуль для работы с ИИ
"""
import os
import time
from typing import Dict, Any, Optional

# Runtime настройки ИИ
RUNTIME_TEMPERATURE: float = 0.6
RUNTIME_TOP_P: float = 1.0
RUNTIME_MAX_TOKENS_OR: int = 80
RUNTIME_MAX_TOKENS_AT: int = 5000
RUNTIME_MAX_AI_CHARS: int = 380
RUNTIME_MAX_HISTORY: int = 8
RUNTIME_REASONING_ENABLED: bool = False
RUNTIME_REASONING_TOKENS: int = 50
RUNTIME_REASONING_DEPTH: str = "low"
RUNTIME_OR_RETRIES: int = 2
RUNTIME_AT_RETRIES: int = 2
RUNTIME_OR_TIMEOUT: int = 60
RUNTIME_AT_TIMEOUT: int = 60
RUNTIME_OR_TO_AT_FALLBACK: bool = True

def runtime_settings() -> Dict[str, Any]:
    """Возвращает текущие runtime настройки ИИ"""
    return {
        "temperature": RUNTIME_TEMPERATURE,
        "top_p": RUNTIME_TOP_P,
        "max_tokens_or": RUNTIME_MAX_TOKENS_OR,
        "max_tokens_at": RUNTIME_MAX_TOKENS_AT,
        "max_ai_chars": RUNTIME_MAX_AI_CHARS,
        "max_history": RUNTIME_MAX_HISTORY,
        "reasoning_enabled": RUNTIME_REASONING_ENABLED,
        "reasoning_tokens": RUNTIME_REASONING_TOKENS,
        "reasoning_depth": RUNTIME_REASONING_DEPTH,
        "or_retries": RUNTIME_OR_RETRIES,
        "at_retries": RUNTIME_AT_RETRIES,
        "or_timeout": RUNTIME_OR_TIMEOUT,
        "at_timeout": RUNTIME_AT_TIMEOUT,
        "or_to_at_fallback": RUNTIME_OR_TO_AT_FALLBACK
    }

def export_ai_settings() -> str:
    """Экспортирует настройки ИИ в JSON"""
    import json
    return json.dumps(runtime_settings(), ensure_ascii=False, indent=2)

def import_ai_settings(settings_json: str) -> bool:
    """Импортирует настройки ИИ из JSON"""
    try:
        import json
        settings = json.loads(settings_json)
        
        global RUNTIME_TEMPERATURE, RUNTIME_TOP_P, RUNTIME_MAX_TOKENS_OR
        global RUNTIME_MAX_TOKENS_AT, RUNTIME_MAX_AI_CHARS, RUNTIME_MAX_HISTORY
        global RUNTIME_REASONING_ENABLED, RUNTIME_REASONING_TOKENS, RUNTIME_REASONING_DEPTH
        global RUNTIME_OR_RETRIES, RUNTIME_AT_RETRIES, RUNTIME_OR_TIMEOUT, RUNTIME_AT_TIMEOUT
        global RUNTIME_OR_TO_AT_FALLBACK
        
        RUNTIME_TEMPERATURE = settings.get("temperature", RUNTIME_TEMPERATURE)
        RUNTIME_TOP_P = settings.get("top_p", RUNTIME_TOP_P)
        RUNTIME_MAX_TOKENS_OR = settings.get("max_tokens_or", RUNTIME_MAX_TOKENS_OR)
        RUNTIME_MAX_TOKENS_AT = settings.get("max_tokens_at", RUNTIME_MAX_TOKENS_AT)
        RUNTIME_MAX_AI_CHARS = settings.get("max_ai_chars", RUNTIME_MAX_AI_CHARS)
        RUNTIME_MAX_HISTORY = settings.get("max_history", RUNTIME_MAX_HISTORY)
        RUNTIME_REASONING_ENABLED = settings.get("reasoning_enabled", RUNTIME_REASONING_ENABLED)
        RUNTIME_REASONING_TOKENS = settings.get("reasoning_tokens", RUNTIME_REASONING_TOKENS)
        RUNTIME_REASONING_DEPTH = settings.get("reasoning_depth", RUNTIME_REASONING_DEPTH)
        RUNTIME_OR_RETRIES = settings.get("or_retries", RUNTIME_OR_RETRIES)
        RUNTIME_AT_RETRIES = settings.get("at_retries", RUNTIME_AT_RETRIES)
        RUNTIME_OR_TIMEOUT = settings.get("or_timeout", RUNTIME_OR_TIMEOUT)
        RUNTIME_AT_TIMEOUT = settings.get("at_timeout", RUNTIME_AT_TIMEOUT)
        RUNTIME_OR_TO_AT_FALLBACK = settings.get("or_to_at_fallback", RUNTIME_OR_TO_AT_FALLBACK)
        
        return True
    except Exception:
        return False

def reset_ai_settings() -> None:
    """Сбрасывает настройки ИИ к значениям по умолчанию"""
    global RUNTIME_TEMPERATURE, RUNTIME_TOP_P, RUNTIME_MAX_TOKENS_OR
    global RUNTIME_MAX_TOKENS_AT, RUNTIME_MAX_AI_CHARS, RUNTIME_MAX_HISTORY
    global RUNTIME_REASONING_ENABLED, RUNTIME_REASONING_TOKENS, RUNTIME_REASONING_DEPTH
    global RUNTIME_OR_RETRIES, RUNTIME_AT_RETRIES, RUNTIME_OR_TIMEOUT, RUNTIME_AT_TIMEOUT
    global RUNTIME_OR_TO_AT_FALLBACK
    
    RUNTIME_TEMPERATURE = 0.6
    RUNTIME_TOP_P = 1.0
    RUNTIME_MAX_TOKENS_OR = 80
    RUNTIME_MAX_TOKENS_AT = 5000
    RUNTIME_MAX_AI_CHARS = 380
    RUNTIME_MAX_HISTORY = 8
    RUNTIME_REASONING_ENABLED = False
    RUNTIME_REASONING_TOKENS = 50
    RUNTIME_REASONING_DEPTH = "low"
    RUNTIME_OR_RETRIES = 2
    RUNTIME_AT_RETRIES = 2
    RUNTIME_OR_TIMEOUT = 60
    RUNTIME_AT_TIMEOUT = 60
    RUNTIME_OR_TO_AT_FALLBACK = True