import os
import sys
import json
import logging
import random
import ctypes
import atexit
import requests
import difflib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, List, Tuple
from enum import Enum
from datetime import datetime

from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


# ---------- Система ролей и привилегий ----------
class UserRole(Enum):
	USER = "user"
	EDITOR = "editor"      # Может редактировать контент
	MODERATOR = "moderator" # Может модерировать чат
	ADMIN = "admin"        # Полный доступ
	SUPER_ADMIN = "super_admin" # Создатель бота

# Привилегии для каждой роли
ROLE_PRIVILEGES = {
	UserRole.USER: set(),
	UserRole.EDITOR: {"edit_content", "view_stats"},
	UserRole.MODERATOR: {"edit_content", "view_stats", "warn_users", "delete_messages", "kick_users"},
	UserRole.ADMIN: {"edit_content", "view_stats", "warn_users", "delete_messages", "kick_users", "ban_users", "manage_roles", "ai_control"},
	UserRole.SUPER_ADMIN: {"*"}  # Все привилегии
}

# Роли пользователей (user_id -> role)
USER_ROLES: Dict[int, UserRole] = {}

# 2FA коды для админов (user_id -> {"code": "123456", "expires": timestamp})
ADMIN_2FA_CODES: Dict[int, Dict] = {}

# Ранний загрузчик .env до чтения переменных окружения в константах ниже
load_dotenv()