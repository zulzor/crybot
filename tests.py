"""
Unit тесты для всех модулей бота
"""
import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули для тестирования
try:
    import ai
    import admin
    import monitoring
    import games
    import content
    import streaming
    import utils
    import config
except ImportError as e:
    print(f"Warning: Could not import module: {e}")

# ---------- Тесты AI модуля ----------
class TestAIModule(unittest.TestCase):
    """Тесты для AI модуля"""
    
    def setUp(self):
        """Подготовка к тестам"""
        self.runtime_settings = ai.RuntimeAISettings()
    
    def test_runtime_settings_defaults(self):
        """Тест значений по умолчанию"""
        self.assertEqual(self.runtime_settings.temperature, 0.6)
        self.assertEqual(self.runtime_settings.top_p, 1.0)
        self.assertEqual(self.runtime_settings.max_tokens_or, 80)
        self.assertEqual(self.runtime_settings.max_tokens_at, 5000)
        self.assertFalse(self.runtime_settings.reasoning_enabled)
        self.assertEqual(self.runtime_settings.max_history, 8)
        self.assertEqual(self.runtime_settings.max_ai_chars, 380)
    
    def test_runtime_settings_to_dict(self):
        """Тест конвертации в словарь"""
        settings_dict = self.runtime_settings.to_dict()
        self.assertIsInstance(settings_dict, dict)
        self.assertIn('temperature', settings_dict)
        self.assertIn('max_tokens_or', settings_dict)
        self.assertIn('max_tokens_at', settings_dict)
    
    def test_runtime_settings_from_dict(self):
        """Тест загрузки из словаря"""
        test_data = {
            'temperature': 1.0,
            'max_tokens_or': 100,
            'max_ai_chars': 500
        }
        self.runtime_settings.from_dict(test_data)
        self.assertEqual(self.runtime_settings.temperature, 1.0)
        self.assertEqual(self.runtime_settings.max_tokens_or, 100)
        self.assertEqual(self.runtime_settings.max_ai_chars, 500)
    
    def test_ai_health_checker(self):
        """Тест health checker"""
        health_checker = ai.AIHealthChecker()
        self.assertIsInstance(health_checker.health_data, dict)
        self.assertEqual(health_checker.circuit_breaker_threshold, 5)
        self.assertEqual(health_checker.circuit_breaker_timeout, 300)
    
    def test_circuit_breaker(self):
        """Тест circuit breaker"""
        cb = ai.CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        self.assertEqual(cb.state, "CLOSED")
        self.assertEqual(cb.failure_count, 0)
    
    def test_http_session_pool(self):
        """Тест HTTP session pool"""
        pool = ai.HTTPSessionPool()
        session = pool.get_session("test_provider")
        self.assertIsInstance(session, type(pool.get_session("test_provider")))
    
    def test_rate_limiter(self):
        """Тест rate limiter"""
        limiter = ai.RateLimiter(max_requests=2, window=60)
        self.assertTrue(limiter.is_allowed("user1"))
        self.assertTrue(limiter.is_allowed("user1"))
        self.assertFalse(limiter.is_allowed("user1"))
    
    def test_response_cache(self):
        """Тест response cache"""
        cache = ai.ResponseCache(max_size=2, ttl=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        
        # Тест переполнения
        cache.set("key3", "value3")
        self.assertIsNone(cache.get("key1"))  # Должен быть удален
    
    def test_content_filter(self):
        """Тест content filter"""
        filter_instance = ai.content_filter
        text = "Это нормальный текст"
        filtered_text, warnings = filter_instance.filter_content(text)
        self.assertEqual(filtered_text, text)
        self.assertEqual(len(warnings), 0)
        
        # Тест токсичности
        toxic_text = "Я ненавижу всех"
        filtered_text, warnings = filter_instance.filter_content(toxic_text)
        self.assertIn("ненавижу", filtered_text)
        self.assertGreater(len(warnings), 0)
    
    def test_clamp_text(self):
        """Тест обрезки текста"""
        long_text = "Это очень длинный текст который нужно обрезать до определенной длины"
        clamped = ai.clamp_text(long_text, max_chars=20)
        self.assertLessEqual(len(clamped), 20)
        self.assertIn("...", clamped)
    
    def test_summarize_history(self):
        """Тест суммаризации истории"""
        history = [
            {"role": "system", "content": "Система"},
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Привет!"},
            {"role": "user", "content": "Как дела?"},
            {"role": "assistant", "content": "Хорошо!"}
        ]
        summarized = ai.summarize_history(history, max_tokens=50)
        self.assertLessEqual(len(summarized), len(history))

# ---------- Тесты Admin модуля ----------
class TestAdminModule(unittest.TestCase):
    """Тесты для Admin модуля"""
    
    def test_user_roles(self):
        """Тест системы ролей"""
        self.assertEqual(admin.UserRole.USER.value, "user")
        self.assertEqual(admin.UserRole.ADMIN.value, "admin")
        self.assertEqual(admin.UserRole.SUPER_ADMIN.value, "super_admin")
    
    def test_user_profile(self):
        """Тест профиля пользователя"""
        profile = admin.UserProfile(
            user_id=123,
            role=admin.UserRole.ADMIN
        )
        self.assertEqual(profile.user_id, 123)
        self.assertEqual(profile.role, admin.UserRole.ADMIN)
        self.assertEqual(profile.temperature, 0.6)
    
    def test_chat_settings(self):
        """Тест настроек чата"""
        chat_settings = admin.ChatSettings(chat_id=456)
        self.assertEqual(chat_settings.chat_id, 456)
        self.assertEqual(chat_settings.ai_provider, "AUTO")
        self.assertEqual(chat_settings.temperature, 0.6)
    
    def test_ai_presets(self):
        """Тест AI пресетов"""
        presets = admin.AIPresets.list_presets()
        self.assertIn("Коротко", presets)
        self.assertIn("Детально", presets)
        self.assertIn("Дешево", presets)
        self.assertIn("Креативно", presets)
        
        # Тест применения пресета
        preset = admin.AIPresets.get_preset("Коротко")
        self.assertIsInstance(preset, dict)
        self.assertIn("temperature", preset)
        self.assertIn("max_tokens", preset)
    
    def test_paginator(self):
        """Тест пагинации"""
        items = list(range(25))  # 25 элементов
        paginator = admin.Paginator(items, page_size=10)
        
        self.assertEqual(paginator.total_pages, 3)
        
        page1, current, total, count = paginator.get_page(0)
        self.assertEqual(len(page1), 10)
        self.assertEqual(current, 0)
        self.assertEqual(total, 3)
        self.assertEqual(count, 25)
    
    def test_model_search(self):
        """Тест поиска моделей"""
        search = admin.ModelSearch()
        all_models = search.get_all()
        self.assertGreater(len(all_models), 0)
        
        # Тест поиска
        results = search.search("deepseek")
        self.assertGreater(len(results), 0)
        self.assertTrue(all("deepseek" in model.lower() for model in results))

# ---------- Тесты Monitoring модуля ----------
class TestMonitoringModule(unittest.TestCase):
    """Тесты для Monitoring модуля"""
    
    def test_metric(self):
        """Тест метрики"""
        metric = monitoring.Metric(
            name="test_metric",
            value=42.0,
            timestamp=time.time(),
            labels={"test": "value"}
        )
        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.value, 42.0)
        self.assertIn("test", metric.labels)
    
    def test_metrics_collector(self):
        """Тест коллектора метрик"""
        collector = monitoring.MetricsCollector()
        
        # Тест счетчиков
        collector.increment_counter("test_counter")
        collector.increment_counter("test_counter")
        self.assertEqual(collector.get_counter("test_counter"), 2)
        
        # Тест gauge
        collector.set_gauge("test_gauge", 100.0)
        self.assertEqual(collector.get_gauge("test_gauge"), 100.0)
        
        # Тест гистограммы
        collector.observe_histogram("test_hist", 10.0)
        collector.observe_histogram("test_hist", 20.0)
        stats = collector.get_histogram_stats("test_hist")
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["avg"], 15.0)
    
    def test_health_checker(self):
        """Тест health checker"""
        health_checker = monitoring.HealthChecker()
        health_status = health_checker.check_health()
        self.assertIsInstance(health_status, dict)
        
        overall_status = health_checker.get_overall_status()
        self.assertIn(overall_status, ["healthy", "degraded", "unhealthy", "unknown"])

