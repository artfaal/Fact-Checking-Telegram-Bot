#!/usr/bin/env python3
"""
Запуск всех тестов
"""

import asyncio
import subprocess
import sys
import os

def run_test(test_name):
    """Запуск отдельного теста"""
    print(f"\n{'='*50}")
    print(f"🧪 Запуск теста: {test_name}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run([
            sys.executable, 
            os.path.join('tests', f'{test_name}.py')
        ], check=True, capture_output=False)
        print(f"✅ Тест {test_name} завершен успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Тест {test_name} завершен с ошибкой: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка запуска теста {test_name}: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 Запуск всех тестов fact-checking бота")
    
    tests = [
        'test_config',
        'test_two_stage',
        'test_translation_formatting'
    ]
    
    results = {}
    
    for test in tests:
        test_file = os.path.join('tests', f'{test}.py')
        if os.path.exists(test_file):
            results[test] = run_test(test)
        else:
            print(f"⚠️ Тест {test} не найден, пропускаем")
            results[test] = None
    
    # Итоговый отчет
    print(f"\n{'='*50}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for test, result in results.items():
        if result is True:
            print(f"✅ {test}")
        elif result is False:
            print(f"❌ {test}")
        else:
            print(f"⚠️ {test} (пропущен)")
    
    print(f"\nВсего: {len(results)}")
    print(f"Успешно: {passed}")
    print(f"Ошибки: {failed}")
    print(f"Пропущено: {skipped}")
    
    if failed > 0:
        print(f"\n❌ Некоторые тесты завершились с ошибками")
        sys.exit(1)
    else:
        print(f"\n✅ Все тесты успешно завершены!")

if __name__ == "__main__":
    main()