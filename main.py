import os
import time
import time as time_module
import feedparser
import requests
import re
from datetime import datetime
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VK_TOKEN = os.getenv("VK_TOKEN")

# --- ИСТОЧНИКИ НОВОСТЕЙ ---
RSS_SOURCES = [
    "https://altai.aif.ru/rss/all.php",
]

VK_GROUPS = [
    "-75554521",
    "-221195646",
]

STATE_FILE = "last_url.txt"
LOCK_FILE = "bot.lock"
NEWS_PER_SOURCE = 5
MAX_HISTORY = 100
SIMILARITY_THRESHOLD = 0.7

# --- ГЕОГРАФИЯ ---
GEO_KEYWORDS = [
    "барнаул", "барнауле", "барнаула", "барнаульск", "барнаульцы", "барнаульцев",
    "бийск", "бийске", "бийска", "бийский", "бийского", "бийском", "бийчане",
    "рубцовск", "рубцовске", "рубцовска", "рубцовский", "рубцовчане",
    "новоалтайск", "новоалтайске", "новоалтайска",
    "заринск", "заринске", "заринска", "заринский", "заринского", "заринском",
    "камень-на-оби", "каменский район",
    "славгород", "славгороде", "славгородский", "славгородского",
    "алейск", "алейске", "алейский", "алейского",
    "белокуриха", "белокурихе", "белокурихи",
    "яровое", "яровом",
    "змеиногорск", "змеиногорске", "змеиногорский",
    "алтай", "алтае", "алтая", "алтайский", "алтайского", "алтайском",
    "на алтае", "по алтаю", "алтайский край", "алтайском крае", "алтайского края",
    "алейский район", "алтайский район", "баевский район", "бийский район",
    "благовещенский район", "бурлинский район", "быстроистокский район",
    "волчихинский район", "егорьевский район", "еланский район",
    "завьяловский район", "залесовский район", "заринский район",
    "зеленодольский район", "зональный район", "калманский район",
    "каменский район", "ключевский район", "косихинский район",
    "краснощековский район", "крутихинский район", "кулундинский район",
    "курский район", "кытмановский район", "локтевский район",
    "мамонтовский район", "михайловский район", "немецкий национальный район",
    "новичихинский район", "павловский район", "панкрушихинский район",
    "первомайский район", "петропавловский район", "поспелихинский район",
    "ребрихинский район", "родинский район", "романский район",
    "рубцовский район", "славгородский район", "смоленский район",
    "советский район", "солонешенский район", "солтонский район",
    "суетский район", "табунский район", "талменский район",
    "тогульский район", "топчихинский район", "третьяковский район",
    "троицкий район", "тыменский район", "усть-калманский район",
    "усть-пристанский район", "хабаровский район", "целинный район",
    "чарышский район", "шелболихинский район", "шипуновский район",
    "ненинка", "солтон", "топчиха", "бурла", "залесово",
    "тогул", "целинное", "майма", "мамонтово", "поспелиха",
    "павловск", "ребриха", "шипуново", "кулунда", "баево",
    "волчиха", "завьялово", "ключи", "краснощёково",
    "крутиха", "курья", "кытманово", "локоть", "михайловское",
    "новичиха", "панкрушиха", "петропавловское", "родино", "роман",
    "смоленское", "советское", "солонешное", "суетка", "табуны",
    "тальменка", "третьяково", "троицкое", "тым", "усть-калманка",
    "усть-пристань", "чарыш", "шелболиха",
]

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
    "сошли с рельсов", "сход с рельсов", "аварийн",
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
    "анонс", "мероприятие", "форум", "конференция", "презентация",
    "субботник", "месячник",
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
    "тверь", "новгород", "псков", "орел", "курск", "белгород",
    "тува", "тыва", "кызыл", "хакасия", "абакан",
    "бурятия", "забайкаль", "якутия", "саха",
    "омская область", "томская область",
    "кемеровская область", "новосибирская область",
    "красноярский край", "иркутская область",
    "свердловская область", "челябинская область",
    "тюменская область", "курганская область",
    "оренбургская область", "самарская область",
    "саратовская область", "волгоградская область",
    "ростовская область", "краснодарский край",
    "ставропольский край", "астраханская область",
    "калмыкия", "дагестан", "чечня", "ингушетия",
    "кабардино-балкария", "карачаево-черкесия",
    "северная осетия", "адыгея", "крым", "севастополь",
    "храм", "церковь", "мечеть", "синагога", "монастырь",
    "буддийский", "буддийского", "буддизм",
    "православн", "мусульман", "иудейск",
    "религиозн", "верующих", "обрядов",
    "епархия", "митрополит", "архиепископ",
    "духовенство", "священник", "имам", "раввин",
    "культурное наследие", "духовное наследие",
    "памятник архитектуры", "памятник культуры",
    "утрата", "соболезнования",
    "госуслуг", "госуслуги", "госуслугах", "госуслугам",
    "портал госуслуг", "красная кнопка", "зеленая кнопка", "зелёная кнопка",
    "госсервис", "госсервисы", "электронные услуги",
    "цифровизация", "цифровые сервисы",
    "разработчики", "разработка", "внедрение",
    "запустят", "новая функция",
    "в россии", "по россии", "россияне", "россиян",
    "минцифры", "минздрав", "минтруд", "минобороны",
    "федеральный", "федеральная", "федеральное",
    "по всей стране", "в регионах",
]

