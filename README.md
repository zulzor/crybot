# Cry Cat VK Bot

## Быстрый старт
- Установите зависимости:
```bash
pip install -r requirements.txt
```
- Создайте файл `.env` (см. пример ниже)
- Запустите бота:
```bash
python3 bot_vk.py
```

## Пример .env
```ini
# VK
VK_GROUP_TOKEN=vk1.a.your_group_token
VK_GROUP_ID=123456789

# Выбор провайдера ИИ: OPENROUTER, AITUNNEL, AUTO
AI_PROVIDER=AUTO

# OpenRouter (DeepSeek)
DEEPSEEK_API_KEY=your_openrouter_key
OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
# Список моделей (через запятую) — опционально, для авто-переключения
# OPENROUTER_MODELS=deepseek/deepseek-chat-v3-0324:free,openai/gpt-4o-mini
# Доп. заголовки для OpenRouter (опционально)
OPENROUTER_REFERER=https://vk.com/crycat_memes
OPENROUTER_TITLE=Cry Cat Bot

# AITunnel
AITUNNEL_API_URL=https://api.aitunnel.ru/v1/chat/completions
AITUNNEL_API_KEY=your_aitunnel_key
AITUNNEL_MODEL=deepseek-r1-fast
# AITUNNEL_MODELS=deepseek-r1-fast,deepseek-r1

# Системный промпт ИИ (выберите один из вариантов ниже)
AI_SYSTEM_PROMPT=Ты КиберКусь. Пиши по-русски, дружелюбно, до 380 символов. По запросу кратко упоминай: Мафия, Угадай число, Викторина, Кальмар, ИИ‑чат.
```

## Варианты AI_SYSTEM_PROMPT

- Нормальный стиль:
```text
Ты КиберКусь. Пиши по-русски, дружелюбно, до 380 символов. По запросу кратко упоминай: Мафия, Угадай число, Викторина, Кальмар, ИИ‑чат.
```

- Мемный стиль (для AITunnel тоже подходит):
```text
Ты мемный КиберКусь. Отвечай по‑делу, коротко (до 380 символов), но с лёгким вайбом мемов. Не скатывайся в токсичность, не используй оскорбления. Если спрашивают про бота — расскажи, что есть «Мафия», «Угадай число», «Викторина», «Кальмар» и «ИИ‑чат».
```

## Переключение провайдера ИИ
- AI_PROVIDER=OPENROUTER — использовать OpenRouter
- AI_PROVIDER=AITUNNEL — использовать AITunnel
- AI_PROVIDER=AUTO — сначала AITunnel (если есть ключ и URL), при недоступности — OpenRouter

## Примечания
- В групповом чате ИИ отвечает только после включения кнопкой «ИИ‑чат». В личных сообщениях ИИ активен всегда.
- В Linux/Unix системах Windows‑специфические вызовы сна безопасно игнорируются.
