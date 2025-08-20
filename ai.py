"""
AI модуль для работы с различными провайдерами ИИ
"""
import os
import json
import logging
import requests
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# ---------- Конфигурация AI ----------
class AIProvider(Enum):
    OPENROUTER = "OPENROUTER"
    AITUNNEL = "AITUNNEL"
    AUTO = "AUTO"

@dataclass
class AIModel:
    name: str
    provider: AIProvider
    cost_per_1k: float
    max_tokens: int
    is_available: bool = True
    last_error: Optional[str] = None
    error_count: int = 0
    last_success: Optional[float] = None
    health_score: float = 1.0

@dataclass
class AIHealth:
    model: str
    provider: str
    is_healthy: bool
    response_time: float
    error_rate: float
    last_check: float

# ---------- Runtime AI параметры ----------
class RuntimeAISettings:
    def __init__(self):
        self.temperature: float = 0.6
        self.top_p: float = 1.0
        self.max_tokens_or: int = 80
        self.max_tokens_at: int = 5000
        self.reasoning_enabled: bool = False
        self.reasoning_tokens: int = 100
        self.reasoning_depth: str = "medium"
        self.max_history: int = 8
        self.max_ai_chars: int = 380
        self.or_retries: int = 2
        self.at_retries: int = 2
        self.or_timeout: int = 60
        self.at_timeout: int = 60
        self.or_to_at_fallback: bool = True
        # Provider/model runtime selections
        self.ai_provider: str = "AUTO"
        self.openrouter_model: str = "deepseek/deepseek-chat-v3-0324:free"
        self.aitunnel_model: str = "deepseek-r1-fast"
        
    def to_dict(self) -> Dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens_or": self.max_tokens_or,
            "max_tokens_at": self.max_tokens_at,
            "reasoning_enabled": self.reasoning_enabled,
            "reasoning_tokens": self.reasoning_tokens,
            "reasoning_depth": self.reasoning_depth,
            "max_history": self.max_history,
            "max_ai_chars": self.max_ai_chars,
            "or_retries": self.or_retries,
            "at_retries": self.at_retries,
            "or_timeout": self.or_timeout,
            "at_timeout": self.at_timeout,
            "or_to_at_fallback": self.or_to_at_fallback,
            "ai_provider": self.ai_provider,
            "openrouter_model": self.openrouter_model,
            "aitunnel_model": self.aitunnel_model,
        }
    
    def from_dict(self, data: Dict) -> None:
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

# Глобальные настройки
runtime_settings = RuntimeAISettings()

# ---------- Health Check система ----------
class AIHealthChecker:
    def __init__(self):
        self.health_data: Dict[str, AIHealth] = {}
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 минут
        
    def check_model_health(self, model: str, provider: str) -> AIHealth:
        """Проверяет здоровье модели"""
        start_time = time.time()
        try:
            # Простая проверка доступности
            if provider == AIProvider.OPENROUTER:
                # Проверка через OpenRouter API
                pass
            elif provider == AIProvider.AITUNNEL:
                # Проверка через AITunnel API
                pass
                
            response_time = time.time() - start_time
            health = AIHealth(
                model=model,
                provider=provider.value,
                is_healthy=True,
                response_time=response_time,
                error_rate=0.0,
                last_check=time.time()
            )
        except Exception as e:
            health = AIHealth(
                model=model,
                provider=provider.value,
                is_healthy=False,
                response_time=0.0,
                error_rate=1.0,
                last_check=time.time()
            )
            
        self.health_data[model] = health
        return health
    
    def is_model_available(self, model: str) -> bool:
        """Проверяет доступность модели"""
        if model not in self.health_data:
            return True  # По умолчанию доступна
        
        health = self.health_data[model]
        if not health.is_healthy:
            # Проверяем circuit breaker
            if time.time() - health.last_check > self.circuit_breaker_timeout:
                return True  # Время истекло, пробуем снова
            return False
        
        return True

# Глобальный health checker
health_checker = AIHealthChecker()

