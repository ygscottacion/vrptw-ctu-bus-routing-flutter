from datetime import datetime, timedelta, timezone

from app.crud import crud_route_matrix_cache
from app.models.route_matrix_cache import RouteMatrixCache
from app.schemas.route_matrix_cache import RouteMatrixCacheCreate


def test_generate_cache_key_rounds_sub_meter_jitter():
    """Cùng cặp điểm lệch < 1m sau round 5 decimals phải ra cùng cache_key."""
    key_a = RouteMatrixCache.generate_cache_key(
        10.034156, 105.768401, 10.029901, 105.770001, "DRIVE"
    )
    key_b = RouteMatrixCache.generate_cache_key(
        10.03416, 105.76840, 10.02990, 105.77000, "drive"
    )
    assert key_a == key_b
    assert len(key_a) == 64


def test_generate_cache_key_differs_by_travel_mode():
    kwargs = dict(
        origin_lat=10.03416,
        origin_lng=105.76840,
        dest_lat=10.02990,
        dest_lng=105.77000,
    )
    drive = RouteMatrixCache.generate_cache_key(**kwargs, travel_mode="DRIVE")
    transit = RouteMatrixCache.generate_cache_key(**kwargs, travel_mode="TRANSIT")
    assert drive != transit


def test_upsert_bulk_matrix_inserts_new_records(db_session):
    records = [
        RouteMatrixCacheCreate(
            origin_lat=10.034156,
            origin_lng=105.768401,
            dest_lat=10.029901,
            dest_lng=105.770001,
            distance_km=2.4,
            duration_mins=8.5,
            provider="GOOGLE_ROUTES",
        ),
        RouteMatrixCacheCreate(
            origin_lat=10.02990,
            origin_lng=105.77000,
            dest_lat=10.03416,
            dest_lng=105.76840,
            distance_km=2.5,
            duration_mins=9.0,
            provider="OSRM",
        ),
    ]

    written = crud_route_matrix_cache.upsert_bulk_matrix(db_session, records)
    assert written == 2

    cache_key = RouteMatrixCache.generate_cache_key(
        10.03416, 105.76840, 10.02990, 105.77000, "DRIVE"
    )
    row = crud_route_matrix_cache.get_by_key(db_session, cache_key)
    assert row is not None
    assert row.distance_km == 2.4
    assert row.duration_mins == 8.5
    assert row.provider == "GOOGLE_ROUTES"
    assert float(row.origin_lat) == 10.03416
    assert float(row.origin_lng) == 105.76840


def test_upsert_bulk_matrix_updates_on_conflict(db_session):
    first = [
        RouteMatrixCacheCreate(
            origin_lat=10.03,
            origin_lng=105.77,
            dest_lat=10.04,
            dest_lng=105.78,
            distance_km=1.0,
            duration_mins=3.0,
        )
    ]
    crud_route_matrix_cache.upsert_bulk_matrix(db_session, first)

    updated = [
        RouteMatrixCacheCreate(
            origin_lat=10.03,
            origin_lng=105.77,
            dest_lat=10.04,
            dest_lng=105.78,
            distance_km=1.7,
            duration_mins=5.5,
            provider="OSRM",
        )
    ]
    crud_route_matrix_cache.upsert_bulk_matrix(db_session, updated)

    cache_key = RouteMatrixCache.generate_cache_key(10.03, 105.77, 10.04, 105.78)
    row = crud_route_matrix_cache.get_by_key(db_session, cache_key)
    assert row is not None
    assert row.distance_km == 1.7
    assert row.duration_mins == 5.5
    assert row.provider == "OSRM"
    assert db_session.query(RouteMatrixCache).count() == 1


def test_get_bulk_matrix_returns_cached_pairs(db_session):
    records = [
        RouteMatrixCacheCreate(
            origin_lat=10.01,
            origin_lng=105.76,
            dest_lat=10.02,
            dest_lng=105.77,
            distance_km=3.1,
            duration_mins=10.0,
        ),
        RouteMatrixCacheCreate(
            origin_lat=10.02,
            origin_lng=105.77,
            dest_lat=10.03,
            dest_lng=105.78,
            distance_km=4.2,
            duration_mins=12.0,
        ),
    ]
    crud_route_matrix_cache.upsert_bulk_matrix(db_session, records)

    pairs = [
        ((10.010001, 105.760002), (10.020003, 105.770004)),
        ((10.02, 105.77), (10.03, 105.78)),
        ((10.99, 105.99), (10.88, 105.88)),
    ]
    hits = crud_route_matrix_cache.get_bulk_matrix(db_session, pairs, travel_mode="DRIVE")
    assert len(hits) == 2

    distances = sorted(row.distance_km for row in hits)
    assert distances == [3.1, 4.2]


def test_get_by_key_skips_expired_row(db_session):
    expired = RouteMatrixCacheCreate(
        origin_lat=10.10,
        origin_lng=105.10,
        dest_lat=10.20,
        dest_lng=105.20,
        distance_km=1.0,
        duration_mins=2.0,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    crud_route_matrix_cache.upsert_bulk_matrix(db_session, [expired])
    cache_key = RouteMatrixCache.generate_cache_key(10.10, 105.10, 10.20, 105.20)
    assert crud_route_matrix_cache.get_by_key(db_session, cache_key) is None
    assert crud_route_matrix_cache.get_bulk_matrix(
        db_session, [((10.10, 105.10), (10.20, 105.20))]
    ) == []