# ---------- Тесты Games модуля ----------
class TestGamesModule(unittest.TestCase):
    """Тесты для Games модуля"""
    
    def test_guess_number_session(self):
        """Тест игры 'Угадай число'"""
        session = games.GuessNumberSession(creator_id=123)
        self.assertEqual(session.creator_id, 123)
        self.assertFalse(session.started)
        self.assertEqual(session.attempts, 0)
        
        # Тест начала игры
        session.start()
        self.assertTrue(session.started)
        self.assertGreater(session.start_time, 0)
        
        # Тест угадывания
        result, is_finished = session.guess(123, session.number)
        if is_finished:
            self.assertIn("Поздравляем", result)
        else:
            self.assertIn("Больше" if session.number > session.number else "Меньше", result)
    
    def test_squid_game_session(self):
        """Тест игры 'Кальмар'"""
        session = games.SquidGameSession()
        self.assertEqual(len(session.players), 0)
        self.assertFalse(session.started)
        
        # Тест добавления игрока
        result = session.add_player(123)
        self.assertIn("добавлен", result)
        self.assertEqual(len(session.players), 1)
        
        # Тест начала игры
        result = session.start_game()
        self.assertIn("началась", result)
        self.assertTrue(session.started)
    
    def test_quiz_session(self):
        """Тест викторины"""
        session = games.QuizSession()
        self.assertEqual(len(session.players), 0)
        self.assertFalse(session.started)
        
        # Тест добавления игрока
        result = session.add_player(123)
        self.assertIn("добавлен", result)
        self.assertEqual(len(session.players), 1)
        self.assertEqual(session.scores[123], 0)
    
    def test_mafia_session(self):
        """Тест игры 'Мафия'"""
        session = games.MafiaSession()
        self.assertEqual(len(session.players), 0)
        self.assertEqual(session.phase, "waiting")
        
        # Тест добавления игрока
        result = session.add_player(123)
        self.assertIn("добавлен", result)
        self.assertEqual(len(session.players), 1)
        
        # Тест начала игры
        result = session.start_game()
        self.assertIn("началась", result)
        self.assertTrue(session.started)
        self.assertEqual(session.phase, "night")