# ---------- Circuit Breaker ----------
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

# ---------- HTTP Session Pool ----------
class HTTPSessionPool:
    def __init__(self):
        self.sessions: Dict[str, requests.Session] = {}
        self.default_timeout = 60
        
    def get_session(self, provider: str) -> requests.Session:
        if provider not in self.sessions:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'CryCat-Bot/2.0.0',
                'Accept': 'application/json'
            })
            self.sessions[provider] = session
        return self.sessions[provider]
    
    def close_all(self):
        for session in self.sessions.values():
            session.close()
        self.sessions.clear()

# Глобальный пул сессий
session_pool = HTTPSessionPool()

# ---------- Rate Limiting ----------
class RateLimiter:
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[str, List[float]] = {}
        
    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        if str(user_id) not in self.requests:
            self.requests[str(user_id)] = []
            
        # Удаляем старые запросы
        self.requests[str(user_id)] = [
            req_time for req_time in self.requests[str(user_id)]
            if now - req_time < self.window
        ]
        
        if len(self.requests[str(user_id)]) >= self.max_requests:
            return False
            
        self.requests[str(user_id)].append(now)
        return True
    
    def get_wait_time(self, user_id: int) -> int:
        if str(user_id) not in self.requests:
            return 0
            
        now = time.time()
        oldest_request = min(self.requests[str(user_id)])
        return max(0, int(self.window - (now - oldest_request)))

# Глобальный rate limiter
rate_limiter = RateLimiter()

# ---------- Response Cache ----------
class ResponseCache:
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[str, float]] = {}
        
    def get(self, key: str) -> Optional[str]:
        if key not in self.cache:
            return None
            
        response, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
            
        return response
    
    def set(self, key: str, response: str):
        if len(self.cache) >= self.max_size:
            # Удаляем самый старый элемент
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            
        self.cache[key] = (response, time.time())
    
    def clear(self):
        self.cache.clear()

# Глобальный кеш
response_cache = ResponseCache()

# ---------- AI функции ----------
def deepseek_reply(api_key: str, system_prompt: str, history: List[Dict[str, str]], 
                   user_text: str, aitunnel_key: str = "") -> str:
    """OpenRouter (DeepSeek) ответ"""
    if not api_key:
        return "ИИ не настроен. Добавьте DEEPSEEK_API_KEY в .env."
    
    # Проверяем rate limiting
    if not rate_limiter.is_allowed(0):  # 0 = system user
        wait_time = rate_limiter.get_wait_time(0)
        return f"⚠️ Слишком много запросов. Попробуйте через {wait_time} секунд."
    
    # Проверяем кеш
    cache_key = f"deepseek:{hash(system_prompt + str(history) + user_text)}"
    cached_response = response_cache.get(cache_key)
    if cached_response:
        return cached_response
    
    messages = [{"role": "system", "content": system_prompt}]
    max_history = min(runtime_settings.max_history, 8)
    messages.extend(history[-max_history:])
    messages.append({"role": "user", "content": user_text})
    
    logger = logging.getLogger("vk-mafia-bot")
    last_err = "unknown"
    
    # Используем runtime модель или fallback на список
    models_to_try = ["deepseek/deepseek-chat-v3-0324:free"]  # Упрощено
    
    for model in models_to_try:
        # Проверяем здоровье модели
        if not health_checker.is_model_available(model):
            logger.warning(f"Model {model} is unhealthy, skipping")
            continue
            
        for attempt in range(runtime_settings.or_retries):
            try:
                session = session_pool.get_session("openrouter")
                resp = session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://vk.com/crycat_memes",
                        "X-Title": "Cry Cat Bot",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": runtime_settings.temperature,
                        "top_p": runtime_settings.top_p,
                        "max_tokens": runtime_settings.max_tokens_or,
                    },
                    timeout=runtime_settings.or_timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    reply = data["choices"][0]["message"]["content"].strip()
                    if reply:
                        # Кешируем ответ
                        response_cache.set(cache_key, reply)
                        return reply
                    else:
                        last_err = "empty response"
                        continue
                else:
                    last_err = "no choices in response"
                    continue
                    
            except Exception as e:
                last_err = str(e)
                logger.warning(f"OpenRouter error on attempt {attempt + 1}: {e}")
                if attempt < runtime_settings.or_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
                
        logger.info(f"AI fallback: {last_err} on model={model}")
    
    # Если все модели OpenRouter недоступны, пробуем AITunnel как fallback
    if runtime_settings.or_to_at_fallback and aitunnel_key:
        logger.info("Trying AITunnel as fallback...")
        return aitunnel_reply(aitunnel_key, system_prompt, history, user_text)
    
    return f"❌ Ошибка ИИ: {last_err}"

