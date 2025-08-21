"""
Экономика и социальные функции для CryBot
"""
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from storage import get_storage_from_env


# -------- Экономика --------
class Currency(Enum):
    RUB = "₽"
    USD = "$"
    EUR = "€"
    CRYCOIN = "🪙"


@dataclass
class UserWallet:
    user_id: int
    balance: Dict[Currency, int] = field(default_factory=lambda: {Currency.CRYCOIN: 1000})
    last_daily: float = 0
    daily_streak: int = 0
    total_earned: int = 0
    total_spent: int = 0


@dataclass
class ShopItem:
    id: str
    name: str
    description: str
    price: int
    currency: Currency
    category: str
    rarity: str  # common, rare, epic, legendary
    effects: Dict[str, float] = field(default_factory=dict)
    is_consumable: bool = False
    stack_size: int = 1


@dataclass
class UserInventory:
    user_id: int
    items: Dict[str, int] = field(default_factory=dict)  # item_id -> quantity
    equipped: Dict[str, str] = field(default_factory=dict)  # slot -> item_id


class EconomyManager:
    def __init__(self):
        self.wallets: Dict[int, UserWallet] = {}
        self.inventories: Dict[int, UserInventory] = {}
        self.shop_items: Dict[str, ShopItem] = {}
        self.tournaments: Dict[str, Tournament] = {}
        self.leaderboards: Dict[str, Dict[int, Leaderboard]] = {}  # game_type -> user_id -> Leaderboard
        self.achievements: Dict[str, Achievement] = {}
        self.user_achievements: Dict[int, Dict[str, UserAchievement]] = {}  # user_id -> achievement_id -> UserAchievement
        self._init_shop()
        self._init_achievements()
        self._storage = get_storage_from_env()
    
    def _init_shop(self):
        """Инициализация магазина"""
        # Бустеры для игр
        self.shop_items["game_boost"] = ShopItem(
            id="game_boost",
            name="🎮 Игровой бустер",
            description="+50% очков в играх на 1 час",
            price=100,
            currency=Currency.CRYCOIN,
            category="boosters",
            rarity="common",
            effects={"game_score_multiplier": 1.5},
            is_consumable=True
        )
        
        # Косметика
        self.shop_items["vip_badge"] = ShopItem(
            id="vip_badge",
            name="👑 VIP значок",
            description="Эксклюзивный значок для профиля",
            price=500,
            currency=Currency.CRYCOIN,
            category="cosmetics",
            rarity="rare",
            effects={"profile_badge": "vip"}
        )
        
        # Функциональные предметы
        self.shop_items["extra_life"] = ShopItem(
            id="extra_life",
            name="💖 Дополнительная жизнь",
            description="+1 жизнь в играх",
            price=200,
            currency=Currency.CRYCOIN,
            category="functional",
            rarity="common",
            effects={"extra_lives": 1},
            is_consumable=True
        )
        
        # Материалы для крафтинга
        self.shop_items["wood"] = ShopItem(
            id="wood",
            name="🪵 Дерево",
            description="Базовый материал для крафтинга",
            price=10,
            currency=Currency.CRYCOIN,
            category="materials",
            rarity="common",
            effects={},
            is_consumable=True
        )
        
        self.shop_items["iron"] = ShopItem(
            id="iron",
            name="⛏️ Железо",
            description="Прочный материал для крафтинга",
            price=25,
            currency=Currency.CRYCOIN,
            category="materials",
            rarity="common",
            effects={},
            is_consumable=True
        )
        
        self.shop_items["gem"] = ShopItem(
            id="gem",
            name="💎 Драгоценный камень",
            description="Редкий материал для элитных предметов",
            price=100,
            currency=Currency.CRYCOIN,
            category="materials",
            rarity="rare",
            effects={},
            is_consumable=True
        )
        
        # Готовые крафтовые предметы
        self.shop_items["sword"] = ShopItem(
            id="sword",
            name="⚔️ Меч",
            description="Оружие, созданное из железа",
            price=150,
            currency=Currency.CRYCOIN,
            category="crafted",
            rarity="rare",
            effects={"attack": 10},
            is_consumable=False
        )
        
        self.shop_items["shield"] = ShopItem(
            id="shield",
            name="🛡️ Щит",
            description="Защита, созданная из дерева и железа",
            price=120,
            currency=Currency.CRYCOIN,
            category="crafted",
            rarity="rare",
            effects={"defense": 8},
            is_consumable=False
        )
    
    def _init_achievements(self):
        """Инициализация достижений"""
        # Достижения за игры
        self.achievements["first_win"] = Achievement(
            id="first_win",
            name="🎯 Первая победа",
            description="Выиграйте свою первую игру",
            icon="🎯",
            condition="games_won_1",
            reward=50
        )
        
        self.achievements["game_master"] = Achievement(
            id="game_master",
            name="🏆 Мастер игр",
            description="Выиграйте 10 игр",
            icon="🏆",
            condition="games_won_10",
            reward=200
        )
        
        self.achievements["high_scorer"] = Achievement(
            id="high_scorer",
            name="⭐ Высокий счёт",
            description="Наберите 1000 очков в играх",
            icon="⭐",
            condition="total_score_1000",
            reward=300
        )
        
        # Достижения за экономику
        self.achievements["rich_player"] = Achievement(
            id="rich_player",
            name="💰 Богач",
            description="Накопите 5000 монет",
            icon="💰",
            condition="total_money_5000",
            reward=500
        )
        
        self.achievements["craftsman"] = Achievement(
            id="craftsman",
            name="🔨 Мастер-крафтер",
            description="Создайте 5 предметов",
            icon="🔨",
            condition="items_crafted_5",
            reward=150
        )
        
        # Достижения за социальное
        self.achievements["social_butterfly"] = Achievement(
            id="social_butterfly",
            name="🦋 Общительный",
            description="Добавьте 5 друзей",
            icon="🦋",
            condition="friends_5",
            reward=100
        )
        
        self.achievements["married"] = Achievement(
            id="married",
            name="💍 Женат",
            description="Вступите в брак",
            icon="💍",
            condition="married_1",
            reward=250
        )
    
    def check_achievements(self, user_id: int, action: str, value: int = 1) -> List[str]:
        """Проверка и выдача достижений"""
        unlocked = []
        
        # Получаем статистику пользователя
        stats = self._get_user_stats(user_id)
        
        for achievement in self.achievements.values():
            if achievement.id in self.user_achievements.get(user_id, {}):
                continue  # Уже получено
            
            if self._check_achievement_condition(achievement, stats, action, value):
                # Выдаем достижение
                if user_id not in self.user_achievements:
                    self.user_achievements[user_id] = {}
                
                self.user_achievements[user_id][achievement.id] = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id
                )
                
                # Выдаем награду
                self.add_money(user_id, achievement.reward)
                unlocked.append(f"{achievement.icon} {achievement.name} (+{achievement.reward} 🪙)")
        
        return unlocked
    
    def _get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Получение статистики пользователя"""
        stats = {
            "games_won": 0,
            "total_score": 0,
            "total_money": 0,
            "items_crafted": 0,
            "friends": 0,
            "married": 0
        }
        
        # Подсчитываем статистику из разных источников
        for game_type in self.leaderboards:
            if user_id in self.leaderboards[game_type]:
                lb = self.leaderboards[game_type][user_id]
                stats["games_won"] += lb.wins
                stats["total_score"] += lb.score
        
        wallet = self.get_wallet(user_id)
        stats["total_money"] = wallet.total_earned
        
        return stats
    
    def _check_achievement_condition(self, achievement: Achievement, stats: Dict[str, int], action: str, value: int) -> bool:
        """Проверка условия достижения"""
        condition = achievement.condition
        
        if condition == "games_won_1" and stats["games_won"] >= 1:
            return True
        elif condition == "games_won_10" and stats["games_won"] >= 10:
            return True
        elif condition == "total_score_1000" and stats["total_score"] >= 1000:
            return True
        elif condition == "total_money_5000" and stats["total_money"] >= 5000:
            return True
        elif condition == "items_crafted_5" and stats["items_crafted"] >= 5:
            return True
        elif condition == "friends_5" and stats["friends"] >= 5:
            return True
        elif condition == "married_1" and stats["married"] >= 1:
            return True
        
        return False
    
    def get_user_achievements(self, user_id: int) -> str:
        """Получение достижений пользователя"""
        if user_id not in self.user_achievements:
            return "🏆 У вас пока нет достижений"
        
        user_achs = self.user_achievements[user_id]
        result = "🏆 Ваши достижения:\n\n"
        
        for ach_id, user_ach in user_achs.items():
            achievement = self.achievements.get(ach_id)
            if achievement:
                result += f"{achievement.icon} {achievement.name}\n"
                result += f"   {achievement.description}\n"
                result += f"   Получено: {time.strftime('%d.%m.%Y', time.localtime(user_ach.unlocked_at))}\n\n"
        
        return result
    
    def get_wallet(self, user_id: int) -> UserWallet:
        if user_id in self.wallets:
            return self.wallets[user_id]
        # попробовать из хранилища
        data = self._storage.get("wallets", str(user_id))
        if data:
            w = UserWallet(user_id=int(data.get("user_id", user_id)))
            w.balance = {Currency[k]: v for k, v in data.get("balance", {}).items()} if data.get("balance") else w.balance
            w.last_daily = float(data.get("last_daily", 0))
            w.daily_streak = int(data.get("daily_streak", 0))
            w.total_earned = int(data.get("total_earned", 0))
            w.total_spent = int(data.get("total_spent", 0))
            self.wallets[user_id] = w
            return w
        w = UserWallet(user_id=user_id)
        self.wallets[user_id] = w
        return w
    
    def get_inventory(self, user_id: int) -> UserInventory:
        if user_id in self.inventories:
            return self.inventories[user_id]
        data = self._storage.get("inventories", str(user_id))
        if data:
            inv = UserInventory(user_id=int(data.get("user_id", user_id)))
            inv.items = {str(k): int(v) for k, v in data.get("items", {}).items()}
            inv.equipped = {str(k): str(v) for k, v in data.get("equipped", {}).items()}
            self.inventories[user_id] = inv
            return inv
        inv = UserInventory(user_id=user_id)
        self.inventories[user_id] = inv
        return inv
    
    def add_money(self, user_id: int, amount: int, currency: Currency = Currency.CRYCOIN) -> str:
        wallet = self.get_wallet(user_id)
        if currency not in wallet.balance:
            wallet.balance[currency] = 0
        
        wallet.balance[currency] += amount
        wallet.total_earned += amount
        # persist
        self._storage.set("wallets", str(user_id), {
            "user_id": user_id,
            "balance": {k.name: v for k, v in wallet.balance.items()},
            "last_daily": wallet.last_daily,
            "daily_streak": wallet.daily_streak,
            "total_earned": wallet.total_earned,
            "total_spent": wallet.total_spent,
        })
        
        return f"💰 +{amount} {currency.value}\nБаланс: {wallet.balance[currency]} {currency.value}"
    
    def spend_money(self, user_id: int, amount: int, currency: Currency = Currency.CRYCOIN) -> bool:
        wallet = self.get_wallet(user_id)
        if currency not in wallet.balance or wallet.balance[currency] < amount:
            return False
        
        wallet.balance[currency] -= amount
        wallet.total_spent += amount
        self._storage.set("wallets", str(user_id), {
            "user_id": user_id,
            "balance": {k.name: v for k, v in wallet.balance.items()},
            "last_daily": wallet.last_daily,
            "daily_streak": wallet.daily_streak,
            "total_earned": wallet.total_earned,
            "total_spent": wallet.total_spent,
        })
        return True
    
    def craft_item(self, user_id: int, recipe_name: str) -> str:
        """Крафтинг предметов"""
        recipes = {
            "sword": {
                "materials": {"iron": 3, "wood": 1},
                "result": "sword",
                "name": "⚔️ Меч"
            },
            "shield": {
                "materials": {"iron": 2, "wood": 2},
                "result": "shield", 
                "name": "🛡️ Щит"
            },
            "magic_staff": {
                "materials": {"wood": 2, "gem": 1},
                "result": "magic_staff",
                "name": "🔮 Магический посох"
            }
        }
        
        if recipe_name not in recipes:
            return "❌ Рецепт не найден"
        
        recipe = recipes[recipe_name]
        inventory = self.get_inventory(user_id)
        
        # Проверяем материалы
        for material, amount in recipe["materials"].items():
            if inventory.items.get(material, 0) < amount:
                return f"❌ Недостаточно материала: {material} (нужно {amount})"
        
        # Тратим материалы
        for material, amount in recipe["materials"].items():
            inventory.items[material] -= amount
            if inventory.items[material] <= 0:
                del inventory.items[material]
        
        # Добавляем результат
        result_item = recipe["result"]
        inventory.items[result_item] = inventory.items.get(result_item, 0) + 1
        
        # Сохраняем инвентарь
        self._storage.set("inventories", str(user_id), {
            "user_id": user_id,
            "items": inventory.items,
            "equipped": inventory.equipped
        })
        
        return f"✅ {recipe['name']} создан!"
    
    def create_auction(self, user_id: int, item_id: str, quantity: int, starting_price: int) -> str:
        """Создание аукциона"""
        inventory = self.get_inventory(user_id)
        
        if item_id not in inventory.items or inventory.items[item_id] < quantity:
            return "❌ Недостаточно предметов для аукциона"
        
        # Создаем аукцион
        auction_id = f"auction_{user_id}_{int(time.time())}"
        auction = {
            "id": auction_id,
            "seller_id": user_id,
            "item_id": item_id,
            "quantity": quantity,
            "starting_price": starting_price,
            "current_price": starting_price,
            "highest_bidder": None,
            "created_at": time.time(),
            "ends_at": time.time() + 3600,  # 1 час
            "is_active": True
        }
        
        # Убираем предметы из инвентаря
        inventory.items[item_id] -= quantity
        if inventory.items[item_id] <= 0:
            del inventory.items[item_id]
        
        # Сохраняем аукцион и инвентарь
        self._storage.set("auctions", auction_id, auction)
        self._storage.set("inventories", str(user_id), {
            "user_id": user_id,
            "items": inventory.items,
            "equipped": inventory.equipped
        })
        
        item = self.shop_items.get(item_id)
        item_name = item.name if item else item_id
        
        return f"🏷️ Аукцион создан!\n\nПредмет: {item_name}\nКоличество: {quantity}\nСтартовая цена: {starting_price} 🪙\n\nID аукциона: {auction_id}"
    
    def bid_on_auction(self, user_id: int, auction_id: str, bid_amount: int) -> str:
        """Ставка на аукцион"""
        auction_data = self._storage.get("auctions", auction_id)
        if not auction_data:
            return "❌ Аукцион не найден"
        
        if not auction_data.get("is_active", False):
            return "❌ Аукцион завершён"
        
        if time.time() > auction_data.get("ends_at", 0):
            return "❌ Время аукциона истекло"
        
        if bid_amount <= auction_data.get("current_price", 0):
            return "❌ Ставка должна быть выше текущей"
        
        wallet = self.get_wallet(user_id)
        if wallet.balance.get(Currency.CRYCOIN, 0) < bid_amount:
            return "❌ Недостаточно средств"
        
        # Обновляем аукцион
        auction_data["current_price"] = bid_amount
        auction_data["highest_bidder"] = user_id
        
        self._storage.set("auctions", auction_id, auction_data)
        
        return f"✅ Ставка {bid_amount} 🪙 принята!"
    
    def get_active_auctions(self) -> str:
        """Получение списка активных аукционов"""
        all_auctions = self._storage.get_all("auctions")
        active_auctions = []
        
        for auction_id, auction_data in all_auctions.items():
            if auction_data.get("is_active", False) and time.time() <= auction_data.get("ends_at", 0):
                active_auctions.append((auction_id, auction_data))
        
        if not active_auctions:
            return "🏷️ Активных аукционов нет"
        
        result = "🏷️ Активные аукционы:\n\n"
        for auction_id, auction_data in active_auctions[:5]:  # Показываем первые 5
            item = self.shop_items.get(auction_data["item_id"])
            item_name = item.name if item else auction_data["item_id"]
            
            time_left = int(auction_data["ends_at"] - time.time())
            minutes = time_left // 60
            
            result += f"📦 {item_name} x{auction_data['quantity']}\n"
            result += f"💰 Текущая цена: {auction_data['current_price']} 🪙\n"
            result += f"⏰ Осталось: {minutes} мин\n"
            result += f"🏷️ ID: {auction_id}\n\n"
        
        return result
    
    def create_tournament(self, name: str, game_type: str, entry_fee: int, max_participants: int = 16) -> str:
        """Создание турнира"""
        tournament_id = f"tournament_{int(time.time())}"
        
        tournament = Tournament(
            id=tournament_id,
            name=name,
            game_type=game_type,
            entry_fee=entry_fee,
            prize_pool=entry_fee * max_participants,
            max_participants=max_participants
        )
        
        self.tournaments[tournament_id] = tournament
        
        return f"🏆 Турнир создан!\n\nНазвание: {name}\nИгра: {game_type}\nВзнос: {entry_fee} 🪙\nПризовой фонд: {tournament.prize_pool} 🪙\nУчастников: 0/{max_participants}\n\nID турнира: {tournament_id}"
    
    def join_tournament(self, user_id: int, tournament_id: str) -> str:
        """Присоединение к турниру"""
        if tournament_id not in self.tournaments:
            return "❌ Турнир не найден"
        
        tournament = self.tournaments[tournament_id]
        if not tournament.is_active:
            return "❌ Турнир завершён"
        
        if user_id in tournament.participants:
            return "❌ Вы уже участвуете в турнире"
        
        if len(tournament.participants) >= tournament.max_participants:
            return "❌ Турнир заполнен"
        
        # Проверяем взнос
        wallet = self.get_wallet(user_id)
        if wallet.balance.get(Currency.CRYCOIN, 0) < tournament.entry_fee:
            return f"❌ Недостаточно средств. Нужно {tournament.entry_fee} 🪙"
        
        # Списываем взнос
        self.spend_money(user_id, tournament.entry_fee)
        tournament.participants.append(user_id)
        
        return f"✅ Вы присоединились к турниру '{tournament.name}'!\nУчастников: {len(tournament.participants)}/{tournament.max_participants}"
    
    def get_tournaments(self) -> str:
        """Список активных турниров"""
        active_tournaments = [t for t in self.tournaments.values() if t.is_active]
        
        if not active_tournaments:
            return "🏆 Активных турниров нет"
        
        result = "🏆 Активные турниры:\n\n"
        for tournament in active_tournaments[:5]:  # Показываем первые 5
            result += f"📋 {tournament.name}\n"
            result += f"🎮 Игра: {tournament.game_type}\n"
            result += f"💰 Взнос: {tournament.entry_fee} 🪙\n"
            result += f"🏆 Призовой фонд: {tournament.prize_pool} 🪙\n"
            result += f"👥 Участников: {len(tournament.participants)}/{tournament.max_participants}\n"
            result += f"🏷️ ID: {tournament.id}\n\n"
        
        return result
    
    def update_leaderboard(self, user_id: int, game_type: str, won: bool, score: int = 0) -> None:
        """Обновление рейтинга игрока"""
        if game_type not in self.leaderboards:
            self.leaderboards[game_type] = {}
        
        if user_id not in self.leaderboards[game_type]:
            self.leaderboards[game_type][user_id] = Leaderboard(
                user_id=user_id,
                game_type=game_type,
                score=0,
                wins=0,
                losses=0,
                total_games=0
            )
        
        leaderboard = self.leaderboards[game_type][user_id]
        leaderboard.total_games += 1
        leaderboard.score += score
        
        if won:
            leaderboard.wins += 1
        else:
            leaderboard.losses += 1
        
        leaderboard.last_updated = time.time()
    
    def get_leaderboard(self, game_type: str, limit: int = 10) -> str:
        """Получение рейтинга по игре"""
        if game_type not in self.leaderboards:
            return f"📊 Рейтинг по {game_type} пуст"
        
        players = list(self.leaderboards[game_type].values())
        players.sort(key=lambda x: x.score, reverse=True)
        
        result = f"📊 Рейтинг по {game_type}:\n\n"
        for i, player in enumerate(players[:limit], 1):
            win_rate = (player.wins / player.total_games * 100) if player.total_games > 0 else 0
            result += f"{i}. Игрок {player.user_id}\n"
            result += f"   Очки: {player.score} | Победы: {player.wins}/{player.total_games} ({win_rate:.1f}%)\n\n"
        
        return result
    
    def daily_bonus(self, user_id: int) -> str:
        wallet = self.get_wallet(user_id)
        now = time.time()
        
        # Проверяем, прошло ли 24 часа
        if now - wallet.last_daily < 86400:  # 24 часа в секундах
            remaining = int(86400 - (now - wallet.last_daily))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return f"⏰ Следующий бонус через {hours}ч {minutes}м"
        
        # Увеличиваем стрик
        wallet.daily_streak += 1
        wallet.last_daily = now
        
        # Бонус зависит от стрика
        base_bonus = 100
        streak_bonus = min(wallet.daily_streak * 10, 200)  # Максимум +200 за стрик
        total_bonus = base_bonus + streak_bonus
        
        wallet.balance[Currency.CRYCOIN] += total_bonus
        wallet.total_earned += total_bonus
        self._storage.set("wallets", str(user_id), {
            "user_id": user_id,
            "balance": {k.name: v for k, v in wallet.balance.items()},
            "last_daily": wallet.last_daily,
            "daily_streak": wallet.daily_streak,
            "total_earned": wallet.total_earned,
            "total_spent": wallet.total_spent,
        })
        
        return (
            f"🎁 Ежедневный бонус!\n"
            f"💰 +{total_bonus} 🪙\n"
            f"🔥 Стрик: {wallet.daily_streak} дней\n"
            f"Баланс: {wallet.balance[Currency.CRYCOIN]} 🪙"
        )
    
    def buy_item(self, user_id: int, item_id: str) -> str:
        if item_id not in self.shop_items:
            return "❌ Товар не найден"
        
        item = self.shop_items[item_id]
        wallet = self.get_wallet(user_id)
        inventory = self.get_inventory(user_id)
        
        if not self.spend_money(user_id, item.price, item.currency):
            return f"❌ Недостаточно средств. Нужно: {item.price} {item.currency.value}"
        
        # Добавляем в инвентарь
        if item_id in inventory.items:
            inventory.items[item_id] += item.stack_size
        else:
            inventory.items[item_id] = item.stack_size
        self._storage.set("inventories", str(user_id), {
            "user_id": user_id,
            "items": inventory.items,
            "equipped": inventory.equipped,
        })
        
        return (
            f"✅ Покупка совершена!\n"
            f"🎁 {item.name}\n"
            f"💰 Потрачено: {item.price} {item.currency.value}\n"
            f"📦 В инвентаре: {inventory.items[item_id]}"
        )
    
    def get_shop(self, category: Optional[str] = None) -> str:
        items = self.shop_items.values()
        if category:
            items = [item for item in items if item.category == category]
        
        if not items:
            return "❌ Товары не найдены"
        
        result = "🛒 Магазин:\n\n"
        for item in items:
            rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🟡"}.get(item.rarity, "⚪")
            result += (
                f"{rarity_emoji} {item.name}\n"
                f"📝 {item.description}\n"
                f"💰 {item.price} {item.currency.value}\n"
                f"⭐ {item.rarity.upper()}\n"
                f"📂 {item.category}\n\n"
            )
        
        return result


# -------- Социальное --------
class RelationshipStatus(Enum):
    SINGLE = "холост"
    DATING = "в отношениях"
    MARRIED = "женат/замужем"
    DIVORCED = "в разводе"


@dataclass
class UserProfile:
    user_id: int
    name: str
    bio: str = ""
    avatar: str = "👤"
    level: int = 1
    experience: int = 0
    relationship_status: RelationshipStatus = RelationshipStatus.SINGLE
    partner_id: Optional[int] = None
    clan_id: Optional[int] = None
    friends: Set[int] = field(default_factory=set)
    followers: Set[int] = field(default_factory=set)
    following: Set[int] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_online: float = field(default_factory=time.time)
    preferred_language: str = "ru"


@dataclass
class Clan:
    id: int
    name: str
    description: str
    leader_id: int
    members: Set[int] = field(default_factory=set)
    level: int = 1
    experience: int = 0
    treasury: int = 0
    created_at: float = field(default_factory=time.time)
    is_public: bool = True


@dataclass
class Marriage:
    id: int
    partner1_id: int
    partner2_id: int
    married_at: float
    is_active: bool = True
    divorce_requested_by: Optional[int] = None

@dataclass
class Tournament:
    id: str
    name: str
    game_type: str  # "chess", "poker", "hangman", "crossword"
    entry_fee: int
    prize_pool: int
    max_participants: int
    participants: List[int] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    is_active: bool = True
    winner_id: Optional[int] = None

@dataclass
class Leaderboard:
    user_id: int
    game_type: str
    score: int
    wins: int
    losses: int
    total_games: int
    last_updated: float = field(default_factory=time.time)

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str
    condition: str  # "games_won_10", "total_score_1000", etc.
    reward: int  # монеты за получение
    is_hidden: bool = False

@dataclass
class UserAchievement:
    user_id: int
    achievement_id: str
    unlocked_at: float = field(default_factory=time.time)
    progress: int = 0  # для прогрессивных достижений


class SocialManager:
    def __init__(self):
        self.profiles: Dict[int, UserProfile] = {}
        self.clans: Dict[int, Clan] = {}
        self.marriages: Dict[int, Marriage] = {}
        self.clan_counter = 1
        self._storage = get_storage_from_env()
        # попытка восстановить счетчик кланов из meta
        meta = self._storage.get("meta", "clan_counter")
        if meta and isinstance(meta.get("value"), int):
            self.clan_counter = int(meta["value"])
    
    def get_profile(self, user_id: int) -> UserProfile:
        if user_id in self.profiles:
            return self.profiles[user_id]
        # пробуем из хранилища
        data = self._storage.get("profiles", str(user_id))
        if data:
            p = UserProfile(
                user_id=int(data.get("user_id", user_id)),
                name=str(data.get("name", f"Игрок {user_id}")),
                bio=str(data.get("bio", "")),
                avatar=str(data.get("avatar", "👤")),
                level=int(data.get("level", 1)),
                experience=int(data.get("experience", 0)),
                relationship_status=RelationshipStatus[data.get("relationship_status", "SINGLE")],
                partner_id=(int(data["partner_id"]) if data.get("partner_id") is not None else None),
                clan_id=(int(data["clan_id"]) if data.get("clan_id") is not None else None),
                friends=set(int(x) for x in data.get("friends", [])),
                followers=set(int(x) for x in data.get("followers", [])),
                following=set(int(x) for x in data.get("following", [])),
                created_at=float(data.get("created_at", time.time())),
                last_online=float(data.get("last_online", time.time())),
            )
            self.profiles[user_id] = p
            return p
        p = UserProfile(user_id=user_id, name=f"Игрок {user_id}")
        self.profiles[user_id] = p
        # первичное сохранение
        self._save_profile(p)
        return p

    def _save_profile(self, profile: UserProfile) -> None:
        self._storage.set("profiles", str(profile.user_id), {
            "user_id": profile.user_id,
            "name": profile.name,
            "bio": profile.bio,
            "avatar": profile.avatar,
            "level": profile.level,
            "experience": profile.experience,
            "relationship_status": profile.relationship_status.name,
            "partner_id": profile.partner_id,
            "clan_id": profile.clan_id,
            "friends": list(profile.friends),
            "followers": list(profile.followers),
            "following": list(profile.following),
            "created_at": profile.created_at,
            "last_online": profile.last_online,
        })
    
    def update_profile(self, user_id: int, **kwargs) -> str:
        profile = self.get_profile(user_id)
        
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.last_online = time.time()
        self._save_profile(profile)
        return "✅ Профиль обновлён"
    
    def add_friend(self, user_id: int, friend_id: int) -> str:
        if user_id == friend_id:
            return "❌ Нельзя добавить себя в друзья"
        
        profile = self.get_profile(user_id)
        friend_profile = self.get_profile(friend_id)
        
        if friend_id in profile.friends:
            return "❌ Уже в друзьях"
        
        profile.friends.add(friend_id)
        friend_profile.followers.add(user_id)
        self._save_profile(profile)
        self._save_profile(friend_profile)
        return f"✅ {friend_profile.name} добавлен в друзья"
    
    def remove_friend(self, user_id: int, friend_id: int) -> str:
        profile = self.get_profile(user_id)
        friend_profile = self.get_profile(friend_id)
        
        if friend_id not in profile.friends:
            return "❌ Не в друзьях"
        
        profile.friends.discard(friend_id)
        friend_profile.followers.discard(user_id)
        self._save_profile(profile)
        self._save_profile(friend_profile)
        return f"❌ {friend_profile.name} удалён из друзей"
    
    def create_clan(self, user_id: int, name: str, description: str) -> str:
        profile = self.get_profile(user_id)
        
        if profile.clan_id:
            return "❌ Вы уже в клане"
        
        # Проверяем уникальность имени
        for clan in self.clans.values():
            if clan.name.lower() == name.lower():
                return "❌ Клан с таким именем уже существует"
        
        clan_id = self.clan_counter
        self.clan_counter += 1
        
        clan = Clan(
            id=clan_id,
            name=name,
            description=description,
            leader_id=user_id
        )
        clan.members.add(user_id)
        
        self.clans[clan_id] = clan
        profile.clan_id = clan_id
        # сохраняем
        self._save_profile(profile)
        self._storage.set("clans", str(clan_id), {
            "id": clan_id,
            "name": clan.name,
            "description": clan.description,
            "leader_id": clan.leader_id,
            "members": list(clan.members),
            "level": clan.level,
            "experience": clan.experience,
            "treasury": clan.treasury,
            "created_at": clan.created_at,
            "is_public": clan.is_public,
        })
        self.clan_counter += 1
        self._storage.set("meta", "clan_counter", {"value": self.clan_counter})
        
        return (
            f"🏰 Клан '{name}' создан!\n"
            f"👑 Лидер: {profile.name}\n"
            f"📝 Описание: {description}"
        )
    
    def join_clan(self, user_id: int, clan_id: int) -> str:
        if clan_id not in self.clans:
            return "❌ Клан не найден"
        
        profile = self.get_profile(user_id)
        clan = self.clans[clan_id]
        
        if profile.clan_id:
            return "❌ Вы уже в клане"
        
        if not clan.is_public:
            return "❌ Клан закрыт для вступления"
        
        clan.members.add(user_id)
        profile.clan_id = clan_id
        self._save_profile(profile)
        self._storage.set("clans", str(clan_id), {
            "id": clan.id,
            "name": clan.name,
            "description": clan.description,
            "leader_id": clan.leader_id,
            "members": list(clan.members),
            "level": clan.level,
            "experience": clan.experience,
            "treasury": clan.treasury,
            "created_at": clan.created_at,
            "is_public": clan.is_public,
        })
        return f"✅ Вы вступили в клан '{clan.name}'"
    
    def leave_clan(self, user_id: int) -> str:
        profile = self.get_profile(user_id)
        
        if not profile.clan_id:
            return "❌ Вы не в клане"
        
        clan = self.clans[profile.clan_id]
        
        if clan.leader_id == user_id:
            return "❌ Лидер не может покинуть клан. Передайте лидерство или распустите клан"
        
        clan.members.discard(user_id)
        profile.clan_id = None
        self._save_profile(profile)
        self._storage.set("clans", str(clan.id), {
            "id": clan.id,
            "name": clan.name,
            "description": clan.description,
            "leader_id": clan.leader_id,
            "members": list(clan.members),
            "level": clan.level,
            "experience": clan.experience,
            "treasury": clan.treasury,
            "created_at": clan.created_at,
            "is_public": clan.is_public,
        })
        return f"✅ Вы покинули клан '{clan.name}'"
    
    def propose_marriage(self, user_id: int, partner_id: int) -> str:
        if user_id == partner_id:
            return "❌ Нельзя жениться на себе"
        
        profile = self.get_profile(user_id)
        partner_profile = self.get_profile(partner_id)
        
        if profile.relationship_status != RelationshipStatus.SINGLE:
            return "❌ Вы уже в отношениях"
        
        if partner_profile.relationship_status != RelationshipStatus.SINGLE:
            return f"❌ {partner_profile.name} уже в отношениях"
        
        # Создаём предложение
        marriage_id = len(self.marriages) + 1
        marriage = Marriage(
            id=marriage_id,
            partner1_id=user_id,
            partner2_id=partner_id,
            married_at=time.time()
        )
        
        self.marriages[marriage_id] = marriage
        
        # Обновляем статусы
        profile.relationship_status = RelationshipStatus.MARRIED
        profile.partner_id = partner_id
        partner_profile.relationship_status = RelationshipStatus.MARRIED
        partner_profile.partner_id = user_id
        self._save_profile(profile)
        self._save_profile(partner_profile)
        self._storage.set("marriages", str(marriage_id), {
            "id": marriage.id,
            "partner1_id": marriage.partner1_id,
            "partner2_id": marriage.partner2_id,
            "married_at": marriage.married_at,
            "is_active": marriage.is_active,
            "divorce_requested_by": marriage.divorce_requested_by,
        })
        
        return (
            f"💍 Поздравляем с браком!\n"
            f"👰 {profile.name} и 🤵 {partner_profile.name}\n"
            f"💕 Теперь вы муж и жена!"
        )
    
    def request_divorce(self, user_id: int) -> str:
        profile = self.get_profile(user_id)
        
        if profile.relationship_status != RelationshipStatus.MARRIED:
            return "❌ Вы не женаты"
        
        # Находим брак
        for marriage in self.marriages.values():
            if (marriage.partner1_id == user_id or marriage.partner2_id == user_id) and marriage.is_active:
                if marriage.divorce_requested_by:
                    if marriage.divorce_requested_by == user_id:
                        return "❌ Вы уже подали заявление на развод"
                    else:
                        # Второй партнёр тоже хочет развод
                        return self._process_divorce(marriage)
                else:
                    marriage.divorce_requested_by = user_id
                    return "📝 Заявление на развод подано. Партнёр должен подтвердить"
        
        return "❌ Брак не найден"
    
    def _process_divorce(self, marriage: Marriage) -> str:
        """Обработка развода"""
        marriage.is_active = False
        
        # Обновляем профили
        partner1 = self.get_profile(marriage.partner1_id)
        partner2 = self.get_profile(marriage.partner2_id)
        
        partner1.relationship_status = RelationshipStatus.DIVORCED
        partner1.partner_id = None
        partner2.relationship_status = RelationshipStatus.DIVORCED
        partner2.partner_id = None
        self._save_profile(partner1)
        self._save_profile(partner2)
        self._storage.set("marriages", str(marriage.id), {
            "id": marriage.id,
            "partner1_id": marriage.partner1_id,
            "partner2_id": marriage.partner2_id,
            "married_at": marriage.married_at,
            "is_active": marriage.is_active,
            "divorce_requested_by": marriage.divorce_requested_by,
        })
        
        return "💔 Развод оформлен"


# Глобальные экземпляры
economy_manager = EconomyManager()
social_manager = SocialManager()