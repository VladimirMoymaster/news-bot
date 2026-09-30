import os
import feedparser
import requests
import re
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# RSS-лента новостей Барнаула (Алтапресс)
RSS_URL = "https://altapress.ru/rss"
STATE_FILE = "last_url.txt"

client = Groq(api_key=GROQ_API_KEY)

def get_image_from_description(entry):
    """Ищет картинку в разных местах RSS-ленты"""
    # 1. Проверяем тег enclosure (самый частый вариант)
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href')
    
    # 2. Проверяем media_content
    if 'media_content' in entry and len(entry.media_content) > 0:
        for media in entry.media_content:
            if media.get('url'):
                return media.get('url')
    
    # 3. Если ничего не нашли — ищем в HTML-описании
    description = entry.get('summary', '')
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
    """Отправляет пост в Telegram (с картинкой или без) с HTML-разметкой"""
    
    # --- ПОДПИСЬ ПОД ПОСТОМ ---
    signature = '\n\n━━━━━━━━━━━━━━━\n📌 <b>Барнаул ЧП | Новости и Разборы</b>\n👉 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c">Подписаться на канал</a>'
    final_text = text + signature
    # --------------------------

    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            # Лимит подписи к фото в Telegram — 1024 символа
            data = {
                'chat_id': CHAT_ID, 
                'caption': final_text[:1024],
                'parse_mode': 'HTML'  # Включаем HTML для ссылки и жирного текста
            }
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            
            if r.status_code != 200:
                print(f"Не удалось отправить фото. Ответ: {r.text}")
                # Если фото не отправилось, шлем текстом
                send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
    else:
        # Лимит текстового сообщения в Telegram — 4096 символов
        data = {
            'chat_id': CHAT_ID, 
            'text': final_text[:4096],
            'parse_mode': 'HTML'
        }
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, data=data, timeout=15)
        print("Telegram ответ (текст):", r.status_code)
        if r.status_code != 200:
            print(f"Ошибка отправки текста. Ответ: {r.text}")

def main():
    last_url = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_url = f.read().strip()

    # --- МАСКИРУЕМСЯ ПОД БРАУЗЕР ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"Ошибка загрузки RSS: {e}")
        return

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
    clean_summary = re.sub('<.*?>', '', summary)
    
    image_url = get_image_from_description(latest_entry)
    print(f"Найдена картинка: {image_url}")
    
    rewritten_text = rewrite_text(title, clean_summary)
    
    # --- ОТПРАВЛЯЕМ И СОХРАНЯЕМ ---
    try:
        send_to_telegram(rewritten_text, image_url)
        print("Пост успешно отправлен!")
    except Exception as e:
        print(f"ОШИБКА при отправке в Telegram: {e}")
    finally:
        with open(STATE_FILE, "w") as f:
            f.write(news_url)
        print(f"Файл {STATE_FILE} сохранен.")

if __name__ == "__main__":
    main()