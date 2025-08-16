import os
import sys
import json
import logging
from typing import Optional

from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dataclasses import dataclass, field
from typing import Dict, Set


def configure_logging() -> None:
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)


def load_config() -> tuple[str, int]:
	load_dotenv()
	token = os.getenv("VK_GROUP_TOKEN", "").strip()
	group_id_str = os.getenv("VK_GROUP_ID", "").strip()
	if not token:
		raise RuntimeError(
			"VK_GROUP_TOKEN is not set. Create a .env file with VK_GROUP_TOKEN and VK_GROUP_ID."
		)
	if not group_id_str.isdigit():
		raise RuntimeError("VK_GROUP_ID must be a number (group ID without the minus sign)")
	return token, int(group_id_str)

@dataclass
class Lobby:
	leader_id: int
	player_ids: Set[int] = field(default_factory=set)

	def add_player(self, user_id: int) -> None:
		self.player_ids.add(user_id)

	def remove_player(self, user_id: int) -> None:
		self.player_ids.discard(user_id)

	def has_player(self, user_id: int) -> bool:
		return user_id in self.player_ids

# peer_id -> Lobby
LOBBIES: Dict[int, Lobby] = {}


def build_main_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button(
		"Начать игру",
		color=VkKeyboardColor.PRIMARY,
		payload={"action": "start_game"},
	)
	return keyboard.get_keyboard()

def build_lobby_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button("Присоединиться", color=VkKeyboardColor.PRIMARY, payload={"action": "join"})
	keyboard.add_button("Выйти", color=VkKeyboardColor.SECONDARY, payload={"action": "leave"})
	keyboard.add_line()
	keyboard.add_button("Старт", color=VkKeyboardColor.POSITIVE, payload={"action": "begin"})
	keyboard.add_button("Отмена", color=VkKeyboardColor.NEGATIVE, payload={"action": "cancel"})
	return keyboard.get_keyboard()


def build_empty_keyboard() -> str:
	# An explicit empty keyboard payload to remove any old persistent buttons
	return json.dumps({"one_time": True, "buttons": []}, ensure_ascii=False)


def send_message(vk, peer_id: int, text: str, keyboard: Optional[str] = None) -> None:
	params: dict[str, object] = {
		"peer_id": peer_id,
		"random_id": 0,
		"message": text,
	}
	if keyboard is not None:
		params["keyboard"] = keyboard
	vk.messages.send(**params)

def mention(user_id: int, name: str = "игрок") -> str:
	return f"[id{user_id}|{name}]"

def format_players(vk, user_ids: Set[int]) -> str:
	if not user_ids:
		return "(никого)"
	try:
		users = vk.users.get(user_ids=",".join(str(u) for u in user_ids), name_case="Nom")
		parts = [mention(u["id"], f"{u['first_name']} {u['last_name']}") for u in users]
	except Exception:
		parts = [mention(u) for u in user_ids]
	return ", ".join(parts)


def handle_start(vk, peer_id: int) -> None:
	# First, remove any old keyboard; then show our main keyboard
	send_message(vk, peer_id, "Старые кнопки убраны.", keyboard=build_empty_keyboard())
	send_message(
		vk,
		peer_id,
		"Привет! Я бот мафии. Нажми «Начать игру», чтобы запустить лобби.",
		keyboard=build_main_keyboard(),
	)

def handle_start_game(vk, peer_id: int, user_id: int) -> None:
	if peer_id in LOBBIES:
		lobby = LOBBIES[peer_id]
		text = (
			"Лобби уже создано. Участники: "
			+ format_players(vk, lobby.player_ids)
			+ "\nНажмите «Присоединиться», чтобы войти."
		)
		send_message(vk, peer_id, text, keyboard=build_lobby_keyboard())
		return
	lobby = Lobby(leader_id=user_id)
	lobby.add_player(user_id)
	LOBBIES[peer_id] = lobby
	text = (
		f"Лобби создано лидером {mention(user_id)}.\n"
		f"Игроки: {format_players(vk, lobby.player_ids)}\n"
		"Нажмите «Присоединиться», чтобы войти. Лидер может нажать «Старт»."
	)
	send_message(vk, peer_id, text, keyboard=build_lobby_keyboard())

