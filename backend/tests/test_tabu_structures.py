import sys
import os
# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tabu_structures import SwapMove, TwoOptMove, TabuList

def test_swap_move_apply():
    route = [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    
    # Hoán đổi chỉ số 1 và 3 (id: 1 và id: 3)
    move = SwapMove(1, 3)
    new_route = move.apply(route)
    
    # Kiểm tra xem route gốc không bị thay đổi
    assert route == [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    # Kiểm tra route mới
    assert new_route == [{"id": 0}, {"id": 3}, {"id": 2}, {"id": 1}, {"id": 4}]


def test_swap_move_tabu_key():
    move1 = SwapMove(1, 3)
    move2 = SwapMove(3, 1)
    
    # Khóa tabu phải có tính đối xứng
    assert move1.tabu_key() == move2.tabu_key()
    assert move1.tabu_key() == ("swap", 1, 3)


def test_two_opt_move_apply():
    route = [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    
    # Đảo ngược đoạn từ 1 đến 3 (tức là 1, 2, 3) -> kết quả: 0, 3, 2, 1, 4
    move = TwoOptMove(1, 3)
    new_route = move.apply(route)
    
    assert route == [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    assert new_route == [{"id": 0}, {"id": 3}, {"id": 2}, {"id": 1}, {"id": 4}]
    
    # Test với toàn bộ route
    move_all = TwoOptMove(0, 4)
    new_route_all = move_all.apply(route)
    assert new_route_all == [{"id": 4}, {"id": 3}, {"id": 2}, {"id": 1}, {"id": 0}]


def test_two_opt_move_tabu_key():
    move1 = TwoOptMove(1, 4)
    move2 = TwoOptMove(4, 1)
    
    assert move1.tabu_key() == move2.tabu_key()
    assert move1.tabu_key() == ("two_opt", 1, 4)


def test_tabu_list_behavior():
    tabu_list = TabuList(tenure=5)
    
    move = SwapMove(1, 2)
    
    # 1. Ban đầu không cấm
    assert not tabu_list.is_tabu(move, current_iteration=0, candidate_cost=100.0, best_cost=90.0)
    
    # 2. Thêm vào tabu tại iteration=0. Sẽ hết hạn tại iteration=5.
    tabu_list.add_move(move, current_iteration=0)
    
    # Bị cấm tại iteration=1, 2, 3, 4
    assert tabu_list.is_tabu(move, current_iteration=1, candidate_cost=100.0, best_cost=90.0)
    assert tabu_list.is_tabu(move, current_iteration=4, candidate_cost=100.0, best_cost=90.0)
    
    # Hết hạn tại iteration=5
    assert not tabu_list.is_tabu(move, current_iteration=5, candidate_cost=100.0, best_cost=90.0)


def test_tabu_list_aspiration_criteria():
    tabu_list = TabuList(tenure=5)
    move = SwapMove(1, 2)
    
    tabu_list.add_move(move, current_iteration=0)
    
    # Nước đi bị cấm nếu chi phí ứng cử viên tệ hơn best_cost (95.0 > 90.0)
    assert tabu_list.is_tabu(move, current_iteration=2, candidate_cost=95.0, best_cost=90.0)
    
    # Nước đi KHÔNG BỊ CẤM (Aspiration Criteria) nếu chi phí ứng cử viên tốt hơn best_cost (85.0 < 90.0)
    assert not tabu_list.is_tabu(move, current_iteration=2, candidate_cost=85.0, best_cost=90.0)
