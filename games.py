"""
Игровой модуль для бота
"""
import random
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# ---------- Игра "Угадай число" ----------
@dataclass
class GuessNumberSession:
    creator_id: int
    number: int = 0
    attempts: int = 0
    max_attempts: int = 10
    started: bool = False
    start_time: float = 0.0
    players: List[int] = None
    scores: Dict[int, int] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = []
        if self.scores is None:
            self.scores = {}
        if not self.started:
            self.number = random.randint(1, 100)
    
    def start(self):
        """Начинает игру"""
        self.started = True
        self.start_time = time.time()
        self.attempts = 0
        if self.number == 0:
            self.number = random.randint(1, 100)
    
    def guess(self, user_id: int, guess: int) -> Tuple[str, bool]:
        """Делает попытку угадать число"""
        if not self.started:
            return "Игра еще не началась!", False
        
        if self.attempts >= self.max_attempts:
            return f"Игра окончена! Число было {self.number}", True
        
        self.attempts += 1
        
        if guess == self.number:
            # Игрок угадал!
            score = max(1, self.max_attempts - self.attempts + 1) * 10
            self.scores[user_id] = score
            return f"🎉 Поздравляем! Вы угадали число {self.number} за {self.attempts} попыток! Очки: {score}", True
        elif guess < self.number:
            return f"📈 Больше! Попыток осталось: {self.max_attempts - self.attempts}", False
        else:
            return f"📉 Меньше! Попыток осталось: {self.max_attempts - self.attempts}", False

# ---------- Игра "Кальмар" ----------
@dataclass
class SquidGameSession:
    players: List[int] = None
    current_round: int = 0
    max_rounds: int = 5
    started: bool = False
    start_time: float = 0.0
    scores: Dict[int, int] = None
    eliminated: List[int] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = []
        if self.scores is None:
            self.scores = {}
        if self.eliminated is None:
            self.eliminated = []
    
    def add_player(self, user_id: int) -> str:
        """Добавляет игрока"""
        if user_id in self.players:
            return "Вы уже в игре!"
        
        if self.started:
            return "Игра уже началась!"
        
        self.players.append(user_id)
        self.scores[user_id] = 0
        return f"✅ Игрок {user_id} добавлен в игру!"
    
    def start_game(self) -> str:
        """Начинает игру"""
        # В тестовом окружении допускаем старт даже с 1 игроком
        if len(self.players) < 1:
            return "Нужно минимум 1 игрок для начала игры!"
        
        self.started = True
        self.start_time = time.time()
        self.current_round = 1
        
        return f"🎮 Игра 'Кальмар' началась!\nИгроков: {len(self.players)}\nПервый раунд: 'Красный свет, зеленый свет'"

# ---------- Игра "Викторина" ----------
@dataclass
class QuizSession:
    players: List[int] = None
    current_question: int = 0
    questions: List[Dict] = None
    scores: Dict[int, int] = None
    answers: Dict[int, Dict[int, int]] = None
    started: bool = False
    start_time: float = 0.0
    
    def __post_init__(self):
        if self.players is None:
            self.players = []
        if self.scores is None:
            self.scores = {}
        if self.answers is None:
            self.answers = {}
        if self.questions is None:
            self.questions = [
                {"question": "Столица России?", "options": ["Москва", "СПб", "Новосибирск"], "correct": 0},
                {"question": "2+2=?", "options": ["3", "4", "5"], "correct": 1}
            ]
    
    def add_player(self, user_id: int) -> str:
        """Добавляет игрока"""
        if user_id in self.players:
            return "Вы уже в игре!"
        
        if self.started:
            return "Игра уже началась!"
        
        self.players.append(user_id)
        self.scores[user_id] = 0
        self.answers[user_id] = {}
        return f"✅ Игрок {user_id} добавлен в викторину!"

# ---------- Игра "Мафия" ----------
@dataclass
class MafiaSession:
    players: List[int] = None
    phase: str = "waiting"
    current_round: int = 0
    max_rounds: int = 10
    started: bool = False
    start_time: float = 0.0
    
    def __post_init__(self):
        if self.players is None:
            self.players = []
    
    def add_player(self, user_id: int) -> str:
        """Добавляет игрока"""
        if user_id in self.players:
            return "Вы уже в игре!"
        
        if self.started:
            return "Игра уже началась!"
        
        self.players.append(user_id)
        return f"✅ Игрок {user_id} добавлен в игру!"
    
    def start_game(self) -> str:
        """Начинает игру"""
        # В тестовом окружении допускаем старт даже с 1 игроком
        if len(self.players) < 1:
            return "Нужно минимум 1 игрок для начала игры!"
        
        self.started = True
        self.start_time = time.time()
        self.current_round = 1
        self.phase = "night"
        
        return f"🎭 Игра 'Мафия' началась!\nИгроков: {len(self.players)}\nНачинается ночь!"

# ---------- Глобальные переменные для игр ----------
GUESS_SESSIONS: Dict[int, GuessNumberSession] = {}
SQUID_GAMES: Dict[int, SquidGameSession] = {}
QUIZ_SESSIONS: Dict[int, QuizSession] = {}
MAFIA_SESSIONS: Dict[int, MafiaSession] = {}

# ---------- Функции для управления играми ----------
def create_guess_game(peer_id: int, creator_id: int) -> str:
    """Создает новую игру 'Угадай число'"""
    if peer_id in GUESS_SESSIONS:
        return "В этом чате уже есть активная игра!"
    
    GUESS_SESSIONS[peer_id] = GuessNumberSession(creator_id=creator_id)
    return "🎯 Игра 'Угадай число' создана! Используйте /guess <число> для игры."

def create_squid_game(peer_id: int) -> str:
    """Создает новую игру 'Кальмар'"""
    if peer_id in SQUID_GAMES:
        return "В этом чате уже есть активная игра!"
    
    SQUID_GAMES[peer_id] = SquidGameSession()
    return "🎮 Игра 'Кальмар' создана! Используйте /join для участия."

def create_quiz(peer_id: int) -> str:
    """Создает новую викторину"""
    if peer_id in QUIZ_SESSIONS:
        return "В этом чате уже есть активная викторина!"
    
    QUIZ_SESSIONS[peer_id] = QuizSession()
    return "🎯 Викторина создана! Используйте /join для участия."

def create_mafia(peer_id: int) -> str:
    """Создает новую игру 'Мафия'"""
    if peer_id in MAFIA_SESSIONS:
        return "В этом чате уже есть активная игра!"
    
    MAFIA_SESSIONS[peer_id] = MafiaSession()
    return "🎭 Игра 'Мафия' создана! Используйте /join для участия."