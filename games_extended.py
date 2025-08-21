"""
Игры для CryBot с правильным UX и inline-кнопками
"""
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


# -------- Базовые структуры для игр --------
@dataclass
class GameAction:
    """Действие в игре с кнопкой"""
    label: str
    emoji: str
    next_state: str
    command: str  # команда для обработки


@dataclass
class GameState:
    """Состояние игры"""
    state_id: str
    title: str
    description: str
    actions: List[GameAction]
    progress_text: str = ""
    show_progress_bar: bool = False


@dataclass
class GameSession:
    """Сессия игры пользователя"""
    user_id: int
    peer_id: int
    game_type: str
    current_state: str
    start_time: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)  # игровые данные
    is_active: bool = True


class GameEngine:
    """Движок для управления играми"""
    
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.games: Dict[str, Dict[str, GameState]] = {}
        self._init_games()
    
    def _init_games(self):
        """Инициализация всех игр"""
        self._init_conductor_game()
        self._init_hangman_game()
        self._init_poker_game()
    
    def _init_conductor_game(self):
        """Инициализация игры 'Проводница РЖД'"""
        self.games["conductor"] = {
            "welcome": GameState(
                state_id="welcome",
                title="🚂 Проводница РЖД",
                description="Привет! Это 'Проводница РЖД' — помоги пассажирам и сохрани поезд. Выбери действие:",
                actions=[
                    GameAction("Начать смену", "🚂", "on_duty", "start_shift"),
                    GameAction("Правила игры", "📖", "rules", "show_rules")
                ]
            ),
            "rules": GameState(
                state_id="rules",
                title="📖 Правила игры",
                description="""🎯 Цель: Помогай пассажирам и проверяй билеты
⏱️ Время: 5 поездов за смену
💰 Награда: Очки за каждый поезд
🏆 Бонус: За быструю и качественную работу""",
                actions=[
                    GameAction("Начать игру", "🚂", "on_duty", "start_shift"),
                    GameAction("Назад", "⬅️", "welcome", "back")
                ]
            ),
            "on_duty": GameState(
                state_id="on_duty",
                title="🚂 Проводница РЖД",
                description="Ты на поезде. Пассажиры заходят в вагон. Что делаешь?",
                actions=[
                    GameAction("Проверить билеты", "🎫", "check_tickets", "check_tickets"),
                    GameAction("Помочь пассажирам", "🤝", "help_passengers", "help_passengers"),
                    GameAction("Решить проблемы", "🔧", "solve_problems", "solve_problems"),
                    GameAction("Следующий поезд", "➡️", "next_train", "next_train")
                ],
                progress_text="Поезд {current_train} из {total_trains}",
                show_progress_bar=True
            ),
            "check_tickets": GameState(
                state_id="check_tickets",
                title="🎫 Проверка билетов",
                description="Проверяешь билеты у пассажиров...",
                actions=[
                    GameAction("Продолжить", "➡️", "on_duty", "continue"),
                    GameAction("Завершить смену", "🏁", "end_shift", "end_shift")
                ]
            ),
            "help_passengers": GameState(
                state_id="help_passengers",
                title="🤝 Помощь пассажирам",
                description="Помогаешь пассажирам с багажом и вопросами...",
                actions=[
                    GameAction("Продолжить", "➡️", "on_duty", "continue"),
                    GameAction("Завершить смену", "🏁", "end_shift", "end_shift")
                ]
            ),
            "solve_problems": GameState(
                state_id="solve_problems",
                title="🔧 Решение проблем",
                description="Решаешь проблемы с кондиционером и освещением...",
                actions=[
                    GameAction("Продолжить", "➡️", "on_duty", "continue"),
                    GameAction("Завершить смену", "🏁", "end_shift", "end_shift")
                ]
            ),
            "next_train": GameState(
                state_id="next_train",
                title="➡️ Следующий поезд",
                description="Переходишь к следующему поезду...",
                actions=[
                    GameAction("Продолжить", "➡️", "on_duty", "continue"),
                    GameAction("Завершить смену", "🏁", "end_shift", "end_shift")
                ]
            ),
            "end_shift": GameState(
                state_id="end_shift",
                title="🏁 Смена завершена",
                description="Подводим итоги твоей работы...",
                actions=[
                    GameAction("Новая смена", "🔄", "welcome", "new_shift"),
                    GameAction("В главное меню", "🏠", "main_menu", "main_menu")
                ]
            )
        }
    
    def _init_hangman_game(self):
        """Инициализация игры 'Виселица'"""
        self.games["hangman"] = {
            "welcome": GameState(
                state_id="welcome",
                title="🎯 Виселица",
                description="Привет! Это 'Виселица' — угадай слово по буквам. Выбери действие:",
                actions=[
                    GameAction("Начать игру", "🎯", "playing", "start_game"),
                    GameAction("Правила", "📖", "rules", "show_rules")
                ]
            ),
            "rules": GameState(
                state_id="rules",
                title="📖 Правила Виселицы",
                description="""🎯 Цель: Угадай слово по буквам
❌ Ошибок: Максимум 6
⏱️ Время: Чем быстрее, тем больше очков
💰 Награда: Очки за скорость и точность""",
                actions=[
                    GameAction("Начать игру", "🎯", "playing", "start_game"),
                    GameAction("Назад", "⬅️", "welcome", "back")
                ]
            ),
            "playing": GameState(
                state_id="playing",
                title="🎯 Виселица",
                description="Угадывай буквы! Слово: {word_display}",
                actions=[
                    GameAction("Угадать букву", "🔤", "guess_letter", "guess_letter"),
                    GameAction("Сдаться", "🏳️", "game_over", "give_up")
                ],
                progress_text="Ошибок: {wrong_guesses}/6",
                show_progress_bar=True
            ),
            "guess_letter": GameState(
                state_id="guess_letter",
                title="🔤 Угадывание буквы",
                description="Введи букву для угадывания...",
                actions=[
                    GameAction("Продолжить", "➡️", "playing", "continue"),
                    GameAction("Сдаться", "🏳️", "game_over", "give_up")
                ]
            ),
            "game_over": GameState(
                state_id="game_over",
                title="🏁 Игра окончена",
                description="Результат игры...",
                actions=[
                    GameAction("Новая игра", "🔄", "welcome", "new_game"),
                    GameAction("В главное меню", "🏠", "main_menu", "main_menu")
                ]
            )
        }
    
    def _init_poker_game(self):
        """Инициализация игры 'Покер'"""
        self.games["poker"] = {
            "welcome": GameState(
                state_id="welcome",
                title="🃏 Покер",
                description="Привет! Это 'Покер' — создай стол или присоединись к игре. Выбери действие:",
                actions=[
                    GameAction("Создать стол", "🃏", "create_table", "create_table"),
                    GameAction("Присоединиться", "➕", "join_table", "join_table"),
                    GameAction("Правила", "📖", "rules", "show_rules")
                ]
            ),
            "rules": GameState(
                state_id="rules",
                title="📖 Правила Покера",
                description="""🃏 Цель: Собрать лучшую комбинацию карт
👥 Игроков: 2-8 человек
💰 Ставки: Фишки за действия
🏆 Победа: Последний игрок с картами""",
                actions=[
                    GameAction("Создать стол", "🃏", "create_table", "create_table"),
                    GameAction("Присоединиться", "➕", "join_table", "join_table"),
                    GameAction("Назад", "⬅️", "welcome", "back")
                ]
            ),
            "create_table": GameState(
                state_id="create_table",
                title="🃏 Создание стола",
                description="Стол создан! Ожидание игроков...",
                actions=[
                    GameAction("Начать игру", "🎮", "playing", "start_game"),
                    GameAction("Отменить", "❌", "welcome", "cancel")
                ]
            ),
            "join_table": GameState(
                state_id="join_table",
                title="➕ Присоединение к столу",
                description="Выбери стол для присоединения...",
                actions=[
                    GameAction("Стол #1", "🃏", "playing", "join_1"),
                    GameAction("Стол #2", "🃏", "playing", "join_2"),
                    GameAction("Назад", "⬅️", "welcome", "back")
                ]
            ),
            "playing": GameState(
                state_id="playing",
                title="🃏 Покер",
                description="Твой ход! Выбери действие:",
                actions=[
                    GameAction("Ставка", "💰", "bet", "bet"),
                    GameAction("Колл", "✅", "call", "call"),
                    GameAction("Фолд", "❌", "fold", "fold"),
                    GameAction("Чек", "🤝", "check", "check")
                ],
                progress_text="Банк: {pot} 🪙 | Твои фишки: {chips}",
                show_progress_bar=True
            ),
            "bet": GameState(
                state_id="bet",
                title="💰 Ставка",
                description="Введи сумму ставки...",
                actions=[
                    GameAction("Продолжить", "➡️", "playing", "continue"),
                    GameAction("Отмена", "❌", "playing", "cancel")
                ]
            ),
            "game_over": GameState(
                state_id="game_over",
                title="🏁 Игра окончена",
                description="Результат игры...",
                actions=[
                    GameAction("Новая игра", "🔄", "welcome", "new_game"),
                    GameAction("В главное меню", "🏠", "main_menu", "main_menu")
                ]
            )
        }
    
    def start_game(self, user_id: int, peer_id: int, game_type: str) -> Tuple[str, List[Dict[str, str]]]:
        """Начать игру"""
        session_id = f"{game_type}_{user_id}_{peer_id}"
        
        # Создаем сессию
        session = GameSession(
            user_id=user_id,
            peer_id=peer_id,
            game_type=game_type,
            current_state="welcome"
        )
        self.sessions[session_id] = session
        
        return self._get_state_message(session_id)
    
    def handle_action(self, user_id: int, peer_id: int, game_type: str, command: str) -> Tuple[str, List[Dict[str, str]]]:
        """Обработать действие в игре"""
        session_id = f"{game_type}_{user_id}_{peer_id}"
        
        if session_id not in self.sessions:
            return "❌ Игра не найдена. Начни новую игру.", []
        
        session = self.sessions[session_id]
        if not session.is_active:
            return "❌ Игра завершена.", []
        
        # Обрабатываем команду
        result = self._process_command(session, command)
        
        return self._get_state_message(session_id)
    
    def _process_command(self, session: GameSession, command: str) -> str:
        """Обработать команду и обновить состояние"""
        game_type = session.game_type
        current_state = session.current_state
        
        # Обработка команд для разных игр
        if game_type == "conductor":
            return self._process_conductor_command(session, command)
        elif game_type == "hangman":
            return self._process_hangman_command(session, command)
        elif game_type == "poker":
            return self._process_poker_command(session, command)
        
        return "❌ Неизвестная команда"
    
    def _process_conductor_command(self, session: GameSession, command: str) -> str:
        """Обработать команду в игре 'Проводница РЖД'"""
        if command == "start_shift":
            session.current_state = "on_duty"
            session.data["current_train"] = 1
            session.data["total_trains"] = 5
            session.data["passengers_helped"] = 0
            session.data["tickets_checked"] = 0
            session.data["problems_solved"] = 0
            return "✅ Смена началась! Ты на первом поезде."
        
        elif command == "check_tickets":
            session.current_state = "check_tickets"
            session.data["tickets_checked"] += 1
            return "✅ Билеты проверены! Все пассажиры довольны 😊"
        
        elif command == "help_passengers":
            session.current_state = "help_passengers"
            session.data["passengers_helped"] += 1
            return "✅ Помог пассажиру! Спасибо за помощь 🤝"
        
        elif command == "solve_problems":
            session.current_state = "solve_problems"
            session.data["problems_solved"] += 1
            return "✅ Проблема решена! Поезд работает исправно 🔧"
        
        elif command == "next_train":
            session.current_state = "next_train"
            session.data["current_train"] += 1
            if session.data["current_train"] > session.data["total_trains"]:
                session.current_state = "end_shift"
                return "🏁 Все поезда обработаны! Смена завершена."
            return f"➡️ Переход к поезду {session.data['current_train']} из {session.data['total_trains']}"
        
        elif command == "end_shift":
            session.current_state = "end_shift"
            return "🏁 Смена завершена! Подводим итоги..."
        
        elif command == "continue":
            session.current_state = "on_duty"
            return "➡️ Продолжаем работу!"
        
        elif command == "new_shift":
            session.current_state = "welcome"
            session.data.clear()
            return "🔄 Новая смена готова к началу!"
        
        elif command == "back":
            session.current_state = "welcome"
            return "⬅️ Возвращаемся в главное меню"
        
        return "❌ Неизвестная команда"
    
    def _process_hangman_command(self, session: GameSession, command: str) -> str:
        """Обработать команду в игре 'Виселица'"""
        if command == "start_game":
            session.current_state = "playing"
            words = ["программирование", "компьютер", "алгоритм", "база данных", "интернет"]
            session.data["word"] = random.choice(words)
            session.data["guessed_letters"] = set()
            session.data["wrong_guesses"] = 0
            session.data["word_display"] = "_" * len(session.data["word"])
            return "🎯 Игра началась! Угадывай буквы!"
        
        elif command == "guess_letter":
            session.current_state = "guess_letter"
            return "🔤 Введи букву для угадывания..."
        
        elif command == "continue":
            session.current_state = "playing"
            return "➡️ Продолжаем игру!"
        
        elif command == "give_up":
            session.current_state = "game_over"
            session.is_active = False
            return f"🏁 Игра окончена! Слово было: {session.data.get('word', 'неизвестно')}"
        
        elif command == "new_game":
            session.current_state = "welcome"
            session.data.clear()
            session.is_active = True
            return "🔄 Новая игра готова!"
        
        elif command == "back":
            session.current_state = "welcome"
            return "⬅️ Возвращаемся в главное меню"
        
        return "❌ Неизвестная команда"
    
    def _process_poker_command(self, session: GameSession, command: str) -> str:
        """Обработать команду в игре 'Покер'"""
        if command == "create_table":
            session.current_state = "create_table"
            session.data["table_id"] = f"table_{int(time.time())}"
            session.data["players"] = [session.user_id]
            session.data["pot"] = 0
            session.data["chips"] = 1000
            return "🃏 Стол создан! Ожидание игроков..."
        
        elif command == "start_game":
            session.current_state = "playing"
            return "🎮 Игра началась! Твой ход!"
        
        elif command == "bet":
            session.current_state = "bet"
            return "💰 Введи сумму ставки..."
        
        elif command == "call":
            session.current_state = "playing"
            session.data["chips"] -= 50
            session.data["pot"] += 50
            return "✅ Ставка уравнена!"
        
        elif command == "fold":
            session.current_state = "game_over"
            session.is_active = False
            return "❌ Карты сброшены. Игра окончена."
        
        elif command == "check":
            session.current_state = "playing"
            return "🤝 Пас. Ход переходит к следующему игроку."
        
        elif command == "continue":
            session.current_state = "playing"
            return "➡️ Продолжаем игру!"
        
        elif command == "cancel":
            session.current_state = "playing"
            return "❌ Действие отменено."
        
        elif command == "new_game":
            session.current_state = "welcome"
            session.data.clear()
            session.is_active = True
            return "🔄 Новая игра готова!"
        
        elif command == "back":
            session.current_state = "welcome"
            return "⬅️ Возвращаемся в главное меню"
        
        return "❌ Неизвестная команда"
    
    def _get_state_message(self, session_id: str) -> Tuple[str, List[Dict[str, str]]]:
        """Получить сообщение и кнопки для текущего состояния"""
        session = self.sessions[session_id]
        game_type = session.game_type
        current_state = session.current_state
        
        if game_type not in self.games or current_state not in self.games[game_type]:
            return "❌ Состояние игры не найдено.", []
        
        state = self.games[game_type][current_state]
        
        # Формируем описание с подстановкой данных
        description = state.description
        if game_type == "conductor" and current_state == "on_duty":
            description = description.format(
                current_train=session.data.get("current_train", 1),
                total_trains=session.data.get("total_trains", 5)
            )
        elif game_type == "hangman" and current_state == "playing":
            description = description.format(
                word_display=session.data.get("word_display", "_____")
            )
        elif game_type == "poker" and current_state == "playing":
            description = description.format(
                pot=session.data.get("pot", 0),
                chips=session.data.get("chips", 1000)
            )
        
        # Формируем прогресс-бар
        progress_text = ""
        if state.show_progress_bar:
            if game_type == "conductor":
                current = session.data.get("current_train", 1)
                total = session.data.get("total_trains", 5)
                progress = int((current / total) * 100)
                progress_text = f"\n\n📊 Прогресс: [{('█' * (progress // 20)).ljust(5, '░')}] {progress}%"
            elif game_type == "hangman":
                wrong = session.data.get("wrong_guesses", 0)
                progress = int((wrong / 6) * 100)
                progress_text = f"\n\n📊 Прогресс: [{('█' * (progress // 20)).ljust(5, '░')}] {progress}%"
        
        # Формируем кнопки
        buttons = []
        for action in state.actions:
            buttons.append({
                "label": f"{action.emoji} {action.label}",
                "command": f"/game {game_type} {action.command}"
            })
        
        # Формируем итоговое сообщение
        message = f"{state.title}\n\n{description}{progress_text}"
        
        if state.progress_text:
            progress_text = state.progress_text
            if game_type == "conductor":
                progress_text = progress_text.format(
                    current_train=session.data.get("current_train", 1),
                    total_trains=session.data.get("total_trains", 5)
                )
            elif game_type == "hangman":
                progress_text = progress_text.format(
                    wrong_guesses=session.data.get("wrong_guesses", 0)
                )
            elif game_type == "poker":
                progress_text = progress_text.format(
                    pot=session.data.get("pot", 0),
                    chips=session.data.get("chips", 1000)
                )
            message += f"\n\n{progress_text}"
        
        return message, buttons


# Глобальный экземпляр движка игр
game_engine = GameEngine()