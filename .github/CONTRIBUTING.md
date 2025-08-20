# Руководство для участников

Спасибо за интерес к участию в проекте Cry Cat Bot! 🚀

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.8+
- Git
- VK Group Token (для тестирования)

### Установка
1. Fork репозитория
2. Клонируйте ваш fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/crycat-bot.git
   cd crycat-bot
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   ```
4. Создайте `.env` файл на основе `.env.example`
5. Установите pre-commit hooks:
   ```bash
   pre-commit install
   ```

## 🔧 Разработка

### Структура проекта
```
crycat-bot/
├── bot_vk.py          # Основной файл бота
├── requirements.txt    # Зависимости
├── .env.example       # Пример конфигурации
├── README.md          # Документация
├── CHANGELOG.md       # История изменений
├── LICENSE            # Лицензия
├── .github/           # GitHub конфигурация
├── Dockerfile         # Docker образ
├── docker-compose.yml # Docker Compose
├── Makefile           # Команды Make
├── pyproject.toml     # Конфигурация Python инструментов
└── .pre-commit-config.yaml # Pre-commit hooks
```

### Запуск для разработки
```bash
make run
```

### Проверка кода
```bash
make lint
make format
```

### Тестирование
```bash
make test
```

## 📝 Рабочий процесс

### 1. Создание Issue
- Используйте соответствующие шаблоны для [bug reports](.github/ISSUE_TEMPLATE/bug_report.md) и [feature requests](.github/ISSUE_TEMPLATE/feature_request.md)
- Опишите проблему или предложение как можно подробнее
- Укажите версию бота и контекст

### 2. Создание ветки
```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/your-bug-fix
```

### 3. Разработка
- Следуйте стилю кода проекта
- Добавляйте комментарии к сложным участкам кода
- Обновляйте документацию при необходимости
- Добавляйте тесты для новых функций

### 4. Коммиты
```bash
git add .
git commit -m "feat: добавить новую функцию X"
git commit -m "fix: исправить ошибку в Y"
git commit -m "docs: обновить README"
```

### 5. Push и Pull Request
```bash
git push origin feature/your-feature-name
```
- Создайте Pull Request с описанием изменений
- Используйте [шаблон PR](.github/pull_request_template.md)
- Убедитесь, что все CI проверки проходят

## 🎨 Стандарты кода

### Python
- Следуйте PEP 8
- Используйте type hints
- Документируйте функции и классы
- Максимальная длина строки: 88 символов

### Форматирование
```bash
make format  # Автоматическое форматирование
make lint    # Проверка стиля
```

### Импорты
```python
# Стандартная библиотека
import os
import sys
from typing import List, Dict

# Сторонние библиотеки
import requests
import vk_api

# Локальные модули
from .utils import helper_function
```

## 🧪 Тестирование

### Добавление тестов
- Создавайте тесты для новых функций
- Тесты должны быть в папке `tests/`
- Используйте pytest для тестирования

### Запуск тестов
```bash
make test
```

## 📚 Документация

### Обновление документации
- Обновляйте README.md при добавлении новых функций
- Обновляйте CHANGELOG.md при изменениях
- Добавляйте комментарии к коду
- Создавайте примеры использования

### Структура документации
- README.md - основная документация
- CHANGELOG.md - история изменений
- Комментарии в коде
- Примеры в issues и PR

## 🚀 CI/CD

### GitHub Actions
- Автоматические проверки при каждом PR
- Тестирование на разных версиях Python
- Проверка стиля кода
- Сборка Docker образа

### Локальная проверка
```bash
make lint      # Проверка стиля
make format    # Форматирование
make test      # Тесты
```

## 🤝 Сообщество

### Общение
- Будьте вежливы и уважительны
- Помогайте другим участникам
- Задавайте вопросы в issues
- Обсуждайте идеи в discussions

### Кодекс поведения
- Следуйте [Кодексу поведения](CODE_OF_CONDUCT.md)
- Сообщайте о нарушениях команде проекта
- Создавайте инклюзивную среду

## 🎯 Приоритеты развития

### v2.1 - Health Checks & Monitoring
- [ ] Health checks для моделей ИИ
- [ ] Авто-отключение "битых" моделей
- [ ] Метрики производительности
- [ ] Мониторинг ошибок

### v2.2 - Персональные настройки
- [ ] Пер-чат профили настроек
- [ ] Пер-роль профили
- [ ] Пресеты настроек

### v2.3 - Улучшения UX
- [ ] Стриминг ответов ИИ
- [ ] Индикатор "набирает текст..."
- [ ] Авто-сжатие длинных ответов

## 📞 Поддержка

### Получение помощи
- Создайте issue для вопросов
- Используйте discussions для обсуждений
- Свяжитесь с командой проекта

### Полезные ссылки
- [VK API Documentation](https://vk.com/dev)
- [OpenRouter API](https://openrouter.ai/docs)
- [AITunnel API](https://aitunnel.ru/docs)
- [Python Documentation](https://docs.python.org/)

---

Спасибо за ваш вклад в развитие Cry Cat Bot! 🎉