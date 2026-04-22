import requests
import json

LM_STUDIO_URL = "http://172.26.48.1:1234/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-9b"

CONTENT = """✅ Грузоперевозки №1 в Белграде
🇷🇸 𝑹𝑼𝑺 𝑳𝑶𝑮𝑰𝑺𝑻𝑰𝑪𝑺 🇷🇸
🚚 Квартирные и Офисные переезды «Под ключ»
🚀 Доставка мебели и бытовой техники
🚛 Перевозка любых грузов весом до 1500кг, объём кузова 10 м³
💪 Проф. Грузчики
🛠️ Разборка & Сборка мебели
📦 Защитная упаковка
✅ Предузетник
💰 Различные способы оплаты (дин/евро/руб)
🌍 Работаем по Белграду и всей Сербии, Европе & России
☎️ +381-656-138-028
📲 WhatsApp, Viber
⚡ Telegram https://t.me/rus_logistics"""

PROMPT = f"""Analyze the following Telegram message and determine if it is an advertisement, an offer of services, or a product sale.
Answer ONLY in JSON format:
{{
  "is_ad": boolean,
  "reason": "string",
  "category": "string (e.g. services, electronics, real_estate, etc.)"
}}

Message:
\"\"\"{CONTENT}\"\"\"
"""

payload = {
    "model": MODEL_NAME,
    "messages": [
        {"role": "system", "content": "You are a classifier that detects advertisements and service offers. Return ONLY a JSON object."},
        {"role": "user", "content": PROMPT}
    ],
    "temperature": 0.1,
}

response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
print(f"Full Response: {response.text}")
