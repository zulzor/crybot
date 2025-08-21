"""
Модуль мониторинга и метрик
"""
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

# ---------- Метрики ----------
@dataclass
class Metric:
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str]
    
    def to_dict(self) -> Dict:
        return asdict(self)

class MetricsCollector:
    def __init__(self):
        self.metrics: List[Metric] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        # Store histogram observations as tuples (value, timestamp)
        self.histograms: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self.lock = threading.Lock()
        
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Увеличивает счетчик"""
        with self.lock:
            self.counters[name] += 1
            self.metrics.append(Metric(
                name=f"{name}_total",
                value=float(self.counters[name]),
                timestamp=time.time(),
                labels=labels or {}
            ))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Устанавливает значение gauge"""
        with self.lock:
            self.gauges[name] = value
            self.metrics.append(Metric(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            ))
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Добавляет значение в гистограмму"""
        with self.lock:
            self.histograms[name].append((value, time.time()))
            self.metrics.append(Metric(
                name=f"{name}_bucket",
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            ))
    
    def get_metrics(self) -> List[Metric]:
        """Возвращает все метрики"""
        with self.lock:
            return self.metrics.copy()
    
    def get_counter(self, name: str) -> int:
        """Возвращает значение счетчика"""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Возвращает значение gauge"""
        return self.gauges.get(name, 0.0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Возвращает статистику гистограммы"""
        observations = self.histograms.get(name, [])
        if not observations:
            return {}
        values = [v for v, ts in observations]
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted(values)[len(values) // 2],
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)]
        }
    
    def clear_old_metrics(self, max_age_hours: int = 24):
        """Очищает старые метрики"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        with self.lock:
            self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
            
            # Очищаем старые значения гистограмм
            for name in list(self.histograms.keys()):
                self.histograms[name] = [
                    (v, ts) for (v, ts) in self.histograms[name] if ts > cutoff_time
                ]

# Глобальный коллектор метрик
metrics_collector = MetricsCollector()

# ---------- Health Checks ----------
@dataclass
class HealthStatus:
    service: str
    status: str  # "healthy", "unhealthy", "degraded"
    message: str
    timestamp: float
    details: Optional[Dict] = None

START_TIME = time.time()


class HealthChecker:
    def __init__(self):
        self.health_status: Dict[str, HealthStatus] = {}
        self.check_interval = 30  # секунды
        self.last_check = 0
        
    def check_health(self) -> Dict[str, HealthStatus]:
        """Выполняет проверки здоровья всех сервисов"""
        current_time = time.time()
        if current_time - self.last_check < self.check_interval:
            return self.health_status.copy()
        
        self.last_check = current_time
        
        # Проверяем AI провайдеры
        self._check_ai_providers()
        
        # Проверяем системные ресурсы
        self._check_system_resources()
        
        # Проверяем базу данных (если есть)
        self._check_database()
        
        return self.health_status.copy()
    
    def _check_ai_providers(self):
        """Проверяет здоровье AI провайдеров"""
        # OpenRouter
        try:
            # Простая проверка доступности
            import requests
            response = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
            if response.status_code == 200:
                self.health_status["openrouter"] = HealthStatus(
                    service="OpenRouter",
                    status="healthy",
                    message="API доступен",
                    timestamp=time.time(),
                    details={"status_code": response.status_code}
                )
            else:
                self.health_status["openrouter"] = HealthStatus(
                    service="OpenRouter",
                    status="degraded",
                    message=f"API вернул статус {response.status_code}",
                    timestamp=time.time(),
                    details={"status_code": response.status_code}
                )
        except Exception as e:
            self.health_status["openrouter"] = HealthStatus(
                service="OpenRouter",
                status="unhealthy",
                message=f"Ошибка подключения: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )
        
        # AITunnel
        try:
            response = requests.get("https://api.aitunnel.ru/v1/models", timeout=5)
            if response.status_code == 200:
                self.health_status["aitunnel"] = HealthStatus(
                    service="AITunnel",
                    status="healthy",
                    message="API доступен",
                    timestamp=time.time(),
                    details={"status_code": response.status_code}
                )
            else:
                self.health_status["aitunnel"] = HealthStatus(
                    service="AITunnel",
                    status="degraded",
                    message=f"API вернул статус {response.status_code}",
                    timestamp=time.time(),
                    details={"status_code": response.status_code}
                )
        except Exception as e:
            self.health_status["aitunnel"] = HealthStatus(
                service="AITunnel",
                status="unhealthy",
                message=f"Ошибка подключения: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )
    
    def _check_system_resources(self):
        """Проверяет системные ресурсы"""
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent < 80:
            status = "healthy"
        elif cpu_percent < 95:
            status = "degraded"
        else:
            status = "unhealthy"
            
        self.health_status["cpu"] = HealthStatus(
            service="CPU",
            status=status,
            message=f"Использование CPU: {cpu_percent}%",
            timestamp=time.time(),
            details={"cpu_percent": cpu_percent}
        )
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        if memory_percent < 80:
            status = "healthy"
        elif memory_percent < 95:
            status = "degraded"
        else:
            status = "unhealthy"
            
        self.health_status["memory"] = HealthStatus(
            service="Memory",
            status=status,
            message=f"Использование памяти: {memory_percent}%",
            timestamp=time.time(),
            details={"memory_percent": memory_percent, "available_gb": memory.available / (1024**3)}
        )
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        if disk_percent < 80:
            status = "healthy"
        elif disk_percent < 95:
            status = "degraded"
        else:
            status = "unhealthy"
            
        self.health_status["disk"] = HealthStatus(
            service="Disk",
            status=status,
            message=f"Использование диска: {disk_percent}%",
            timestamp=time.time(),
            details={"disk_percent": disk_percent, "free_gb": disk.free / (1024**3)}
        )
    
    def _check_database(self):
        """Проверяет базу данных"""
        try:
            from storage import get_storage_from_env
            storage = get_storage_from_env()
            
            # Проверяем подключение к БД
            if hasattr(storage, 'conn'):
                # SQLite
                cursor = storage.conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    self.health_status["database"] = HealthStatus(
                        service="Database",
                        status="healthy",
                        message="SQLite база данных доступна",
                        timestamp=time.time(),
                        details={"type": "sqlite", "path": getattr(storage, 'db_path', 'unknown')}
                    )
                else:
                    self.health_status["database"] = HealthStatus(
                        service="Database",
                        status="unhealthy",
                        message="SQLite база данных недоступна",
                        timestamp=time.time(),
                        details={"type": "sqlite", "error": "query_failed"}
                    )
            else:
                # JSON storage
                try:
                    # Проверяем доступность файловой системы
                    test_data = {"test": "health_check"}
                    storage.set("health_check", "test", test_data)
                    retrieved = storage.get("health_check", "test")
                    if retrieved and retrieved.get("test") == "health_check":
                        self.health_status["database"] = HealthStatus(
                            service="Database",
                            status="healthy",
                            message="JSON хранилище доступно",
                            timestamp=time.time(),
                            details={"type": "json", "path": getattr(storage, 'data_dir', 'unknown')}
                        )
                    else:
                        self.health_status["database"] = HealthStatus(
                            service="Database",
                            status="unhealthy",
                            message="JSON хранилище недоступно",
                            timestamp=time.time(),
                            details={"type": "json", "error": "read_write_failed"}
                        )
                except Exception as e:
                    self.health_status["database"] = HealthStatus(
                        service="Database",
                        status="unhealthy",
                        message=f"JSON хранилище недоступно: {str(e)}",
                        timestamp=time.time(),
                        details={"type": "json", "error": str(e)}
                    )
                    
        except Exception as e:
            self.health_status["database"] = HealthStatus(
                service="Database",
                status="unhealthy",
                message=f"Ошибка подключения к БД: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )
    
    def get_overall_status(self) -> str:
        """Возвращает общий статус здоровья системы"""
        if not self.health_status:
            return "unknown"
        
        statuses = [status.status for status in self.health_status.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    def _calculate_cache_hit_rate(self) -> float:
        """Вычисляет процент попаданий в кеш"""
        try:
            from cache_monitoring import cache_manager
            if hasattr(cache_manager, 'get_stats'):
                stats = cache_manager.get_stats()
                hits = stats.get('hits', 0)
                misses = stats.get('misses', 0)
                total = hits + misses
                if total > 0:
                    return round((hits / total) * 100, 2)
            return 0.0
        except Exception:
            return 0.0
    
    def _get_active_users_count(self) -> int:
        """Возвращает количество активных пользователей за последний час"""
        try:
            from storage import get_storage_from_env
            storage = get_storage_from_env()
            
            # Получаем профили пользователей
            profiles = storage.get_all("profiles")
            if not profiles:
                return 0
            
            # Считаем пользователей активных за последний час
            current_time = time.time()
            one_hour_ago = current_time - 3600
            active_count = 0
            
            for user_id, profile in profiles.items():
                if isinstance(profile, dict) and 'last_activity' in profile:
                    last_activity = profile.get('last_activity', 0)
                    if last_activity > one_hour_ago:
                        active_count += 1
            
            return active_count
        except Exception:
            return 0

# Глобальный health checker
health_checker = HealthChecker()

# ---------- Логирование ----------
class JSONFormatter(logging.Formatter):
    """Форматтер для JSON логов"""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Добавляем extra поля
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)

class MetricsHandler(logging.Handler):
    """Хендлер для сбора метрик из логов"""
    def emit(self, record):
        try:
            # Собираем метрики на основе логов
            if record.levelname == "ERROR":
                metrics_collector.increment_counter("log_errors_total", {"level": record.levelname})
            elif record.levelname == "WARNING":
                metrics_collector.increment_counter("log_warnings_total", {"level": record.levelname})
            
            # Метрики по модулям
            metrics_collector.increment_counter("log_messages_total", {"module": record.module})
            
        except Exception:
            self.handleError(record)

def setup_logging():
    """Настраивает логирование с JSON форматом и метриками"""
    # Создаем форматтер
    json_formatter = JSONFormatter()
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Очищаем существующие хендлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый хендлер
    try:
        file_handler = logging.FileHandler("bot.log", encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create file handler: {e}")
    
    # Хендлер для метрик
    metrics_handler = MetricsHandler()
    metrics_handler.setLevel(logging.INFO)
    root_logger.addHandler(metrics_handler)
    
    # Настраиваем логгер для бота
    bot_logger = logging.getLogger("vk-mafia-bot")
    bot_logger.setLevel(logging.INFO)

# ---------- Prometheus метрики ----------
def generate_prometheus_metrics() -> str:
    """Генерирует метрики в формате Prometheus"""
    lines = []
    
    # Счетчики
    for name, value in metrics_collector.counters.items():
        lines.append(f"# HELP {name} Total count of {name}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    
    # Gauge
    for name, value in metrics_collector.gauges.items():
        lines.append(f"# HELP {name} Current value of {name}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")
    
    # Гистограммы
    for name, values in metrics_collector.histograms.items():
        if values:
            stats = metrics_collector.get_histogram_stats(name)
            lines.append(f"# HELP {name}_count Total count of {name}")
            lines.append(f"# TYPE {name}_count counter")
            lines.append(f"{name}_count {stats['count']}")
            
            lines.append(f"# HELP {name}_sum Total sum of {name}")
            lines.append(f"# TYPE {name}_sum counter")
            lines.append(f"{name}_sum {stats['sum']}")
            
            lines.append(f"# HELP {name}_bucket Histogram buckets for {name}")
            lines.append(f"# TYPE {name}_bucket histogram")
            lines.append(f"{name}_bucket{{le=\"+Inf\"}} {stats['count']}")
    
    # Health check метрики
    health_status = health_checker.get_overall_status()
    lines.append(f"# HELP bot_health_status Overall bot health status")
    lines.append(f"# TYPE bot_health_status gauge")
    health_value = 1.0 if health_status == "healthy" else 0.5 if health_status == "degraded" else 0.0
    lines.append(f"bot_health_status {health_value}")
    
    return "\n".join(lines)

# ---------- API endpoints для мониторинга ----------
def health_check_endpoint():
    """Health check endpoint для Docker и load balancer"""
    health_status = health_checker.check_health()
    overall_status = health_checker.get_overall_status()
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": {name: asdict(status) for name, status in health_status.items()}
    }
    
    # Устанавливаем HTTP статус
    if overall_status == "healthy":
        status_code = 200
    elif overall_status == "degraded":
        status_code = 200  # 200 для degraded, но с предупреждением
    else:
        status_code = 503  # Service Unavailable
    
    return response, status_code

def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return generate_prometheus_metrics(), 200

def status_endpoint():
    """Общий статус бота"""
    health_status = health_checker.check_health()
    overall_status = health_checker.get_overall_status()
    
    # Собираем статистику
    stats = {
        "total_requests": metrics_collector.get_counter("ai_requests_total"),
        "successful_requests": metrics_collector.get_counter("ai_success_total"),
        "failed_requests": metrics_collector.get_counter("ai_errors_total"),
        "average_response_time": metrics_collector.get_histogram_stats("ai_response_time").get("avg", 0.0),
        "cache_hit_rate": self._calculate_cache_hit_rate(),
        "active_users": self._get_active_users_count(),
        "uptime_seconds": max(0.0, time.time() - START_TIME)
    }
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "statistics": stats,
        "health": {name: asdict(status) for name, status in health_status.items()}
    }
    
    return response, 200

# ---------- Автоматическая очистка метрик ----------
def cleanup_metrics_worker():
    """Фоновая задача для очистки старых метрик"""
    while True:
        try:
            time.sleep(3600)  # Каждый час
            metrics_collector.clear_old_metrics(24)  # Оставляем метрики за 24 часа
        except Exception as e:
            logging.error(f"Error in metrics cleanup worker: {e}")

# Запускаем фоновую задачу
cleanup_thread = threading.Thread(target=cleanup_metrics_worker, daemon=True)
cleanup_thread.start()