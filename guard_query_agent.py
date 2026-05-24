import json
from datetime import datetime
from llm_groq import GroqLLM
from config import GROQ_MODEL
from visitor_record_query import VisitorRecordQuery


class GuardQueryAgent:
    def __init__(self):
        self.llm = GroqLLM(GROQ_MODEL)
        self.query_engine = VisitorRecordQuery()

    def handle_user_text(self, user_text: str) -> str:
        plan = self._make_query_plan(user_text)
        records = self.query_engine.search(plan)
        return self._generate_answer(user_text, plan, records)

    def _make_query_plan(self, user_text: str) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""
你是园区门卫查询 Agent。

今天日期是：{today}

门卫会用自然语言查询来访记录，例如：
- 今天来了多少人
- 上午来了多少人
- 下午三点到五点来了多少人
- 某个车牌来过几次
- 某家公司今天来了几个人
- 最近有哪些访客
- 今天有哪些车牌
- 送货的来了几个
- 某个手机号有没有来过

请你把问题理解成一个查询计划 JSON。

来访记录字段包括：
- plate_number
- target_company
- phone
- visit_reason
- entry_time

你可以自由决定：
- 是否需要统计 count
- 是否需要列出 list
- 是否需要过滤时间
- 是否需要过滤车牌
- 是否需要过滤公司
- 是否需要过滤手机号
- 是否需要过滤来访事由
- 是否需要限制返回数量

用户问题：
{user_text}

只返回 JSON，不要解释。

返回格式：
{{
  "operation": "count | list | exists",
  "filters": {{
    "start_datetime": null,
    "end_datetime": null,
    "plate_number": null,
    "target_company": null,
    "phone": null,
    "visit_reason": null
  }},
  "limit": 5
}}
"""

        try:
            raw = self.llm.generate_json(prompt)
            return json.loads(raw)
        except Exception as e:
            print("门卫查询计划生成失败:", e)
            return {
                "operation": "list",
                "filters": {},
                "limit": 5
            }

    def _generate_answer(self, user_text: str, plan: dict, records: list[dict]) -> str:
        prompt = f"""
你是园区门卫查询 Agent。

用户原始问题：
{user_text}

你的查询计划：
{json.dumps(plan, ensure_ascii=False)}

查询到的记录：
{json.dumps(records, ensure_ascii=False)}

请用简短自然的中文回答门卫。
如果是数量问题，直接回答数量。
如果是是否来过，回答查到或没查到。
如果是列表问题，列出关键信息。
不要编造不存在的数据。
"""

        try:
            return self.llm.generate_json(prompt)
        except Exception:
            return self._fallback_answer(plan, records)

    def _fallback_answer(self, plan: dict, records: list[dict]) -> str:
        operation = plan.get("operation")

        if operation == "count":
            return f"查询到 {len(records)} 条来访记录。"

        if operation == "exists":
            if records:
                return f"查到了，有 {len(records)} 条相关记录。"
            return "没有查到相关来访记录。"

        if not records:
            return "没有查到相关来访记录。"

        lines = ["查询到以下记录："]
        for r in records[:5]:
            lines.append(
                f"{r.get('entry_time')}，"
                f"车牌{r.get('plate_number')}，"
                f"来访单位{r.get('target_company')}，"
                f"事由{r.get('visit_reason')}。"
            )

        return "\n".join(lines)