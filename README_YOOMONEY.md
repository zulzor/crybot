# Настройка YooMoney для личного кошелька

## Шаг 1: Настройка .env файла

Создайте файл `.env` в корне проекта:

```env
# YooMoney настройки для личного кошелька
YOOMONEY_MODE=PERSONAL
YOOMONEY_SHOP_ID=4100117804002054
YOOMONEY_NOTIFICATION_SECRET=ИТАЛИЯ
YOOMONEY_REDIRECT_URL=https://vk.com/im?sel=-ID_ВАШЕЙ_ГРУППЫ
YOOMONEY_WEBHOOK_URL=https://una-retrieve-german-tennis.trycloudflare.com/yoomoney

# Остальные настройки бота
BOT_TOKEN=your_bot_token_here
GROUP_ID=your_group_id_here
ADMIN_USER_IDS=253133228
```

## Шаг 2: Настройка HTTP-уведомлений в YooMoney

1. Войдите в YooMoney
2. Перейдите в Настройки → Приём переводов → HTTP-уведомления
3. Заполните:
   - **URL**: https://una-retrieve-german-tennis.trycloudflare.com/yoomoney
   - **Секрет для уведомлений**: ИТАЛИЯ
4. Сохраните настройки

## Шаг 3: Запуск вебхука

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите вебхук:
```bash
python webhook.py
```

3. В другом терминале запустите туннель Cloudflare:
```bash
cd C:\tools
.\cloudflared.exe tunnel --url http://localhost:5000
```

## Шаг 4: Тестирование

1. В боте нажмите "💳 Донаты"
2. Выберите пакет
3. Перейдите по ссылке и оплатите
4. После оплаты YooMoney отправит уведомление на вебхук
5. Бот автоматически начислит монеты

## Структура label для платежей

YooMoney отправляет label в формате:
```
ORDER_<user_id>_<timestamp>_<package_key>
```

Пример: `ORDER_123456_1692480000_starter`

## Проверка подписи

Вебхук проверяет подпись YooMoney по алгоритму SHA1:
```
notification_type&operation_id&amount&currency&datetime&sender&codepro&notification_secret&label
```

## Логи

Вебхук логирует все операции в консоль. Проверяйте логи для отладки.
