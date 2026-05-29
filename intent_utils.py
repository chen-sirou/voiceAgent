import json


ALLOWED_INTENTS = {
    "confirm",
    "deny",
    "modify",
    "wait",
    "unknown",
    "cancel",
    "info",
}


def normalize_text(text: str) -> str:
    return text.strip().replace(" ", "").replace("，", "").replace("。", "")


def detect_user_intent_fast(text: str) -> str:
    """
    规则快速判断。
    只处理高置信度短句。
    其余返回 info，交给 LLM 或后续信息抽取。
    """

    text = normalize_text(text)

    if not text:
        return "unknown"

    cancel_words = ["取消", "不用了", "挂了", "不登记", "算了"]
    modify_words = ["修改", "改一下", "换成", "重新登记", "重新说", "改成"]
    wait_words = ["等一下", "稍等", "等会", "我看一下"]
    unknown_words = ["不知道", "不清楚", "忘了"]

    # 这些可以出现在长句中，优先判断
    if any(w in text for w in cancel_words):
        return "cancel"

    if any(w in text for w in modify_words):
        return "modify"

    if any(w in text for w in wait_words):
        return "wait"

    if any(w in text for w in unknown_words):
        return "unknown"

    # 长句不直接做 confirm / deny 判断
    # 避免 “是上海大众” 被识别成 confirm
    if len(text) > 4:
        return "info"

    positive_exact = [
        "对",
        "对的",
        "是",
        "是呢",
        "是的",
        "正确",
        "没错",
        "可以",
        "嗯",
        "嗯嗯",
        "好",
        "好的",
        "行",
    ]

    negative_exact = [
        "不对",
        "不是",
        "不是的",
        "错了",
        "不正确",
        "没有",
        "没",
    ]

    if text in negative_exact:
        return "deny"

    if text in positive_exact:
        return "confirm"

    if text.startswith(("不是", "不对", "没有", "错了")):
        return "deny"

    return "info"


def detect_user_intent_llm(
    text: str,
    llm,
    last_agent_question: str = ""
) -> str:
    """
    LLM 兜底判断。
    llm 需要有 generate_json(prompt) 方法。
    """

    prompt = f"""
你是一个电话访客登记系统的意图识别模块。

请根据上一轮系统问题和用户回答，判断用户真实意图。

只能返回 JSON，不要输出其他内容。

可选 intent：
- confirm：用户确认信息正确，例如“是”“对”“没错”
- deny：用户否认、表示信息不对，但没有提供新信息
- modify：用户想修改已有信息
- wait：用户表示稍等、需要时间
- unknown：用户表示不知道、不清楚、忘记了
- cancel：用户想取消登记、挂断、不继续
- info：用户正在提供登记信息，例如车牌号、公司、来访事由

特别注意：
1. “是”出现在长句里，不一定表示 confirm。
例如“是上海大众”应该判断为 info。
2. “不是腾讯，是阿里”不是单纯 deny，更接近 info 或 modify。
3. 如果用户提供了新的车牌、公司、事由，优先判断为 info。
4. 只有用户短句明确确认时，才判断为 confirm。

上一轮系统问题：
{last_agent_question}

用户回答：
{text}

返回格式：
{{
  "intent": "info"
}}
"""

    try:
        result = llm.generate_json(prompt)
        data = json.loads(result)

        intent = data.get("intent", "info")

        if intent not in ALLOWED_INTENTS:
            return "info"

        return intent

    except Exception as e:
        print("LLM intent 识别失败:", e)
        return "info"


def detect_user_intent(
    text: str,
    llm=None,
    last_agent_question: str = ""
) -> str:
    """
    对外统一调用这个函数。
    """

    fast_intent = detect_user_intent_fast(text)

    # 快速规则已经明确判断
    if fast_intent != "info":
        return fast_intent

    # 没有 LLM，就返回 info
    if llm is None:
        return "info"

    # 交给 LLM 判断长句或模糊句
    return detect_user_intent_llm(
        text=text,
        llm=llm,
        last_agent_question=last_agent_question
    )