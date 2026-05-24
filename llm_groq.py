from openai import OpenAI
from config import GROQ_API_KEY

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


class GroqLLM:

    def __init__(self, model: str):
        self.model = model

    def generate_json(self, prompt: str) -> str:
        """
        调用 Groq API
        """

        response = client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个专业的园区门岗来客登记AI。"
                        "必须返回合法JSON。"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content