# ---------- Тесты Content модуля ----------
class TestContentModule(unittest.TestCase):
    """Тесты для Content модуля"""
    
    def test_user_wallet(self):
        """Тест кошелька пользователя"""
        wallet = content.UserWallet(user_id=123)
        self.assertEqual(wallet.user_id, 123)
        self.assertEqual(wallet.balance, 0.0)
        self.assertEqual(wallet.currency, "RUB")
        
        # Тест добавления средств
        wallet.add_funds(100.0)
        self.assertEqual(wallet.balance, 100.0)
        
        # Тест траты средств
        self.assertTrue(wallet.spend_funds(50.0))
        self.assertEqual(wallet.balance, 50.0)
        
        # Тест недостатка средств
        self.assertFalse(wallet.spend_funds(100.0))
        self.assertEqual(wallet.balance, 50.0)
    
    def test_ai_booster(self):
        """Тест AI бустера"""
        booster = content.AIBooster(
            id="test_boost",
            name="Test Boost",
            description="Test description",
            price=50.0,
            effects={"max_tokens_multiplier": 2.0}
        )
        self.assertEqual(booster.id, "test_boost")
        self.assertEqual(booster.price, 50.0)
        self.assertIn("max_tokens_multiplier", booster.effects)
        
        effects_desc = booster.get_effects_description()
        self.assertIn("Токены x2.0", effects_desc)
    
    def test_daily_task(self):
        """Тест ежедневного задания"""
        task = content.DailyTask(
            id="test_task",
            name="Test Task",
            description="Test description",
            type="test",
            target_value=5,
            reward=10.0
        )
        self.assertEqual(task.id, "test_task")
        self.assertEqual(task.target_value, 5)
        self.assertEqual(task.reward, 10.0)
        
        progress = task.get_progress_text(3)
        self.assertIn("3/5", progress)
        self.assertIn("60.0%", progress)
    
    def test_booster_shop(self):
        """Тест магазина бустеров"""
        boosters = content.BoosterShop.list_boosters()
        self.assertGreater(len(boosters), 0)
        
        # Проверяем наличие основных бустеров
        booster_names = [b.name for b in boosters]
        self.assertIn("Fast Lane", booster_names)
        self.assertIn("Token Boost", booster_names)
        self.assertIn("Speed Boost", booster_names)
        self.assertIn("Quality Boost", booster_names)
    
    def test_daily_tasks(self):
        """Тест ежедневных заданий"""
        tasks = content.DailyTasks.list_tasks()
        self.assertGreater(len(tasks), 0)
        
        # Проверяем наличие основных заданий
        task_names = [t.name for t in tasks]
        self.assertIn("AI Чат x5", task_names)
        self.assertIn("Игрок", task_names)
        self.assertIn("Ежедневный вход", task_names)