client = Groq(api_key=GROQ_API_KEY)

def clean_html_entities(text):
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
    
    text = re.sub(r'фото[:\s—-]+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'фото взято с\s+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'видео[:\s—-]+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'видео с\s+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'источник[:\s—-]+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'по информации\s+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'как сообщает\s+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'сообщается\s+[«"]?[А-Яа-яA-Za-z0-9\-\.\s]+[»"]?', '', text, flags=re.IGNORECASE)
    
    for source in ['Банкфакс', 'Алтапресс', 'АиФ', 'Толк', 'Амител', 
                   'Комсомольская правда', 'Катунь 24', 'Вести22',
                   'Барнаул 22', 'Барнаул Life', 'Подслушано Барнаул',
                   'НГС22', 'Алтайская правда', 'СпасАлтай22']:
        text = text.replace(f'«{source}»', '')
        text = text.replace(f'"{source}"', '')
        text = text.replace(source, '')
    
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    return text

def is_chp_news(title, summary):
    text = (title + " " + summary).lower()
    title_lower = title.lower()
    
    has_geo = any(keyword in text for keyword in GEO_KEYWORDS)
    if not has_geo:
        return False
    
    for exclude in HARD_EXCLUDE:
        if exclude in title_lower:
            return False
    
    chp_in_title = any(keyword in title_lower for keyword in CHP_KEYWORDS)
    if chp_in_title:
        return True
    
    has_chp = any(keyword in text for keyword in CHP_KEYWORDS)
    return has_chp

def is_similar_title(title, published_titles):
    words = set(re.findall(r'\w+', title.lower()))
    words = {w for w in words if len(w) > 3}
    
    if not words:
        return False
    
    for published in published_titles:
        published_words = set(re.findall(r'\w+', published.lower()))
        published_words = {w for w in published_words if len(w) > 3}
        
        if not published_words:
            continue
        
        common = words & published_words
        similarity = len(common) / max(len(words), len(published_words))
        
        if similarity >= SIMILARITY_THRESHOLD:
            return True
    
    return False

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
            
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            pub_timestamp = time_module.mktime(published) if published else 0
            
            news.append({
                'title': title,
                'summary': clean_html_entities(re.sub('<.*?>', '', entry.get('summary', ''))),
                'url': url_link,
                'guid': guid,
                'image': get_image_from_description(entry),
                'source': 'rss',
                'timestamp': pub_timestamp
            })
        return news
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return []

def parse_vk(group_id, count=5):
    if not VK_TOKEN:
        print("VK_TOKEN не задан, пропускаем ВК")
        return []
    
    url = "https://api.vk.com/method/wall.get"
    params = {
        "owner_id": group_id,
        "count": count,
        "access_token": VK_TOKEN,
        "v": "5.199"
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        
        if "error" in data:
            print(f"Ошибка ВК {group_id}: {data['error'].get('error_msg', 'unknown')}")
            return []
        
        news = []
        items = data.get("response", {}).get("items", [])
        for post in items:
            if post.get("marked_as_ads") or not post.get("text"):
                continue
            
            text = post["text"]
            title = text[:100].strip()
            if not title:
                continue
            
            image_url = None
            if "attachments" in post:
                for attach in post["attachments"]:
                    if attach["type"] == "photo":
                        sizes = attach["photo"].get("sizes", [])
                        if sizes:
                            image_url = max(sizes, key=lambda x: x["width"])["url"]
                            break
            
            news.append({
                'title': title,
                'summary': clean_html_entities(text),
                'url': f"https://vk.com/wall{group_id}_{post['id']}",
                'guid': f"vk_{group_id}_{post['id']}",
                'image': image_url,
                'source': f'vk_{group_id}',
                'timestamp': post.get('date', 0)
            })
        return news
    except Exception as e:
        print(f"Ошибка ВК {group_id}: {e}")
        return []

def get_emoji(text_lower):
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
    """Переписывает новость: жирный заголовок + текст."""
    original_len = len(title) + len(summary)
    
    prompt = f"""
Ты — редактор Telegram-канала «Барнаул ЧП | Новости и Разборы».
Пиши в современном смешанном стиле: факты + лёгкая подача, но с уважением к трагедиям.

ФОРМАТ ОТВЕТА:
- Первая строка — ЗАГОЛОВОК с эмодзи в начале.
- Заголовок нужно обернуть в HTML-тег <b>...</b>, чтобы он был жирным.
- Пустая строка после заголовка.
- Затем 3-4 абзаца обычного текста (без HTML-тегов).
- Каждый абзац — 2-3 предложения.
- НЕ используй разделители (━━━), списки (•, ▪️), маркеры.

ПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:
<b>🚗 ДТП на Ленина: двое пострадавших</b>

В Барнауле на проспекте Ленина произошло серьёзное ДТП. Водитель «Тойоты» не справился с управлением и столкнулся с другой машиной.

В результате аварии пострадали два человека. Их доставили в больницу с травмами различной степени тяжести.

По данным ГИБДД, причиной могла стать высокая скорость. На месте работают инспекторы, движение на участке затруднено.

СТИЛЬ:
- Современный, живой, но уважительный.
- Факты + лёгкая подача.
- Без жаргона («тачка», «разложился»).
- Без смайликов (😂😍🥰) — только тематические эмодзи (🚗🔥👮🚑⚠️🚨).
- Без шуток про погибших и пострадавших.

ПРАВИЛА:
- НЕ сокращай текст. Сохрани все факты, цифры, имена, адреса.
- НЕ используй Markdown (**, *, __).
- НЕ используй символы < и > в тексте (только в теге <b> для заголовка).
- НЕ упоминай источник новости.
- НЕ задавай вопросов.
- Длина: 800-1500 символов.

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000
        )
        result = completion.choices[0].message.content.strip()
        
        # Убираем лишние < и >, кроме тега <b> и </b>
        result = re.sub(r'<(?!b>|/b>)', '', result)
        result = re.sub(r'(?<!<b)(?<!</b)>', '', result)
        
        # Убираем упоминания источников (но не трогаем <b>)
        result = re.sub(r'пишет\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', result, flags=re.IGNORECASE)
        result = re.sub(r'сообщает\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', result, flags=re.IGNORECASE)
        result = re.sub(r'по данным\s+[«"]?[А-Яа-яA-Za-z0-9\-]+[»"]?', '', result, flags=re.IGNORECASE)
        
        for source in ['Банкфакс', 'Алтапресс', 'АиФ', 'Толк', 'Амител', 'Катунь 24', 'Вести22']:
            result = result.replace(f'«{source}»', '')
            result = result.replace(source, '')
        
        result = re.sub(r'[ \t]+', ' ', result).strip()
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        refuse_markers = [
            "пришлите", "пришли", "мне нужен", "не хватает",
            "недостаточно", "к сожалению", "я не могу",
            "уточните", "расскажите больше",
        ]
        result_lower = result.lower()
        is_refusal = any(marker in result_lower for marker in refuse_markers)
        is_too_short = len(result) < original_len * 0.5
        
        if is_refusal or is_too_short:
            reason = "отказ" if is_refusal else f"сокращение"
            print(f"⚠️ ИИ: {reason}. Используем оригинал.")
            emoji = get_emoji((title + " " + summary).lower())
            result = f"<b>{emoji} {title}</b>\n\n{summary}"
        
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        emoji = get_emoji((title + " " + summary).lower())
        return f"<b>{emoji} {title}</b>\n\n{summary}"

def smart_cut(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5:
        return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None):
    """Отправляет пост. Если фото нет — только текст."""
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    
    MAX_MSG = 4096 - len(signature) - 50
    
    # Если есть фото и текст влезает в caption
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
    
    # Если есть фото, но текст длинный — раздельно
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            
            print("⏱️ Ждём 20 секунд перед отправкой текста...")
            time.sleep(20)
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    # Текст (с фото или без)
    final_text = smart_cut(text, MAX_MSG) + signature
    data = {'chat_id': CHAT_ID, 'text': final_text, 'parse_mode': 'HTML'}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data=data, timeout=15)
    print("Telegram ответ (текст):", r.status_code)
    
    if r.status_code != 200:
        print(f"Ошибка HTML: {r.text}")
        plain_text = re.sub(r'<[^>]+>', '', text)
        plain_signature = '\n\n📌 Барнаул ЧП | Новости и Разборы\n👉 https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c'
        final_plain = smart_cut(plain_text, MAX_MSG) + plain_signature
        data = {'chat_id': CHAT_ID, 'text': final_plain[:4096]}
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
        
        published_titles = [k.replace("TITLE:", "") for k in published_keys if k.startswith("TITLE:")]
        print(f"Опубликованных заголовков: {len(published_titles)}")
        
        all_news = []
        
        for source in RSS_SOURCES:
            print(f"Загружаем RSS {source}...")
            news = parse_rss(source)
            print(f"  → {len(news)} новостей")
            all_news.extend(news)
        
        for vk_group in VK_GROUPS:
            print(f"Загружаем ВК {vk_group}...")
            news = parse_vk(vk_group)
            print(f"  → {len(news)} постов")
            all_news.extend(news)
        
        all_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
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
            
            pub_date = datetime.fromtimestamp(news.get('timestamp', 0)).strftime('%d.%m %H:%M') if news.get('timestamp') else '?'
            
            if guid in published_keys:
                print(f"[{pub_date}] Пропускаем (GUID): {title[:50]}...")
                continue
            
            if url in published_keys:
                print(f"[{pub_date}] Пропускаем (URL): {title[:50]}...")
                continue
            
            if is_similar_title(title, published_titles):
                print(f"[{pub_date}] Пропускаем (похожий): {title[:50]}...")
                continue
            
            # ⚠️ ПРОВЕРКА "НЕТ КАРТИНКИ" УДАЛЕНА
            # Теперь бот публикует даже без фото
            
            if not is_chp_news(title, summary):
                print(f"[{pub_date}] Пропускаем (не ЧП Алтая): {title[:50]}...")
                continue
            
            found_news = news
            break
        
        if not found_news:
            print("Подходящих ЧП-новостей не найдено.")
            return
        
        print(f"Найдена ЧП-новость: {found_news['title']}")
        print(f"Источник: {found_news['source']}")
        print(f"Картинка: {found_news.get('image') or 'НЕТ'}")
        
        image_url = found_news.get('image')
        
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
            published_keys.append(f"TITLE:{found_news['title'][:100]}")
            save_published_keys(published_keys)
            print(f"Ключи сохранены. Всего в памяти: {len(published_keys)}")
    
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()