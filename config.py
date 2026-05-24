import os
from dotenv import load_dotenv

load_dotenv()

PUBLIC_HOST = os.getenv("PUBLIC_HOST")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK")

required = {
    "PUBLIC_HOST": PUBLIC_HOST,
    "DEEPGRAM_API_KEY": DEEPGRAM_API_KEY,
    "GROQ_API_KEY": GROQ_API_KEY,
    "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
}

missing = [k for k, v in required.items() if not v]
if missing:
    raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")