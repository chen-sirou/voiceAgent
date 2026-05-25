import json
import base64
import asyncio
import html
import time

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Start, Stream
from twilio.rest import Client

from config import (
    PUBLIC_HOST,
    DEEPGRAM_API_KEY,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
)
from stt_deepgram import DeepgramSTT
from registration_agent import VisitorRegistrationAgent

from guard_query_agent import GuardQueryAgent
from guard_config import is_guard_phone

app = FastAPI()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

call_sessions = {}
last_processed_text = {}
agent_speaking_until = {}
finished_calls = set()
last_spoken_text = {}
caller_phone_by_call_sid = {}
greeting_played = set()

@app.post("/voice")
async def voice_webhook(request: Request):
    form = await request.form()

    caller_phone = form.get("From")
    call_sid = form.get("CallSid")

    response = VoiceResponse()

    start = Start()
    stream = Stream(url=f"wss://{PUBLIC_HOST}/media-stream")

    if caller_phone:
        stream.parameter(name="caller_phone", value=caller_phone)

    if call_sid:
        stream.parameter(name="call_sid", value=call_sid)

    start.append(stream)
    response.append(start)

    response.say(
        language="zh-CN",
        voice="Polly.Zhiyu",
    )
    response.pause(length=300)

    return Response(content=str(response), media_type="application/xml")


def build_stream_twiml(call_sid: str, text: str, caller_phone: str | None = None) -> str:
    safe_text = html.escape(text)

    caller_param = ""
    if caller_phone:
        caller_param = f'<Parameter name="caller_phone" value="{html.escape(caller_phone)}" />'

    return f"""
<Response>
    <Start>
        <Stream url="wss://{PUBLIC_HOST}/media-stream">
            <Parameter name="call_sid" value="{html.escape(call_sid)}" />
            {caller_param}
        </Stream>
    </Start>
    <Say language="zh-CN" voice="Polly.Zhiyu">{safe_text}</Say>
    <Pause length="300"/>
</Response>
"""

def estimate_speech_seconds(text: str) -> float:
    return max(3.0, min(5.0, len(text) * 0.35))


def speak_to_caller(call_sid: str, text: str):
    if not call_sid:
        print("没有 call_sid，无法播放回复")
        return

    if last_spoken_text.get(call_sid) == text:
        print("忽略重复播报:", text)
        return

    last_spoken_text[call_sid] = text

    caller_phone = caller_phone_by_call_sid.get(call_sid)

    try:
        agent_speaking_until[call_sid] = time.time() + estimate_speech_seconds(text)

        twilio_client.calls(call_sid).update(
            twiml=build_stream_twiml(call_sid, text, caller_phone)
        )

        print("已播放给用户:", text)

    except Exception as e:
        print("Twilio 播放失败:", e)
        
    
def should_ignore_text(call_sid: str, text: str) -> bool:
    text = text.strip()

    if not text:
        return True

    if time.time() < agent_speaking_until.get(call_sid, 0):
        print("忽略 Agent 播报期间的识别:", text)
        return True

    previous = last_processed_text.get(call_sid)

    if previous == text:
        print("忽略重复识别:", text)
        return True

    last_processed_text[call_sid] = text
    return False

def make_session_key(mode: str, call_sid: str) -> str:
    return f"{mode}:{call_sid}"

def get_or_create_visitor_agent(call_sid: str):
    key = make_session_key("visitor", call_sid)

    if key not in call_sessions:
        call_sessions[key] = VisitorRegistrationAgent()

    return call_sessions[key]

def get_or_create_guard_agent(call_sid: str):
    key = make_session_key("guard", call_sid)

    if key not in call_sessions:
        call_sessions[key] = GuardQueryAgent()

    return call_sessions[key]

