import os
import time
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
    "https://altapress.ru/rss",
    "https://altai.aif.ru/rss/all.php",
]

STATE_FILE = "last_url.txt"
LOCK_FILE = "bot.lock"
NEWS_PER_SOURCE = 30
MAX_HISTORY = 100

# --- ТЕМАТИКА ЧП ---
CHP_KEYWORDS = [
    "дтп", "авария", "столкновение", "наезд", "сбил", "сбила", "сбили",
    "перевернулся", "перевернулась", "опрокинулся", "опрокинулась",
    "лобовое", "столкнулись", "разбился", "разбилась",
    "врезался", "врезалась", "влетел", "влетела", "въехал", "въехала",
    "съехал в кювет", "съехала в кювет", "вылетел с трассы",
    "протаранил", "протаранила", "снес", "снесла",
    "не справился с управлением", "не справилась с управлением",
    "выехал на встречку", "вылетел на встречку",
    "погиб", "погибла", "погибли", "погибший", "погибшая",
    "пострадал", "пострадала", "пострадали", "пострадавший",
    "госпитализирован", "госпитализирована", "госпитализировали",
    "травмы", "травму", "травма", "ушибы", "перелом",
    "скорая", "реанимация",
    "пешеход", "пешехода",
    "без прав", "без водительских прав", "пьяный за рулём",
    "пьяный", "пьяная", "пьяные", "пьяном", "пьяного",
    "нетрезвый", "нетрезвая", "нетрезвом", "нетрезвого",
    "алкоголь", "алкогольное", "опьянение",
    "угнал", "угнала", "угнали", "угон", "угонщик", "угонщики",
    "скрылся", "скрылась", "скрылись",
    "скрылся с места дтп", "покинул место дтп",
    "пожар", "возгорание", "горел", "горела", "горело", "горели",
    "сгорел", "сгорела", "сгорело", "сгорели", "выгорел",
    "взрыв", "взорвался", "взорвалась", "хлопок",
    "огнеборцы", "пожарные", "мчс", "спасатели",
    "задымление", "эвакуация", "эвакуировали",
    "обрушение", "обрушился", "обрушилась", "обрушилось",
    "поджог", "поджёг", "подожгли",
    "убийство", "убил", "убила", "убили", "убийца",
    "труп", "нашли тело", "нашли труп",
    "ограбление", "ограбил", "ограбили", "грабёж", "грабеж",
    "кража", "украли", "украл", "похитил", "похитили", "похищение",
    "разбой", "разбойное", "вымогательство",
    "мошенник", "мошенники", "мошенничество",
    "обманул", "обманули", "афера",
    "нападение", "напал", "напали", "нападавший",
    "избил", "избила", "избили", "избиение", "побои",
    "драка", "подрались", "потасовка",
    "нож", "ножом", "порезал", "порезала", "ранение",
    "выстрел", "выстрелы", "стрельба", "стрелял", "застрелил",
    "огнестрел", "пистолет", "ружьё",
    "наркотик", "наркотики", "закладка", "сбыт",
    "педофил", "насильник", "изнасилование",
    "домогательство", "секта",
    "осудили", "осужден", "осуждена", "приговор", "приговорил",
    "уголовное дело", "следствие", "следственный комитет",
    "задержан", "задержали", "арестован", "арестовали", "под стражу",
    "подозреваемый", "обвиняемый", "прокуратура", "росгвардия",
    "расследование", "разыскивается", "в розыске",
    "чп", "чрезвычайное", "трагедия", "катастрофа",
    "утонул", "утонула", "утонули", "утопление",
    "пропал", "пропала", "пропали", "пропавший", "пропавшая",
    "розыск", "объявлен в розыск",
    "спасение", "спасли", "спас", "спасла",
    "поиски", "поисковая операция",
    "несчастный случай", "отравился", "отравление",
    "эпидемия", "вспышка", "карантин",
    "обморожение", "переохлаждение", "тепловой удар",
    "укус", "укусил", "напала собака",
]

