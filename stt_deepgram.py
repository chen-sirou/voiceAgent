import json
import websockets
from urllib.parse import urlencode


class DeepgramSTT:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws = None
        self.last_transcript = ""

    async def connect(self):
        params = {
            "model": "nova-2-general",
            "encoding": "mulaw",
            "sample_rate": "8000",
            "channels": "1",
            "language": "zh-CN",
            "punctuate": "true",
            "smart_format": "true",
            "interim_results": "true",
            "endpointing": "1200",
            "utterance_end_ms": "1200",
            "vad_events": "true",
        }

        url = "wss://api.deepgram.com/v1/listen?" + urlencode(params)

        headers = {
            "Authorization": f"Token {self.api_key}"
        }

        try:
            self.ws = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            )
        except TypeError:
            self.ws = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            )

        print("Deepgram STT 已连接")

    async def send_audio(self, audio_bytes: bytes):
        if self.ws:
            await self.ws.send(audio_bytes)

    async def receive_final_text(self):
        final_parts = []

        async for message in self.ws:
            data = json.loads(message)

            msg_type = data.get("type")

            if msg_type == "SpeechStarted":
                print("Deepgram 检测到用户开始说话")
                continue

            if msg_type == "UtteranceEnd":
                full_text = "".join(final_parts).strip() or self.last_transcript.strip()
                final_parts.clear()
                self.last_transcript = ""

                if full_text:
                    print("Deepgram UtteranceEnd 输出:", full_text)
                    yield full_text

                continue

            if msg_type != "Results":
                continue

            channel = data.get("channel")

            if isinstance(channel, dict):
                alternatives = channel.get("alternatives", [])
            elif isinstance(channel, list) and len(channel) > 0:
                alternatives = channel[0].get("alternatives", [])
            else:
                continue

            if not alternatives:
                continue

            transcript = alternatives[0].get("transcript", "").strip()

            if not transcript:
                continue

            self.last_transcript = transcript

            is_final = data.get("is_final", False)
            speech_final = data.get("speech_final", False)

            print(
                "Deepgram识别:",
                transcript,
                "| is_final:",
                is_final,
                "| speech_final:",
                speech_final,
            )

            if is_final:
                final_parts.append(transcript)

            if speech_final:
                full_text = "".join(final_parts).strip() or self.last_transcript.strip()
                final_parts.clear()
                self.last_transcript = ""

                if full_text:
                    print("Deepgram speech_final 输出:", full_text)
                    yield full_text