def cleanup_call_session(call_sid: str):
    finished_calls.discard(call_sid)
    last_spoken_text.pop(call_sid, None)
    greeting_played.discard(call_sid)
    
    if not call_sid:
        return

    for mode in ["visitor", "guard"]:
        key = make_session_key(mode, call_sid)
        call_sessions.pop(key, None)

    last_processed_text.pop(call_sid, None)
    agent_speaking_until.pop(call_sid, None)

    print("已清理通话 session:", call_sid)

@app.websocket("/media-stream")
async def media_stream(twilio_ws: WebSocket):
    await twilio_ws.accept()
    print("Twilio WebSocket connected")

    stt = DeepgramSTT(DEEPGRAM_API_KEY)
    await stt.connect()

    call_sid = None
    agent = None

    async def receive_from_twilio():
        nonlocal call_sid, agent

        try:
            while True:
                message = await twilio_ws.receive_text()
                data = json.loads(message)

                event = data.get("event")

                if event == "start":

                    print("电话音频流开始")

                    start_info = data.get("start", {})
                    custom_params = start_info.get("customParameters", {})

                    call_sid = (
                        start_info.get("callSid")
                        or custom_params.get("call_sid")
                    )

                    if not call_sid:
                        print("警告：没有获取到 call_sid")
                        continue

                    caller_phone = custom_params.get("caller_phone")
                    if caller_phone:
                        caller_phone_by_call_sid[call_sid] = caller_phone
                    else:
                        caller_phone = caller_phone_by_call_sid.get(call_sid)
                    print("来电号码:", caller_phone)

                    if is_guard_phone(caller_phone):
                        print("进入门卫查询模式")
                        agent = get_or_create_guard_agent(call_sid)

                        if call_sid not in greeting_played:
                            greeting_played.add(call_sid)
                            speak_to_caller(
                                call_sid,
                                "您好，门卫查询模式已开启，请说出您要查询的内容。"
                            )

                    else:

                        print("进入访客登记模式")
                        agent = get_or_create_visitor_agent(call_sid)

                        if call_sid not in greeting_played:
                            greeting_played.add(call_sid)

                            if caller_phone:
                                memory_reply = agent.preload_by_caller_phone(caller_phone)

                                if memory_reply:
                                    speak_to_caller(call_sid, memory_reply)
                                else:
                                    speak_to_caller(
                                        call_sid,
                                        "您好，这里是园区来客登记，请说出您的车牌号、要去的公司和来访事由。"
                                    )
                            else:
                                speak_to_caller(
                                    call_sid,
                                    "您好，这里是园区来客登记，请说出您的车牌号、要去的公司和来访事由。"
                                )
                    print("CallSid:", call_sid)

                elif event == "media":
                    if not call_sid:
                        continue

                    payload = data["media"]["payload"]
                    audio_bytes = base64.b64decode(payload)

                    await stt.send_audio(audio_bytes)

                elif event == "stop":
                    print("电话音频流停止")
                    try:
                        if stt.ws:
                            await stt.ws.send(json.dumps({"type": "Finalize"}))
                            await asyncio.sleep(1.0)
                    except Exception as e:
                        print("Deepgram finalize 失败:", e)
                    break

        except Exception as e:
            print("接收 Twilio 音频出错:", e)

        finally:
            try:
                if stt.ws:
                    await stt.ws.close()
            except Exception:
                pass

    async def receive_from_stt():
        nonlocal call_sid, agent

        try:
            async for text in stt.receive_final_text():
                if not call_sid or not agent:
                    continue

                if should_ignore_text(call_sid, text):
                    continue

                print("用户说:", text)

                if call_sid in finished_calls:
                    print("通话已完成，忽略后续识别:", text)
                    continue
                
                reply = agent.handle_user_text(text)

                print("Agent 回复:", reply)

                speak_to_caller(call_sid, reply)

                if hasattr(agent, "state") and getattr(agent.state, "finished", False):
                    print("本次登记流程结束")
                    finished_calls.add(call_sid)

        except Exception as e:
            print("STT/Agent 处理出错:", e)

    await asyncio.gather(
        receive_from_twilio(),
        receive_from_stt(),
    )