"""
Расширенные игры для CryBot
"""
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


# -------- Проводница РЖД --------
class TrainStatus(Enum):
    ON_TIME = "время"
    DELAYED = "задержка"
    CANCELLED = "отменён"
    DIVERTED = "перенаправлен"


@dataclass
class Train:
    number: str
    route: str
    departure: str
    arrival: str
    status: TrainStatus
    delay_minutes: int = 0
    platform: str = "?"
    passengers: int = 0
    problems: List[str] = field(default_factory=list)


@dataclass
class ConductorSession:
    peer_id: int
    user_id: int
    score: int = 0
    trains_handled: int = 0
    passengers_helped: int = 0
    problems_solved: int = 0
    start_time: float = field(default_factory=time.time)
    current_train: Optional[Train] = None
    is_active: bool = False


class ConductorGame:
    def __init__(self):
        self.sessions: Dict[int, ConductorSession] = {}
        self.routes = [
            "Москва - Санкт-Петербург",
            "Москва - Екатеринбург", 
            "Санкт-Петербург - Сочи",
            "Казань - Москва",
            "Новосибирск - Москва",
            "Владивосток - Москва",
            "Калининград - Москва"
        ]
        self.stations = [
            "Москва", "Санкт-Петербург", "Екатеринбург", "Сочи", "Казань",
            "Новосибирск", "Владивосток", "Калининград", "Нижний Новгород",
            "Самара", "Ростов-на-Дону", "Уфа", "Краснодар", "Пермь"
        ]
        self.problems = [
            "опоздание", "переполнение", "поломка", "погодные условия",
            "ремонт пути", "карантин", "технические работы"
        ]
    
    def start_session(self, peer_id: int, user_id: int) -> str:
        if peer_id in self.sessions:
            return "❌ Игра уже идёт в этом чате"
        
        session = ConductorSession(peer_id=peer_id, user_id=user_id, is_active=True)
        self.sessions[peer_id] = session
        
        # Генерируем первый поезд
        train = self._generate_train()
        session.current_train = train
        
        return (
            f"🚂 Добро пожаловать на работу проводницы РЖД!\n\n"
            f"Поезд №{train.number}\n"
            f"Маршрут: {train.route}\n"
            f"Отправление: {train.departure}\n"
            f"Прибытие: {train.arrival}\n"
            f"Статус: {train.status.value}\n"
            f"Платформа: {train.platform}\n"
            f"Пассажиры: {train.passengers}\n\n"
            f"Что делаем? (проверить билеты, помочь пассажирам, решить проблемы)"
        )
    
    def _generate_train(self) -> Train:
        route = random.choice(self.routes)
        dep, arr = route.split(" - ")
        
        status = random.choice(list(TrainStatus))
        delay = random.randint(0, 120) if status == TrainStatus.DELAYED else 0
        
        problems = []
        if random.random() < 0.3:  # 30% шанс проблем
            problems = random.sample(self.problems, random.randint(1, 2))
        
        return Train(
            number=f"{random.randint(1, 999):03d}",
            route=route,
            departure=dep,
            arrival=arr,
            status=status,
            delay_minutes=delay,
            platform=str(random.randint(1, 20)),
            passengers=random.randint(50, 500),
            problems=problems
        )
    
    def handle_action(self, peer_id: int, action: str) -> str:
        if peer_id not in self.sessions:
            return "❌ Игра не запущена. Напиши /conductor"
        
        session = self.sessions[peer_id]
        if not session.is_active:
            return "❌ Игра завершена"
        
        train = session.current_train
        if not train:
            return "❌ Ошибка: поезд не найден"
        
        if action == "проверить билеты":
            return self._check_tickets(session, train)
        elif action == "помочь пассажирам":
            return self._help_passengers(session, train)
        elif action == "решить проблемы":
            return self._solve_problems(session, train)
        elif action == "следующий поезд":
            return self._next_train(session)
        elif action == "завершить смену":
            return self._end_shift(session)
        else:
            return (
                f"❓ Непонятная команда. Доступные действия:\n"
                f"• проверить билеты\n"
                f"• помочь пассажирам\n"
                f"• решить проблемы\n"
                f"• следующий поезд\n"
                f"• завершить смену"
            )
    
    def _check_tickets(self, session: ConductorSession, train: Train) -> str:
        # Проверка билетов
        score_gain = random.randint(5, 15)
        session.score += score_gain
        session.trains_handled += 1
        
        return (
            f"🎫 Проверка билетов завершена!\n"
            f"✅ Все пассажиры имеют билеты\n"
            f"💰 +{score_gain} очков\n"
            f"📊 Общий счёт: {session.score}"
        )
    
    def _help_passengers(self, session: ConductorSession, train: Train) -> str:
        # Помощь пассажирам
        help_count = random.randint(3, 8)
        score_gain = help_count * 2
        session.score += score_gain
        session.passengers_helped += help_count
        
        return (
            f"👥 Помощь пассажирам оказана!\n"
            f"✅ Помогли {help_count} пассажирам\n"
            f"💰 +{score_gain} очков\n"
            f"📊 Общий счёт: {session.score}"
        )
    
    def _solve_problems(self, session: ConductorSession, train: Train) -> str:
        if not train.problems:
            return "✅ Проблем нет, поезд идёт по расписанию!"
        
        # Решение проблем
        solved = random.randint(1, len(train.problems))
        score_gain = solved * 10
        session.score += score_gain
        session.problems_solved += solved
        
        return (
            f"🔧 Проблемы решены!\n"
            f"✅ Решили {solved} из {len(train.problems)} проблем\n"
            f"💰 +{score_gain} очков\n"
            f"📊 Общий счёт: {session.score}"
        )
    
    def _next_train(self, session: ConductorSession) -> str:
        # Переход к следующему поезду
        train = self._generate_train()
        session.current_train = train
        
        return (
            f"🚂 Следующий поезд!\n\n"
            f"Поезд №{train.number}\n"
            f"Маршрут: {train.route}\n"
            f"Отправление: {train.departure}\n"
            f"Прибытие: {train.arrival}\n"
            f"Статус: {train.status.value}\n"
            f"Платформа: {train.platform}\n"
            f"Пассажиры: {train.passengers}\n"
            f"Проблемы: {', '.join(train.problems) if train.problems else 'нет'}"
        )
    
    def _end_shift(self, session: ConductorSession) -> str:
        # Завершение смены
        duration = int(time.time() - session.start_time) // 60
        session.is_active = False
        
        total_score = session.score
        bonus = session.trains_handled * 5 + session.passengers_helped * 2 + session.problems_solved * 10
        
        final_score = total_score + bonus
        
        result = (
            f"🏁 Смена завершена!\n\n"
            f"📊 Статистика:\n"
            f"• Обработано поездов: {session.trains_handled}\n"
            f"• Помогли пассажирам: {session.passengers_helped}\n"
            f"• Решили проблем: {session.problems_solved}\n"
            f"• Время смены: {duration} мин\n\n"
            f"💰 Итоговый счёт: {final_score}\n"
            f"🎯 Бонус за эффективность: +{bonus}"
        )
        
        # Очищаем сессию
        del self.sessions[session.peer_id]
        
        return result


