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

# --- ТЕМАТИКА ЧП (расширенный список, но без общих слов) ---
CHP_KEYWORDS = [
    # ДТП и аварии
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
    # Пожары и ЧС
    "пожар", "возгорание", "горел", "горела", "горело", "горели",
    "сгорел", "сгорела", "сгорело", "сгорели", "выгорел",
    "взрыв", "взорвался", "взорвалась", "хлопок",
    "огнеборцы", "пожарные", "мчс", "спасатели",
    "задымление", "эвакуация", "эвакуировали",
    "обрушение", "обрушился", "обрушилась", "обрушилось",
    "поджог", "поджёг", "подожгли",
    # Преступления
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
    # Суды и следствие
    "осудили", "осужден", "осуждена", "приговор", "приговорил",
    "уголовное дело", "следствие", "следственный комитет",
    "задержан", "задержали", "арестован", "арестовали", "под стражу",
    "подозреваемый", "обвиняемый", "прокуратура", "росгвардия",
    "расследование", "разыскивается", "в розыске",
    # Происшествия
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

# --- ИСКЛЮЧАЮЩИЕ СЛОВА ---
EXCLUDE_KEYWORDS = [
    # Погода
    "погода", "прогноз", "осадки", "снегопад", "дождь",
    "гололёд", "гололед", "туман", "жара", "мороз",
    "потепление", "похолодание", "магнитная буря",
    # Культура
    "культура", "концерт", "выставка", "театр", "музей", "фестиваль",
    "спектакль", "премьера", "кино", "фильм", "библиотека",
    "экскурсия", "ярмарка", "праздник", "парад", "салют",
    "рок-фестиваль", "рок-концерт", "рок-субботник",
    # Спорт
    "спорт", "футбол", "хоккей", "матч", "олимпиада", "чемпионат",
    "турнир", "соревнование", "тренировка", "игрок", "команда",
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
    # Медицина и кадры
    "лекция", "семинар", "вебинар", "мастер-класс", "тренинг",
    "профилактика", "здоровье", "сердце", "сердечно",
    "вакцинация", "прививка", "диспансеризация", "чекап",
    "поликлиника", "маммография", "диагност", "медицин",
    "заболеван", "болезн", "лечен", "эндокринолог",
    "назнач", "сменил", "возглав", "перестановк", "кадров",
    "главврач", "главный врач", "и.о.", "исполняющ",
    "руководитель", "директор", "заместитель", "министр",
    # Мероприятия
    "анонс", "мероприятие", "событие", "форум", "конференция",
    "презентация", "субботник", "месячник",
    "предупредили", "предупреждает", "предупреждение",
    "напомнили", "напоминает", "рассказали", "объяснили",
    "штраф", "штрафы", "штрафах",
    # Жалобы и хамство
    "пожаловалась", "пожаловался", "пожаловались",
    "обматерил", "обматерила", "хамство", "хамил",
    "нахамил", "нахамила", "грубил", "нагрубил",
    "жалоба", "жалобу", "жалуется",
    # Природа
    "парк", "изумрудный", "сквер", "набережная", "зоопарк",
    "животное", "собака", "кошка", "птица", "балобан", "сокол",
    "медвед", "медвеж", "волк", "волч", "лис", "лисиц", "звер",
    "заяц", "зайц", "белка", "белк",
    # Образование
    "школа", "лицей", "университет", "студент", "экзамен", "урок",
    "образование", "стипендия", "призывн", "призыв",
    # Транспорт (мирное)
    "расписание", "маршрут", "трамвай", "троллейбус",
    "ремонт дорог", "благоустройство", "озеленение",
    "ограничение движения", "перекрытие движения", "пробки",
    # Реклама
    "скидка", "распродажа", "подарок", "розыгрыш",
    # Разное
    "свадьба", "юбилей", "выставка достижений",
    # Другие регионы
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
    """Строгая проверка на ЧП."""
    text = (title + " " + summary).lower()
    title_lower = title.lower()
    
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in text:
            return False
    
    has_chp = any(keyword in text for keyword in CHP_KEYWORDS)
    if not has_chp:
        return False
    
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
        for entry in feed.entries[:NEWS_PER_SOURCE]:
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
    """Полноценный текст новости (не обрезанный)."""
    prompt = f"""
Ты — редактор новостного Telegram-канала о происшествиях в Барнауле и Алтайском крае.
Напиши информационное сообщение на основе новости.

ТРЕБОВАНИЯ:
- Официально-информационный тон, как у региональных новостных агентств.
- Живой, но серьёзный язык. Без разговорных выражений и обращений к читателю.
- Сохрани все факты, цифры, имена, должности и адреса без изменений.
- Не выдумывай детали, которых нет в исходном тексте.
- Структура: сначала что произошло, потом детали, в конце — последствия или решения властей.
- Длина: 3-5 абзацев, полноценный текст (до 1500 символов).
- В начале заголовка — ОДИН тематический эмодзи: 🚨, 🚗, 🔥, 🚑, ⚠️ или 👮. Не используй смайлики и другие эмодзи.
- НЕ используй HTML-теги, HTML-сущности и Markdown (**, *, __, _, #).
- НЕ используй символы < и >.
- НЕ упоминай источник новости (Банкфакс, Алтапресс, АиФ, Толк и другие).

Заголовок: {title}
Текст: {summary}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=600
        )
        result = completion.choices[0].message.content.strip()
        result = clean_html_entities(result)
        
        if len(result) < 50:
            print(f"⚠️ ИИ вернул пустой текст. Используем оригинал.")
            result = f"🚨 {title}\n\n{clean_html_entities(summary)}"
        
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return f"🚨 {title}\n\n{clean_html_entities(summary)}"

def send_to_telegram(text, image_url=None):
    """
    Отправляет пост.
    Если текст короткий (до 900 символов) — фото с caption (одним сообщением).
    Если длинный — фото отдельно, текст отдельно с HTML-ссылкой.
    """
    # Подпись с HTML-ссылкой (кликабельная, жирная)
    signature = '\n\n📌 <a href="https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c"><b>Барнаул ЧП | Новости и Разборы</b></a>'
    
    final_text = text + signature

    # Если текст короткий (влезает в caption) — фото с caption
    if len(final_text) <= 1024 and image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID, 'caption': final_text, 'parse_mode': 'HTML'}
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото с caption):", r.status_code)
            
            if r.status_code == 200:
                return  # Всё ок
            
            print(f"Ошибка caption: {r.text}")
            print("Fallback: отправляем раздельно...")
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    # Длинный текст ИЛИ caption не сработал — раздельная отправка
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
    
    # Текст с HTML-ссылкой
    data = {'chat_id': CHAT_ID, 'text': final_text[:4096], 'parse_mode': 'HTML'}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data=data, timeout=15)
    print("Telegram ответ (текст):", r.status_code)
    
    if r.status_code != 200:
        print(f"Ошибка HTML: {r.text}")
        # Fallback: без HTML
        plain_signature = '\n\n📌 Барнаул ЧП | Новости и Разборы\n👉 https://max.ru/join/hafpWBhRmo-zf-QYuFkzd-GSPiaNb-q86W7vUsiAb2c'
        plain_text = text + plain_signature
        data = {'chat_id': CHAT_ID, 'text': plain_text[:4096]}
        r2 = requests.post(url, data=data, timeout=15)
        print("Telegram ответ (без HTML):", r2.status_code)

def load_published_urls():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_published_urls(urls):
    urls = urls[-50:]
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
                print(f"Пропускаем (не ЧП): {title[:50]}...")
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
        print(f"Текст ({len(rewritten_text)} символов)")
        
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