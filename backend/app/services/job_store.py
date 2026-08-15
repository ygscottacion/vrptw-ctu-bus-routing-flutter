import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RouteGenerationJobStore:
    """
    Theo dõi trạng thái của các tác vụ sinh lộ trình VRPTW chạy bất đồng bộ qua
    fastapi.BackgroundTasks (Sweep + Tabu Search có thể mất vài giây với dữ liệu lớn).

    LƯU Ý: Đây là store trong bộ nhớ (in-memory) của một tiến trình (process).
    - Dữ liệu sẽ mất khi restart server.
    - KHÔNG được chia sẻ giữa nhiều worker process (vd: uvicorn --workers > 1 hoặc
      gunicorn nhiều worker). Nếu sau này scale ra nhiều worker/instance, cần thay
      bằng một store dùng chung (Redis, bảng DB riêng, Celery result backend, ...).
    Với quy mô hiện tại (1 worker) thì store này đủ dùng và đơn giản, không cần
    thêm migration DB mới.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, requested_by_user_id: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": JobStatus.PENDING,
                "requested_by_user_id": requested_by_user_id,
                "created_at": now,
                "updated_at": now,
                "route_ids": [],
                "error_message": None,
            }
        return job_id

    def mark_processing(self, job_id: str) -> None:
        self._update(job_id, status=JobStatus.PROCESSING)

    def mark_completed(self, job_id: str, route_ids: List[int]) -> None:
        self._update(job_id, status=JobStatus.COMPLETED, route_ids=route_ids)

    def mark_failed(self, job_id: str, error_message: str) -> None:
        self._update(job_id, status=JobStatus.FAILED, error_message=error_message)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def _update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.update(fields)
            job["updated_at"] = datetime.now(timezone.utc)


route_job_store = RouteGenerationJobStore()