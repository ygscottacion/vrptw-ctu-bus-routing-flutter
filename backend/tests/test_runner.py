import sys
import os

# Thêm thư mục cha (backend) vào đầu sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_tabu_structures import (
    test_swap_move_apply,
    test_swap_move_tabu_key,
    test_two_opt_move_apply,
    test_two_opt_move_tabu_key,
    test_tabu_list_behavior,
    test_tabu_list_aspiration_criteria
)

if __name__ == "__main__":
    print("Running custom unit tests for Tabu Search structures...")
    
    tests = [
        ("test_swap_move_apply", test_swap_move_apply),
        ("test_swap_move_tabu_key", test_swap_move_tabu_key),
        ("test_two_opt_move_apply", test_two_opt_move_apply),
        ("test_two_opt_move_tabu_key", test_two_opt_move_tabu_key),
        ("test_tabu_list_behavior", test_tabu_list_behavior),
        ("test_tabu_list_aspiration_criteria", test_tabu_list_aspiration_criteria),
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
