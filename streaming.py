"""
Модуль стриминга и индикаторов для AI ответов
"""
import time
import threading
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from enum import Enum

# ---------- Типы индикаторов ----------
class IndicatorType(Enum):
    TYPING = "typing"
    THINKING = "thinking"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class StreamingIndicator:
    type: IndicatorType
    message: str
    emoji: str
    duration: float = 0.0
    is_active: bool = False
    start_time: float = 0.0
    
    def start(self):
        """Запускает индикатор"""
        self.is_active = True
        self.start_time = time.time()
    
    def stop(self):
        """Останавливает индикатор"""
        self.is_active = False
        self.duration = time.time() - self.start_time
    
    def get_elapsed_time(self) -> float:
        """Возвращает прошедшее время"""
        if not self.is_active:
            return self.duration
        return time.time() - self.start_time

# ---------- Индикаторы по умолчанию ----------
DEFAULT_INDICATORS = {
    IndicatorType.TYPING: StreamingIndicator(
        type=IndicatorType.TYPING,
        message="набирает текст...",
        emoji="⌨️"
    ),
    IndicatorType.THINKING: StreamingIndicator(
        type=IndicatorType.THINKING,
        message="думает...",
        emoji="🤔"
    ),
    IndicatorType.PROCESSING: StreamingIndicator(
        type=IndicatorType.PROCESSING,
        message="обрабатывает запрос...",
        emoji="⚙️"
    ),
    IndicatorType.GENERATING: StreamingIndicator(
        type=IndicatorType.GENERATING,
        message="генерирует ответ...",
        emoji="🧠"
    ),
    IndicatorType.COMPLETED: StreamingIndicator(
        type=IndicatorType.COMPLETED,
        message="готово!",
        emoji="✅"
    ),
    IndicatorType.ERROR: StreamingIndicator(
        type=IndicatorType.ERROR,
        message="ошибка!",
        emoji="❌"
    )
}

# ---------- Менеджер индикаторов ----------
class IndicatorManager:
    def __init__(self):
        self.active_indicators: Dict[str, StreamingIndicator] = {}
        self.indicator_callbacks: Dict[str, Callable] = {}
        self.lock = threading.Lock()
    
    def start_indicator(self, session_id: str, indicator_type: IndicatorType, 
                       custom_message: Optional[str] = None) -> str:
        """Запускает индикатор для сессии"""
        with self.lock:
            if session_id in self.active_indicators:
                # Останавливаем предыдущий индикатор
                self.stop_indicator(session_id)
            
            # Создаем новый индикатор
            indicator = DEFAULT_INDICATORS[indicator_type]
            indicator.start()
            
            if custom_message:
                indicator.message = custom_message
            
            self.active_indicators[session_id] = indicator
            
            # Формируем текст индикатора
            indicator_text = f"{indicator.emoji} {indicator.message}"
            
            return indicator_text
    
    def update_indicator(self, session_id: str, indicator_type: IndicatorType,
                        custom_message: Optional[str] = None) -> str:
        """Обновляет индикатор"""
        with self.lock:
            if session_id not in self.active_indicators:
                return self.start_indicator(session_id, indicator_type, custom_message)
            
            indicator = self.active_indicators[session_id]
            indicator.type = indicator_type
            
            if custom_message:
                indicator.message = custom_message
            
            # Обновляем эмодзи
            indicator.emoji = DEFAULT_INDICATORS[indicator_type].emoji
            
            indicator_text = f"{indicator.emoji} {indicator.message}"
            return indicator_text
    
    def stop_indicator(self, session_id: str) -> Optional[str]:
        """Останавливает индикатор"""
        with self.lock:
            if session_id not in self.active_indicators:
                return None
            
            indicator = self.active_indicators[session_id]
            indicator.stop()
            
            # Удаляем индикатор
            del self.active_indicators[session_id]
            
            # Возвращаем финальное сообщение
            return f"{indicator.emoji} {indicator.message}"
    
    def get_indicator_status(self, session_id: str) -> Optional[StreamingIndicator]:
        """Получает статус индикатора"""
        with self.lock:
            return self.active_indicators.get(session_id)
    
    def is_indicator_active(self, session_id: str) -> bool:
        """Проверяет, активен ли индикатор"""
        with self.lock:
            return session_id in self.active_indicators

# Глобальный менеджер индикаторов
indicator_manager = IndicatorManager()

# ---------- Функции для работы с индикаторами ----------
def show_typing_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор набора текста"""
    return indicator_manager.start_indicator(session_id, IndicatorType.TYPING, custom_message)

def show_thinking_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор размышления"""
    return indicator_manager.start_indicator(session_id, IndicatorType.THINKING, custom_message)

def show_processing_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор обработки"""
    return indicator_manager.start_indicator(session_id, IndicatorType.PROCESSING, custom_message)

def show_generating_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор генерации"""
    return indicator_manager.start_indicator(session_id, IndicatorType.GENERATING, custom_message)

def show_completed_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор завершения"""
    return indicator_manager.update_indicator(session_id, IndicatorType.COMPLETED, custom_message)

def show_error_indicator(session_id: str, custom_message: Optional[str] = None) -> str:
    """Показывает индикатор ошибки"""
    return indicator_manager.update_indicator(session_id, IndicatorType.ERROR, custom_message)

def hide_indicator(session_id: str) -> Optional[str]:
    """Скрывает индикатор"""
    return indicator_manager.stop_indicator(session_id)