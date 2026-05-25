import json
import re
from pathlib import Path

from schemas import VisitorRegistration, ConversationState
from memory_store import MemoryStore
from llm_groq import GroqLLM
from config import GROQ_MODEL
from correction_engine import CorrectionEngine, clean_text, correct_plate_province
from intent_utils import detect_user_intent
from wechat_sender import WeChatSender
from config import WECHAT_WEBHOOK


PLATE_PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"


def normalize_plate_number(plate: str) -> str:
    if not plate:
        return ""

    plate = clean_text(plate)
    plate = correct_plate_province(plate)

    remove_words = [
        "车牌号是", "车牌是", "车牌号", "车牌",
        "我的", "是"
    ]

    for word in remove_words:
        plate = plate.replace(word, "")

    return plate.upper()


def extract_plate_by_rule(text: str) -> str | None:
    text = normalize_plate_number(text)

    pattern = rf"([{PLATE_PROVINCES}][A-Z][A-Z0-9]{{5,6}})"
    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return None


def is_mainland_plate(plate: str) -> bool:
    if not plate:
        return False

    plate = normalize_plate_number(plate)

    normal_pattern = rf"^[{PLATE_PROVINCES}][A-Z][0-9]{{5}}$"
    new_energy_pattern = rf"^[{PLATE_PROVINCES}][A-Z][0-9]{{6}}$"

    return bool(
        re.match(normal_pattern, plate)
        or re.match(new_energy_pattern, plate)
    )


def merge_value(old: str | None, new: str | None) -> str | None:
    if not new:
        return old

    if not old:
        return new

    if old == new:
        return old

    if len(new) > len(old):
        return new

    return old


