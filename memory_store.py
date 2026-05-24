import json
from pathlib import Path
from typing import Optional

from schemas import VisitorRegistration


class MemoryStore:

    def __init__(self, path: str = "visitor_memory.json"):

        self.path = Path(path)

        if not self.path.exists():

            initial_data = {
                "visitors": {},

                "lexicon": {
                    "companies": [],

                    "visit_reasons": [
                        "送货",
                        "拜访",
                        "面试",
                        "维修",
                        "取货",
                        "安装",
                        "商务洽谈"
                    ]
                }
            }

            self.path.write_text(
                json.dumps(
                    initial_data,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

    def _load(self) -> dict:

        return json.loads(
            self.path.read_text(encoding="utf-8")
        )

    def _save(self, data: dict):

        self.path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    def get_by_phone(self, phone: str) -> Optional[dict]:

        data = self._load()

        return data.get("visitors", {}).get(phone)

    def get_lexicon(self) -> dict:
        """
        返回：
        常用公司名
        常用来访事由
        """

        data = self._load()

        return data.get("lexicon", {})

    def update(self, registration: VisitorRegistration):

        if not registration.phone:
            return

        data = self._load()

        visitors = data.setdefault("visitors", {})

        lexicon = data.setdefault("lexicon", {})

        companies = lexicon.setdefault("companies", [])

        reasons = lexicon.setdefault("visit_reasons", [])

        old = visitors.get(registration.phone, {})

        visitors[registration.phone] = {

            "plate_number":
                registration.plate_number
                or old.get("plate_number"),

            "target_company":
                registration.target_company
                or old.get("target_company"),

            "phone":
                registration.phone,

            "last_visit_reason":
                registration.visit_reason
                or old.get("last_visit_reason"),

            "last_entry_time":
                registration.entry_time,
        }

        # 自动加入公司词库
        if (
            registration.target_company
            and registration.target_company not in companies
        ):
            companies.append(
                registration.target_company
            )

        # 自动加入来访事由词库
        if (
            registration.visit_reason
            and registration.visit_reason not in reasons
        ):
            reasons.append(
                registration.visit_reason
            )

        self._save(data)