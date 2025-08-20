"""
Кеширование и мониторинг для CryBot
"""
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from collections import defaultdict, deque
import json


# -------- Кеширование --------
@dataclass
class CacheItem:
    key: str
    value: Any
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)


class CacheManager:
    """
    Простой in-memory кеш с TTL и LRU эвакуацией
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheItem] = {}
        self.access_order: deque = deque()  # LRU порядок
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Установка значения в кеш"""
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            expires_at = time.time() + ttl if ttl > 0 else None
            
            # Если ключ уже существует, обновляем
            if key in self.cache:
                old_item = self.cache[key]
                self.access_order.remove(key)
                self.stats["sets"] += 1
            else:
                # Проверяем размер кеша
                if len(self.cache) >= self.max_size:
                    self._evict_lru()
            
            item = CacheItem(
                key=key,
                value=value,
                expires_at=expires_at
            )
            
            self.cache[key] = item
            self.access_order.append(key)
            self.stats["sets"] += 1
            return True
    
    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кеша"""
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None
            
            item = self.cache[key]
            
            # Проверяем TTL
            if item.expires_at and time.time() > item.expires_at:
                self.delete(key)
                self.stats["misses"] += 1
                return None
            
            # Обновляем статистику доступа
            item.access_count += 1
            item.last_access = time.time()
            
            # Перемещаем в конец (LRU)
            self.access_order.remove(key)
            self.access_order.append(key)
            
            self.stats["hits"] += 1
            return item.value
    
    def delete(self, key: str) -> bool:
        """Удаление ключа из кеша"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                self.stats["deletes"] += 1
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        with self.lock:
            if key not in self.cache:
                return False
            
            item = self.cache[key]
            if item.expires_at and time.time() > item.expires_at:
                self.delete(key)
                return False
            
            return True
    
    def ttl(self, key: str) -> Optional[int]:
        """Получение оставшегося времени жизни ключа"""
        with self.lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            if item.expires_at is None:
                return -1  # Без TTL
            
            remaining = int(item.expires_at - time.time())
            return max(0, remaining) if remaining > 0 else None
    
    def _evict_lru(self):
        """Эвакуация наименее используемых элементов"""
        if not self.access_order:
            return
        
        # Удаляем самый старый элемент
        oldest_key = self.access_order.popleft()
        if oldest_key in self.cache:
            del self.cache[oldest_key]
            self.stats["evictions"] += 1
    
    def clear(self):
        """Очистка всего кеша"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кеша"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self.stats,
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests
            }
    
    def cleanup_expired(self):
        """Очистка просроченных элементов"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.cache.items()
                if item.expires_at and current_time > item.expires_at
            ]
            
            for key in expired_keys:
                self.delete(key)


