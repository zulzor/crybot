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
        self._init_shop()
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