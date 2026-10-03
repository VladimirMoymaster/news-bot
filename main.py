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
    "укус", "укусил", "напала собака", "задушил", "задушила",
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
    """Улучшенная проверка на ЧП."""
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

def rewrite_text(title, summary):
    """Полноценный текст новости с жёсткой структурой."""
    prompt = f"""
Ты — редактор новостного Telegram-канала о происшествиях в Барнауле и Алтайском крае.
Напиши информационное сообщение на основе новости.

ЖЁСТКИЕ ТРЕБОВАНИЯ (не нарушай):
- Объём: СТРОГО 4 абзаца. Примерно 1000-1300 символов. МЕНЬШЕ 800 символов НЕ ДОПУСКАЕТСЯ.
- Абзац 1: Заголовок с эмодзи + что произошло, где, когда (2-3 предложения).
- Абзац 2: Детали происшествия — кто участвовал, что случилось, обстоятельства (2-3 предложения).
- Абзац 3: Последствия — пострадавшие, ущерб, реакция властей (2-3 предложения).
- Абзац 4: Что дальше — следствие, проверка, решения (1-2 предложения).

ПРИМЕР ПРАВИЛЬНОГО ПОСТА:
«🚗 Два человека пострадали в ДТП на трассе под Барнаулом

Авария произошла вечером 2 октября на трассе Р-256 в районе села Калманка. Водитель автомобиля Toyota Corolla не справился с управлением и выехал на встречную полосу движения.

По предварительным данным, в результате столкновения с грузовиком пострадали два человека — водитель и пассажир легковушки. Оба доставлены в больницу с травмами различной степени тяжести.

На месте работали сотрудники ГИБДД и скорая помощь. Правоохранители устанавливают все обстоятельства произошедшего.»

ТРЕБОВАНИЯ К ТЕКСТУ:
- Официально-информационный тон, как у новостных агентств.
- Сохрани ВСЕ факты, цифры, имена, должности и адреса.
- Не выдумывай детали, которых нет в исходной новости.
- В начале заголовка — ОДИН эмодзи: 🚨, 🚗, 🔥, 🚑, ⚠️ или 👮.
- НЕ используй HTML, Markdown, символы < и >.
- НЕ упоминай источник новости.

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=900
        )
        result = completion.choices[0].message.content.strip()
        result = clean_html_entities(result)
        
        # Если ИИ вернул СЛИШКОМ короткий текст (меньше 600 символов) — fallback на оригинал
        if len(result) < 600:
            print(f"⚠️ ИИ вернул короткий текст ({len(result)} символов). Используем оригинал.")
            result = f"🚨 {title}\n\n{summary}"
            if len(result) > 1400:
                result = result[:1400]
                last_dot = max(result.rfind('.'), result.rfind('!'), result.rfind('?'))
                if last_dot > 800:
                    result = result[:last_dot + 1]
        
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        fallback = f"🚨 {title}\n\n{summary}"
        if len(fallback) > 1400:
            fallback = fallback[:1400]
            last_dot = max(fallback.rfind('.'), fallback.rfind('!'), fallback.rfind('?'))
            if last_dot > 800:
                fallback = fallback[:last_dot + 1]
        return fallback

def smart_cut(text, limit):
    """Обрезка по последней точке, а не посередине."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5:
        return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None):
    """Отправляет пост с умной обрезкой и защитой от неполного текста."""
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    
    # Резерв 200 символов под подпись
    MAX_CAPTION = 1024 - len(signature) - 50
    MAX_MSG = 4096 - len(signature) - 50
    
    # Если фото есть и текст влезает в caption — фото с caption
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
    
    # Иначе — раздельно: фото, потом текст
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    # Текст с умной обрезкой
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
        print(f"GUID: {found_news['guid']}")
        print(f"URL: {found_news['url']}")
        
        image_url = found_news['image']
        print(f"Картинка: {image_url}")
        
        rewritten_text = rewrite_text(found_news['title'], found_news['summary'])
        print(f"Текст ({len(rewritten_text)} символов)")
        
        try:
            send_to_telegram(rewritten_text, image_url)
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