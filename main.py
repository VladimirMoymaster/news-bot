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
SIMILARITY_THRESHOLD = 0.7

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

# --- ЖЁСТКИЕ ИСКЛЮЧЕНИЯ (МАКСИМАЛЬНО РАСШИРЕННЫЙ) ---
HARD_EXCLUDE = [
    # Погода
    "погода", "прогноз", "осадки", "снегопад", "гололёд", "гололед",
    "магнитная буря", "потепление", "похолодание",
    # Культура
    "культура", "концерт", "выставка", "театр", "музей", "фестиваль",
    "спектакль", "премьера", "библиотека", "экскурсия",
    "ярмарка", "праздник", "парад", "салют", "рок-фестиваль",
    # Спорт
    "футбол", "хоккей", "олимпиада", "чемпионат", "турнир",
    "соревнование", "тренировка",
    # Еда
    "кулинария", "рецепт", "ресторан", "кафе", "меню", "блюдо",
    # Экономика
    "экономика", "курс валют", "доллар", "евро", "биржа", "акции",
    "кредит", "ипотека", "вклад", "инфляция", "пенсия", "осаго",
    # Политика
    "политика", "госдума", "депутат", "выборы", "заксобрание",
    "правительство", "путин", "президент",
    # Туризм
    "отпуск", "туризм", "путешествие", "курорт", "санаторий",
    "турмаршрут", "турпоток",
    # Медицина
    "лекция", "семинар", "вебинар", "мастер-класс",
    "профилактика", "вакцинация", "прививка", "диспансеризация",
    "чекап", "маммография",
    # Кадры
    "назнач", "сменил", "возглав", "перестановк", "кадров",
    "главврач", "и.о.", "исполняющ",
    # Мероприятия
    "анонс", "мероприятие", "форум", "конференция", "презентация",
    "субботник", "месячник",
    "предупредили", "предупреждает", "предупреждение",
    "напомнили", "напоминает",
    "штраф", "штрафы", "штрафах",
    # Жалобы
    "пожаловалась", "пожаловался", "пожаловались",
    "обматерил", "обматерила", "хамство",
    "нахамил", "нахамила", "нагрубил",
    "жалоба", "жалобу", "жалуется",
    # Транспорт
    "расписание", "маршрут", "ремонт дорог", "благоустройство",
    "озеленение", "ограничение движения", "перекрытие движения",
    # Реклама
    "скидка", "распродажа", "подарок", "розыгрыш",
    # --- ГОРОДА РФ (расширенный список) ---
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
    # --- РЕГИОНЫ РФ (расширенный список) ---
    "тува", "тыва", "кызыл", "хакасия", "абакан",
    "бурятия", "забайкаль", "якутия", "саха",
    "алтай республика", "горно-алтайск",
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
    # --- ФЕДЕРАЛЬНЫЕ НОВОСТИ (расширенно) ---
    "во владивостоке", "в хабаровске", "в якутске",
    "в иркутске", "в красноярске", "в кемерове",
    "в томске", "в омске", "в тюмени",
    "в екатеринбурге", "в челябинске", "в уфе",
    "в казани", "в самаре", "в саратове",
    "в волгограде", "в ростове", "в краснодаре",
    "в сочи", "в ставрополе", "в воронеже",
    "в нижнем новгороде", "в перми", "в ижевске",
    "в оренбурге", "в орле", "в туле", "в калуге",
    "в рязани", "в липецке", "в тамбове", "в пензе",
    "в ульяновске", "в чебоксарах", "в йошкар-оле",
    "в кирове", "в сыктывкаре", "в петрозаводске",
    "в вологде", "в ярославле", "в костроме",
    "в иванове", "во владимире", "в твер",
    "в новгороде", "в пскове", "в смоленске",
    "в брянске", "в калининграде", "в мурманске",
    "в архангельске",
    # --- РЕЛИГИОЗНЫЕ ОБЪЕКТЫ ---
    "храм", "церковь", "мечеть", "синагога", "монастырь",
    "буддийский", "буддийского", "буддизм",
    "православн", "мусульман", "иудейск",
    "религиозн", "верующих", "обрядов",
    "епархия", "митрополит", "архиепископ",
    "духовенство", "священник", "имам", "раввин",
    # --- КУЛЬТУРНОЕ НАСЛЕДИЕ ---
    "культурное наследие", "духовное наследие",
    "памятник архитектуры", "памятник культуры",
    "утрата", "соболезнования",
    # --- ГОСУСЛУГИ И ГОССЕРВИСЫ ---
    "госуслуг", "госуслуги", "госуслугах", "госуслугам",
    "портал госуслуг", "красная кнопка", "зеленая кнопка", "зелёная кнопка",
    "госсервис", "госсервисы", "электронные услуги", "электронные сервисы",
    "цифровизация", "цифровые сервисы", "цифровые технологии",
    # --- ФЕДЕРАЛЬНЫЕ НОВОСТИ И ТЕХНОЛОГИИ ---
    "разработчики", "разработка", "внедрение", "внедрят",
    "запустят", "запуск функции", "новая функция",
    "пользователи сервиса", "граждане смогут",
    "защита персональных данных", "финансовые средства граждан",
    "служба поддержки", "безопасность данных",
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
    
    for source in ['Банкфакс', 'Алтапресс', 'АиФ', 'Толк', 'Амител', 'Комсомольская правда']:
        text = text.replace(f'«{source}»', '')
        text = text.replace(f'"{source}"', '')
        text = text.replace(source, '')
    
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text

def is_chp_news(title, summary):
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
            
            news.append({
                'title': title,
                'summary': clean_html_entities(re.sub('<.*?>', '', entry.get('summary', ''))),
                'url': url_link,
                'guid': guid,
                'image': get_image_from_description(entry),
                'source': url
            })
        return news
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
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
        
        refuse_markers = [
            "пришлите", "пришли", "мне нужен", "нужен более полный",
            "не хватает", "недостаточно", "для того чтобы",
            "к сожалению", "я не могу", "требуется больше",
            "дополнительную информацию", "оставшуюся часть",
            "уточните", "расскажите больше", "пожалуйста, пришлите",
        ]
        result_lower = result.lower()
        is_refusal = any(marker in result_lower for marker in refuse_markers)
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
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5:
        return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None):
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    
    MAX_MSG = 4096 - len(signature) - 50
    
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
        
        published_titles = [k.replace("TITLE:", "") for k in published_keys if k.startswith("TITLE:")]
        print(f"Опубликованных заголовков: {len(published_titles)}")
        
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
            
            if guid in published_keys:
                print(f"Пропускаем (GUID уже был): {title[:50]}...")
                continue
            
            if url in published_keys:
                print(f"Пропускаем (URL уже был): {title[:50]}...")
                continue
            
            if is_similar_title(title, published_titles):
                print(f"Пропускаем (похожий заголовок): {title[:50]}...")
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
            published_keys.append(f"TITLE:{found_news['title'][:100]}")
            save_published_keys(published_keys)
            print(f"Ключи сохранены. Всего в памяти: {len(published_keys)}")
    
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()