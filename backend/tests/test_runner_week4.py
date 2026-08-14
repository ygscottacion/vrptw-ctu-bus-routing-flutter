import sys
import os

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_tabu_optimization import (
    test_early_stopping_behavior,
    test_diversification_behavior
)

if __name__ == "__main__":
    print("Running custom tests for Tabu Search local optima escape & convergence...")
    
    tests = [
        ("test_early_stopping_behavior", test_early_stopping_behavior),
        ("test_diversification_behavior", test_diversification_behavior)
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
