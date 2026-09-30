import os
import feedparser
import requests
import re
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RSS_URL = "https://lenta.ru/rss"  # Замените на RSS нужного вам сайта
STATE_FILE = "last_url.txt"

client = Groq(api_key=GROQ_API_KEY)

def get_image_from_description(description):
    match = re.search(r'<img[^>]+src="([^">]+)"', description)
    return match.group(1) if match else None

def rewrite_text(title, summary):
    prompt = f"""
Ты — автор Telegram-канала. Перепиши эту новость.
Правила стиля:
- Живой, разговорный язык, как будто рассказываешь другу.
- Начни с цепляющей фразы или вопроса.
- Добавь 2-4 подходящих эмодзи.
- Сохрани все факты, цифры и имена из оригинала. Не выдумывай детали.
- Длина: 3-4 коротких абзаца.

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return f"🚨 {title}\n\n{re.sub('<.*?>', '', summary)[:300]}..."

def send_to_telegram(text, image_url=None):
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=10).content
            files = {'photo': ('image.jpg', img_data, 'image/jpeg')}
            data = {'chat_id': CHAT_ID, 'caption': text, 'parse_mode': 'Markdown'}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code, r.text[:200])
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            send_to_telegram(text + f"\n\n🖼 [Фото]({image_url})", None)
    else:
        data = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, data=data, timeout=30)
        print("Telegram ответ (текст):", r.status_code, r.text[:200])

def main():
    last_url = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_url = f.read().strip()

    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("Не удалось получить RSS")
        return

    latest_entry = feed.entries[0]
    news_url = latest_entry.get('link', '')

    if news_url == last_url:
        print("Новостей нет.")
        return

    print(f"Найдена новость: {latest_entry.title}")
    
    title = latest_entry.get('title', 'Без заголовка')
    summary = latest_entry.get('summary', latest_entry.get('description', 'Нет текста'))
    clean_summary = re.sub('<.*?>', '', summary)
    
    image_url = get_image_from_description(summary)

    rewritten_text = rewrite_text(title, clean_summary)
    send_to_telegram(rewritten_text, image_url)

    with open(STATE_FILE, "w") as f:
        f.write(news_url)
    
    print("Опубликовано!")

if __name__ == "__main__":
    main()