# ---------- Тесты Streaming модуля ----------
class TestStreamingModule(unittest.TestCase):
    """Тесты для Streaming модуля"""
    
    def test_indicator_type(self):
        """Тест типов индикаторов"""
        self.assertEqual(streaming.IndicatorType.TYPING.value, "typing")
        self.assertEqual(streaming.IndicatorType.THINKING.value, "thinking")
        self.assertEqual(streaming.IndicatorType.PROCESSING.value, "processing")
        self.assertEqual(streaming.IndicatorType.GENERATING.value, "generating")
        self.assertEqual(streaming.IndicatorType.COMPLETED.value, "completed")
        self.assertEqual(streaming.IndicatorType.ERROR.value, "error")
    
    def test_streaming_indicator(self):
        """Тест индикатора стриминга"""
        indicator = streaming.StreamingIndicator(
            type=streaming.IndicatorType.TYPING,
            message="Test message",
            emoji="🧪"
        )
        self.assertEqual(indicator.message, "Test message")
        self.assertEqual(indicator.emoji, "🧪")
        self.assertFalse(indicator.is_active)
        
        # Тест запуска
        indicator.start()
        self.assertTrue(indicator.is_active)
        self.assertGreater(indicator.start_time, 0)
        
        # Тест остановки
        indicator.stop()
        self.assertFalse(indicator.is_active)
        self.assertGreater(indicator.duration, 0)
    
    def test_indicator_manager(self):
        """Тест менеджера индикаторов"""
        manager = streaming.IndicatorManager()
        session_id = "test_session"
        
        # Тест запуска индикатора
        result = manager.start_indicator(session_id, streaming.IndicatorType.TYPING)
        self.assertIn("набирает текст", result)
        self.assertTrue(manager.is_indicator_active(session_id))
        
        # Тест обновления индикатора
        result = manager.update_indicator(session_id, streaming.IndicatorType.THINKING)
        self.assertIn("думает", result)
        
        # Тест остановки индикатора
        result = manager.stop_indicator(session_id)
        self.assertIn("думает", result)
        self.assertFalse(manager.is_indicator_active(session_id))

# ---------- Тесты Utils модуля ----------
class TestUtilsModule(unittest.TestCase):
    """Тесты для Utils модуля"""
    
    def test_validation_functions(self):
        """Тест функций валидации"""
        # Email валидация
        self.assertTrue(utils.validate_email("test@example.com"))
        self.assertFalse(utils.validate_email("invalid-email"))
        
        # Phone валидация
        self.assertTrue(utils.validate_phone("+7 999 123-45-67"))
        self.assertFalse(utils.validate_phone("123"))
        
        # JSON валидация
        self.assertTrue(utils.validate_json('{"key": "value"}'))
        self.assertFalse(utils.validate_json('invalid json'))
    
    def test_text_utilities(self):
        """Тест текстовых утилит"""
        # Санитизация текста
        dirty_text = "<script>alert('xss')</script>   много   пробелов"
        clean_text = utils.sanitize_text(dirty_text)
        self.assertNotIn("<script>", clean_text)
        self.assertNotIn("   ", clean_text)
        
        # Обрезка текста
        long_text = "Это очень длинный текст для тестирования обрезки"
        truncated = utils.truncate_text(long_text, 20)
        self.assertLessEqual(len(truncated), 20)
        self.assertIn("...", truncated)
        
        # Подсчет слов
        word_count = utils.count_words("Это тестовый текст")
        self.assertEqual(word_count, 3)
        
        # Подсчет символов
        char_count = utils.count_characters("Тест", include_spaces=False)
        self.assertEqual(char_count, 4)
    
    def test_hash_functions(self):
        """Тест функций хеширования"""
        test_data = "test_string"
        
        # MD5
        md5_hash = utils.generate_hash(test_data, "md5")
        self.assertEqual(len(md5_hash), 32)
        self.assertTrue(utils.verify_hash(test_data, md5_hash, "md5"))
        
        # SHA256
        sha256_hash = utils.generate_hash(test_data, "sha256")
        self.assertEqual(len(sha256_hash), 64)
        self.assertTrue(utils.verify_hash(test_data, sha256_hash, "sha256"))
    
    def test_time_utilities(self):
        """Тест временных утилит"""
        now = time.time()
        
        # Форматирование timestamp
        formatted = utils.format_timestamp(now)
        self.assertIsInstance(formatted, str)
        
        # Проверка недавности
        self.assertTrue(utils.is_recent(now, 3600))
        self.assertFalse(utils.is_recent(now - 7200, 3600))
        
        # Время назад
        time_ago = utils.get_time_ago(now - 300)  # 5 минут назад
        self.assertIn("мин назад", time_ago)
    
    def test_simple_cache(self):
        """Тест простого кэша"""
        cache = utils.SimpleCache(max_size=2, ttl=1)
        
        # Тест установки и получения
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # Тест переполнения
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        self.assertIsNone(cache.get("key1"))  # Должен быть удален
        
        # Тест TTL
        cache.set("key4", "value4")
        time.sleep(1.1)  # Ждем истечения TTL
        self.assertIsNone(cache.get("key4"))
    
    def test_rate_limiter(self):
        """Тест rate limiter"""
        limiter = utils.RateLimiter(max_requests=2, window=60)
        
        # Первые два запроса должны пройти
        self.assertTrue(limiter.is_allowed("user1"))
        self.assertTrue(limiter.is_allowed("user1"))
        
        # Третий должен быть заблокирован
        self.assertFalse(limiter.is_allowed("user1"))
        
        # Сброс
        limiter.reset("user1")
        self.assertTrue(limiter.is_allowed("user1"))

