import os
import sys
import json
import logging
from typing import Optional

from dotenv import load_dotenv
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


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


def build_main_keyboard() -> str:
	keyboard = VkKeyboard(one_time=False, inline=False)
	keyboard.add_button(
		"Начать игру",
		color=VkKeyboardColor.PRIMARY,
		payload={"action": "start_game"},
	)
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


def handle_start(vk, peer_id: int) -> None:
	# First, remove any old keyboard; then show our main keyboard
	send_message(vk, peer_id, "Старые кнопки убраны.", keyboard=build_empty_keyboard())
	send_message(
		vk,
		peer_id,
		"Привет! Я бот мафии. Нажми «Начать игру», чтобы запустить лобби.",
		keyboard=build_main_keyboard(),
	)


def handle_start_game(vk, peer_id: int) -> None:
	send_message(
		vk,
		peer_id,
		"Игра будет запущена здесь. Пока это заглушка — функционал добавим позже.",
	)


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
			handle_start_game(vk, peer_id)
			continue

		# Optional: brief help on unknown input
		send_message(
			vk,
			peer_id,
			"Команда не распознана. Напиши /start, чтобы увидеть кнопку.",
		)


if __name__ == "__main__":
	main()