from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Hashable

class NeighborhoodMove(ABC):
    """
    Interface chung đại diện cho các bước di chuyển lân cận (Neighborhood Operations)
    """

    @abstractmethod
    def apply(self, route: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Áp dụng di chuyển này lên một lộ trình (bản danh sách điểm đón)
        và trả về một lộ trình mới (được sao chép mới, không chỉnh sửa trực tiếp lộ trình cũ).
        """
        pass

    @abstractmethod
    def tabu_key(self) -> Hashable:
        """
        Trả về giá trị đại diện cho nước đi để lưu trong Tabu List.
        Ví dụ: ("swap", 2, 5) hoặc ("two_opt", 1, 4)
        Lưu ý: Để chuẩn hóa, nước đi có tính đối xứng (như swap i,j và j,i) nên được sắp xếp
        để trả về cùng một khóa (ví dụ: luôn để chỉ số nhỏ hơn đứng trước).
        """
        pass


class SwapMove(NeighborhoodMove):
    """
    Phép toán hoán đổi (Swap): Hoán đổi vị trí của hai phần tử tại chỉ số i và j.
    """
    def __init__(self, i: int, j: int):
        self.i = min(i, j)
        self.j = max(i, j)

    def apply(self, route: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        new_route = list(route)
        new_route[self.i], new_route[self.j] = new_route[self.j], new_route[self.i]
        return new_route

    def tabu_key(self) -> Hashable:
        return ("swap", self.i, self.j)

    def __repr__(self) -> str:
        return f"SwapMove(i={self.i}, j={self.j})"


class TwoOptMove(NeighborhoodMove):
    """
    Phép toán 2-Opt: Đảo ngược đoạn lộ trình từ chỉ số i đến j (bao gồm cả i và j).
    Ví dụ: Lộ trình [A, B, C, D, E], 2-opt từ 1 đến 3 (B, C, D) -> [A, D, C, B, E].
    """
    def __init__(self, i: int, j: int):
        self.i = min(i, j)
        self.j = max(i, j)

    def apply(self, route: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        new_route = list(route)
        # Đảo ngược đoạn từ i đến j
        new_route[self.i:self.j+1] = list(reversed(new_route[self.i:self.j+1]))
        return new_route

    def tabu_key(self) -> Hashable:
        return ("two_opt", self.i, self.j)

    def __repr__(self) -> str:
        return f"TwoOptMove(i={self.i}, j={self.j})"


class TabuList:
    """
    Cấu trúc quản lý danh sách cấm (Tabu List) với Tenure và Aspiration Criteria.
    """
    def __init__(self, tenure: int):
        self.tenure = tenure
        # Lưu trữ move_key -> iteration_expired_at
        self.tabu_dict: Dict[Hashable, int] = {}

    def add_move(self, move: NeighborhoodMove, current_iteration: int) -> None:
        """
        Thêm một nước đi vào danh sách tabu, nước đi này sẽ hết hạn
        sau current_iteration + tenure.
        """
        key = move.tabu_key()
        self.tabu_dict[key] = current_iteration + self.tenure

    def is_tabu(
        self,
        move: NeighborhoodMove,
        current_iteration: int,
        candidate_cost: float,
        best_cost: float
    ) -> bool:
        """
        Kiểm tra xem nước đi có bị cấm tại vòng lặp hiện tại hay không.
        Aspiration Criteria (Tiêu chí khát vọng):
        Nếu nước đi mang lại giải pháp có chi phí tốt hơn giải pháp tốt nhất toàn cục (best_cost),
        thì cho phép thực hiện (không bị cấm), ngay cả khi nó nằm trong Tabu List.
        """
        key = move.tabu_key()
        expired_iteration = self.tabu_dict.get(key, 0)
        
        # Nếu chưa hết hạn tabu
        if expired_iteration > current_iteration:
            # Áp dụng Aspiration Criteria: nếu chi phí tốt hơn hẳn best_cost
            if candidate_cost < best_cost:
                return False
            return True
            
        return False

    def clear(self) -> None:
        """Xóa sạch danh sách tabu"""
        self.tabu_dict.clear()
