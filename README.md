# 🚀 CryCat Bot v2.0.0 - AI-Powered VK Bot

**Многофункциональный VK бот с модульной архитектурой, ИИ, играми, мониторингом и монетизацией**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/zulzor/crybot)
[![CI/CD](https://github.com/zulzor/crybot/workflows/CI%2FCD%20Pipeline%20v2.0.0/badge.svg)](https://github.com/zulzor/crybot/actions)

## 🌟 Что нового в v2.0.0

### 🏗️ **Модульная архитектура**
- **8 специализированных модулей** вместо одного монолитного файла
- **Чистый код** с разделением ответственности
- **Легкое тестирование** и поддержка

### 🤖 **AI система нового поколения**
- **Health checks** + авто-отключение "битых" моделей
- **Circuit breaker** + экспоненциальный бэкофф
- **HTTP session pool** для эффективности
- **Response caching** для скорости
- **Rate limiting** для защиты
- **Content filtering** (Guardrails) для безопасности

### 🎮 **Игровая система**
- **4 полноценные игры** с сессиями и очками
- **Угадай число** - классическая логическая игра
- **Кальмар** - мини-игры с элиминацией
- **Викторина** - образовательные вопросы
- **Мафия** - командная социальная игра

### 💰 **Монетизация и контент**
- **Внутренняя валюта** с кошельками пользователей
- **AI бустеры** (Fast Lane, Token Boost, Speed Boost, Quality Boost)
- **Ежедневные задания** с наградами
- **Сезонные события** и активности

### 📊 **Мониторинг и метрики**
- **Prometheus метрики** в реальном времени
- **Health checks** для всех сервисов
- **JSON логирование** структурированное
- **Метрики производительности** (латентность, ошибки, пустые ответы)

### 🔧 **DevOps и качество кода**
- **Полный CI/CD pipeline** с GitHub Actions
- **Автоматическое тестирование** всех модулей
- **Linting** с Ruff, Black, isort
- **Type checking** с mypy
- **Security scanning** с bandit
- **Code coverage** 80%+

## 🚀 Возможности

### 🤖 **AI и надежность**
- **OpenRouter** - DeepSeek, Qwen, Llama модели
- **AITunnel** - GPT-5-nano, Gemini Flash, DeepSeek Chat
- **Runtime параметры** - полный контроль в реальном времени
- **Авто-переключение** между провайдерами при ошибках
- **Health monitoring** - автоматическое отключение проблемных моделей
- **Circuit breaker** - защита от каскадных сбоев
- **HTTP connection pooling** - оптимизация производительности
- **Response caching** - ускорение повторных запросов
- **Rate limiting** - защита от злоупотреблений
- **Content filtering** - фильтры токсичности и PII
- **History summarization** - умное управление контекстом

### 🎮 **Игры и развлечения**
- **Угадай число** - логическая игра с очками
- **Кальмар** - мини-игры с элиминацией
- **Викторина** - образовательные вопросы
- **Мафия** - командная социальная игра
- **Система очков** и рейтингов
- **Сессионное управление** игр

### ⚙️ **Админ-панель**
- **Система ролей** (User, Editor, Moderator, Admin, Super Admin)
- **Per-chat/Per-role настройки** - индивидуальные настройки
- **AI пресеты** - готовые конфигурации
- **Пагинация моделей** - удобная навигация
- **Поиск по моделям** - быстрый поиск
- **Экспорт/импорт** конфигурации
- **Runtime контроль** всех AI параметров

### 💰 **Монетизация**
- **Внутренняя валюта** с поддержкой RUB/USD/EUR
- **AI бустеры:**
  - **Fast Lane** - приоритетная очередь
  - **Token Boost** - увеличенные лимиты токенов
  - **Speed Boost** - ускоренные ответы
  - **Quality Boost** - повышенное качество
- **Ежедневные задания** с наградами
- **Сезонные события** и активности

### 📊 **Мониторинг и метрики**
- **Prometheus метрики** для интеграции с Grafana
- **Health checks** для всех сервисов
- **JSON логирование** структурированное
- **Метрики производительности:**
  - Латентность ответов
  - Процент ошибок
  - Процент пустых ответов
  - Использование ресурсов
- **Автоматическая очистка** старых метрик

### 🔧 **DevOps и качество**
- **CI/CD Pipeline** с автоматическим тестированием
- **Docker поддержка** с multi-stage builds
- **Автоматическое развертывание** в production
- **Code quality gates** с обязательными проверками
- **Security scanning** и vulnerability detection
- **Performance testing** с Locust

## 🏗️ Архитектура

### 📁 **Структура модулей**
```
crycat-bot/
├── ai.py              # AI система и провайдеры
├── admin.py           # Админ-панель и управление
├── monitoring.py      # Мониторинг и метрики
├── games.py           # Игровая система
├── content.py         # Контент и монетизация
├── streaming.py       # Стриминг AI ответов
├── utils.py           # Утилиты и хелперы
├── config.py          # Конфигурация и env
├── bot_vk.py          # Основной бот (обновлен)
└── tests.py           # Unit тесты всех модулей
```

### 🔄 **Взаимодействие модулей**
```
bot_vk.py (основной)
    ├── ai.py (AI логика)
    ├── admin.py (админ функции)
    ├── monitoring.py (метрики)
    ├── games.py (игры)
    ├── content.py (монетизация)
    ├── streaming.py (индикаторы)
    ├── utils.py (утилиты)
    └── config.py (конфигурация)
```

## 🔧 Установка

### 📋 **Требования**
- **Python 3.8+** (рекомендуется 3.11)
- **VK Group Token** (обязательно)
- **OpenRouter API Key** (опционально)
- **AITunnel API Key** (опционально)
- **Redis** (опционально, для кэширования)

### 🐳 **Docker (рекомендуется)**
```bash
# Клонирование репозитория
git clone https://github.com/zulzor/crybot.git
cd crybot

# Запуск с Docker Compose
docker-compose up -d

# Или сборка образа
docker build -t crycat-bot:v2.0.0 .
docker run -d --name crycat-bot crycat-bot:v2.0.0
```

### 🐍 **Python установка**
```bash
# Клонирование
git clone https://github.com/zulzor/crybot.git
cd crybot

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск
python bot_vk.py
```

### ⚙️ **Переменные окружения (.env)**
```bash
# VK настройки (обязательно)
VK_GROUP_TOKEN=your_vk_token
VK_GROUP_ID=your_group_id

# AI провайдеры (опционально)
AI_PROVIDER=AUTO  # AUTO, OPENROUTER, AITUNNEL
OPENROUTER_API_KEY=your_openrouter_key
AITUNNEL_API_KEY=your_aitunnel_key

# Админ настройки
ADMIN_USER_IDS=123456,789012

# Логирование
LOG_LEVEL=INFO
LOG_FILE=bot.log

# Мониторинг
MONITORING_ENABLED=true
METRICS_COLLECTION=true

# Игры и контент
GAMES_ENABLED=true
CONTENT_ENABLED=true
DAILY_TASKS_ENABLED=true
```

## 🚀 Быстрый старт

### 1️⃣ **Минимальная конфигурация**
```bash
# Создайте .env файл
echo "VK_GROUP_TOKEN=your_token" > .env
echo "VK_GROUP_ID=123456" >> .env
echo "ADMIN_USER_IDS=your_user_id" >> .env

# Запустите бота
python bot_vk.py
```

### 2️⃣ **Полная конфигурация с AI**
```bash
# Добавьте AI ключи в .env
echo "OPENROUTER_API_KEY=your_key" >> .env
echo "AITUNNEL_API_KEY=your_key" >> .env
echo "AI_PROVIDER=AUTO" >> .env

# Запустите с полным функционалом
python bot_vk.py
```

### 3️⃣ **Тестирование модулей**
```bash
# Запуск всех тестов
python tests.py

# Или с pytest
pytest tests.py -v --cov=. --cov-report=html
```

## 🤖 AI Настройки

### ⚡ **Runtime Параметры**
Все параметры ИИ можно изменять в реальном времени:

#### 🌡️ **Основные параметры**
- **Temperature** (0.0-2.0) - креативность ответов
- **Top-P** (0.0-1.0) - разнообразие выбора токенов
- **Max Tokens OR** (10-200) - токены для OpenRouter
- **Max Tokens AT** (100-10000) - токены для AITunnel
- **Max Characters** (50-1000) - ограничение длины ответа

#### 🧠 **Reasoning и контекст**
- **Reasoning Enabled** - включение/выключение рассуждений
- **Reasoning Tokens** (10-500) - токены для рассуждений
- **Reasoning Depth** - глубина (low/medium/high)
- **Max History** (1-20) - количество сообщений в контексте

#### 🛡️ **Надежность и производительность**
- **OR Retries** (1-5) - попытки для OpenRouter
- **AT Retries** (1-5) - попытки для AITunnel
- **OR Timeout** (10-300s) - таймаут OpenRouter
- **AT Timeout** (10-300s) - таймаут AITunnel
- **Fallback OR→AT** - автоматическое переключение

### 🎛️ **Команды для админов**

#### 📊 **Основные команды**
- `/admin` - админ-панель
- `/ai_settings` - просмотр AI настроек
- `/ai_current` - текущий провайдер и модель
- `/ai_export` - экспорт настроек в JSON
- `/ai_import [json]` - импорт настроек
- `/ai_reset` - сброс к значениям по умолчанию

#### 🔄 **Настройка провайдера**
- `/ai_provider [OPENROUTER|AITUNNEL|AUTO]` - смена провайдера
- `/ai_model [название]` - смена модели

#### ⚙️ **Настройка параметров**
- `/ai_temp [0.0-2.0]` - температура
- `/ai_top_p [0.0-1.0]` - top-p
- `/ai_max_tokens [OR|AT] [число]` - максимальные токены
- `/ai_max_chars [50-1000]` - максимальные символы
- `/ai_history [1-20]` - история сообщений

#### 🧠 **Настройка reasoning**
- `/ai_reasoning [on|off]` - включение/выключение
- `/ai_reasoning tokens [10-500]` - токены для reasoning
- `/ai_reasoning depth [low|medium|high]` - глубина reasoning

#### 🛡️ **Настройка надежности**
- `/ai_retries [OR|AT] [1-5]` - количество попыток
- `/ai_timeout [OR|AT] [10-300]` - таймауты
- `/ai_fallback [on|off]` - включение/выключение fallback

## 🎮 Игры

### 🎯 **Угадай число**
- **Команда**: `/guess [число]`
- **Описание**: Угадайте число от 1 до 100
- **Особенности**: Система очков, ограниченные попытки
- **Награды**: Очки за скорость угадывания

### 🎮 **Кальмар**
- **Команда**: `/squid_game`
- **Описание**: Серия мини-игр с элиминацией
- **Раунды**: Красный свет/зеленый свет, перетягивание каната
- **Особенности**: Командная игра, система очков

### 🧠 **Викторина**
- **Команда**: `/quiz`
- **Описание**: Образовательные вопросы с вариантами ответов
- **Особенности**: Разные категории, система подсказок
- **Награды**: Очки за правильные ответы

### 🎭 **Мафия**
- **Команда**: `/mafia`
- **Описание**: Классическая социальная игра
- **Роли**: Мафия, Мирные, Доктор, Шериф
- **Особенности**: Командная игра, голосования

## 💰 Монетизация

### 💳 **Внутренняя валюта**
- **Поддержка**: RUB, USD, EUR
- **Пополнение**: Ежедневные задания, события
- **Траты**: AI бустеры, премиум функции

### 🚀 **AI бустеры**
- **Fast Lane** (50₽) - приоритетная очередь запросов
- **Token Boost** (100₽) - увеличенные лимиты токенов
- **Speed Boost** (75₽) - ускоренные ответы
- **Quality Boost** (150₽) - повышенное качество ответов

### 📋 **Ежедневные задания**
- **AI Чат x5** - 10₽ за 5 сообщений в AI
- **Игрок** - 15₽ за участие в 3 играх
- **Ежедневный вход** - 100₽ за 7 дней подряд

## 📊 Мониторинг

### 📈 **Prometheus метрики**
```bash
# Основные метрики
bot_ai_requests_total{provider="openrouter"}
bot_ai_response_time_seconds{model="deepseek"}
bot_health_status{service="openrouter"}

# Метрики игр
bot_games_active_total{game="guess_number"}
bot_games_completed_total{game="mafia"}

# Системные метрики
bot_memory_usage_bytes
bot_cpu_usage_percent
bot_disk_usage_percent
```

### 🔍 **Health checks**
- **AI провайдеры** - доступность API
- **Системные ресурсы** - CPU, память, диск
- **База данных** - состояние хранилища
- **Внешние сервисы** - мониторинг зависимостей

### 📝 **Логирование**
- **JSON формат** для структурированного анализа
- **Уровни логирования** - DEBUG, INFO, WARNING, ERROR
- **Автоматическая ротация** логов
- **Интеграция с Sentry** (опционально)

## 🛠️ Разработка

### 🧪 **Тестирование**
```bash
# Запуск всех тестов
python tests.py

# С покрытием кода
pytest tests.py -v --cov=. --cov-report=html

# Отдельные модули
python -m pytest tests.py::TestAIModule -v
python -m pytest tests.py::TestGamesModule -v
```

### 🔍 **Linting и форматирование**
```bash
# Проверка кода
ruff check .

# Форматирование
black .
isort .

# Type checking
mypy .

# Security scanning
bandit -r .
```

### 🐳 **Docker разработка**
```bash
# Сборка для разработки
docker build -f Dockerfile.dev -t crycat-bot:dev .

# Запуск с hot reload
docker run -v $(pwd):/app crycat-bot:dev
```

## 📚 API Документация

### 🤖 **AI API**
```python
from ai import deepseek_reply, aitunnel_reply, runtime_settings

# Настройка параметров
runtime_settings.temperature = 0.8
runtime_settings.max_tokens_or = 100

# Генерация ответа
response = deepseek_reply(api_key, system_prompt, history, user_text)
```

### 🎮 **Games API**
```python
from games import create_guess_game, create_mafia

# Создание игры
game = create_guess_game(peer_id, creator_id)

# Управление игрой
result, finished = game.guess(user_id, guess_number)
```

### 📊 **Monitoring API**
```python
from monitoring import metrics_collector, health_checker

# Сбор метрик
metrics_collector.increment_counter("ai_requests_total")

# Проверка здоровья
health_status = health_checker.check_health()
```

## 🚀 Деплой

### ☁️ **Production**
```bash
# Сборка production образа
docker build -t crycat-bot:prod .

# Запуск с переменными окружения
docker run -d \
  --name crycat-bot \
  --env-file .env \
  -p 8080:8080 \
  crycat-bot:prod
```

### 🔄 **CI/CD Pipeline**
1. **Push в main** → автоматический запуск pipeline
2. **Тестирование** → unit тесты, linting, security
3. **Сборка Docker** → multi-stage build
4. **Деплой** → автоматическое развертывание
5. **Мониторинг** → health checks и метрики

## 🤝 Вклад в проект

### 📝 **Как помочь**
1. **Fork** репозитория
2. **Создайте feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** изменения (`git commit -m 'Add amazing feature'`)
4. **Push** в branch (`git push origin feature/amazing-feature`)
5. **Создайте Pull Request**

### 🐛 **Сообщение об ошибках**
- Используйте **GitHub Issues**
- Опишите **шаги для воспроизведения**
- Укажите **версию Python и ОС**
- Приложите **логи ошибок**

### 💡 **Предложения функций**
- Создайте **Feature Request** issue
- Опишите **проблему и решение**
- Укажите **приоритет и сложность**

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**. См. файл [LICENSE](LICENSE) для подробностей.

## 🙏 Благодарности

- **VK API** - за платформу для ботов
- **OpenRouter** - за доступ к AI моделям
- **AITunnel** - за альтернативный AI API
- **Сообщество Python** - за отличные библиотеки
- **Все контрибьюторы** - за помощь в развитии проекта

## 📞 Поддержка

- **GitHub Issues**: [Создать issue](https://github.com/zulzor/crybot/issues)
- **Discord**: [Присоединиться к серверу](https://discord.gg/crycat)
- **Telegram**: [@crycat_support](https://t.me/crycat_support)
- **Email**: [team@crycat.bot](mailto:team@crycat.bot)

---

**⭐ Если проект вам понравился, поставьте звездочку на GitHub!**

**🚀 CryCat Bot v2.0.0 - будущее VK ботов уже здесь!**
