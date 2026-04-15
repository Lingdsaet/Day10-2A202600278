"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v..
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc trường `latest_exported_at` hoặc max exported_at trong cleaned summary.
    Thiết kế mở rộng: Đo freshness ở 2 boundary (Ingest Data và Publish Pipeline).
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    # Boundary 1: Source/Ingest Freshness
    export_ts = data.get("latest_exported_at")
    export_dt = parse_iso(str(export_ts)) if export_ts else None
    
    # Boundary 2: Pipeline Publish Freshness
    run_ts = data.get("run_timestamp")
    run_dt = parse_iso(str(run_ts)) if run_ts else None

    if export_dt is None and run_dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}

    dt_to_check = export_dt or run_dt
    age_hours = (now - dt_to_check).total_seconds() / 3600.0
    
    detail = {
        "latest_exported_at": export_ts,
        "run_timestamp": run_ts,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    
    # Bonus: So sánh clock batch và tính khoảng thời gian Ingest -> Publish
    if export_dt and run_dt:
        ingest_publish_lag = (run_dt - export_dt).total_seconds() / 3600.0
        detail["ingest_to_publish_lag_hours"] = round(ingest_publish_lag, 3)
        publish_age = (now - run_dt).total_seconds() / 3600.0
        detail["publish_age_hours"] = round(publish_age, 3)

    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}