# --- ЖЁСТКИЕ ИСКЛЮЧЕНИЯ ---
HARD_EXCLUDE = [
    "погода", "прогноз", "осадки", "снегопад", "гололёд", "гололед",
    "магнитная буря", "потепление", "похолодание",
    "культура", "концерт", "выставка", "театр", "музей", "фестиваль",
    "спектакль", "премьера", "библиотека", "экскурсия",
    "ярмарка", "праздник", "парад", "салют", "рок-фестиваль",
    "футбол", "хоккей", "олимпиада", "чемпионат", "турнир",
    "соревнование", "тренировка",
    "кулинария", "рецепт", "ресторан", "кафе", "меню", "блюдо",
    "экономика", "курс валют", "доллар", "евро", "биржа", "акции",
    "кредит", "ипотека", "вклад", "инфляция", "пенсия", "осаго",
    "политика", "госдума", "депутат", "выборы", "заксобрание",
    "правительство", "путин", "президент",
    "отпуск", "туризм", "путешествие", "курорт", "санаторий",
    "турмаршрут", "турпоток",
    "лекция", "семинар", "вебинар", "мастер-класс",
    "профилактика", "вакцинация", "прививка", "диспансеризация",
    "чекап", "маммография",
    "назнач", "сменил", "возглав", "перестановк", "кадров",
    "главврач", "и.о.", "исполняющ",
    "анонс", "мероприятие", "форум", "конференция", "презентация",
    "субботник", "месячник",
    "предупредили", "предупреждает", "предупреждение",
    "напомнили", "напоминает",
    "штраф", "штрафы", "штрафах",
    "пожаловалась", "пожаловался", "пожаловались",
    "обматерил", "обматерила", "хамство",
    "нахамил", "нахамила", "нагрубил",
    "жалоба", "жалобу", "жалуется",
    "расписание", "маршрут", "ремонт дорог", "благоустройство",
    "озеленение", "ограничение движения", "перекрытие движения",
    "скидка", "распродажа", "подарок", "розыгрыш",
    "новосибирск", "красноярск", "кемерово", "томск", "омск",
    "екатеринбург", "свердловск", "челябинск", "тюмень",
    "иркутск", "улан-удэ", "чита", "якутск", "хабаровск",
    "владивосток", "краснодар", "ростов", "сочи", "ставрополь",
    "воронеж", "самара", "казань", "уфа", "пермь",
    "нижний новгород", "волгоград", "саратов", "тольятти",
    "ижевск", "оренбург", "москва", "московск", "петербург",
    "ленинградск", "мурманск", "архангельск", "калининград",
    "смоленск", "брянск", "тула", "калуга", "рязань",
    "липецк", "тамбов", "пенза", "ульяновск", "чебоксары",
    "йошкар-ола", "киров", "сыктывкар", "петрозаводск",
    "вологда", "ярославль", "кострома", "иваново", "владимир",
    "тверь", "новгород", "псков",
]

client = Groq(api_key=GROQ_API_KEY)

def clean_html_entities(text):
    """Очищает текст от HTML, Markdown и упоминаний источников."""
    replacements = {
        '&laquo;': '«', '&raquo;': '»', '&amp;': '&', 
        '&quot;': '"', '&apos;': "'", '&nbsp;': ' ',
        '&mdash;': '—', '&ndash;': '–', '&hellip;': '…',
        '&lt;': '', '&gt;': ''
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = text.replace('<', '').replace('>', '')
    
    text = re.sub(r'пишет\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'сообщает\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'по данным\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'как пишет\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'информационное агентство\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', text, flags=re.IGNORECASE)
    
    for source in ['Банкфакс', 'Алтапресс', 'АиФ', 'Толк', 'Амител', 'Комсомольская правда']:
        text = text.replace(f'«{source}»', '')
        text = text.replace(f'"{source}"', '')
        text = text.replace(source, '')
    
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text

def is_chp_news(title, summary):
    """Проверка на ЧП."""
    text = (title + " " + summary).lower()
    title_lower = title.lower()
    
    for exclude in HARD_EXCLUDE:
        if exclude in text:
            return False
    
    chp_in_title = any(keyword in title_lower for keyword in CHP_KEYWORDS)
    if chp_in_title:
        return True
    
    has_chp = any(keyword in text for keyword in CHP_KEYWORDS)
    return has_chp

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
        for entry in feed.entries[:NEWS_PER_SOURCE]:
            title = entry.get('title', '')
            url_link = entry.get('link', '')
            guid = entry.get('id', url_link)
            title_hash = re.sub(r'\W+', '', title.lower())[:60]
            
            news.append({
                'title': title,
                'summary': clean_html_entities(re.sub('<.*?>', '', entry.get('summary', ''))),
                'url': url_link,
                'guid': guid,
                'title_hash': title_hash,
                'image': get_image_from_description(entry),
                'source': url
            })
        return news
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return []

def get_emoji(text_lower):
    """Подбирает эмодзи по теме новости."""
    if any(w in text_lower for w in ["дтп", "авария", "сбил", "столкнов", "врезал", "влетел", "перевернул", "наезд"]):
        return "🚗"
    if any(w in text_lower for w in ["пожар", "возгора", "горел", "сгорел", "огнеборц", "поджог"]):
        return "🔥"
    if any(w in text_lower for w in ["убийств", "убил", "труп", "нашли тело", "убийца"]):
        return "👮"
    if any(w in text_lower for w in ["пострадал", "госпитализ", "травм"]):
        return "🚑"
    if any(w in text_lower for w in ["взрыв", "взорвал", "хлопок"]):
        return "⚠️"
    return "🚨"

def rewrite_text(title, summary):
    """
    Украшает текст через ИИ. Защита от отказов и сокращений.
    """
    original_len = len(title) + len(summary)
    
    prompt = f"""
Ты — редактор Telegram-канала о ЧП в Барнауле и Алтайском крае.
Перепиши эту новость красиво и структурированно.

ЖЁСТКИЕ ПРАВИЛА:
- НЕ сокращай текст. Сохрани все факты, цифры, имена, адреса.
- Добавь ОДИН эмодзи в начало заголовка (🚗, 🔥, 👮, 🚑, ⚠️ или 🚨).
- Разбей текст на 3-4 абзаца.
- НЕ используй HTML, Markdown, символы < и >.
- НЕ упоминай источник новости.
- НЕ задавай вопросов. НЕ проси дополнительную информацию.
- НЕ пиши фразы типа "пришлите", "мне нужно больше данных", "к сожалению".
- Если информации мало — просто оформи то, что есть.

ЦЕЛЬ: пост 800-1500 символов, в котором есть ВСЁ из оригинала.

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500
        )
        result = completion.choices[0].message.content.strip()
        result = clean_html_entities(result)
        
        # Защита от отказов ИИ
        refuse_markers = [
            "пришлите", "пришли", "мне нужен", "нужен более полный",
            "не хватает", "недостаточно", "для того чтобы",
            "к сожалению", "я не могу", "требуется больше",
            "дополнительную информацию", "оставшуюся часть",
            "уточните", "расскажите больше", "пожалуйста, пришлите",
        ]
        result_lower = result.lower()
        is_refusal = any(marker in result_lower for marker in refuse_markers)
        
        # Защита от сокращения
        is_too_short = len(result) < original_len * 0.7
        
        if is_refusal or is_too_short:
            reason = "отказ" if is_refusal else f"сокращение ({len(result)} vs {original_len})"
            print(f"⚠️ ИИ: {reason}. Используем оригинал.")
            emoji = get_emoji((title + " " + summary).lower())
            result = f"{emoji} {title}\n\n{summary}"
        
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        emoji = get_emoji((title + " " + summary).lower())
        return f"{emoji} {title}\n\n{summary}"

def smart_cut(text, limit):
    """Обрезка по последней точке."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5:
        return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None):
    """Отправляет фото, ждёт 20 секунд, потом текст."""
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    
    MAX_MSG = 4096 - len(signature) - 50
    
    # Если фото есть и текст влезает в caption — фото с caption (без задержки)
    if image_url and len(text) + len(signature) <= 1024:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID, 'caption': text + signature, 'parse_mode': 'HTML'}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото с caption):", r.status_code)
            if r.status_code == 200:
                return
            print(f"Ошибка caption: {r.text}")
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    # Иначе — раздельно с задержкой 20 секунд
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            
            # ⏱️ ЗАДЕРЖКА 20 СЕКУНД
            print("⏱️ Ждём 20 секунд перед отправкой текста...")
            time.sleep(20)
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    # Текст
    final_text = smart_cut(text, MAX_MSG) + signature
    data = {'chat_id': CHAT_ID, 'text': final_text, 'parse_mode': 'HTML'}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data=data, timeout=15)
    print("Telegram ответ (текст):", r.status_code)
    
    if r.status_code != 200:
        print(f"Ошибка HTML: {r.text}")
        plain_signature = '\n\n📌 Барнаул ЧП | Новости и Разборы\n👉 https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c'
        plain_text = smart_cut(text, MAX_MSG) + plain_signature
        data = {'chat_id': CHAT_ID, 'text': plain_text[:4096]}
        r2 = requests.post(url, data=data, timeout=15)
        print("Telegram ответ (без HTML):", r2.status_code)

