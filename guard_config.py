import os


def clean_phone(phone: str | None) -> str:
    """
    清洗手机号：
    +86 13800138000
    -> 13800138000
    """

    if not phone:
        return ""

    return (
        phone.replace(" ", "")
        .replace("-", "")
        .replace("+86", "")
        .replace("+49", "")
    )


def load_guard_phone_numbers() -> set[str]:
    """
    从 .env 读取门卫号码：

    GUARD_PHONE_NUMBERS=13800138000,15126155311
    """

    raw = os.getenv("GUARD_PHONE_NUMBERS", "")

    numbers = set()

    for item in raw.split(","):

        phone = clean_phone(item)

        if phone:
            numbers.add(phone)

    return numbers


GUARD_PHONE_NUMBERS = load_guard_phone_numbers()


def is_guard_phone(phone: str | None) -> bool:
    """
    判断是否属于门卫号码
    """

    clean = clean_phone(phone)

    return clean in GUARD_PHONE_NUMBERS