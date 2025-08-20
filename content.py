"""
Модуль контента и монетизации
"""
import json
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# ---------- Система валюты ----------
@dataclass
class UserWallet:
    user_id: int
    balance: float = 0.0
    currency: str = "RUB"
    created_at: float = 0.0
    last_activity: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        self.last_activity = time.time()
    
    def add_funds(self, amount: float):
        """Добавляет средства"""
        self.balance += amount
        self.last_activity = time.time()
    
    def spend_funds(self, amount: float) -> bool:
        """Тратит средства"""
        if self.balance >= amount:
            self.balance -= amount
            self.last_activity = time.time()
            return True
        return False
    
    def get_balance_formatted(self) -> str:
        """Возвращает отформатированный баланс"""
        if self.currency == "RUB":
            return f"{self.balance:.2f} ₽"
        elif self.currency == "USD":
            return f"${self.balance:.2f}"
        elif self.currency == "EUR":
            return f"€{self.balance:.2f}"
        else:
            return f"{self.balance:.2f} {self.currency}"

# ---------- Бустеры для ИИ ----------
@dataclass
class AIBooster:
    id: str
    name: str
    description: str
    price: float
    currency: str = "RUB"
    duration_hours: int = 24
    effects: Dict[str, float] = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = {}
    
    def get_effects_description(self) -> str:
        """Возвращает описание эффектов бустера"""
        if not self.effects:
            return "Без особых эффектов"
        
        effects_text = []
        for effect, value in self.effects.items():
            if effect == "max_tokens_multiplier":
                effects_text.append(f"Токены x{value}")
            elif effect == "response_speed_multiplier":
                effects_text.append(f"Скорость x{value}")
            elif effect == "quality_boost":
                effects_text.append(f"Качество +{value}%")
            elif effect == "priority_queue":
                effects_text.append("Приоритетная очередь")
        
        return ", ".join(effects_text)

# ---------- Ежедневные задания ----------
@dataclass
class DailyTask:
    id: str
    name: str
    description: str
    type: str
    target_value: int
    reward: float
    reward_currency: str = "RUB"
    category: str = "general"
    
    def get_progress_text(self, current_value: int) -> str:
        """Возвращает текст прогресса"""
        progress = min(current_value, self.target_value)
        percentage = (progress / self.target_value) * 100
        return f"{progress}/{self.target_value} ({percentage:.1f}%)"

# ---------- Магазин бустеров ----------
class BoosterShop:
    BOOSTERS = {
        "fast_lane": AIBooster(
            id="fast_lane",
            name="Fast Lane",
            description="Приоритетная очередь для AI запросов",
            price=50.0,
            duration_hours=24,
            effects={"priority_queue": 1.0}
        ),
        "token_boost": AIBooster(
            id="token_boost",
            name="Token Boost",
            description="Увеличенный лимит токенов для ответов",
            price=100.0,
            duration_hours=24,
            effects={"max_tokens_multiplier": 2.0}
        ),
        "speed_boost": AIBooster(
            id="speed_boost",
            name="Speed Boost",
            description="Ускоренные ответы от AI",
            price=75.0,
            duration_hours=12,
            effects={"response_speed_multiplier": 1.5}
        ),
        "quality_boost": AIBooster(
            id="quality_boost",
            name="Quality Boost",
            description="Повышенное качество AI ответов",
            price=150.0,
            duration_hours=24,
            effects={"quality_boost": 25.0}
        )
    }
    
    @classmethod
    def get_booster(cls, booster_id: str) -> Optional[AIBooster]:
        """Получает бустер по ID"""
        return cls.BOOSTERS.get(booster_id)
    
    @classmethod
    def list_boosters(cls) -> List[AIBooster]:
        """Возвращает список всех бустеров"""
        return list(cls.BOOSTERS.values())

# ---------- Ежедневные задания ----------
class DailyTasks:
    TASKS = {
        "ai_chat_5": DailyTask(
            id="ai_chat_5",
            name="AI Чат x5",
            description="Отправьте 5 сообщений в AI чат",
            type="ai_chat",
            target_value=5,
            reward=10.0,
            category="ai"
        ),
        "play_games_3": DailyTask(
            id="play_games_3",
            name="Игрок",
            description="Сыграйте в 3 разные игры",
            type="game_play",
            target_value=3,
            reward=15.0,
            category="games"
        ),
        "daily_login": DailyTask(
            id="daily_login",
            name="Ежедневный вход",
            description="Заходите в бота 7 дней подряд",
            type="social",
            target_value=7,
            reward=100.0,
            category="social"
        )
    }
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[DailyTask]:
        """Получает задание по ID"""
        return cls.TASKS.get(task_id)
    
    @classmethod
    def list_tasks(cls, category: Optional[str] = None) -> List[DailyTask]:
        """Возвращает список заданий"""
        if category:
            return [task for task in cls.TASKS.values() if task.category == category]
        return list(cls.TASKS.values())

# ---------- Глобальные переменные ----------
USER_WALLETS: Dict[int, UserWallet] = {}

# ---------- Функции для работы с валютой ----------
def get_user_wallet(user_id: int) -> UserWallet:
    """Получает или создает кошелек пользователя"""
    if user_id not in USER_WALLETS:
        USER_WALLETS[user_id] = UserWallet(user_id=user_id)
    return USER_WALLETS[user_id]

def add_funds_to_user(user_id: int, amount: float, currency: str = "RUB"):
    """Добавляет средства пользователю"""
    wallet = get_user_wallet(user_id)
    wallet.add_funds(amount)
    return wallet.balance

def spend_user_funds(user_id: int, amount: float) -> bool:
    """Тратит средства пользователя"""
    wallet = get_user_wallet(user_id)
    return wallet.spend_funds(amount)

def get_user_balance(user_id: int) -> float:
    """Получает баланс пользователя"""
    wallet = get_user_wallet(user_id)
    return wallet.balance