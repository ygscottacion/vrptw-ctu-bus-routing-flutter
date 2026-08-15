import sys
import os

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_fitness_function import (
    test_fitness_perfect_timing,
    test_fitness_waiting_time,
    test_fitness_lateness_penalty
)

if __name__ == "__main__":
    print("Running custom unit tests for VRPTW Fitness/Cost function...")
    
    tests = [
        ("test_fitness_perfect_timing", test_fitness_perfect_timing),
        ("test_fitness_waiting_time", test_fitness_waiting_time),
        ("test_fitness_lateness_penalty", test_fitness_lateness_penalty),
    ]
    
    failed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            print(f"  [FAIL] {name}: Assertion failed")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            failed += 1
            
    print(f"\nTest run finished. Failures/Errors: {failed}")
    sys.exit(failed)
