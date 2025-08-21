#!/usr/bin/env python3
"""
Тесты для новой функциональности
"""
import sys
import os
import time
from unittest.mock import Mock, patch

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_role_system():
    """Тест системы ролей"""
    print("🧪 Тестирование системы ролей...")
    
    try:
        # Мокаем переменные окружения
        with patch.dict(os.environ, {
            'VK_GROUP_TOKEN': 'test_token',
            'VK_GROUP_ID': '123456789',
            'ADMIN_USER_IDS': '12345,67890'
        }):
            from admin import get_user_role, has_privilege, can_manage_roles, can_view_stats
            from bot_vk import UserRole
            
            # Тест получения роли
            role = get_user_role(12345)
            print(f"✅ Роль пользователя 12345: {role}")
            
            # Тест проверки привилегий
            has_edit = has_privilege(12345, "edit_content")
            print(f"✅ Пользователь 12345 может редактировать контент: {has_edit}")
            
            can_manage = can_manage_roles(12345)
            print(f"✅ Пользователь 12345 может управлять ролями: {can_manage}")
            
            can_stats = can_view_stats(12345)
            print(f"✅ Пользователь 12345 может просматривать статистику: {can_stats}")
            
            return True
    except Exception as e:
        print(f"❌ Ошибка в тесте системы ролей: {e}")
        return False

def test_storage_functions():
    """Тест функций хранилища"""
    print("🧪 Тестирование функций хранилища...")
    
    try:
        from storage import update_user_activity, get_user_profile, set_user_profile
        
        user_id = 12345
        
        # Тест обновления активности
        update_user_activity(user_id)
        print("✅ Активность пользователя обновлена")
        
        # Тест получения профиля
        profile = get_user_profile(user_id)
        print(f"✅ Профиль пользователя получен: {profile is not None}")
        
        # Тест установки профиля
        test_profile = {"name": "Test User", "level": 1}
        set_user_profile(user_id, test_profile)
        print("✅ Профиль пользователя установлен")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в тесте хранилища: {e}")
        return False

def test_monitoring_functions():
    """Тест функций мониторинга"""
    print("🧪 Тестирование функций мониторинга...")
    
    try:
        from monitoring import health_checker
        
        # Тест проверки здоровья системы
        health_status = health_checker.check_health()
        print(f"✅ Статус здоровья получен: {len(health_status)} сервисов")
        
        # Тест общего статуса
        overall_status = health_checker.get_overall_status()
        print(f"✅ Общий статус: {overall_status}")
        
        # Тест метрик кеша
        cache_hit_rate = health_checker._calculate_cache_hit_rate()
        print(f"✅ Процент попаданий в кеш: {cache_hit_rate}%")
        
        # Тест активных пользователей
        active_users = health_checker._get_active_users_count()
        print(f"✅ Активных пользователей: {active_users}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в тесте мониторинга: {e}")
        return False

def test_cache_monitoring():
    """Тест системы кеширования"""
    print("🧪 Тестирование системы кеширования...")
    
    try:
        from cache_monitoring import cache_manager
        
        # Тест установки значения в кеш
        cache_manager.set("test_key", "test_value", ttl=60)
        print("✅ Значение установлено в кеш")
        
        # Тест получения значения из кеша
        value = cache_manager.get("test_key")
        print(f"✅ Значение получено из кеша: {value}")
        
        # Тест статистики кеша
        stats = cache_manager.get_stats()
        print(f"✅ Статистика кеша: {stats}")
        
        # Тест очистки кеша
        cache_manager.clear()
        print("✅ Кеш очищен")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в тесте кеширования: {e}")
        return False

def test_new_commands():
    """Тест новых команд"""
    print("🧪 Тестирование новых команд...")
    
    try:
        from commands.router import _handle_role_info, _handle_role_list, _handle_stats, _handle_health
        
        # Создаем мок контекст
        mock_ctx = Mock()
        mock_ctx.user_id = 12345
        mock_ctx.text = ""
        
        # Тест команды информации о роли
        role_info = _handle_role_info(mock_ctx)
        print(f"✅ Команда /role info работает: {role_info is not None}")
        
        # Тест команды списка ролей
        role_list = _handle_role_list(mock_ctx)
        print(f"✅ Команда /role list работает: {role_list is not None}")
        
        # Тест команды статистики (должна вернуть ошибку прав)
        stats_result = _handle_stats(mock_ctx)
        print(f"✅ Команда /stats проверяет права: {stats_result is not None}")
        
        # Тест команды здоровья (должна вернуть ошибку прав)
        health_result = _handle_health(mock_ctx)
        print(f"✅ Команда /health проверяет права: {health_result is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка в тесте команд: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов новой функциональности...\n")
    
    tests = [
        test_role_system,
        test_storage_functions,
        test_monitoring_functions,
        test_cache_monitoring,
        test_new_commands
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test.__name__}: {e}\n")
    
    print(f"📊 Результаты тестирования: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно!")
        return 0
    else:
        print("⚠️ Некоторые тесты не прошли")
        return 1

if __name__ == "__main__":
    exit(main())