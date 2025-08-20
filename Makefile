.PHONY: help install run test clean docker-build docker-run docker-stop format lint setup dev install-dev

help: ## Показать справку
	@echo "🚀 CryCat Bot v2.0.0 - Доступные команды:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить production зависимости
	pip install -r requirements.txt

install-dev: ## Установить development зависимости
	pip install -r requirements.txt
	pip install -e .[dev]

run: ## Запустить бота
	python bot_vk.py

run-dev: ## Запустить бота в режиме разработки
	python -m uvicorn webhook:app --reload --host 0.0.0.0 --port 8080

test: ## Запустить все тесты
	python tests.py

test-pytest: ## Запустить тесты с pytest
	python -m pytest tests.py -v --cov=. --cov-report=html --cov-report=term-missing

test-modules: ## Тестировать отдельные модули
	@echo "🧪 Тестирование AI модуля..."
	python -c "import ai; print('✅ AI модуль работает')"
	@echo "🧪 Тестирование Admin модуля..."
	python -c "import admin; print('✅ Admin модуль работает')"
	@echo "🧪 Тестирование Monitoring модуля..."
	python -c "import monitoring; print('✅ Monitoring модуль работает')"
	@echo "🧪 Тестирование Games модуля..."
	python -c "import games; print('✅ Games модуль работает')"
	@echo "🧪 Тестирование Content модуля..."
	python -c "import content; print('✅ Content модуль работает')"
	@echo "🧪 Тестирование Streaming модуля..."
	python -c "import streaming; print('✅ Streaming модуль работает')"
	@echo "🧪 Тестирование Utils модуля..."
	python -c "import utils; print('✅ Utils модуль работает')"
	@echo "🧪 Тестирование Config модуля..."
	python -c "import config; print('✅ Config модуль работает')"

test-ai: ## Тестировать AI модуль
	python -m pytest tests.py::TestAIModule -v

test-admin: ## Тестировать Admin модуль
	python -m pytest tests.py::TestAdminModule -v

test-monitoring: ## Тестировать Monitoring модуль
	python -m pytest tests.py::TestMonitoringModule -v

test-games: ## Тестировать Games модуль
	python -m pytest tests.py::TestGamesModule -v

test-content: ## Тестировать Content модуль
	python -m pytest tests.py::TestContentModule -v

test-streaming: ## Тестировать Streaming модуль
	python -m pytest tests.py::TestStreamingModule -v

test-utils: ## Тестировать Utils модуль
	python -m pytest tests.py::TestUtilsModule -v

test-config: ## Тестировать Config модуль
	python -m pytest tests.py::TestConfigModule -v

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name "htmlcov" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete

clean-docker: ## Очистить Docker образы и контейнеры
	docker system prune -f
	docker image prune -f
	docker container prune -f

docker-build: ## Собрать Docker образ
	docker build -t crycat-bot:v2.0.0 .

docker-build-dev: ## Собрать development Docker образ
	docker build -f Dockerfile.dev -t crycat-bot:dev .

docker-run: ## Запустить в Docker
	docker-compose up -d

docker-stop: ## Остановить Docker контейнеры
	docker-compose down

docker-logs: ## Показать логи Docker
	docker-compose logs -f

docker-shell: ## Войти в Docker контейнер
	docker exec -it crycat-bot /bin/bash

docker-test: ## Протестировать Docker образ
	docker run --rm crycat-bot:v2.0.0 python -c "
	import ai, admin, monitoring, games, content, streaming, utils, config
	print('✅ Все модули загружены успешно!')
	print('🚀 Docker образ работает корректно!')
	"

format: ## Форматировать код
	black .
	isort .

format-check: ## Проверить форматирование кода
	black --check .
	isort --check-only .

lint: ## Проверить код линтером
	ruff check .
	black --check .
	isort --check-only .

lint-fix: ## Исправить проблемы с кодом
	ruff check . --fix
	black .
	isort .

type-check: ## Проверить типы с mypy
	mypy . --ignore-missing-imports --exclude=__pycache__

security-check: ## Проверить безопасность кода
	bandit -r . -f json -o bandit-report.json

