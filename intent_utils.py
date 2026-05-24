def detect_user_intent(text: str) -> str:
    text = text.strip()

    positive_words = ["对", "是的", "正确", "没错", "可以", "嗯", "好"]
    negative_words = ["不对", "不是", "错了", "不正确", "重新", "改一下"]
    wait_words = ["等一下", "稍等", "等会", "我看一下"]
    unknown_words = ["不知道", "不清楚", "忘了"]
    cancel_words = ["取消", "不用了", "挂了", "不登记"]

    if any(w in text for w in cancel_words):
        return "cancel"

    if any(w in text for w in negative_words):
        return "deny"

    if any(w in text for w in positive_words):
        return "confirm"

    if any(w in text for w in wait_words):
        return "wait"

    if any(w in text for w in unknown_words):
        return "unknown"

    return "info"