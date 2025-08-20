"""
Экономика и социальные функции для CryBot
"""
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


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
    
    def get_wallet(self, user_id: int) -> UserWallet:
        if user_id not in self.wallets:
            self.wallets[user_id] = UserWallet(user_id=user_id)
        return self.wallets[user_id]
    
    def get_inventory(self, user_id: int) -> UserInventory:
        if user_id not in self.inventories:
            self.inventories[user_id] = UserInventory(user_id=user_id)
        return self.inventories[user_id]
    
    def add_money(self, user_id: int, amount: int, currency: Currency = Currency.CRYCOIN) -> str:
        wallet = self.get_wallet(user_id)
        if currency not in wallet.balance:
            wallet.balance[currency] = 0
        
        wallet.balance[currency] += amount
        wallet.total_earned += amount
        
        return f"💰 +{amount} {currency.value}\nБаланс: {wallet.balance[currency]} {currency.value}"
    
    def spend_money(self, user_id: int, amount: int, currency: Currency = Currency.CRYCOIN) -> bool:
        wallet = self.get_wallet(user_id)
        if currency not in wallet.balance or wallet.balance[currency] < amount:
            return False
        
        wallet.balance[currency] -= amount
        wallet.total_spent += amount
        return True
    
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
            result += (
                f"🎁 {item.name}\n"
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
    
    def get_profile(self, user_id: int) -> UserProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id, name=f"Игрок {user_id}")
        return self.profiles[user_id]
    
    def update_profile(self, user_id: int, **kwargs) -> str:
        profile = self.get_profile(user_id)
        
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.last_online = time.time()
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
        
        return f"✅ {friend_profile.name} добавлен в друзья"
    
    def remove_friend(self, user_id: int, friend_id: int) -> str:
        profile = self.get_profile(user_id)
        friend_profile = self.get_profile(friend_id)
        
        if friend_id not in profile.friends:
            return "❌ Не в друзьях"
        
        profile.friends.discard(friend_id)
        friend_profile.followers.discard(user_id)
        
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
        
        return "💔 Развод оформлен"


# Глобальные экземпляры
economy_manager = EconomyManager()
social_manager = SocialManager()