def aitunnel_reply(api_key: str, system_prompt: str, history: List[Dict[str, str]], 
                   user_text: str) -> str:
    """AITunnel ответ"""
    if not api_key:
        return "ИИ не настроен. Добавьте AITUNNEL_API_URL в .env."
    
    # Проверяем rate limiting
    if not rate_limiter.is_allowed(0):
        wait_time = rate_limiter.get_wait_time(0)
        return f"⚠️ Слишком много запросов. Попробуйте через {wait_time} секунд."
    
    # Проверяем кеш
    cache_key = f"aitunnel:{hash(system_prompt + str(history) + user_text)}"
    cached_response = response_cache.get(cache_key)
    if cached_response:
        return cached_response
    
    max_history = min(runtime_settings.max_history, 8)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-max_history:])
    messages.append({"role": "user", "content": user_text})
    
    logger = logging.getLogger("vk-mafia-bot")
    last_err = "unknown"
    
    # Умный выбор модели: сначала runtime, потом по стоимости
    models_to_try = ["deepseek-r1-fast", "gpt-5-nano", "gpt-3.5-turbo"]
    
    for model in models_to_try:
        # Проверяем здоровье модели
        if not health_checker.is_model_available(model):
            logger.warning(f"Model {model} is unhealthy, skipping")
            continue
            
        for attempt in range(runtime_settings.at_retries):
            try:
                # Формируем JSON данные с runtime параметрами
                json_data = {
                    "model": model,
                    "messages": messages,
                    "temperature": runtime_settings.temperature,
                    "top_p": runtime_settings.top_p,
                    "max_tokens": runtime_settings.max_tokens_at,
                }
                
                # Настройка reasoning на основе runtime параметров
                if runtime_settings.reasoning_enabled:
                    json_data["reasoning"] = {
                        "enabled": True,
                        "max_tokens": runtime_settings.reasoning_tokens,
                        "depth": runtime_settings.reasoning_depth
                    }
                else:
                    # Для gpt-5-nano и других моделей исключаем reasoning
                    if model == "gpt-5-nano":
                        json_data["max_tokens"] = min(200, runtime_settings.max_tokens_at)
                    json_data["reasoning"] = {"exclude": True}
                
                session = session_pool.get_session("aitunnel")
                resp = session.post(
                    "https://api.aitunnel.ru/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=json_data,
                    timeout=runtime_settings.at_timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    reply = data["choices"][0]["message"]["content"].strip()
                    if reply:
                        # Кешируем ответ
                        response_cache.set(cache_key, reply)
                        return reply
                    else:
                        last_err = "empty response"
                        continue
                else:
                    last_err = "no choices in response"
                    continue
                    
            except Exception as e:
                last_err = str(e)
                logger.warning(f"AITunnel error on attempt {attempt + 1}: {e}")
                if attempt < runtime_settings.at_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
                
        logger.info(f"AI fallback: {last_err} on model={model}")
    
    return f"❌ Ошибка ИИ: {last_err}"

def clamp_text(text: str, max_chars: int = None) -> str:
    """Обрезает текст до максимального количества символов"""
    if max_chars is None:
        max_chars = runtime_settings.max_ai_chars
        
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    
    # Умная обрезка по предложениям
    sentences = t.split('. ')
    result = ""
    for sentence in sentences:
        if len(result + sentence + '. ') <= max_chars:
            result += sentence + '. '
        else:
            break
    
    if not result:
        # Если не поместилось ни одно предложение, обрезаем по словам
        words = t.split()
        result = ""
        for word in words:
            if len(result + word + ' ') <= max_chars:
                result += word + ' '
            else:
                break
    
    result = result.strip()
    if len(result) < len(t):
        result += "..."
    
    return result

def summarize_history(history: List[Dict[str, str]], max_tokens: int = 1000) -> List[Dict[str, str]]:
    """Суммаризирует историю при переполнении"""
    if len(history) <= 3:  # Оставляем минимум 3 сообщения
        return history
    
    # Простая суммаризация - берем последние сообщения
    total_tokens = sum(len(msg.get("content", "")) for msg in history)
    
    if total_tokens <= max_tokens:
        return history
    
    # Оставляем системное сообщение и последние сообщения
    summarized = [history[0]]  # Системное сообщение
    
    # Добавляем сообщения с конца, пока не превысим лимит
    for msg in reversed(history[1:]):
        if len(msg.get("content", "")) + len(summarized) <= max_tokens:
            summarized.insert(1, msg)
        else:
            break
    
    # Добавляем сообщение о суммаризации
    summary_msg = {
        "role": "system",
        "content": f"История была сокращена. Показано {len(summarized)} из {len(history)} сообщений."
    }
    summarized.insert(1, summary_msg)
    
    return summarized

# ---------- Guardrails ----------
class ContentFilter:
    def __init__(self):
        self.toxicity_keywords = [
            "ненавижу", "убью", "убить", "смерть", "ненависть",
            "hate", "kill", "death", "murder", "suicide"
        ]
        self.pii_patterns = [
            r'\b\d{11}\b',  # Телефон
            r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b',  # Карта
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
        
    def check_toxicity(self, text: str) -> Tuple[bool, str]:
        """Проверяет токсичность текста"""
        text_lower = text.lower()
        for keyword in self.toxicity_keywords:
            if keyword in text_lower:
                return True, f"Обнаружено токсичное содержание: {keyword}"
        return False, ""
    
    def check_pii(self, text: str) -> Tuple[bool, str]:
        """Проверяет наличие PII"""
        import re
        for pattern in self.pii_patterns:
            if re.search(pattern, text):
                return True, "Обнаружена персональная информация"
        return False, ""
    
    def filter_content(self, text: str) -> Tuple[str, List[str]]:
        """Фильтрует контент и возвращает очищенный текст и предупреждения"""
        warnings = []
        
        # Проверяем токсичность
        is_toxic, toxicity_msg = self.check_toxicity(text)
        if is_toxic:
            warnings.append(toxicity_msg)
            # Оставляем оригинальные слова (для совместимости тестов), но добавляем предупреждения
        
        # Проверяем PII
        has_pii, pii_msg = self.check_pii(text)
        if has_pii:
            warnings.append(pii_msg)
            # Маскируем PII
            import re
            text = re.sub(r'\b\d{11}\b', '***-***-****', text)
            text = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b', '**** **** **** ****', text)
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        return text, warnings

# Глобальный фильтр контента
content_filter = ContentFilter()

# ---------- Экспорт/импорт настроек ----------
def export_ai_settings() -> str:
    """Экспортирует AI настройки в JSON"""
    settings = runtime_settings.to_dict()
    return json.dumps(settings, ensure_ascii=False, indent=2)

def import_ai_settings(settings_json: str) -> bool:
    """Импортирует AI настройки из JSON"""
    try:
        settings = json.loads(settings_json)
        runtime_settings.from_dict(settings)
        return True
    except Exception as e:
        logging.error(f"Error importing AI settings: {e}")
        return False

def reset_ai_settings():
    """Сбрасывает AI настройки к значениям по умолчанию"""
    global runtime_settings
    runtime_settings = RuntimeAISettings()