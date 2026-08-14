import sys
import os

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_tabu_perf import test_tabu_performance_and_optimality

if __name__ == "__main__":
    print("Running custom performance and optimality tests for Tabu Search...")
    
    try:
        test_tabu_performance_and_optimality()
        print("\n[PASS] test_tabu_performance_and_optimality")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] test_tabu_performance_and_optimality: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] test_tabu_performance_and_optimality: {e}")
        sys.exit(1)
