import os
import feedparser
import requests
import re
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# RSS-лента новостей Барнаула (Амител)
RSS_URL = "https://www.amic.ru/rss/"
STATE_FILE = "last_url.txt"

client = Groq(api_key=GROQ_API_KEY)

def get_image_from_description(description):
    """Ищет ссылку на картинку в HTML-описании новости"""
    match = re.search(r'<img[^>]+src="([^">]+)"', description)
    return match.group(1) if match else None

def rewrite_text(title, summary):
    """Отправляет текст в Groq для переписывания"""
    prompt = f"""
Ты — автор Telegram-канала о новостях Барнаула и Алтайского края. Перепиши эту новость.
Правила стиля:
- Живой, разговорный язык, как будто рассказываешь другу-барнаульцу.
- Начни с цепляющей фразы или вопроса.
- Добавь 2-4 подходящих эмодзи.
- Сохрани все факты, цифры и имена из оригинала.
- Упоминай местные реалии, если они есть в тексте.
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
        # Если ИИ упал, возвращаем оригинальный текст без HTML-тегов
        return f"📰 {title}\n\n{re.sub('<.*?>', '', summary)}"

def send_to_telegram(text, image_url=None):
    """Отправляет пост в Telegram (с картинкой или без)"""
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=10).content
            files = {'photo': ('image.jpg', img_data)}
            # Лимит подписи к фото в Telegram — 1024 символа
            data = {'chat_id': CHAT_ID, 'caption': text[:1024]}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data)
            print("Telegram ответ (фото):", r.status_code)
            
            if r.status_code != 200:
                print("Не удалось отправить фото, отправляем текстом...")
                send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
    else:
        # Лимит текстового сообщения в Telegram — 4096 символов
        data = {'chat_id': CHAT_ID, 'text': text[:4096]}
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, data=data, timeout=10)
        print("Telegram ответ (текст):", r.status_code)

def main():
    last_url = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_url = f.read().strip()

    # --- МАСКИРУЕМСЯ ПОД БРАУЗЕР, ЧТОБЫ САЙТ НЕ БЛОКИРОВАЛ GITHUB ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"Ошибка загрузки RSS: {e}")
        return
    # ----------------------------------------------------------------

    if not feed.entries:
        print("Не удалось получить RSS (лента пуста)")
        return

    # Берем самую свежую новость
    latest_entry = feed.entries[0]
    news_url = latest_entry.get('link', '')

    if news_url == last_url:
        print("Новостей нет.")
        return

    print(f"Найдена новость: {latest_entry.title}")
    
    title = latest_entry.get('title', 'Без заголовка')
    summary = latest_entry.get('summary', '')
    # Очищаем текст от HTML-тегов
    clean_summary = re.sub('<.*?>', '', summary)
    
    image_url = get_image_from_description(summary)
    
    rewritten_text = rewrite_text(title, clean_summary)
    
    # --- ОТПРАВЛЯЕМ И СОХРАНЯЕМ (ДАЖЕ ЕСЛИ УПАДЕТ) ---
    try:
        send_to_telegram(rewritten_text, image_url)
        print("Пост успешно отправлен!")
    except Exception as e:
        print(f"ОШИБКА при отправке в Telegram: {e}")
    finally:
        # Этот блок выполнится ВСЕГДА, чтобы сохранить URL и не дублировать новость
        with open(STATE_FILE, "w") as f:
            f.write(news_url)
        print(f"Файл {STATE_FILE} сохранен.")

if __name__ == "__main__":
    main()