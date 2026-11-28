import os
import time
import time as time_module
import requests
import json
import re
from datetime import datetime, timedelta
import pytz
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "-1005656106786") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VK_TOKEN = os.getenv("VK_TOKEN")

CHANNEL_URL = "https://t.me/+COpP5PRxevYwM2Y6" 
CHANNEL_NAME = "Prognoz.Insider"
REF_LINK = "https://r1wzrnh.com/?open=register&p=3ti2"

# --- ИСТОЧНИКИ (ТОЛЬКО ВК) ---
VK_GROUPS = [
    "-51015741", # ID группы INBET
]

STATE_FILE = "last_url.txt"
LOCK_FILE = "bot.lock"
NEWS_PER_SOURCE = 5 
MAX_HISTORY = 300

# --- ПРАВИЛА ФИЛЬТРАЦИИ ---
STOP_WORDS = ["стоимость: 2000 за оба", "послеоплату", "ночи", "экспресс"]
REQUIRED_WORD = "ординар"
REPLACEMENTS = {"INBET": "Insider", "инбет": "Insider", "Inbet": "Insider"}

BET_KEYWORDS = [
    "ставка", "ординар", "кф", "коэф", "коэффициент", 
    "тотал", "фора", "исход", "победа", "прогноз", "прогнозы",
    "оба забьют", "ничья", "больше", "меньше", "1х", "2х", "12", 
    "п1", "п2", "х", "тм", "тб"
]

client = Groq(api_key=GROQ_API_KEY)

def clean_html_entities(text):
    replacements = {'&laquo;': '«', '&raquo;': '»', '&amp;': '&', '&quot;': '"', '&apos;': "'", '&nbsp;': ' ', '&mdash;': '—', '&ndash;': '–', '&hellip;': '…'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text

def is_valid_post(title, summary):
    text = (title + " " + summary).lower()
    
    for stop_word in STOP_WORDS:
        if stop_word.lower() in text:
            return False
            
    if REQUIRED_WORD.lower() not in text:
        return False
            
    has_bet = any(keyword in text for keyword in BET_KEYWORDS)
    if "ставка" in text and re.search(r'\d+[.,]\d+', text):
        return True
        
    return has_bet

def get_text_hash(text):
    clean = re.sub(r'\s+', '', text.lower())[:200]
    return f"TEXTHASH:{clean}"

def load_published_keys():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_published_keys(keys):
    keys = keys[-MAX_HISTORY:]
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(keys))

def parse_vk(group_id, count=5):
    if not VK_TOKEN: return []
    url = "https://api.vk.com/method/wall.get"
    params = {"owner_id": group_id, "count": count, "access_token": VK_TOKEN, "v": "5.199"}
    
    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        if "error" in data: return []
        
        news = []
        for post in data.get("response", {}).get("items", []):
            if post.get("marked_as_ads"): continue
            
            text = post.get("text", "").strip()
            if not text: text = "Прогноз на спорт (подробности на картинке)"
            
            title = text[:100].strip().replace("\n", " ")
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
                'text_hash': get_text_hash(text),
                'url': f"https://vk.com/wall{group_id}_{post['id']}",
                'guid': f"vk_{group_id}_{post['id']}",
                'image': image_url,
                'timestamp': post.get('date', 0)
            })
        return news
    except Exception as e:
        print(f"Ошибка ВК {group_id}: {e}")
        return []

