from enum import Enum
from typing import Union
from app.services.student_routing import config


class TrafficPeriod(str, Enum):
    MORNING_PEAK = "MORNING_PEAK"
    NOON_PEAK = "NOON_PEAK"
    NORMAL = "NORMAL"


class PathFlexibilityManager:
    """
    Quản lý khung giờ và phân tích điều kiện giao thông (Time-of-day Traffic Conditions).
    Cung cấp vận tốc di chuyển trung bình theo khung giờ mà không can thiệp trực tiếp vào distance matrix calculations.
    """

    @staticmethod
    def get_traffic_period(time_str_or_session: str) -> TrafficPeriod:
        """
        Xác định TrafficPeriod dựa trên Session ID (vd: 'MORNING_1') hoặc chuỗi giờ 'HH:MM'.
        """
        if time_str_or_session in ["MORNING_1", "MORNING_2"]:
            return TrafficPeriod.MORNING_PEAK
        if time_str_or_session in ["NOON_1", "NOON_2"]:
            return TrafficPeriod.NOON_PEAK

        # Thử parse chuỗi HH:MM
        try:
            parts = time_str_or_session.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            time_mins = hour * 60 + minute

            # Morning peak: 06:30 (390) - 08:30 (510)
            if 390 <= time_mins <= 510:
                return TrafficPeriod.MORNING_PEAK
            # Noon peak: 11:00 (660) - 13:00 (780)
            elif 660 <= time_mins <= 780:
                return TrafficPeriod.NOON_PEAK
            else:
                return TrafficPeriod.NORMAL
        except Exception:
            return TrafficPeriod.NORMAL

    @classmethod
    def get_average_speed_kmh(cls, time_str_or_session: str) -> float:
        """
        Trả về vận tốc trung bình (km/h) theo khung giờ.
        """
        period = cls.get_traffic_period(time_str_or_session)
        if period == TrafficPeriod.MORNING_PEAK:
            return config.SPEED_MORNING_PEAK_KMH
        elif period == TrafficPeriod.NOON_PEAK:
            return config.SPEED_NOON_PEAK_KMH
        else:
            return config.SPEED_NORMAL_KMH
