# ── Fixed 4 Sessions ──────────────────────────────────────────────────
PICKUP_SESSIONS = {
    "MORNING_1": {"id": "MORNING_1", "school_start": "07:00", "vehicle_depart_latest": "05:30"},
    "MORNING_2": {"id": "MORNING_2", "school_start": "08:30", "vehicle_depart_latest": "07:00"},
}

DROPOFF_SESSIONS = {
    "NOON_1": {"id": "NOON_1", "school_end": "10:00", "vehicle_depart_after": "10:10"},
    "NOON_2": {"id": "NOON_2", "school_end": "11:30", "vehicle_depart_after": "11:40"},
}

# ── Operating Parameters ──────────────────────────────────────────────
VEHICLE_CAPACITY         = 45       # Default bus seats
MAX_SERVICE_RADIUS_KM    = 10.0     # Maximum distance from CTU campus
BUFFER_MINUTES           = 15       # Safety arrival buffer before school start
BOARDING_AT_SCHOOL_MIN   = 10       # Boarding time at CTU campus for dropoff
MAX_RIDE_TIME_MINUTES    = 45       # Hard constraint: max time student stays on bus

# ── Speed by Time of Day (km/h) ───────────────────────────────────────
SPEED_MORNING_PEAK_KMH   = 25.0     # Morning peak (06:30 - 08:30)
SPEED_NOON_PEAK_KMH      = 28.0     # Noon peak (11:00 - 13:00)
SPEED_NORMAL_KMH         = 30.0     # Normal traffic speed

# ── OSRM & Matrix Settings ─────────────────────────────────────────────
OSRM_PUBLIC_URL          = "http://router.project-osrm.org/table/v1/driving/"
OSRM_TIMEOUT_SECONDS     = 3.0      # 3 seconds fallback trigger
TRAFFIC_CACHE_TTL        = 300      # 5 minutes

# ── Objective Function Weights & Penalties ────────────────────────────
DISTANCE_WEIGHT          = 1.0
EARLY_PENALTY_WEIGHT     = 0.5
LATE_PENALTY_WEIGHT      = 10.0     # Late penalty > Early penalty
CAPACITY_PENALTY_WEIGHT  = 1000.0   # Large penalty for capacity violation
RIDE_TIME_PENALTY_WEIGHT = 10000.0  # Large penalty for ride time violation

# ── Tabu Search Parameters ─────────────────────────────────────────────
TABU_MAX_ITERATIONS      = 300
TABU_TENURE_BASE         = 10
EARLY_STOPPING_ROUNDS    = 30
DIVERSIFY_ROUNDS         = 15

# ── School Location (CTU Main Campus) ──────────────────────────────────
SCHOOL_LOCATION          = {"lat": 10.0302, "lng": 105.7721}
SCHOOL_NAME              = "Trường Đại học Cần Thơ"