# -------- Покер --------
class PokerHand(Enum):
    HIGH_CARD = "старшая карта"
    PAIR = "пара"
    TWO_PAIR = "две пары"
    THREE_OF_KIND = "тройка"
    STRAIGHT = "стрит"
    FLUSH = "флеш"
    FULL_HOUSE = "фулл-хаус"
    FOUR_OF_KIND = "каре"
    STRAIGHT_FLUSH = "стрит-флеш"
    ROYAL_FLUSH = "роял-флеш"


@dataclass
class Card:
    suit: str
    rank: str
    value: int


@dataclass
class PokerPlayer:
    user_id: int
    name: str
    chips: int = 1000
    hand: List[Card] = field(default_factory=list)
    bet: int = 0
    folded: bool = False
    is_all_in: bool = False


@dataclass
class PokerGame:
    peer_id: int
    players: Dict[int, PokerPlayer] = field(default_factory=dict)
    deck: List[Card] = field(default_factory=list)
    pot: int = 0
    current_bet: int = 0
    dealer: int = 0
    is_active: bool = False
    round: str = "preflop"  # preflop, flop, turn, river
    community_cards: List[Card] = field(default_factory=list)


class PokerGameManager:
    def __init__(self):
        self.games: Dict[int, PokerGame] = {}
        self.suits = ["♠", "♥", "♦", "♣"]
        self.ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    def create_game(self, peer_id: int, creator_id: int, creator_name: str) -> str:
        if peer_id in self.games:
            return "❌ Игра уже идёт в этом чате"
        
        game = PokerGame(peer_id=peer_id)
        game.players[creator_id] = PokerPlayer(user_id=creator_id, name=creator_name)
        game.is_active = True
        self.games[peer_id] = game
        
        return (
            f"🃏 Покер-стол создан!\n"
            f"👤 Игрок: {creator_name}\n"
            f"💰 Фишки: 1000\n\n"
            f"Другие игроки могут присоединиться командой /poker join"
        )
    
    def join_game(self, peer_id: int, user_id: int, name: str) -> str:
        if peer_id not in self.games:
            return "❌ Игра не создана. Создайте игру командой /poker create"
        
        game = self.games[peer_id]
        if user_id in game.players:
            return "❌ Вы уже в игре"
        
        if len(game.players) >= 8:
            return "❌ Максимум 8 игроков"
        
        game.players[user_id] = PokerPlayer(user_id=user_id, name=name)
        
        return (
            f"✅ {name} присоединился к игре!\n"
            f"👥 Игроков: {len(game.players)}\n"
            f"💰 Фишки: 1000"
        )


