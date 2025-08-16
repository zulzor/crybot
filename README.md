# CryBot - VK Bot с играми и ИИ-чатом

Telegram-бот для ВКонтакте с играми "Мафия", "Угадай число" и интеграцией с ИИ через OpenRouter.

## Возможности

- 🎮 **Игра "Мафия"** - создание лобби и управление игроками
- 🔢 **Игра "Угадай число"** - для 2 игроков с поочередными ходами
- 🤖 **ИИ-чат** - интеграция с DeepSeek через OpenRouter API
- ⌨️ **Интерактивные клавиатуры** для удобного управления
- 📱 **Поддержка личных сообщений и групповых чатов**

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd crybot
```

2. **Для Windows (рекомендуется):**
   - Запустите `install_dependencies.bat` от имени администратора
   - Или установите вручную: `pip install -r requirements.txt`

3. Создайте файл `.env` с настройками:
```env
VK_GROUP_TOKEN=your_vk_group_token
VK_GROUP_ID=your_group_id
DEEPSEEK_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
AI_SYSTEM_PROMPT=Ты дружелюбный нейросотрудник сообщества Cry Cat...
```

## Запуск

### Обычный запуск:
```bash
python bot_vk.py
```

### Windows - через скрипты:
- **`start_bot.bat`** - запуск через командную строку
- **`start_bot.ps1`** - запуск через PowerShell

### Планировщик задач Windows:
1. Откройте "Планировщик задач"
2. Создайте новую задачу
3. В действии укажите: `C:\Users\jolab\Desktop\crybot\start_bot.bat`
4. Установите нужное расписание

## Настройка

### VK API
- Получите токен группы ВКонтакте
- Укажите ID группы (без минуса)

### OpenRouter API
- Зарегистрируйтесь на [OpenRouter](https://openrouter.ai/)
- Получите API ключ
- Настройте модель ИИ (по умолчанию DeepSeek)

## Структура проекта

- `bot_vk.py` - основной файл бота
- `requirements.txt` - зависимости Python
- `.env` - конфигурация (создать самостоятельно)
- `start_bot.bat` - Windows скрипт запуска
- `start_bot.ps1` - PowerShell скрипт запуска
- `install_dependencies.bat` - установка зависимостей

## Устранение проблем

### Ошибка "ModuleNotFoundError":
- Запустите `install_dependencies.bat` от имени администратора
- Или выполните: `pip install -r requirements.txt`

### Планировщик задач не запускает:
- Убедитесь, что Python добавлен в PATH
- Проверьте права доступа к папке проекта
- Используйте полный путь к `start_bot.bat`

## Лицензия

MIT License