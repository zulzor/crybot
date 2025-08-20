"""
Вспомогательные утилиты
"""
import json
import time
import hashlib
import re
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# ---------- Логирование ----------
def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Настраивает логирование"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

# ---------- Валидация данных ----------
def validate_email(email: str) -> bool:
    """Проверяет корректность email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Проверяет корректность номера телефона"""
    # Убираем все кроме цифр
    digits_only = re.sub(r'\D', '', phone)
    return len(digits_only) >= 10

def validate_json(data: str) -> bool:
    """Проверяет, является ли строка валидным JSON"""
    try:
        json.loads(data)
        return True
    except (json.JSONDecodeError, TypeError):
        return False

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Очищает текст от потенциально опасных символов"""
    if not text:
        return ""
    
    # Убираем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Обрезаем по длине
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()

# ---------- Хеширование и безопасность ----------
def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """Генерирует хеш от данных"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

def verify_hash(data: str, hash_value: str, algorithm: str = "sha256") -> bool:
    """Проверяет хеш данных"""
    expected_hash = generate_hash(data, algorithm)
    return expected_hash == hash_value

def generate_random_string(length: int = 16) -> str:
    """Генерирует случайную строку"""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_api_key(prefix: str = "ccb") -> str:
    """Генерирует API ключ"""
    timestamp = str(int(time.time()))
    random_part = generate_random_string(8)
    return f"{prefix}_{timestamp}_{random_part}"

# ---------- Работа с временем ----------
def format_timestamp(timestamp: Union[float, int]) -> str:
    """Форматирует временную метку"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_duration(seconds: float) -> str:
    """Форматирует длительность"""
    if seconds < 60:
        return f"{seconds:.1f}с"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}м"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}ч"
    else:
        days = seconds / 86400
        return f"{days:.1f}д"

def is_recent(timestamp: Union[float, int], max_age_seconds: int = 3600) -> bool:
    """Проверяет, недавняя ли временная метка"""
    return time.time() - timestamp < max_age_seconds

def get_time_ago(timestamp: Union[float, int]) -> str:
    """Возвращает "время назад" в человекочитаемом формате"""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return "только что"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes} мин назад"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} ч назад"
    elif diff < 2592000:  # 30 дней
        days = int(diff / 86400)
        return f"{days} дн назад"
    else:
        months = int(diff / 2592000)
        return f"{months} мес назад"

# ---------- Работа с файлами ----------
def save_json_file(data: Any, filename: str, indent: int = 2) -> bool:
    """Сохраняет данные в JSON файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file {filename}: {e}")
        return False

def load_json_file(filename: str, default: Any = None) -> Any:
    """Загружает данные из JSON файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File {filename} not found, using default value")
        return default
    except Exception as e:
        logging.error(f"Error loading JSON file {filename}: {e}")
        return default

def ensure_directory(path: str) -> bool:
    """Создает директорию если она не существует"""
    import os
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Error creating directory {path}: {e}")
        return False

# ---------- Кэширование ----------
class SimpleCache:
    """Простой кэш в памяти"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кэша"""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any):
        """Устанавливает значение в кэш"""
        if len(self.cache) >= self.max_size:
            # Удаляем самый старый элемент
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (value, time.time())
    
    def delete(self, key: str):
        """Удаляет значение из кэша"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Очищает кэш"""
        self.cache.clear()
    
    def size(self) -> int:
        """Возвращает размер кэша"""
        return len(self.cache)

# ---------- Рейт лимитинг ----------
class RateLimiter:
    """Система ограничения частоты запросов"""
    
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Проверяет, разрешен ли запрос"""
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Удаляем старые запросы
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.window
        ]
        
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_wait_time(self, key: str) -> int:
        """Возвращает время ожидания до следующего разрешенного запроса"""
        if key not in self.requests:
            return 0
        
        now = time.time()
        oldest_request = min(self.requests[key])
        return max(0, int(self.window - (now - oldest_request)))
    
    def reset(self, key: str):
        """Сбрасывает счетчик для ключа"""
        if key in self.requests:
            del self.requests[key]

# ---------- Утилиты для работы с текстом ----------
def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Обрезает текст до максимальной длины"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def count_words(text: str) -> int:
    """Подсчитывает количество слов в тексте"""
    if not text:
        return 0
    
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def count_characters(text: str, include_spaces: bool = True) -> int:
    """Подсчитывает количество символов в тексте"""
    if not text:
        return 0
    
    if include_spaces:
        return len(text)
    else:
        return len(text.replace(" ", ""))

def extract_urls(text: str) -> List[str]:
    """Извлекает URL из текста"""
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    return re.findall(url_pattern, text)

def extract_emails(text: str) -> List[str]:
    """Извлекает email адреса из текста"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def remove_html_tags(text: str) -> str:
    """Удаляет HTML теги из текста"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def normalize_whitespace(text: str) -> str:
    """Нормализует пробельные символы в тексте"""
    # Заменяем множественные пробелы на один
    text = re.sub(r'\s+', ' ', text)
    # Убираем пробелы в начале и конце
    return text.strip()

# ---------- Утилиты для работы с числами ----------
def format_number(number: Union[int, float], precision: int = 2) -> str:
    """Форматирует число для отображения"""
    if isinstance(number, int):
        return str(number)
    
    return f"{number:.{precision}f}"

def format_bytes(bytes_value: int) -> str:
    """Форматирует размер в байтах"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def format_percentage(value: float, total: float) -> str:
    """Форматирует процентное значение"""
    if total == 0:
        return "0%"
    
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"

def clamp_number(value: Union[int, float], min_value: Union[int, float], 
                max_value: Union[int, float]) -> Union[int, float]:
    """Ограничивает число диапазоном"""
    return max(min_value, min(value, max_value))

# ---------- Утилиты для работы с датами ----------
def parse_date(date_string: str, format_string: str = "%Y-%m-%d") -> Optional[datetime]:
    """Парсит строку даты"""
    try:
        return datetime.strptime(date_string, format_string)
    except ValueError:
        return None

def format_date(date: datetime, format_string: str = "%Y-%m-%d") -> str:
    """Форматирует дату в строку"""
    return date.strftime(format_string)

def get_date_range(days: int) -> Tuple[datetime, datetime]:
    """Возвращает диапазон дат"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

def is_weekend(date: datetime) -> bool:
    """Проверяет, является ли дата выходным днем"""
    return date.weekday() >= 5

def is_business_day(date: datetime) -> bool:
    """Проверяет, является ли дата рабочим днем"""
    return not is_weekend(date)

# ---------- Утилиты для работы с ошибками ----------
def format_exception(e: Exception) -> str:
    """Форматирует исключение для логирования"""
    return f"{type(e).__name__}: {str(e)}"

def get_exception_traceback(e: Exception) -> str:
    """Получает traceback исключения"""
    import traceback
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))

def safe_execute(func: callable, *args, default_return: Any = None, **kwargs) -> Any:
    """Безопасно выполняет функцию с обработкой ошибок"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error executing {func.__name__}: {format_exception(e)}")
        return default_return