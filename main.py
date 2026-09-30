import os
import feedparser
import requests
import re
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

RSS_URL = "https://altapress.ru/rss"
STATE_FILE = "last_url.txt"

# Ключевые слова для фильтрации новостей (только про Алтайский край)
KEYWORDS = [
    "барнаул", "алтай", "бийск", "рубцовск", "новоалтайск", 
    "заринск", "камень-на-оби", "славгород", "алейск", "горно-алтайск",
    "алтайский край", "алтайском крае", "алтайского края"
]

client = Groq(api_key=GROQ_API_KEY)

def clean_html_entities(text):
    """Убирает HTML-сущности из текста (чтобы не было &laquo; и т.п.)"""
    replacements = {
        '&laquo;': '«', '&raquo;': '»', '&amp;': '&', 
        '&quot;': '"', '&apos;': "'", '&nbsp;': ' ',
        '&mdash;': '—', '&ndash;': '–', '&hellip;': '…',
        '&lt;': '<', '&gt;': '>'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def is_barnaul_news(title, summary):
    """Проверяет, относится ли новость к Алтайскому краю"""
    text = (title + " " + summary).lower()
    for keyword in KEYWORDS:
        if keyword in text:
            return True
    return False

def get_image_from_description(entry):
    """Ищет картинку в разных местах RSS-ленты"""
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href')
    
    if 'media_content' in entry and len(entry.media_content) > 0:
        for media in entry.media_content:
            if media.get('url'):
                return media.get('url')
    
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
- НЕ используй HTML-теги и сущности (&laquo;, &raquo;, &amp; и т.п.). Только обычный текст.

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
        result = completion.choices[0].message.content
        # Дополнительная очистка на всякий случай
        return clean_html_entities(result)
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return f"📰 {title}\n\n{clean_html_entities(re.sub('<.*?>', '', summary))}"

def send_to_telegram(text, image_url=None):
    """Отправляет пост в Telegram с HTML-разметкой"""
    
    signature = '\n\n━━━━━━━━━━━━━━━\n📌 <b>Барнаул ЧП | Новости и Разборы</b>\n👉 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c">Подписаться на канал</a>'
    final_text = text + signature

    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {
                'chat_id': CHAT_ID, 
                'caption': final_text[:1024],
                'parse_mode': 'HTML'
            }
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            
            if r.status_code != 200:
                print(f"Не удалось отправить фото. Ответ: {r.text}")
                send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
    else:
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

    # --- ИЩЕМ ПОДХОДЯЩУЮ НОВОСТЬ (проверяем первые 10) ---
    found_news = None
    for entry in feed.entries[:10]:
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        clean_summary = clean_html_entities(re.sub('<.*?>', '', summary))
        
        entry_url = entry.get('link', '')
        
        # Пропускаем уже опубликованные
        if entry_url == last_url:
            print(f"Пропускаем (уже было): {title[:50]}...")
            continue
        
        # Проверяем, про Алтай ли новость
        if not is_barnaul_news(title, clean_summary):
            print(f"Пропускаем (не про Алтай): {title[:50]}...")
            continue
        
        # Нашли подходящую
        found_news = entry
        break

    if not found_news:
        print("Подходящих новостей про Алтай не найдено.")
        return

    latest_entry = found_news
    news_url = latest_entry.get('link', '')
    title = latest_entry.get('title', 'Без заголовка')
    summary = clean_html_entities(re.sub('<.*?>', '', latest_entry.get('summary', '')))
    
    print(f"Найдена новость: {title}")
    
    image_url = get_image_from_description(latest_entry)
    print(f"Найдена картинка: {image_url}")
    
    rewritten_text = rewrite_text(title, summary)
    
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