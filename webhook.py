#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вебхук для обработки уведомлений от YooMoney
"""

import os
import json
import hashlib
import hmac
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)

# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация YooMoney
YOOMONEY_MODE = os.getenv("YOOMONEY_MODE", "PERSONAL")
YOOMONEY_SHOP_ID = os.getenv("YOOMONEY_SHOP_ID", "")
YOOMONEY_NOTIFICATION_SECRET = os.getenv("YOOMONEY_NOTIFICATION_SECRET", "")
YOOMONEY_WEBHOOK_URL = os.getenv("YOOMONEY_WEBHOOK_URL", "")

def verify_yoomoney_signature(data, signature):
    """Проверяет подпись от YooMoney"""
    if not YOOMONEY_NOTIFICATION_SECRET:
        logger.warning("YOOMONEY_NOTIFICATION_SECRET не настроен")
        return False
    
    # Формируем строку для проверки подписи
    check_string = "&".join([
        data.get("notification_type", ""),
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        YOOMONEY_NOTIFICATION_SECRET,
        data.get("label", "")
    ])
    
    # Вычисляем SHA1 хеш
    expected_signature = hashlib.sha1(check_string.encode('utf-8')).hexdigest()
    
    logger.info(f"Ожидаемая подпись: {expected_signature}")
    logger.info(f"Полученная подпись: {signature}")
    
    return hmac.compare_digest(expected_signature, signature)

def process_payment(data):
    """Обрабатывает успешный платёж"""
    try:
        # Извлекаем информацию о платеже
        operation_id = data.get("operation_id", "")
        amount = float(data.get("amount", "0"))
        currency = data.get("currency", "")
        sender = data.get("sender", "")
        label = data.get("label", "")
        
        logger.info(f"Обработка платежа: {operation_id}, {amount} {currency}, от {sender}")
        
        # Парсим label для получения информации о пользователе и пакете
        if label and "_" in label:
            parts = label.split("_")
            if len(parts) >= 4:
                user_id = parts[1]
                timestamp = parts[2]
                package = parts[3]
                
                logger.info(f"Пользователь: {user_id}, Пакет: {package}")
                
                # Здесь должна быть логика начисления монет пользователю
                # Пока что просто логируем
                logger.info(f"Начисляем монеты пользователю {user_id} за пакет {package}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "package": package,
                    "amount": amount,
                    "operation_id": operation_id
                }
        
        return {"success": False, "error": "Неверный формат label"}
        
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        return {"success": False, "error": str(e)}

@app.route('/yoomoney', methods=['POST'])
def yoomoney_webhook():
    """Обработчик вебхука от YooMoney"""
    try:
        # Получаем данные
        data = request.form.to_dict()
        signature = request.headers.get('X-YooMoney-Signature', '')
        
        logger.info(f"Получен вебхук от YooMoney: {data}")
        logger.info(f"Подпись: {signature}")
        
        # Проверяем подпись
        if not verify_yoomoney_signature(data, signature):
            logger.warning("Неверная подпись от YooMoney")
            return jsonify({"error": "Invalid signature"}), 400
        
        # Проверяем тип уведомления
        notification_type = data.get("notification_type", "")
        
        if notification_type == "p2p-incoming":
            # Входящий перевод
            result = process_payment(data)
            
            if result["success"]:
                logger.info(f"Платёж успешно обработан: {result}")
                return jsonify({"status": "success"}), 200
            else:
                logger.error(f"Ошибка обработки платежа: {result}")
                return jsonify({"error": result["error"]}), 400
        else:
            logger.info(f"Неизвестный тип уведомления: {notification_type}")
            return jsonify({"status": "ignored"}), 200
            
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "yoomoney_mode": YOOMONEY_MODE,
        "webhook_url": YOOMONEY_WEBHOOK_URL
    })

@app.route('/', methods=['GET'])
def index():
    """Главная страница"""
    return """
    <h1>YooMoney Webhook</h1>
    <p>Статус: Работает</p>
    <p>Режим: {}</p>
    <p>Вебхук: {}</p>
    <p><a href="/health">Проверка здоровья</a></p>
    """.format(YOOMONEY_MODE, YOOMONEY_WEBHOOK_URL)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск вебхука на порту {port}")
    logger.info(f"YooMoney режим: {YOOMONEY_MODE}")
    logger.info(f"Вебхук URL: {YOOMONEY_WEBHOOK_URL}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
