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
        
        # Случайные события при проверке билетов
        events = [
            "Все пассажиры имеют действующие билеты ✅",
            "Нашли безбилетника, но он купил билет ✅",
            "Пассажир потерял билет, помогли восстановить ✅",
            "Проверили билеты у VIP-пассажира ✅",
            "Обнаружили поддельный билет, пассажир купил новый ✅"
        ]
        event = random.choice(events)
        
        return (
            f"🎫 Проверка билетов завершена!\n"
            f"{event}\n"
            f"💰 +{score_gain} очков\n"
            f"📊 Общий счёт: {session.score}"
        )
    
    def _help_passengers(self, session: ConductorSession, train: Train) -> str:
        # Помощь пассажирам
        help_count = random.randint(3, 8)
        score_gain = help_count * 2
        session.score += score_gain
        session.passengers_helped += help_count
        
        # Случайные события помощи пассажирам
        events = [
            f"Помогли {help_count} пассажирам с багажом 🤝",
            f"Объяснили расписание поездов {help_count} пассажирам 🤝", 
            f"Нашли потерянные вещи для {help_count} пассажиров 🤝",
            f"Помогли {help_count} пассажирам с детьми 🤝",
            f"Оказали первую помощь {help_count} пассажирам 🏥"
        ]
        event = random.choice(events)
        
        return (
            f"👥 Помощь пассажирам оказана!\n"
            f"{event}\n"
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
        
        # Сохраняем результат в экономику
        try:
            from economy_social import economy_manager
            economy_manager.add_money(session.user_id, final_score // 10)  # 10% от очков в монеты
        except Exception:
            pass
        
        result = (
            f"🏁 Смена завершена!\n\n"
            f"📊 Статистика:\n"
            f"• Обработано поездов: {session.trains_handled}\n"
            f"• Помогли пассажирам: {session.passengers_helped}\n"
            f"• Решили проблем: {session.problems_solved}\n"
            f"• Время смены: {duration} мин\n\n"
            f"💰 Итоговый счёт: {final_score}\n"
            f"🎯 Бонус за эффективность: +{bonus}\n"
            f"🪙 Получено монет: {final_score // 10}"
        )
        
        # Очищаем сессию
        del self.sessions[session.peer_id]
        
        return result


# -------- Шахматы --------
@dataclass
class ChessGame:
    game_id: str
    white_player: int
    black_player: int
    current_turn: int  # white_player или black_player
    board: List[List[str]] = field(default_factory=lambda: [
        ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
        ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
        ['', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', ''],
        ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
        ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    ])
    move_history: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    is_active: bool = True
    winner: Optional[int] = None

class ChessManager:
    def __init__(self):
        self.games: Dict[str, ChessGame] = {}
        self.game_counter = 1
    
    def create_game(self, white_player: int, black_player: int) -> str:
        game_id = f"chess_{self.game_counter}"
        self.game_counter += 1
        
        game = ChessGame(
            game_id=game_id,
            white_player=white_player,
            black_player=black_player,
            current_turn=white_player
        )
        
        self.games[game_id] = game
        return f"♟️ Шахматная партия создана!\n\nБелые: {white_player}\nЧёрные: {black_player}\n\nХод белых. Отправьте ход в формате 'e2e4'"
    
    def make_move(self, game_id: str, player_id: int, move: str) -> str:
        if game_id not in self.games:
            return "❌ Игра не найдена"
        
        game = self.games[game_id]
        if not game.is_active:
            return "❌ Игра завершена"
        
        if player_id != game.current_turn:
            return "❌ Не ваш ход"
        
        # Улучшенная валидация хода
        if len(move) != 4 or not move.isalpha():
            return "❌ Неверный формат хода. Используйте 'e2e4'"
        
        # Проверяем корректность координат
        from_pos, to_pos = move[:2], move[2:]
        if not (from_pos[0] in 'abcdefgh' and from_pos[1] in '12345678' and 
                to_pos[0] in 'abcdefgh' and to_pos[1] in '12345678'):
            return "❌ Неверные координаты. Используйте буквы a-h и цифры 1-8"
        
        # Добавляем ход в историю
        game.move_history.append(move)
        
        # Передаём ход
        game.current_turn = game.black_player if game.current_turn == game.white_player else game.white_player
        
        # Проверяем условия завершения игры
        if len(game.move_history) >= 20:
            game.is_active = False
            game.winner = player_id
            duration = int(time.time() - game.start_time)
            
            # Интеграция с экономикой
            try:
                from economy_social import economy_manager
                economy_manager.add_money(player_id, 50)  # 50 монет за победу
            except Exception:
                pass
            
            return f"♟️ Игра завершена!\n🏆 Победитель: {game.winner}\n📊 Ходов: {len(game.move_history)}\n⏱️ Время: {duration} сек\n🪙 Получено монет: 50"
        
        # Показываем текущую позицию
        board_str = self.get_board(game_id)
        return f"✅ Ход {move} сделан!\nХод {'чёрных' if game.current_turn == game.black_player else 'белых'}\n\n{board_str}"
    
    def get_board(self, game_id: str) -> str:
        if game_id not in self.games:
            return "❌ Игра не найдена"
        
        game = self.games[game_id]
        board_str = "♟️ Текущая позиция:\n\n"
        
        for i, row in enumerate(game.board):
            board_str += f"{8-i} "
            for piece in row:
                if piece == '':
                    board_str += "· "
                else:
                    board_str += f"{piece} "
            board_str += "\n"
        
        board_str += "  a b c d e f g h"
        return board_str

# -------- Кроссворды --------
@dataclass
class CrosswordGame:
    game_id: str
    player_id: int
    words: List[Dict[str, str]]  # [{"word": "ПРИВЕТ", "clue": "Приветствие", "solved": False}]
    current_word_index: int = 0
    score: int = 0
    start_time: float = field(default_factory=time.time)
    is_active: bool = True

class CrosswordManager:
    def __init__(self):
        self.games: Dict[int, CrosswordGame] = {}
        self.word_sets = [
            [
                {"word": "ПРИВЕТ", "clue": "Приветствие на русском"},
                {"word": "МАШИНА", "clue": "Транспортное средство"},
                {"word": "КОМПЬЮТЕР", "clue": "Электронное устройство для работы"},
                {"word": "ПРОГРАММИРОВАНИЕ", "clue": "Создание программ для компьютера"}
            ],
            [
                {"word": "ИГРА", "clue": "Развлечение для детей и взрослых"},
                {"word": "МУЗЫКА", "clue": "Искусство звуков"},
                {"word": "КНИГА", "clue": "Печатное издание с текстом"},
                {"word": "ПРИРОДА", "clue": "Окружающий мир"}
            ]
        ]
    
    def start_game(self, player_id: int) -> str:
        if player_id in self.games:
            return "❌ У вас уже есть активная игра"
        
        word_set = random.choice(self.word_sets)
        game = CrosswordGame(
            game_id=f"crossword_{player_id}_{int(time.time())}",
            player_id=player_id,
            words=word_set.copy()
        )
        
        self.games[player_id] = game
        
        return f"📝 Кроссворд начат!\n\nСлово 1: {game.words[0]['clue']}\n\nОтправьте ответ:"
    
    def guess_word(self, player_id: int, guess: str) -> str:
        if player_id not in self.games:
            return "❌ Нет активной игры"
        
        game = self.games[player_id]
        if not game.is_active:
            return "❌ Игра завершена"
        
        current_word = game.words[game.current_word_index]
        
        if guess.upper() == current_word["word"]:
            current_word["solved"] = True
            
            # Вычисляем очки за слово
            word_length = len(current_word["word"])
            base_score = word_length * 2  # 2 очка за букву
            time_bonus = max(0, 30 - (time.time() - game.start_time) // 10)  # Бонус за скорость
            
            word_score = base_score + time_bonus
            game.score += word_score
            game.current_word_index += 1
            
            if game.current_word_index >= len(game.words):
                # Игра завершена
                game.is_active = False
                duration = int(time.time() - game.start_time)
                
                # Финальные бонусы
                completion_bonus = 50  # Бонус за завершение
                speed_bonus = max(0, 100 - duration // 10)  # Бонус за общую скорость
                final_score = game.score + completion_bonus + speed_bonus
                
                result = f"🎉 Кроссворд решён!\n\n"
                result += f"📊 Результаты:\n"
                result += f"💰 Очки: {final_score}\n"
                result += f"⏱️ Время: {duration} сек\n"
                result += f"📝 Слов отгадано: {len(game.words)}\n"
                result += f"🏆 Бонус за завершение: +{completion_bonus}\n"
                result += f"⚡ Бонус за скорость: +{speed_bonus}\n\n"
                result += f"Все слова отгаданы!"
                
                # Интеграция с экономикой
                try:
                    from economy_social import economy_manager
                    economy_manager.add_money(player_id, final_score // 15)  # ~6.7% от очков в монеты
                    result += f"\n🪙 Получено монет: {final_score // 15}"
                except Exception:
                    pass
                
                # Очищаем игру
                del self.games[player_id]
                
                return result
            else:
                next_word = game.words[game.current_word_index]
                return f"✅ Правильно! +{word_score} очков\n\nСлово {game.current_word_index + 1}: {next_word['clue']}\n\nОтправьте ответ:"
        else:
            # Подсказки для неправильного ответа
            hint = self._get_hint(current_word["word"], guess)
            return f"❌ Неправильно. Попробуйте ещё раз.\n\nПодсказка: {current_word['clue']}\n💡 {hint}"
    
    def _get_hint(self, correct_word: str, guess: str) -> str:
        """Генерирует подсказку на основе неправильного ответа"""
        if len(guess) != len(correct_word):
            return f"Слово состоит из {len(correct_word)} букв"
        
        # Показываем правильные буквы на правильных позициях
        correct_positions = sum(1 for i, (c1, c2) in enumerate(zip(guess.upper(), correct_word)) if c1 == c2)
        if correct_positions > 0:
            return f"Правильных букв на месте: {correct_positions}"
        
        # Показываем общие буквы
        common_letters = set(guess.upper()) & set(correct_word)
        if common_letters:
            return f"Общие буквы: {', '.join(sorted(common_letters))}"
        
        return "Попробуйте другое слово"

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
        
        result = f"✅ {name} присоединился к игре!\n"
        result += f"👥 Игроков: {len(game.players)}\n"
        result += f"💰 Фишки: 1000\n\n"
        
        if len(game.players) >= 2:
            result += "🎮 Игра готова к началу!\n"
            result += "Команда: /poker start"
        else:
            result += "⏳ Ожидание игроков... (нужно минимум 2)"
        
        return result
    
    def start_game(self, peer_id: int) -> str:
        if peer_id not in self.games:
            return "❌ Игра не найдена"
        
        game = self.games[peer_id]
        if len(game.players) < 2:
            return "❌ Недостаточно игроков. Нужно минимум 2"
        
        # Начинаем игру
        game.is_active = True
        game.round = "preflop"
        game.deal_cards()
        
        # Определяем дилера и первого игрока
        player_ids = list(game.players.keys())
        game.dealer = player_ids[0]
        game.current_player = player_ids[1] if len(player_ids) > 1 else player_ids[0]
        
        result = "🎮 Покер начался!\n\n"
        result += f"Дилер: {game.players[game.dealer].name}\n"
        result += f"Текущий игрок: {game.players[game.current_player].name}\n"
        result += f"Фаза: {game.round}\n"
        result += f"Банк: {game.pot} 🪙\n\n"
        result += "Доступные действия:\n"
        result += "• /poker bet <сумма> - сделать ставку\n"
        result += "• /poker call - уравнять ставку\n"
        result += "• /poker fold - сбросить карты\n"
        result += "• /poker check - пас (если нет ставок)\n"
        result += "• /poker show - показать карты\n"
        
        return result
    
    def deal_cards(self, peer_id: int) -> str:
        """Раздача карт"""
        if peer_id not in self.games:
            return "❌ Игра не найдена"
        
        game = self.games[peer_id]
        
        # Создаем колоду
        game.deck = []
        for suit in self.suits:
            for rank in self.ranks:
                game.deck.append(Card(suit=suit, rank=rank))
        
        # Перемешиваем
        random.shuffle(game.deck)
        
        # Раздаем по 2 карты каждому игроку
        for player in game.players.values():
            player.cards = [game.deck.pop(), game.deck.pop()]
        
        return "🃏 Карты разданы!"
    
    def make_action(self, peer_id: int, player_id: int, action: str, amount: int = 0) -> str:
        """Выполнение действия в покере"""
        if peer_id not in self.games:
            return "❌ Игра не найдена"
        
        game = self.games[peer_id]
        if not game.is_active:
            return "❌ Игра не активна"
        
        if player_id != game.current_player:
            return "❌ Не ваш ход"
        
        player = game.players[player_id]
        
        if action == "fold":
            player.folded = True
            result = f"❌ {player.name} сбросил карты"
        elif action == "check":
            if game.current_bet > 0:
                return "❌ Нельзя пасовать при наличии ставок"
            result = f"✅ {player.name} пасует"
        elif action == "call":
            if game.current_bet == 0:
                return "❌ Нет ставок для уравнивания"
            if player.chips < game.current_bet:
                return "❌ Недостаточно фишек"
            player.chips -= game.current_bet
            game.pot += game.current_bet
            result = f"✅ {player.name} уравнял ставку {game.current_bet} 🪙"
        elif action == "bet":
            if amount <= game.current_bet:
                return "❌ Ставка должна быть больше текущей"
            if player.chips < amount:
                return "❌ Недостаточно фишек"
            player.chips -= amount
            game.pot += amount
            game.current_bet = amount
            result = f"💰 {player.name} поставил {amount} 🪙"
        else:
            return "❌ Неизвестное действие"
        
        # Передаем ход следующему игроку
        self._next_player(game)
        
        return result
    
    def _next_player(self, game: PokerGame) -> None:
        """Переход к следующему игроку"""
        player_ids = [pid for pid, player in game.players.items() if not player.folded]
        
        if len(player_ids) <= 1:
            # Игра завершена
            self._end_game(game)
            return
        
        current_index = player_ids.index(game.current_player)
        next_index = (current_index + 1) % len(player_ids)
        game.current_player = player_ids[next_index]


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
        
        # Вычисляем очки
        duration = int(time.time() - game.start_time)
        base_score = 100 if won else 10
        time_bonus = max(0, 60 - duration)  # Бонус за скорость
        accuracy_bonus = max(0, 50 - game.wrong_guesses * 10)  # Бонус за точность
        
        total_score = base_score + time_bonus + accuracy_bonus
        
        if won:
            result = f"🎉 Поздравляем! Слово угадано: {game.word}\n\n"
            result += f"📊 Результаты:\n"
            result += f"💰 Очки: {total_score}\n"
            result += f"⏱️ Время: {duration} сек\n"
            result += f"🎯 Ошибок: {game.wrong_guesses}\n"
            result += f"⚡ Бонус за скорость: +{time_bonus}\n"
            result += f"🎯 Бонус за точность: +{accuracy_bonus}"
        else:
            result = f"💀 Игра окончена! Слово было: {game.word}\n\n"
            result += f"📊 Результаты:\n"
            result += f"💰 Очки: {total_score}\n"
            result += f"⏱️ Время: {duration} сек\n"
            result += f"🎯 Ошибок: {game.wrong_guesses}"
        
        # Интеграция с экономикой
        try:
            from economy_social import economy_manager
            economy_manager.add_money(game.peer_id, total_score // 20)  # 5% от очков в монеты
            result += f"\n🪙 Получено монет: {total_score // 20}"
        except Exception:
            pass
        
        # Очищаем игру
        del self.games[game.peer_id]
        
        return result


# Глобальные экземпляры игр
conductor_game = ConductorGame()
poker_manager = PokerGameManager()
hangman_manager = HangmanManager()
chess_manager = ChessManager()
crossword_manager = CrosswordManager()