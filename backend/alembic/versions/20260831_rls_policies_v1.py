"""rls_policies_v1

Revision ID: 20260831_rls_v1
Revises: 20260830_uuid_cutover
Create Date: 2026-08-31
"""
from alembic import op

revision = "20260831_rls_policies_v1"
down_revision = "20260829_fk_indexes"
branch_labels = None
depends_on = None

ALL_TABLES = [
    "profiles", "tickets", "routes", "route_stops", "locations",
    "vehicles", "incidents", "bookings", "route_jobs", "idempotency_keys",
]

def upgrade():
    # 1) Bật RLS cho toàn bộ 10 bảng
    for t in ALL_TABLES:
        op.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE "{t}" FORCE ROW LEVEL SECURITY;')  # áp cả cho owner khi query qua PostgREST/API role

    # ---- profiles ----
    op.execute("""
        CREATE POLICY profiles_select_own ON profiles
        FOR SELECT TO authenticated
        USING (id = auth.uid());
    """)
    op.execute("""
        CREATE POLICY profiles_update_own ON profiles
        FOR UPDATE TO authenticated
        USING (id = auth.uid())
        WITH CHECK (id = auth.uid());
    """)
    # Chặn sửa role/id ở cấp quyền cột, không dựa vào RLS
    op.execute('REVOKE UPDATE ON profiles FROM authenticated;')
    op.execute('GRANT UPDATE (full_name, phone) ON profiles TO authenticated;')

    # ---- tickets ----
    op.execute("""
        CREATE POLICY tickets_select_own ON tickets
        FOR SELECT TO authenticated
        USING (user_id = auth.uid());
    """)
    # Không cấp INSERT/UPDATE/DELETE cho authenticated -> mọi write qua backend (service role)

    # ---- routes ----
    op.execute("""
        CREATE POLICY routes_select_assigned ON routes
        FOR SELECT TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM tickets t
                WHERE t.route_id = routes.id
                  AND t.user_id = auth.uid()
                  AND t.status = 'assigned'
            )
            OR EXISTS (
                SELECT 1 FROM vehicles v
                WHERE v.id = routes.vehicle_id
                  AND v.driver_id = auth.uid()
            )
        );
    """)

    # ---- route_stops ----
    op.execute("""
        CREATE POLICY route_stops_select_assigned ON route_stops
        FOR SELECT TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM routes r
                WHERE r.id = route_stops.route_id
                  AND (
                      EXISTS (
                          SELECT 1 FROM tickets t
                          WHERE t.route_id = r.id
                            AND t.user_id = auth.uid()
                            AND t.status = 'assigned'
                      )
                      OR EXISTS (
                          SELECT 1 FROM vehicles v
                          WHERE v.id = r.vehicle_id
                            AND v.driver_id = auth.uid()
                      )
                  )
            )
        );
    """)

    # ---- locations ----
    op.execute("""
        CREATE POLICY locations_select_all ON locations
        FOR SELECT TO authenticated
        USING (true);
    """)

    # ---- vehicles ----
    op.execute("""
        CREATE POLICY vehicles_select_own_driver ON vehicles
        FOR SELECT TO authenticated
        USING (driver_id = auth.uid());
    """)
    # Nếu admin cần đọc thêm: thêm policy riêng dựa vào profiles.role = 'admin', ví dụ:
    op.execute("""
        CREATE POLICY vehicles_select_admin ON vehicles
        FOR SELECT TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM profiles p
                WHERE p.id = auth.uid() AND p.role = 'admin'
            )
        );
    """)

    # ---- incidents ----
    op.execute("""
        CREATE POLICY incidents_select_own_driver ON incidents
        FOR SELECT TO authenticated
        USING (driver_id = auth.uid());
    """)
    op.execute("""
        CREATE POLICY incidents_insert_own_driver ON incidents
        FOR INSERT TO authenticated
        WITH CHECK (driver_id = auth.uid());
    """)
    # Không cấp UPDATE -> workflow status do backend/admin quản lý

    # bookings, route_jobs, idempotency_keys: RLS bật, KHÔNG tạo policy nào -> mặc định deny hết cho client


def downgrade():
    policies = {
        "profiles": ["profiles_select_own", "profiles_update_own"],
        "tickets": ["tickets_select_own"],
        "routes": ["routes_select_assigned"],
        "route_stops": ["route_stops_select_assigned"],
        "locations": ["locations_select_all"],
        "vehicles": ["vehicles_select_own_driver", "vehicles_select_admin"],
        "incidents": ["incidents_select_own_driver", "incidents_insert_own_driver"],
    }
    for table, names in policies.items():
        for name in names:
            op.execute(f'DROP POLICY IF EXISTS "{name}" ON "{table}";')

    op.execute('REVOKE UPDATE ON profiles FROM authenticated;')
    # (nếu cần khôi phục full UPDATE trước RLS thì GRANT lại ở đây theo trạng thái cũ)

    for t in ALL_TABLES:
        op.execute(f'ALTER TABLE "{t}" NO FORCE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY;')