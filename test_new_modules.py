#!/usr/bin/env python3
"""
Тест новых модулей CryBot
"""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_games():
    """Тест игровых модулей"""
    print("🎮 Тестирование игровых модулей...")
    
    try:
        from games_extended import conductor_game, hangman_manager, poker_manager
        
        # Тест Проводница РЖД
        print("  🚂 Проводница РЖД...")
        result = conductor_game.start_session(12345, 67890)
        print(f"    ✅ {result[:50]}...")
        
        # Тест Виселица
        print("  🎯 Виселица...")
        result = hangman_manager.start_game(12345)
        print(f"    ✅ {result[:50]}...")
        
        # Тест Покер
        print("  🃏 Покер...")
        result = poker_manager.create_game(12345, 67890, "Тестовый игрок")
        print(f"    ✅ {result[:50]}...")
        
        print("  🎉 Все игры работают!")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в играх: {e}")
        return False

def test_economy():
    """Тест экономического модуля"""
    print("💰 Тестирование экономики...")
    
    try:
        from economy_social import economy_manager, Currency
        
        # Тест кошелька
        print("  💳 Кошелёк...")
        wallet = economy_manager.get_wallet(12345)
        print(f"    ✅ Баланс: {wallet.balance.get(Currency.CRYCOIN, 0)} 🪙")
        
        # Тест ежедневного бонуса
        print("  🎁 Ежедневный бонус...")
        result = economy_manager.daily_bonus(12345)
        print(f"    ✅ {result[:50]}...")
        
        # Тест магазина
        print("  🛒 Магазин...")
        result = economy_manager.get_shop()
        print(f"    ✅ {result[:50]}...")
        
        print("  🎉 Экономика работает!")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в экономике: {e}")
        return False

def test_social():
    """Тест социального модуля"""
    print("👥 Тестирование социальных функций...")
    
    try:
        from economy_social import social_manager
        
        # Тест профиля
        print("  👤 Профиль...")
        profile = social_manager.get_profile(12345)
        print(f"    ✅ Профиль: {profile.name}")
        
        # Тест клана
        print("  🏰 Клан...")
        result = social_manager.create_clan(12345, "Тестовый клан", "Описание")
        print(f"    ✅ {result[:50]}...")
        
        print("  🎉 Социальные функции работают!")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в социальных функциях: {e}")
        return False

def test_cache_monitoring():
    """Тест кеширования и мониторинга"""
    print("⚡ Тестирование кеширования и мониторинга...")
    
    try:
        from cache_monitoring import cache_manager, monitoring_manager, logger
        
        # Тест кеша
        print("  💾 Кеш...")
        cache_manager.set("test_key", "test_value", ttl=60)
        value = cache_manager.get("test_key")
        print(f"    ✅ Кеш работает: {value}")
        
        # Тест мониторинга
        print("  📊 Мониторинг...")
        monitoring_manager.increment_counter("test_counter")
        monitoring_manager.set_gauge("test_gauge", 42.0)
        print(f"    ✅ Метрики работают")
        
        # Тест логгера
        print("  🔍 Логгер...")
        logger.info("Тестовое сообщение")
        print(f"    ✅ Логгер работает")
        
        print("  🎉 Кеширование и мониторинг работают!")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в кешировании/мониторинге: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 Тестирование новых модулей CryBot\n")
    
    tests = [
        test_games,
        test_economy,
        test_social,
        test_cache_monitoring
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Критическая ошибка в {test.__name__}: {e}")
            results.append(False)
        print()
    
    # Итоговый отчёт
    passed = sum(results)
    total = len(results)
    
    print("📊 Итоговый отчёт:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("⚠️ Некоторые тесты провалены")
        return 1

if __name__ == "__main__":
    sys.exit(main())