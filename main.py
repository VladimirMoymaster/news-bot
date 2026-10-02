import os
import feedparser
import requests
import re
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- ИСТОЧНИКИ НОВОСТЕЙ ---
RSS_SOURCES = [
    "https://altapress.ru/rss",              # Алтапресс
    "https://altai.aif.ru/rss/all.php",       # АиФ-Алтай
]

STATE_FILE = "last_url.txt"
LOCK_FILE = "bot.lock"

# --- ГЕОГРАФИЯ ---
GEO_KEYWORDS = [
    "барнаул", "алтай", "бийск", "рубцовск", "новоалтайск", 
    "заринск", "камень-на-оби", "славгород", "алейск", "горно-алтайск",
    "алтайский край", "алтайском крае", "алтайского края", "алтая"
]

# --- ТЕМАТИКА ЧП ---
CHP_KEYWORDS = [
    "дтп", "авария", "столкновение", "наезд", "сбил", "сбила", "сбили",
    "перевернулся", "опрокинулся", "лобовое", "столкнулись", "разбился",
    "погиб", "погибла", "погибли", "пострадал", "пострадала", "пострадали",
    "госпитализирован", "травмы", "скорая", "пешеход",
    "пожар", "возгорание", "горел", "горела", "горело", "сгорел", "сгорела",
    "взрыв", "взорвался", "хлопок", "огнеборцы", "мчс",
    "убийство", "убил", "убила", "убийца", "труп", "нашли тело",
    "ограбление", "ограбил", "кража", "украли", "похитил", "похищение",
    "мошенник", "мошенничество", "обманул", "афера",
    "нападение", "напал", "избил", "избиение", "драка", "подрались",
    "нож", "ножом", "порезал", "ранение", "выстрел", "стрельба",
    "наркотик", "наркотики", "закладка", "сбыт",
    "осудили", "приговор", "приговорил", "уголовное дело", "следствие",
    "задержан", "задержали", "арестован", "арестовали", "подозреваемый",
    "прокуратура", "следственный комитет", "росгвардия",
    "чп", "чрезвычайное", "трагедия", "катастрофа", "обрушение", "обрушился",
    "утонул", "утонула", "утонули", "пропал", "пропала", "пропали", "розыск",
    "спасатели", "спасение", "эвакуация", "эвакуировали"
]

# --- ИСКЛЮЧАЮЩИЕ СЛОВА ---
EXCLUDE_KEYWORDS = [
    # Погода
    "погода", "прогноз", "температура", "осадки", "снег", "дождь", "ветер",
    "гололёд", "гололед", "туман", "жара", "мороз", "потепление", "похолодание",
    # Культура
    "культура", "концерт", "выставка", "театр", "музей", "фестиваль",
    "спектакль", "премьера", "кино", "фильм", "книга", "библиотека",
    "экскурсия", "ярмарка", "праздник", "парад", "салют",
    # Спорт
    "спорт", "футбол", "хоккей", "матч", "олимпиада", "чемпионат",
    "турнир", "соревнование", "тренировка", "игрок", "команда",
    # Еда
    "кулинария", "рецепт", "еда", "ресторан", "кафе", "меню", "блюдо",
    # Технологии
    "обзор", "тест-драйв", "новинка", "гаджет", "смартфон", "приложение",
    # Экономика
    "экономика", "курс валют", "доллар", "евро", "биржа", "акции",
    "кредит", "ипотека", "банк", "вклад", "инфляция", "пенсия",
    # Политика
    "политика", "путин", "правительство", "госдума", "депутат", "выборы",
    # Туризм
    "отпуск", "туризм", "путешествие", "курорт", "отдых", "санаторий",
    # Здоровье
    "лекция", "семинар", "вебинар", "мастер-класс", "тренинг",
    "профилактика", "здоровье", "давление", "сердце", "сердечно",
    "заболевание", "болезнь", "лечение", "вакцинация", "прививка",
    "диспансеризация", "чекап", "анализ", "врач", "больница", "поликлиника",
    # Мероприятия
    "анонс", "мероприятие", "событие", "встреча", "форум", "конференция",
    "открытие", "закрытие", "презентация", "запуск",
    # Природа
    "парк", "изумрудный", "сквер", "набережная", "зоопарк",
    "животное", "собака", "кошка", "птица", "медведь", "лиса",
    # Образование
    "школа", "университет", "студент", "экзамен", "урок", "образование",
    "олимпиада", "конкурс", "стипендия",
    # Транспорт
    "расписание", "маршрут", "автобус", "трамвай", "троллейбус",
    "ремонт дорог", "благоустройство", "озеленение",
    # Реклама
    "скидка", "акция", "распродажа", "подарок", "конкурс", "розыгрыш",
]

client = Groq(api_key=GROQ_API_KEY)