# -------- Мониторинг --------
@dataclass
class Metric:
    name: str
    value: Union[int, float]
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    name: str
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Gauge:
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Histogram:
    name: str
    buckets: Dict[str, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


class MonitoringManager:
    """
    Система мониторинга с метриками Prometheus-стиля
    """
    def __init__(self):
        self.counters: Dict[str, Counter] = defaultdict(lambda: Counter(""))
        self.gauges: Dict[str, Gauge] = defaultdict(lambda: Gauge(""))
        self.histograms: Dict[str, Histogram] = defaultdict(lambda: Histogram(""))
        self.metrics_history: List[Metric] = []
        self.max_history = 10000
        self.lock = threading.RLock()
        
        # Предустановленные метрики
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Инициализация стандартных метрик"""
        self.counter("bot_messages_total", {"type": "total"})
        self.counter("bot_commands_total", {"type": "total"})
        self.counter("bot_errors_total", {"type": "total"})
        self.gauge("bot_active_users", {"type": "current"})
        self.gauge("bot_active_games", {"type": "current"})
        self.histogram("bot_response_time_seconds", {"type": "api"})
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Получение или создание счётчика"""
        if labels is None:
            labels = {}
        
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.counters:
            self.counters[key] = Counter(name, 0, labels)
        
        return self.counters[key]
    
    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Получение или создание датчика"""
        if labels is None:
            labels = {}
        
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.gauges:
            self.gauges[key] = Gauge(name, 0.0, labels)
        
        return self.gauges[key]
    
    def histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> Histogram:
        """Получение или создание гистограммы"""
        if labels is None:
            labels = {}
        
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.histograms:
            self.histograms[key] = Histogram(name, {}, 0.0, 0, labels)
        
        return self.histograms[key]
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Увеличение счётчика"""
        counter = self.counter(name, labels)
        counter.value += value
        
        # Добавляем в историю
        self._add_metric(Metric(name, counter.value, time.time(), counter.labels))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Установка значения датчика"""
        gauge = self.gauge(name, labels)
        gauge.value = value
        
        # Добавляем в историю
        self._add_metric(Metric(name, value, time.time(), gauge.labels))
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Добавление наблюдения в гистограмму"""
        histogram = self.histogram(name, labels)
        histogram.count += 1
        histogram.sum += value
        
        # Простые бакеты
        if value < 0.1:
            bucket = "0.1"
        elif value < 0.5:
            bucket = "0.5"
        elif value < 1.0:
            bucket = "1.0"
        elif value < 5.0:
            bucket = "5.0"
        else:
            bucket = "+Inf"
        
        histogram.buckets[bucket] = histogram.buckets.get(bucket, 0) + 1
        
        # Добавляем в историю
        self._add_metric(Metric(name, value, time.time(), histogram.labels))
    
    def _add_metric(self, metric: Metric):
        """Добавление метрики в историю"""
        with self.lock:
            self.metrics_history.append(metric)
            
            # Ограничиваем размер истории
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
    
    def get_metrics_prometheus(self) -> str:
        """Экспорт метрик в формате Prometheus"""
        result = []
        
        # Счётчики
        for counter in self.counters.values():
            labels_str = ""
            if counter.labels:
                labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in counter.labels.items()) + "}"
            result.append(f"# HELP {counter.name} Total count of {counter.name}")
            result.append(f"# TYPE {counter.name} counter")
            result.append(f"{counter.name}{labels_str} {counter.value}")
        
        # Датчики
        for gauge in self.gauges.values():
            labels_str = ""
            if gauge.labels:
                labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in gauge.labels.items()) + "}"
            result.append(f"# HELP {gauge.name} Current value of {gauge.name}")
            result.append(f"# TYPE {gauge.name} gauge")
            result.append(f"{gauge.name}{labels_str} {gauge.value}")
        
        # Гистограммы
        for histogram in self.histograms.values():
            labels_str = ""
            if histogram.labels:
                labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in histogram.labels.items()) + "}"
            
            result.append(f"# HELP {histogram.name} Histogram of {histogram.name}")
            result.append(f"# TYPE {histogram.name} histogram")
            
            # Бакеты
            for bucket, count in sorted(histogram.buckets.items()):
                bucket_labels = {**histogram.labels, "le": bucket}
                bucket_labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in bucket_labels.items()) + "}"
                result.append(f"{histogram.name}_bucket{bucket_labels_str} {count}")
            
            # Сумма и количество
            result.append(f"{histogram.name}_sum{labels_str} {histogram.sum}")
            result.append(f"{histogram.name}_count{labels_str} {histogram.count}")
        
        return "\n".join(result)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получение сводки метрик"""
        with self.lock:
            return {
                "counters": {name: counter.value for name, counter in self.counters.items()},
                "gauges": {name: gauge.value for name, gauge in self.gauges.items()},
                "histograms": {
                    name: {
                        "count": hist.count,
                        "sum": hist.sum,
                        "buckets": hist.buckets
                    } for name, hist in self.histograms.items()
                },
                "total_metrics": len(self.metrics_history),
                "last_update": time.time()
            }


# -------- Система логирования --------
class LogLevel:
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class LogEntry:
    timestamp: float
    level: int
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


class Logger:
    """Простой логгер с уровнями и контекстом"""
    
    def __init__(self, name: str = "CryBot", level: int = LogLevel.INFO):
        self.name = name
        self.level = level
        self.entries: List[LogEntry] = []
        self.max_entries = 1000
        self.lock = threading.RLock()
    
    def _log(self, level: int, message: str, **context):
        """Внутренний метод логирования"""
        if level < self.level:
            return
        
        with self.lock:
            entry = LogEntry(
                timestamp=time.time(),
                level=level,
                message=message,
                context=context
            )
            
            self.entries.append(entry)
            
            # Ограничиваем размер логов
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)
            
            # Выводим в консоль
            level_names = {0: "DEBUG", 1: "INFO", 2: "WARN", 3: "ERROR", 4: "CRIT"}
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
            print(f"[{timestamp}] {level_names.get(level, 'UNKN')} [{self.name}] {message}")
    
    def debug(self, message: str, **context):
        self._log(LogLevel.DEBUG, message, **context)
    
    def info(self, message: str, **context):
        self._log(LogLevel.INFO, message, **context)
    
    def warning(self, message: str, **context):
        self._log(LogLevel.WARNING, message, **context)
    
    def error(self, message: str, **context):
        self._log(LogLevel.ERROR, message, **context)
    
    def critical(self, message: str, **context):
        self._log(LogLevel.CRITICAL, message, **context)
    
    def get_logs(self, level: Optional[int] = None, limit: Optional[int] = None) -> List[LogEntry]:
        """Получение логов с фильтрацией"""
        with self.lock:
            logs = self.entries
            
            if level is not None:
                logs = [log for log in logs if log.level >= level]
            
            if limit:
                logs = logs[-limit:]
            
            return logs


# Глобальные экземпляры
cache_manager = CacheManager()
monitoring_manager = MonitoringManager()
logger = Logger()