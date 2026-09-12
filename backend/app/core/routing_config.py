from pydantic import BaseModel
from typing import List, Optional

class LocationConfig(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    is_depot: bool = False
    note: Optional[str] = None

class VehicleConfig(BaseModel):
    id: str
    capacity: int
    is_backup: bool = False

class RoutingRules(BaseModel):
    max_duration_minutes: int = 90
    service_time_seconds: int = 120
    capacity_limit: int = 45

# Depot Configuration
DEPOT = LocationConfig(
    id="D0", 
    name="Đại học Cần Thơ (Khu II)", 
    lat=10.029933, 
    lng=105.770615, 
    is_depot=True,
    note="Điểm đầu/cuối của mọi tuyến"
)

# 20 Stations Configuration
STATIONS: List[LocationConfig] = [
    LocationConfig(id="S01", name="Vincom Hùng Vương", lat=10.040212, lng=105.779765),
    LocationConfig(id="S02", name="Bến Ninh Kiều", lat=10.033580, lng=105.787654),
    LocationConfig(id="S03", name="Co.opmart Cần Thơ", lat=10.035412, lng=105.781210),
    LocationConfig(id="S04", name="Chợ Nổi Cái Răng", lat=10.003112, lng=105.744112),
    LocationConfig(id="S05", name="Bến xe TT Cần Thơ", lat=10.006240, lng=105.759240),
    LocationConfig(id="S06", name="BV Đa khoa Trung Ương", lat=10.016301, lng=105.761044),
    LocationConfig(id="S07", name="Lotte Mart Cần Thơ", lat=10.037144, lng=105.771212),
    LocationConfig(id="S08", name="Đại học Y Dược Cần Thơ", lat=10.028912, lng=105.759321),
    LocationConfig(id="S09", name="Sân bay Quốc tế Cần Thơ", lat=10.082512, lng=105.711822),
    LocationConfig(id="S10", name="Chợ Bình Thủy", lat=10.063124, lng=105.741221),
    LocationConfig(id="S11", name="Cao đẳng Y tế Cần Thơ", lat=10.031555, lng=105.767223),
    LocationConfig(id="S12", name="Chợ Xuân Khánh", lat=10.024567, lng=105.772545),
    LocationConfig(id="S13", name="Công viên Lưu Hữu Phước", lat=10.034512, lng=105.782412),
    LocationConfig(id="S14", name="Vincom Xuân Khánh", lat=10.026412, lng=105.776011),
    LocationConfig(id="S15", name="Big C (GO!) Cần Thơ", lat=10.009412, lng=105.764512),
    LocationConfig(id="S16", name="Chợ An Thới", lat=10.051212, lng=105.760012),
    LocationConfig(id="S17", name="KDC Hồng Phát", lat=10.017812, lng=105.748312),
    LocationConfig(id="S18", name="KDC 91B", lat=10.022412, lng=105.759412),
    LocationConfig(id="S19", name="Cao đẳng Cần Thơ", lat=10.020512, lng=105.763212),
    LocationConfig(id="S20", name="Chợ An Nghiệp", lat=10.038112, lng=105.772112),
]

# Vehicle Configuration
VEHICLES: List[VehicleConfig] = [
    VehicleConfig(id="V1", capacity=45),
    VehicleConfig(id="V2", capacity=45),
    VehicleConfig(id="V3", capacity=45, is_backup=True),
]

# Shifts Configuration
SHIFTS_TO_DEPOT = ["07:00", "08:30"]
SHIFTS_FROM_DEPOT = ["10:00", "11:30"]

# Routing Rules Configuration
ROUTING_RULES = RoutingRules()

def get_station_by_id(station_id: str) -> Optional[LocationConfig]:
    if station_id == DEPOT.id:
        return DEPOT
    for station in STATIONS:
        if station.id == station_id:
            return station
    return None
