# test_main_flow.py

from main import (
    get_or_create_visitor_agent,
    get_or_create_guard_agent,
    is_guard_phone,
    should_ignore_text,
    finished_calls,
    cleanup_call_session,
)


def interactive_test():
    call_sid = "TEST_CALL_001"

    caller_phone = input("请输入模拟来电号码: ").strip()

    print("\n=== 模拟通话开始 ===")
    print("来电号码:", caller_phone)

    if is_guard_phone(caller_phone):
        print("进入门卫查询模式")
        agent = get_or_create_guard_agent(call_sid)
        print("Agent开场: 您好，门卫查询模式已开启，请说出您要查询的内容。")
    else:
        print("进入访客登记模式")
        agent = get_or_create_visitor_agent(call_sid)

        memory_reply = agent.preload_by_caller_phone(caller_phone)

        if memory_reply:
            print("Agent开场:", memory_reply)
        else:
            print("Agent开场: 您好，这里是园区来客登记，请说出您的车牌号、要去的公司和来访事由。")

    print("-" * 50)
    print("输入 q / quit / exit 可结束测试")
    print("-" * 50)

    while True:
        text = input("用户输入: ").strip()

        if text.lower() in ["q", "quit", "exit"]:
            print("手动结束测试")
            cleanup_call_session(call_sid)
            break

        if not text:
            continue

        if should_ignore_text(call_sid, text):
            print("main.py 判断：忽略这句话")
            print("-" * 50)
            continue

        if call_sid in finished_calls:
            print("main.py 判断：通话已完成，忽略后续输入")
            print("-" * 50)
            continue

        reply = agent.handle_user_text(text)

        print("Agent返回:", reply)

        if hasattr(agent, "state") and getattr(agent.state, "finished", False):
            print("main.py 判断：流程已结束")
            finished_calls.add(call_sid)

            final_message = (
                "好的，登记完成。"
                "登记信息已提交给门岗。"
                "电话即将结束，感谢您的来电，再见。"
            )

            print("Agent结束语:", final_message)

            cleanup_call_session(call_sid)
            break

        print("-" * 50)


if __name__ == "__main__":
    interactive_test()