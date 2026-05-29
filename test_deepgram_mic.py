import asyncio
import json
import sounddevice as sd
import websockets
from config import (
    DEEPGRAM_API_KEY,
)

SAMPLE_RATE = 16000
CHANNELS = 1

audio_queue = asyncio.Queue()
main_loop = None


def audio_callback(indata, frames, time, status):
    if status:
        print("音频状态:", status)

    audio_bytes = bytes(indata)

    # 关键修改：从 sounddevice 回调线程安全地放入 asyncio 队列
    main_loop.call_soon_threadsafe(audio_queue.put_nowait, audio_bytes)


async def send_audio(ws):
    while True:
        audio_data = await audio_queue.get()
        await ws.send(audio_data)


async def receive_text(ws):
    async for message in ws:
        data = json.loads(message)

        if data.get("type") == "SpeechStarted":
            print("用户开始说话")
            continue

        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])

        if not alternatives:
            continue

        transcript = alternatives[0].get("transcript", "")
        is_final = data.get("is_final", False)
        speech_final = data.get("speech_final", False)

        if transcript:
            if is_final or speech_final:
                print("最终识别:", transcript)
            else:
                print("临时识别:", transcript)


async def keep_alive(ws):
    while True:
        await asyncio.sleep(5)
        await ws.send(json.dumps({"type": "KeepAlive"}))


async def main():
    global main_loop
    main_loop = asyncio.get_running_loop()

    url = (
        "wss://api.deepgram.com/v1/listen"
        "?model=nova-2"
        "&language=zh-CN"
        "&encoding=linear16"
        f"&sample_rate={SAMPLE_RATE}"
        f"&channels={CHANNELS}"
        "&interim_results=true"
        "&vad_events=true"
        "&endpointing=300"
        "&smart_format=true"
    )

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}"
    }

    print("正在连接 Deepgram...")

    async with websockets.connect(
        url,
        additional_headers=headers
    ) as ws:
        print("Deepgram 已连接")

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=1024,
            callback=audio_callback,
        ):
            print("开始录音，请说话。按 Ctrl+C 退出。")

            await asyncio.gather(
                send_audio(ws),
                receive_text(ws),
                keep_alive(ws),
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("已退出")