import difflib
import re


PROVINCE_ALIASES = {
    "京": ["京", "北京"],
    "津": ["津", "天津"],
    "沪": ["沪", "上海", "护", "互"],
    "浙": ["浙", "浙江", "这", ],
    "苏": ["苏", "江苏", "书", "数"],
    "粤": ["粤", "广东", "月", "越"],
    "鲁": ["鲁", "山东"],
    "川": ["川", "四川"],
}


DIGIT_MAP = {
    "零": "0",
    "〇": "0",
    "洞": "0",

    "一": "1",
    "幺": "1",
    "腰": "1",

    "二": "2",
    "两": "2",

    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
}

LETTER_MAP = {
    "诶": "A",
    "欸": "A",

    "比": "B",
    "壁": "B",
    "币": "B",

    "西": "C",
    "吸": "C",

    "迪": "D",
    "弟": "D",

    "伊": "E",
    "一": "E",

    "艾弗": "F",
    "爱弗": "F",

    "鸡": "G",
    "记": "G",
}


def normalize_plate_letters(text: str) -> str:
    """
    纠正语音识别中的车牌字母：
    浙诶12345 -> 浙A12345
    浙比12345 -> 浙B12345
    浙西12345 -> 浙C12345
    """

    for wrong, right in LETTER_MAP.items():
        text = text.replace(wrong, right)

    return text

def normalize_chinese_digits(text: str) -> str:
    for cn, num in DIGIT_MAP.items():
        text = text.replace(cn, num)

    return text


def clean_text(text: str) -> str:

    if not text:
        return ""

    text = normalize_chinese_digits(text)
    text = normalize_plate_letters(text)

    for ch in [" ", "，", ",", "。", ".", "-", "·"]:
        text = text.replace(ch, "")

    return text.upper()


def correct_plate_province(text: str) -> str:
    """
    纠正：
    这A12345 → 浙A12345
    上海B54321 → 沪B54321
    """

    text = clean_text(text)

    match = re.search(
        r"([\u4e00-\u9fa5])([A-Z])([0-9]{5,6})",
        text
    )

    if not match:
        return text

    province_text, city_letter, tail = match.groups()

    best_province = None
    best_score = 0

    for province, aliases in PROVINCE_ALIASES.items():

        for alias in aliases:

            score = difflib.SequenceMatcher(
                None,
                province_text,
                alias
            ).ratio()

            if province_text in aliases:
                score = 1.0

            if score > best_score:
                best_score = score
                best_province = province

    if best_province and best_score >= 0.5:

        corrected = f"{best_province}{city_letter}{tail}"

        return text.replace(match.group(0), corrected)

    return text


def normalize_company_entries(companies: list) -> list[dict]:

    result = []

    for item in companies:

        if isinstance(item, str):

            result.append({
                "name": item,
                "aliases": [],
                "code": None
            })

        elif isinstance(item, dict):

            name = item.get("name")

            aliases = item.get("aliases", [])

            if not isinstance(aliases, list):
                aliases = []

            aliases = [
                str(alias)
                for alias in aliases
                if isinstance(alias, (str, int, float))
            ]

            code = item.get("code")

            if code is not None:
                code = str(code)

            if name:

                result.append({
                    "name": str(name),
                    "aliases": aliases,
                    "code": code
                })

    return result


def find_best_company(
    text: str,
    companies: list
) -> tuple[str | None, float]:

    text = clean_text(str(text))

    company_entries = normalize_company_entries(companies)

    best_company = None
    best_score = 0.0

    for company in company_entries:

        name = str(company.get("name", ""))

        aliases = company.get("aliases", [])

        code = company.get("code")

        if code:

            code_clean = clean_text(str(code))

            if code_clean and code_clean in text:
                return name, 1.0

        all_names = [name] + aliases

        for candidate in all_names:

            if not candidate:
                continue

            candidate_clean = clean_text(str(candidate))

            if not candidate_clean:
                continue

            if candidate_clean in text:
                score = 0.95

            else:
                score = difflib.SequenceMatcher(
                    None,
                    text,
                    candidate_clean
                ).ratio()

            # 关键词片段匹配
            for i in range(len(candidate_clean)):

                for j in range(i + 2, len(candidate_clean) + 1):

                    part = candidate_clean[i:j]

                    if len(part) >= 2 and part in text:

                        score = max(
                            score,
                            len(part) / len(candidate_clean)
                        )

            if score > best_score:

                best_score = score
                best_company = name

    return best_company, best_score


def find_best_visit_reason(
    text: str,
    reasons: list[str]
) -> tuple[str | None, float]:

    text = clean_text(text)

    best_reason = None
    best_score = 0.0

    for reason in reasons:

        reason_clean = clean_text(reason)

        if reason_clean in text:
            score = 1.0

        else:
            score = difflib.SequenceMatcher(
                None,
                text,
                reason_clean
            ).ratio()

        if score > best_score:

            best_score = score
            best_reason = reason

    return best_reason, best_score


class CorrectionEngine:

    def __init__(self, memory_store):
        self.memory_store = memory_store

    def correct_text(self, text: str) -> str:

        text = clean_text(text)

        text = correct_plate_province(text)

        return text

    def match_company(self, text: str):

        lexicon = self.memory_store.get_lexicon()

        companies = lexicon.get("companies", [])

        return find_best_company(
            text,
            companies
        )

    def match_visit_reason(self, text: str):

        lexicon = self.memory_store.get_lexicon()

        reasons = lexicon.get("visit_reasons", [])

        return find_best_visit_reason(
            text,
            reasons
        )

    def correct(self, text: str) -> str:

        return self.correct_text(text)