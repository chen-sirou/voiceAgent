import json
from pathlib import Path
from datetime import datetime


class VisitorRecordQuery:
    def __init__(self, path: str = "visitor_records.jsonl"):
        self.path = Path(path)

    def load_records(self) -> list[dict]:
        if not self.path.exists():
            return []

        records = []

        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except Exception:
                    continue

        return records

    def search(self, plan: dict) -> list[dict]:
        records = self.load_records()

        filters = plan.get("filters") or {}

        start_dt = self._parse_datetime(filters.get("start_datetime"))
        end_dt = self._parse_datetime(filters.get("end_datetime"))

        result = []

        for record in records:
            if not self._match_time(record, start_dt, end_dt):
                continue

            if not self._match_text(record, "plate_number", filters.get("plate_number")):
                continue

            if not self._match_text(record, "target_company", filters.get("target_company")):
                continue

            if not self._match_text(record, "phone", filters.get("phone")):
                continue

            if not self._match_text(record, "visit_reason", filters.get("visit_reason")):
                continue

            result.append(record)

        result.sort(
            key=lambda r: r.get("entry_time") or "",
            reverse=True
        )

        limit = plan.get("limit")

        if isinstance(limit, int) and limit > 0:
            return result[:limit]

        return result

    def _parse_datetime(self, value: str | None):
        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    def _match_time(self, record: dict, start_dt, end_dt) -> bool:
        entry_time = record.get("entry_time")

        if not entry_time:
            return False

        try:
            entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return False

        if start_dt and entry_dt < start_dt:
            return False

        if end_dt and entry_dt > end_dt:
            return False

        return True

    def _match_text(self, record: dict, field: str, expected: str | None) -> bool:
        if not expected:
            return True

        actual = str(record.get(field) or "")

        return expected in actual or actual in expected