def process_with_ai(title, summary, post_date_timestamp):
    post_date_str = datetime.fromtimestamp(post_date_timestamp).strftime('%d.%m.%Y')
    
    # 1. Проверка времени матча
    time_prompt = f"""
    Прочитай текст прогноза на спорт. Найди дату и время начала матча.
    Дата публикации поста: {post_date_str}.
    Если написано "Сегодня в 20:45", значит время матча: {post_date_str} 20:45.
    Выведи ТОЛЬКО дату и время в формате: YYYY-MM-DD HH:MM.
    Если времени нет, выведи: UNKNOWN.

    Текст:
    {summary[:1000]}
    """
    
    match_time_str = "UNKNOWN"
    try:
        time_completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": time_prompt}],
            temperature=0.0,
            max_tokens=20
        )
        match_time_str = time_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при получении времени: {e}")

    if match_time_str != "UNKNOWN" and re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', match_time_str):
        try:
            moscow_tz = pytz.timezone('Europe/Moscow')
            now_msk = datetime.now(moscow_tz)
            match_time = datetime.strptime(match_time_str, '%Y-%m-%d %H:%M')
            match_time_msk = moscow_tz.localize(match_time)
            
            if (match_time_msk - now_msk) < timedelta(hours=1):
                print(f"⏳ Матч начнется в {match_time_str} МСК (меньше часа). Пропускаем.")
                return None, None 
        except Exception as e:
            print(f"Ошибка парсинга даты ({match_time_str}): {e}")
            
    # 2. Генерация строгого и короткого поста
    text_for_ai = summary[:1500]
    prompt = f"""
Ты — профессиональный редактор канала о ставках. Сделай из этого текста МАКСИМАЛЬНО КОРОТКИЙ пост.
Оставь ТОЛЬКО три строки (без лишних слов, без турниров, без анализов, без времени):

<b>[Эмодзи] [Вид спорта]</b>
<b>[Команда 1] — [Команда 2]</b>
🎯 Ставка: [Текст ставки]

ПРАВИЛА:
1. Если это Выигрыш (есть слова "Зашла", "Выигрыш"), поставь эмодзи ✅ вместо 🎯.
2. Вид спорта: Футбол, Хоккей, Баскетбол и т.д.
3. Категорически запрещено писать "Кф не указан", "нет данных" и т.д. Если кф нет в тексте — просто не пиши его.
4. Никаких букв "ь" в конце сокращений (пиши "РПЛ", а не "РПЛь").
5. Используй только HTML теги <b> и <i>.

ПРИМЕР:
<b>⚽ Футбол</b>
<b>Балтика — Ахмат</b>
🎯 Ставка: Тотал меньше 2.5

Текст из ВК:
{text_for_ai}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        result = completion.choices[0].message.content.strip()
        
        result = re.sub(r'<(?!b>|/b>|i>|/i>)', '', result)
        result = re.sub(r'(?<!<b)(?<!</b)(?<!<i)(?<!</i)>', '', result)
        result = re.sub(r'https?://\S+', '', result)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        
        refuse_markers = ["в предоставленном тексте", "невозможно", "не могу", "недостаточно данных", "нет информации", "не указан"]
        if any(marker in result.lower() for marker in refuse_markers):
            raise ValueError("ИИ отказался")
            
        return result, match_time_str
    except Exception as e:
        print(f"Ошибка ИИ: {e}. Используем оригинал.")
        return f"<b>🎯 Прогноз</b>\n\n{summary[:300]}", match_time_str

def apply_replacements(text):
    for old, new in REPLACEMENTS.items():
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    return text

def smart_cut(text, limit):
    if len(text) <= limit: return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5: return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None, source_url=None):
    signature = f'\n\n📌 <a href="{CHANNEL_URL}"><b>{CHANNEL_NAME}</b></a>'
    MAX_MSG = 4096 - len(signature) - 50
    
    # ВСТАВЬ СЮДА СВОЮ ССЫЛКУ С GITHUB PAGES (ЕСЛИ СДЕЛАЛ СТРАНИЦУ)
    ALL_BETS_URL = CHANNEL_URL 
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Посмотреть все прогнозы", "url": ALL_BETS_URL}],
            [{"text": "🔥 Сделать ставку (Бонус)", "url": REF_LINK}]
        ]
    }
    reply_markup_json = json.dumps(keyboard)

    if image_url and len(text) + len(signature) <= 1024:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID, 'caption': text + signature, 'parse_mode': 'HTML', 'reply_markup': reply_markup_json}
            r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", files=files, data=data, timeout=30)
            print("Telegram ответ (фото с caption):", r.status_code)
            if r.status_code == 200: return True
        except Exception as e: print(f"Ошибка фото: {e}")
    
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {'chat_id': CHAT_ID}
            r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", files=files, data=data, timeout=30)
            print("Telegram ответ (фото):", r.status_code)
            time.sleep(15) 
        except Exception as e: print(f"Ошибка фото: {e}")
    
    final_text = smart_cut(text, MAX_MSG) + signature
    data = {'chat_id': CHAT_ID, 'text': final_text, 'parse_mode': 'HTML', 'reply_markup': reply_markup_json}
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=data, timeout=15)
    print("Telegram ответ (текст):", r.status_code)
    return r.status_code == 200

def main():
    if os.path.exists(LOCK_FILE): return
    with open(LOCK_FILE, "w") as f: f.write("locked")
    
    try:
        published_keys = load_published_keys()
        all_news = []
        
        for vk_group in VK_GROUPS:
            all_news.extend(parse_vk(vk_group, count=NEWS_PER_SOURCE))
        
        all_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        found_news = None
        
        for news in all_news:
            if news['guid'] in published_keys or news['url'] in published_keys or news['text_hash'] in published_keys:
                continue
            if not is_valid_post(news['title'], news['summary']):
                continue
                
            print(f"Проверяем время для поста: {news['title'][:40]}...")
            post_text, match_time = process_with_ai(news['title'], news['summary'], news['timestamp'])
            
            if post_text is None:
                continue
                
            found_news = news
            break
        
        if not found_news:
            print("Подходящих постов не найдено.")
            return
        
        post_text = apply_replacements(post_text)
        
        success = send_to_telegram(post_text, found_news.get('image'), source_url=found_news['url'])
        
        if success:
            print("Пост УСПЕШНО отправлен!")
            published_keys.extend([found_news['guid'], found_news['url'], found_news['text_hash']])
            save_published_keys(published_keys)
        else:
            print("❌ Пост НЕ отправлен.")
            
    finally:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()