# -------- Шахматы --------
class ChessPiece(Enum):
    PAWN = "♟"
    ROOK = "♜"
    KNIGHT = "♞"
    BISHOP = "♝"
    QUEEN = "♛"
    KING = "♚"


@dataclass
class ChessMove:
    from_pos: str
    to_pos: str
    piece: ChessPiece
    is_capture: bool = False
    is_check: bool = False
    is_checkmate: bool = False


@dataclass
class ChessGame:
    peer_id: int
    white_player: int
    black_player: int
    current_turn: int
    board: List[List[Optional[Tuple[ChessPiece, bool]]]] = field(default_factory=list)  # (piece, is_white)
    move_history: List[ChessMove] = field(default_factory=list)
    is_active: bool = False
    winner: Optional[int] = None


# -------- Виселица --------
@dataclass
class HangmanGame:
    peer_id: int
    word: str
    guessed_letters: Set[str] = field(default_factory=set)
    wrong_guesses: int = 0
    max_wrong: int = 6
    is_active: bool = False
    start_time: float = field(default_factory=time.time)


class HangmanManager:
    def __init__(self):
        self.games: Dict[int, HangmanGame] = {}
        self.words = [
            "программирование", "компьютер", "алгоритм", "база данных",
            "интернет", "сервер", "клиент", "функция", "переменная",
            "массив", "объект", "класс", "метод", "интерфейс"
        ]
    
    def start_game(self, peer_id: int) -> str:
        if peer_id in self.games:
            return "❌ Игра уже идёт в этом чате"
        
        word = random.choice(self.words)
        game = HangmanGame(peer_id=peer_id, word=word, is_active=True)
        self.games[peer_id] = game
        
        return (
            f"🎯 Виселица началась!\n\n"
            f"Слово: {'_' * len(word)}\n"
            f"Букв: {len(word)}\n"
            f"Ошибок: 0/{game.max_wrong}\n\n"
            f"Угадывайте буквы по одной!"
        )
    
    def guess_letter(self, peer_id: int, letter: str) -> str:
        if peer_id not in self.games:
            return "❌ Игра не запущена"
        
        game = self.games[peer_id]
        if not game.is_active:
            return "❌ Игра завершена"
        
        letter = letter.lower()
        if len(letter) != 1:
            return "❌ Угадывайте по одной букве"
        
        if letter in game.guessed_letters:
            return "❌ Эта буква уже была"
        
        game.guessed_letters.add(letter)
        
        if letter in game.word:
            # Правильная буква
            if self._is_word_guessed(game):
                return self._end_game(game, True)
            else:
                return self._get_game_status(game)
        else:
            # Неправильная буква
            game.wrong_guesses += 1
            if game.wrong_guesses >= game.max_wrong:
                return self._end_game(game, False)
            else:
                return self._get_game_status(game)
    
    def _is_word_guessed(self, game: HangmanGame) -> bool:
        return all(letter in game.guessed_letters for letter in game.word)
    
    def _get_game_status(self, game: HangmanGame) -> str:
        display_word = ""
        for letter in game.word:
            if letter in game.guessed_letters:
                display_word += letter
            else:
                display_word += "_"
        
        return (
            f"🎯 Слово: {display_word}\n"
            f"Угаданные буквы: {', '.join(sorted(game.guessed_letters))}\n"
            f"Ошибок: {game.wrong_guesses}/{game.max_wrong}\n"
            f"Осталось попыток: {game.max_wrong - game.wrong_guesses}"
        )
    
    def _end_game(self, game: HangmanGame, won: bool) -> str:
        game.is_active = False
        
        if won:
            result = f"🎉 Поздравляем! Слово угадано: {game.word}"
        else:
            result = f"💀 Игра окончена! Слово было: {game.word}"
        
        # Очищаем игру
        del self.games[game.peer_id]
        
        return result


# Глобальные экземпляры игр
conductor_game = ConductorGame()
poker_manager = PokerGameManager()
hangman_manager = HangmanManager()