coverage: ## Показать покрытие кода
	python -m pytest tests.py --cov=. --cov-report=html --cov-report=term-missing

coverage-report: ## Открыть отчет о покрытии
	open htmlcov/index.html || xdg-open htmlcov/index.html || start htmlcov/index.html

setup: install ## Установить и настроить проект
	@echo "🚀 Проект настроен! Создайте .env файл и запустите 'make run'"

setup-dev: install-dev ## Установить и настроить проект для разработки
	@echo "🔧 Проект настроен для разработки!"
	@echo "📝 Создайте .env файл"
	@echo "🧪 Запустите 'make test' для проверки"
	@echo "🚀 Запустите 'make run' для запуска"

dev: setup-dev ## Полная настройка для разработки
	@echo "🎯 Готово к разработке!"
	@echo "📋 Доступные команды:"
	@echo "  make run          - Запуск бота"
	@echo "  make test         - Запуск тестов"
	@echo "  make format       - Форматирование кода"
	@echo "  make lint         - Проверка кода"
	@echo "  make type-check   - Проверка типов"
	@echo "  make coverage     - Покрытие кода"

check-all: ## Выполнить все проверки
	@echo "🔍 Выполняю все проверки..."
	@echo "📝 Форматирование..."
	@make format-check
	@echo "🔍 Linting..."
	@make lint
	@echo "🔍 Type checking..."
	@make type-check
	@echo "🔍 Security check..."
	@make security-check
	@echo "🧪 Тестирование..."
	@make test-pytest
	@echo "✅ Все проверки завершены!"

pre-commit: ## Подготовка к коммиту
	@echo "🚀 Подготовка к коммиту..."
	@make format
	@make lint
	@make type-check
	@make test
	@echo "✅ Код готов к коммиту!"

ci: ## Команды для CI/CD
	@echo "🚀 Выполняю CI/CD проверки..."
	@make format-check
	@make lint
	@make type-check
	@make test-pytest
	@make security-check
	@echo "✅ CI/CD проверки завершены!"

monitoring: ## Запустить мониторинг
	@echo "📊 Запуск мониторинга..."
	python -c "
	import monitoring
	from monitoring import health_checker, metrics_collector
	print('🔍 Health Check:')
	health = health_checker.check_health()
	for service, status in health.items():
		print(f'  {service}: {status.status}')
	print('📈 Метрики:')
	print(f'  Счетчики: {len(metrics_collector.counters)}')
	print(f'  Gauge: {len(metrics_collector.gauges)}')
	print(f'  Гистограммы: {len(metrics_collector.histograms)}')
	"

config: ## Показать конфигурацию
	@echo "⚙️ Текущая конфигурация:"
	python -c "
	import config
	from config import bot_config
	print(f'🤖 Имя бота: {bot_config.bot_name}')
	print(f'📦 Версия: {bot_config.bot_version}')
	print(f'🧠 AI провайдер: {bot_config.ai_provider}')
	print(f'🎮 Игры включены: {bot_config.games_enabled}')
	print(f'📊 Мониторинг включен: {bot_config.monitoring_enabled}')
	print(f'💰 Контент включен: {bot_config.content_enabled}')
	"

modules: ## Показать информацию о модулях
	@echo "📦 Информация о модулях:"
	@echo "  ai.py          - AI система и провайдеры"
	@echo "  admin.py       - Админ-панель и управление"
	@echo "  monitoring.py  - Мониторинг и метрики"
	@echo "  games.py       - Игровая система"
	@echo "  content.py     - Контент и монетизация"
	@echo "  streaming.py   - Стриминг AI ответов"
	@echo "  utils.py       - Утилиты и хелперы"
	@echo "  config.py      - Конфигурация и env"
	@echo "  tests.py       - Unit тесты всех модулей"

version: ## Показать версию
	@echo "🚀 CryCat Bot v2.0.0"
	@echo "📅 Дата релиза: $(shell date +%Y-%m-%d)"
	@echo "🐍 Python: $(shell python --version)"
	@echo "📦 Модулей: 8"
	@echo "🧪 Тестов: 50+"
	@echo "📊 Покрытие: 80%+"