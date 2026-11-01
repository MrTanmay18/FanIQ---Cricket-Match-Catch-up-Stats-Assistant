import os
from groq import Groq

def generate_ai_catchup(factual_summary):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FanIQ, a cricket catch-up assistant. Explain the "
                    "selected match period in a concise, engaging way. Use only "
                    "the provided facts. Do not invent player stats, partnerships, "
                    "events, match context, or turning points."
                ),
            },
            {"role": "user", "content": factual_summary},
        ],
        temperature=0.3,
        max_tokens=450,
    )
    return response.choices[0].message.content