class VisitorRegistrationAgent:
    def __init__(self):
        self.registration = VisitorRegistration()
        self.state = ConversationState()

        self.memory = MemoryStore()
        self.corrector = CorrectionEngine(self.memory)
        self.llm = GroqLLM(GROQ_MODEL)

        self.records_path = Path("visitor_records.jsonl")

        self.has_loaded_memory = False
        self.waiting_memory_confirmation = False
        self.waiting_for_modification = False

        self.wechat = WeChatSender(WECHAT_WEBHOOK)

    def preload_by_caller_phone(self, caller_phone: str | None) -> str | None:
        if not caller_phone:
            return None

        phone = self._clean_phone(caller_phone)
        self.registration.phone = phone

        old_info = self.memory.get_by_phone(phone)

        if not old_info:
            return None

        self.registration.plate_number = old_info.get("plate_number")
        self.registration.target_company = old_info.get("target_company")
        self.registration.visit_reason = old_info.get("last_visit_reason")

        self.has_loaded_memory = True
        self.waiting_memory_confirmation = True

        return (
            f"我查到您之前登记的信息是，"
            f"车牌号{self.registration.plate_number}，"
            f"来访单位{self.registration.target_company}，"
            f"来访事由{self.registration.visit_reason}。"
            f"请问这次还是这些信息吗？"
        )

    def handle_user_text(self, user_text: str) -> str:
        self.state.turn_count += 1
        print("STT原文:", user_text)

        corrected_text = self.corrector.correct(user_text)
        print("纠错后:", corrected_text)

        self.state.history.append({"role": "user", "text": corrected_text})
        intent = detect_user_intent(corrected_text)

        if intent == "cancel":
            self.state.finished = True
            return "好的，已取消登记。"

        if intent == "wait":
            return "好的，您慢慢看。"

        if self.waiting_memory_confirmation:
            if intent == "confirm":
                return self._finalize_registration(
                    "好的，已按上次信息完成登记，您可以挂断电话。"
                )

            if intent == "deny":
                self.waiting_memory_confirmation = False
                self.waiting_for_modification = True
                self._clear_reusable_fields()
                return "好的，请直接说这次新的车牌号、要去的公司和来访事由。"

            self.waiting_memory_confirmation = False
            self.waiting_for_modification = False
            self._extract_and_merge(corrected_text, allow_overwrite=True)
            return self._evaluate_next_step()

        if self.waiting_for_modification:
            self.waiting_for_modification = False
            self._extract_and_merge(corrected_text, allow_overwrite=True)
            return self._evaluate_next_step()

        if self.state.waiting_for_confirmation:
            if intent == "confirm":
                return self._finalize_registration(
                    "好的，登记完成，您可以挂断电话了。"
                )

            if intent == "deny":
                self.state.waiting_for_confirmation = False
                self.waiting_for_modification = True
                return "好的，请告诉我需要修改的信息。"

            self._extract_and_merge(corrected_text, allow_overwrite=True)
            return self._evaluate_next_step()

        if intent == "unknown":
            return self._handle_unknown()

        self._extract_and_merge(corrected_text, allow_overwrite=False)
        return self._evaluate_next_step()

    def _clear_reusable_fields(self):
        self.registration.plate_number = None
        self.registration.target_company = None
        self.registration.visit_reason = None
        self.registration.confirmed = False
        self.state.waiting_for_confirmation = False

    def _evaluate_next_step(self) -> str:
        if self.registration.required_complete():
            self.state.waiting_for_confirmation = True
            return self._build_confirmation_question()

        return self._ask_missing_fields()

    def _finalize_registration(self, success_message: str) -> str:
        self.registration.confirmed = True
        self.registration.fill_entry_time()
        self._save_record()
        self.memory.update(self.registration)
        self.state.finished = True
        return success_message

    def _handle_unknown(self) -> str:
        missing = self._missing_fields()

        if "plate_number" in missing:
            return "没关系，您可以看一下车牌后再告诉我。"

        if "target_company" in missing:
            return "没关系，您可以说大概的公司名称，我会帮您登记。"

        if "visit_reason" in missing:
            return "没关系，来访事由可以简单说，比如送货、拜访、维修或面试。"

        return "好的，请您再补充一下。"

    def _extract_and_merge(self, text: str, allow_overwrite: bool = False):
        rule_plate = extract_plate_by_rule(text)
        llm_info = self._extract_by_llm(text)

        if rule_plate:
            llm_info["plate_number"] = rule_plate

        self._merge_info(llm_info, allow_overwrite=allow_overwrite)

        if self.registration.plate_number:
            invalid_or_raw_plate = normalize_plate_number(self.registration.plate_number)

            if not is_mainland_plate(invalid_or_raw_plate):
                print("车牌校验失败，尝试LLM发音纠错:", invalid_or_raw_plate)

                repaired_plate = self._repair_plate_by_llm(
                    raw_text=text,
                    invalid_plate=invalid_or_raw_plate
                )

                if repaired_plate:
                    self.registration.plate_number = repaired_plate
                    print("LLM修正车牌:", repaired_plate)
                else:
                    self.registration.plate_number = None
            else:
                self.registration.plate_number = invalid_or_raw_plate

    def _extract_by_llm(self, text: str) -> dict:
        prompt = self._build_extraction_prompt(text)

        try:
            raw = self.llm.generate_json(prompt)
            data = json.loads(raw)
            return data.get("registration", {}) or {}
        except Exception as e:
            print("LLM提取失败:", e)
            return {}

    def _build_extraction_prompt(self, text: str) -> str:
        lexicon = self.memory.get_lexicon()

        return f"""
你是园区门岗登记信息提取 Agent。

任务：
从用户输入中提取结构化字段。用户可能重复、说错、改口、顺序混乱。
你要提取最完整、最可信的信息。

字段：
- plate_number: 中国大陆车牌，最终格式如 浙A12345、沪A123456
- target_company: 来访单位，公司名称
- visit_reason: 来访事由，如送货、拜访、面试、维修、取货
- phone: 手机号由系统从来电号码获取，不要从用户输入中猜测

常用公司词库：
{lexicon.get("companies", [])}

常用来访事由词库：
{lexicon.get("visit_reasons", [])}

当前已知登记：
{json.dumps(self.registration.to_dict(), ensure_ascii=False)}

用户输入：
{text}

规则：
1. “上海B12345”输出“沪B12345”。
2. “这A12345”“折A12345”“哲A12345”大概率是“浙A12345”。
3. 如果用户说“不是X，是Y”，优先提取 Y。
4. 如果重复说同一字段，取更完整、更像真实字段的版本。
5. 不确定的字段返回 null。
6. 只返回 JSON。

返回：
{{
  "registration": {{
    "plate_number": null,
    "target_company": null,
    "phone": null,
    "visit_reason": null
  }}
}}
"""

    def _merge_info(self, info: dict, allow_overwrite: bool = False):
        new_plate = info.get("plate_number")
        if new_plate:
            new_plate = normalize_plate_number(new_plate)

        if allow_overwrite:
            if new_plate:
                self.registration.plate_number = new_plate
            if info.get("target_company"):
                self.registration.target_company = info.get("target_company")
            if info.get("visit_reason"):
                self.registration.visit_reason = info.get("visit_reason")
        else:
            self.registration.plate_number = merge_value(
                self.registration.plate_number,
                new_plate
            )
            self.registration.target_company = merge_value(
                self.registration.target_company,
                info.get("target_company")
            )
            self.registration.visit_reason = merge_value(
                self.registration.visit_reason,
                info.get("visit_reason")
            )

        if self.registration.phone:
            self.registration.phone = self._clean_phone(self.registration.phone)

    def _missing_fields(self) -> list[str]:
        missing = []

        if not self.registration.plate_number:
            missing.append("plate_number")

        if not self.registration.target_company:
            missing.append("target_company")

        if not self.registration.visit_reason:
            missing.append("visit_reason")

        if not self.registration.phone:
            missing.append("phone")

        return missing

    def _ask_missing_fields(self) -> str:
        missing = self._missing_fields()

        field_map = {
            "plate_number": "车牌号",
            "target_company": "要去的公司",
            "visit_reason": "来访事由",
            "phone": "手机号",
        }

        readable = [field_map[x] for x in missing]

        if len(readable) == 1:
            return f"还需要您的{readable[0]}。"

        return "还需要您补充：" + "、".join(readable) + "。请一次性说完。"

    def _build_confirmation_question(self) -> str:
        return (
            f"我确认一下，车牌号{self.registration.plate_number}，"
            f"来访单位{self.registration.target_company}，"
            f"来访事由{self.registration.visit_reason}，对吗？"
        )

    def _save_record(self):
        record = self.registration.to_dict()

        with self.records_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print("准备发送给微信的 JSON：")
        print(json.dumps(record, ensure_ascii=False, indent=2))

        try:
            self.wechat.send_registration(record)
        except Exception as e:
            print("微信发送失败:", e)

    def _repair_plate_by_llm(self, raw_text: str, invalid_plate: str) -> str | None:
        prompt = f"""
你是中文车牌语音纠错助手。

用户语音识别文本：
{raw_text}

识别出的疑似车牌：
{invalid_plate}

业务规则：
1. 车牌格式必须是：省份简称 + 一个大写字母 + 后面5位或6位数字。
2. 后半部分只能是数字，不能有字母。
3. 请根据中文发音纠正，例如二、两、三、四、五、六、七、八、九、零等。
4. 如果无法确定，返回 null。
5. 只返回 JSON，不要解释。

返回格式：
{{
  "plate_number": "浙A54321"
}}
"""

        try:
            raw = self.llm.generate_json(prompt)
            data = json.loads(raw)
            plate = data.get("plate_number")

            if plate:
                plate = normalize_plate_number(plate)
                if is_mainland_plate(plate):
                    return plate

        except Exception as e:
            print("LLM车牌纠错失败:", e)

        return None

    @staticmethod
    def _clean_phone(phone: str) -> str:
        if not phone:
            return ""

        return (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("+86", "")
            .replace("+49", "")
        )