def clean_html_entities(text):
    """Очищает текст от HTML-сущностей и Markdown-разметки"""
    replacements = {
        '&laquo;': '«', '&raquo;': '»', '&amp;': '&', 
        '&quot;': '"', '&apos;': "'", '&nbsp;': ' ',
        '&mdash;': '—', '&ndash;': '–', '&hellip;': '…',
        '&lt;': '<', '&gt;': '>'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Убираем Markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    return text

def is_chp_news(title, summary):
    """Проверяет, относится ли новость к ЧП в Барнауле/Алтае"""
    text = (title + " " + summary).lower()
    
    # 1. География
    has_geo = any(keyword in text for keyword in GEO_KEYWORDS)
    if not has_geo:
        return False
    
    # 2. Исключающие слова
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in text:
            return False
    
    # 3. Тематика ЧП
    has_chp = any(keyword in text for keyword in CHP_KEYWORDS)
    if not has_chp:
        return False
    
    # 4. ЧП-слово должно быть в заголовке
    title_lower = title.lower()
    chp_in_title = any(keyword in title_lower for keyword in CHP_KEYWORDS)
    if not chp_in_title:
        return False
    
    return True

def get_image_from_description(entry):
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

def parse_rss(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        news = []
        for entry in feed.entries[:15]:
            news.append({
                'title': entry.get('title', ''),
                'summary': clean_html_entities(re.sub('<.*?>', '', entry.get('summary', ''))),
                'url': entry.get('link', ''),
                'image': get_image_from_description(entry),
                'source': url
            })
        return news
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return []

def rewrite_text(title, summary):
    prompt = f"""
Ты — редактор новостного Telegram-канала о происшествиях в Барнауле и Алтайском крае.
Напиши информационное сообщение на основе следующей новости.

Требования к стилю:
- Официально-информационный тон, как у региональных новостных агентств.
- Живой, но серьёзный язык. Без разговорных выражений и обращений к читателю.
- Сохрани все факты, цифры, имена, должности и адреса без изменений.
- Не выдумывай детали, которых нет в исходном тексте.
- Структура: сначала что произошло, потом детали, в конце — последствия или решения властей.
- Длина: 3-4 коротких абзаца.
- В начале заголовка можно поставить ОДИН тематический эмодзи: 🚨 (ЧП), 🚗 (ДТП), 🔥 (пожар), 🚑 (пострадавшие), ⚠️ (предупреждение), 👮 (преступление). Не используй смайлики и другие эмодзи.
- НЕ используй HTML-теги, HTML-сущности и Markdown-разметку (**, *, __, _, #).

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=500
        )
        result = completion.choices[0].message.content
        return clean_html_entities(result)
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return f"{title}\n\n{clean_html_entities(summary)}"

def send_to_telegram(text, image_url=None):
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    final_text = text + signature

    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID, 'caption': final_text[:1024], 'parse_mode': 'HTML'}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            if r.status_code != 200:
                send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            send_to_telegram(text + f"\n\n🖼 Ссылка на фото: {image_url}")
    else:
        data = {'chat_id': CHAT_ID, 'text': final_text[:4096], 'parse_mode': 'HTML'}
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, data=data, timeout=15)
        print("Telegram ответ (текст):", r.status_code)

def load_published_urls():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_published_urls(urls):
    urls = urls[-20:]
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(urls))

def main():
    if os.path.exists(LOCK_FILE):
        print("Обнаружен параллельный запуск. Пропускаем.")
        return
    
    with open(LOCK_FILE, "w") as f:
        f.write("locked")
    
    try:
        published_urls = load_published_urls()
        
        all_news = []
        for source in RSS_SOURCES:
            print(f"Загружаем {source}...")
            news = parse_rss(source)
            print(f"  → {len(news)} новостей")
            all_news.extend(news)
        
        print(f"Всего новостей: {len(all_news)}")
        
        if not all_news:
            print("Новостей не найдено.")
            return
        
        found_news = None
        for news in all_news:
            title = news['title']
            summary = news['summary']
            url = news['url']
            
            if url in published_urls:
                print(f"Пропускаем (уже было): {title[:50]}...")
                continue
            
            if not is_chp_news(title, summary):
                print(f"Пропускаем (не ЧП или не Алтай): {title[:50]}...")
                continue
            
            found_news = news
            break
        
        if not found_news:
            print("Подходящих ЧП-новостей не найдено.")
            return
        
        print(f"Найдена ЧП-новость: {found_news['title']}")
        print(f"Источник: {found_news['url']}")
        
        image_url = found_news['image']
        print(f"Картинка: {image_url}")
        
        rewritten_text = rewrite_text(found_news['title'], found_news['summary'])
        
        try:
            send_to_telegram(rewritten_text, image_url)
            print("Пост успешно отправлен!")
        except Exception as e:
            print(f"ОШИБКА при отправке: {e}")
        finally:
            published_urls.append(found_news['url'])
            save_published_urls(published_urls)
            print(f"URL сохранён. Всего опубликовано: {len(published_urls)}")
    
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()