def load_published_keys():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_published_keys(keys):
    keys = keys[-MAX_HISTORY:]
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(keys))

def main():
    if os.path.exists(LOCK_FILE):
        print("Обнаружен параллельный запуск. Пропускаем.")
        return
    
    with open(LOCK_FILE, "w") as f:
        f.write("locked")
    
    try:
        published_keys = load_published_keys()
        print(f"В памяти {len(published_keys)} опубликованных ключей.")
        
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
            guid = news['guid']
            title_hash = news['title_hash']
            
            if guid in published_keys:
                print(f"Пропускаем (GUID уже был): {title[:50]}...")
                continue
            if url in published_keys:
                print(f"Пропускаем (URL уже был): {title[:50]}...")
                continue
            if title_hash in published_keys:
                print(f"Пропускаем (заголовок уже был): {title[:50]}...")
                continue
            
            if not is_chp_news(title, summary):
                print(f"Пропускаем (не ЧП): {title[:50]}...")
                continue
            
            found_news = news
            break
        
        if not found_news:
            print("Подходящих ЧП-новостей не найдено.")
            return
        
        print(f"Найдена ЧП-новость: {found_news['title']}")
        print(f"Размер оригинала: {len(found_news['summary'])} символов")
        
        image_url = found_news['image']
        print(f"Картинка: {image_url}")
        
        post_text = rewrite_text(found_news['title'], found_news['summary'])
        print(f"Размер поста: {len(post_text)} символов")
        
        try:
            send_to_telegram(post_text, image_url)
            print("Пост успешно отправлен!")
        except Exception as e:
            print(f"ОШИБКА при отправке: {e}")
        finally:
            published_keys.append(found_news['guid'])
            published_keys.append(found_news['url'])
            published_keys.append(found_news['title_hash'])
            save_published_keys(published_keys)
            print(f"Ключи сохранены. Всего в памяти: {len(published_keys)}")
    
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()