# ---------- Тесты Config модуля ----------
class TestConfigModule(unittest.TestCase):
    """Тесты для Config модуля"""
    
    def test_bot_config_defaults(self):
        """Тест значений по умолчанию конфигурации"""
        config = config.BotConfig()
        self.assertEqual(config.bot_name, "CryCat Bot")
        self.assertEqual(config.bot_version, "2.0.0")
        self.assertEqual(config.ai_provider, "AUTO")
        self.assertEqual(config.runtime_temperature, 0.6)
        self.assertEqual(config.runtime_max_tokens_or, 80)
        self.assertTrue(config.games_enabled)
        self.assertTrue(config.monitoring_enabled)
    
    def test_config_to_dict(self):
        """Тест конвертации конфигурации в словарь"""
        config_instance = config.BotConfig()
        config_dict = config_instance.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn("bot_name", config_dict)
        self.assertIn("ai_provider", config_dict)
        self.assertIn("runtime_temperature", config_dict)
        self.assertIn("games_enabled", config_dict)
    
    def test_config_from_dict(self):
        """Тест загрузки конфигурации из словаря"""
        config_instance = config.BotConfig()
        test_data = {
            "bot_name": "Test Bot",
            "runtime_temperature": 1.0,
            "games_enabled": False
        }
        
        config_instance.from_dict(test_data)
        self.assertEqual(config_instance.bot_name, "Test Bot")
        self.assertEqual(config_instance.runtime_temperature, 1.0)
        self.assertFalse(config_instance.games_enabled)
    
    def test_config_validation(self):
        """Тест валидации конфигурации"""
        # Валидная конфигурация
        valid_config = config.BotConfig()
        valid_config.vk_group_token = "test_token"
        valid_config.vk_group_id = 123
        valid_config.admin_user_ids = [456]
        
        errors = config.validate_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # Невалидная конфигурация
        invalid_config = config.BotConfig()
        errors = config.validate_config(invalid_config)
        self.assertGreater(len(errors), 0)
        self.assertIn("VK_GROUP_TOKEN is required", errors)
        self.assertIn("VK_GROUP_ID must be positive", errors)
        self.assertIn("At least one admin user ID must be specified", errors)

# ---------- Основная функция запуска тестов ----------
def run_all_tests():
    """Запускает все тесты"""
    # Создаем test suite
    test_suite = unittest.TestSuite()
    
    # Добавляем тесты для каждого модуля
    test_classes = [
        TestAIModule,
        TestAdminModule,
        TestMonitoringModule,
        TestGamesModule,
        TestContentModule,
        TestStreamingModule,
        TestUtilsModule,
        TestConfigModule
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Возвращаем результат
    return result.wasSuccessful()

if __name__ == "__main__":
    print("🧪 Запуск unit тестов для CryCat Bot v2.0.0...")
    print("=" * 60)
    
    success = run_all_tests()
    
    print("=" * 60)
    if success:
        print("✅ Все тесты прошли успешно!")
    else:
        print("❌ Некоторые тесты не прошли!")
    
    print(f"Статус: {'УСПЕХ' if success else 'ОШИБКА'}")