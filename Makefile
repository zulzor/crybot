.PHONY: help install run test clean docker-build docker-run docker-stop

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

run: ## Запустить бота
	python bot_vk.py

test: ## Запустить тесты (если есть)
	python -m pytest tests/ -v

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete

docker-build: ## Собрать Docker образ
	docker build -t crycat-bot .

docker-run: ## Запустить в Docker
	docker-compose up -d

docker-stop: ## Остановить Docker контейнеры
	docker-compose down

docker-logs: ## Показать логи Docker
	docker-compose logs -f

docker-shell: ## Войти в Docker контейнер
	docker exec -it crycat-bot /bin/bash

format: ## Форматировать код
	black bot_vk.py
	isort bot_vk.py

lint: ## Проверить код линтером
	flake8 bot_vk.py
	black --check bot_vk.py
	isort --check-only bot_vk.py

setup: install ## Установить и настроить проект
	@echo "Проект настроен! Создайте .env файл и запустите 'make run'"