def handle_join(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби ещё не создано. Нажмите «Начать игру».", keyboard=build_main_keyboard())
		return
	if user_id in lobby.player_ids:
		send_message(vk, peer_id, f"{mention(user_id)} уже в лобби.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_lobby_keyboard())
		return
	lobby.add_player(user_id)
	send_message(vk, peer_id, f"{mention(user_id)} присоединился.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_lobby_keyboard())

def handle_leave(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби ещё не создано.")
		return
	lobby.remove_player(user_id)
	if not lobby.player_ids:
		LOBBIES.pop(peer_id, None)
		send_message(vk, peer_id, "Лобби закрыто: игроков не осталось.", keyboard=build_main_keyboard())
		return
	send_message(vk, peer_id, f"{mention(user_id)} вышел.\nИгроки: {format_players(vk, lobby.player_ids)}", keyboard=build_lobby_keyboard())

def handle_cancel(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби уже отсутствует.")
		return
	if user_id != lobby.leader_id:
		send_message(vk, peer_id, "Отменить может только лидер лобби.")
		return
	LOBBIES.pop(peer_id, None)
	send_message(vk, peer_id, "Лобби отменено лидером.", keyboard=build_main_keyboard())

def handle_begin(vk, peer_id: int, user_id: int) -> None:
	lobby = LOBBIES.get(peer_id)
	if not lobby:
		send_message(vk, peer_id, "Лобби не найдено.")
		return
	if user_id != lobby.leader_id:
		send_message(vk, peer_id, "Запускать игру может только лидер лобби.")
		return
	min_players = 4
	if len(lobby.player_ids) < min_players:
		send_message(vk, peer_id, f"Недостаточно игроков для старта. Нужно минимум {min_players}. Сейчас: {len(lobby.player_ids)}.")
		return
	send_message(vk, peer_id, "Игра стартует! Пока это демо-режим без ролей. Будет добавлено позже.")
	# Сбросим лобби, чтобы можно было создать новое
	LOBBIES.pop(peer_id, None)


def main() -> None:
	configure_logging()
	logger = logging.getLogger("vk-mafia-bot")
	try:
		token, group_id = load_config()
	except Exception as exc:
		logger.error("Config error: %s", exc)
		sys.exit(1)

	vk_session = vk_api.VkApi(token=token)
	vk = vk_session.get_api()
	longpoll = VkBotLongPoll(vk_session, group_id)

	logger.info("Bot started. Listening for events...")

	for event in longpoll.listen():
		if event.type != VkBotEventType.MESSAGE_NEW:
			continue

		message = event.message
		peer_id = message.peer_id
		text_raw = (message.text or "").strip()
		text = text_raw.lower()
		user_id = message.from_id

		payload = {}
		if message.payload:
			try:
				payload = json.loads(message.payload)
			except Exception:
				payload = {}

		if text == "/start":
			handle_start(vk, peer_id)
			continue

		if payload.get("action") == "start_game" or text == "начать игру":
			handle_start_game(vk, peer_id, user_id)
			continue

		action = payload.get("action") if isinstance(payload, dict) else None
		if action == "join":
			handle_join(vk, peer_id, user_id)
			continue
		if action == "leave":
			handle_leave(vk, peer_id, user_id)
			continue
		if action == "cancel":
			handle_cancel(vk, peer_id, user_id)
			continue
		if action == "begin":
			handle_begin(vk, peer_id, user_id)
			continue

		# Optional: brief help on unknown input
		send_message(
			vk,
			peer_id,
			"Команда не распознана. Напиши /start, чтобы увидеть кнопку.",
		)


if __name__ == "__main__":
	main()