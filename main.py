import os
import time
import time as time_module
import requests
import re
from datetime import datetime
from groq import Groq

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VK_TOKEN = os.getenv("VK_TOKEN")

# TODO: ЗАМЕНИ ЭТО
CHANNEL_URL = "https://t.me/ТВОЙ_КАНАЛ" 
CHANNEL_NAME = "Твой Канал | Ставки на спорт"

# --- ИСТОЧНИКИ (ТОЛЬКО ВК) ---
VK_GROUPS = [
    "-123456789", # TODO: ЗАМЕНИ на ID группы INBET или другой
]

STATE_FILE = "last_url.txt"
LOCK_FILE = "bot.lock"
NEWS_PER_SOURCE = 15 # Для ставок лучше брать больше постов
MAX_HISTORY = 300

# --- МАРКЕРЫ СТАВОК ---
BET_KEYWORDS = [
    "ставка", "ординар", "экспресс", "кф", "коэф", "коэффициент", 
    "тотал", "фора", "исход", "победа", "прогноз", "прогнозы",
    "оба забьют", "ничья", "больше", "меньше", "1х", "2х", "12", 
    "инбет", "inbet", "п1", "п2", "х", "тм", "тб"
]

SPAM_KEYWORDS = [
    "промокод", "регистрация", "казино", "бонус", "заработок", 
    "бесплатно", "подписывайтесь", "розыгрыш", "конкурс"
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
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text

def is_bet_post(title, summary):
    text = (title + " " + summary).lower()
    
    # Проверка на спам
    for spam in SPAM_KEYWORDS:
        if spam in text:
            return False
            
    # Проверка на наличие маркеров ставок
    has_bet = any(keyword in text for keyword in BET_KEYWORDS)
    
    # Дополнительная проверка: если есть слово "ставка" и есть цифры (кф)
    if "ставка" in text and re.search(r'\d+[.,]\d+', text):
        return True
        
    return has_bet

# --- ЖЁСТКАЯ ЗАЩИТА ОТ ДУБЛЕЙ ---
def get_text_hash(text):
    clean = re.sub(r'\s+', '', text.lower())[:200]
    return f"TEXTHASH:{clean}"

def get_title_hash(title):
    clean = re.sub(r'\W+', '', title.lower())
    return f"TITLEHASH:{clean}"

def load_published_keys():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_published_keys(keys):
    keys = keys[-MAX_HISTORY:]
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(keys))

# --- ПАРСИНГ ВК ---
def parse_vk(group_id, count=15):
    if not VK_TOKEN:
        print("VK_TOKEN не задан")
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
            title = text[:100].strip().replace("\n", " ")
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
            
            summary_text = clean_html_entities(text)
            
            news.append({
                'title': title,
                'summary': summary_text,
                'text_hash': get_text_hash(summary_text),
                'title_hash': get_title_hash(title),
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

# --- ГЕНЕРАЦИЯ ПОСТА ---
def get_emoji(text_lower):
    if any(w in text_lower for w in ["футбол", "лига", "матч", "гол", "динамо", "байер"]):
        return "⚽"
    if any(w in text_lower for w in ["хоккей", "шайба", "кхл", "нхл"]):
        return "🏒"
    if any(w in text_lower for w in ["баскетбол", "нба", "очко"]):
        return "🏀"
    if any(w in text_lower for w in ["теннис", "сет", "ракетка"]):
        return "🎾"
    if any(w in text_lower for w in ["бокс", "мма", "ufc", "раунд", "боец"]):
        return "🥊"
    return "🎯"

def rewrite_text(title, summary):
    # Обрезаем текст, чтобы не перегружать ИИ (оставляем первые 1500 символов)
    text_for_ai = summary[:1500]
    
    prompt = f"""
Ты — профессиональный редактор Telegram-канала о спортивных ставках «{CHANNEL_NAME}».
Твоя задача — взять сырой пост из ВК и сделать из него КОРОТКИЙ, цепляющий пост для Telegram.

ЖЁСТКИЕ ПРАВИЛА:
- В самом начале обязательно укажи вид спорта (например: ⚽ Футбол).
- Вытащи: Турнир, Дату/Время, Команды (или игроков).
- Вытащи саму ставку (исход, тотал, фора и т.д.).
- Вытащи коэффициент (Кф). Если его нет в тексте, не выдумывай.
- Выкинь весь длинный анализ! Оставь максимум 1-2 предложения с кратким обоснованием (например, из блока "Вывод").
- НЕ используй Markdown (**, *, __). Разрешён только HTML тег <b> для заголовков.
- НЕ упоминай источник, ВК, и не добавляй ссылки на ВК.
- Пиши в сдержанном, уверенном стиле. Без воды.

ПРИМЕР ИДЕАЛЬНОГО ПОСТА:
<b>⚽ Футбол | Лига Европы</b>
🗓 26 ноября, 20:45

<b>Динамо Загреб — Байер</b>
🎯 Ставка: Обе команды забьют — Да
📈 Коэф: 1.52

💡 <i>Хорошая форма атаки Динамо и результативные последние матчи Байера дают основания ждать голов с обеих сторон.</i>

Текст из ВК:
{text_for_ai}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        result = completion.choices[0].message.content.strip()
        
        # Очистка от мусора
        result = re.sub(r'<(?!b>|/b>|i>|/i>)', '', result)
        result = re.sub(r'(?<!<b)(?<!</b)(?<!<i)(?<!</i)>', '', result)
        result = re.sub(r'https?://\S+', '', result)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        
        return result
    except Exception as e:
        print(f"Ошибка ИИ: {e}. Используем оригинал.")
        emoji = get_emoji((title + " " + summary).lower())
        return f"<b>{emoji} {title}</b>\n\n{summary[:800]}"

def smart_cut(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
    if last_dot > limit * 0.5:
        return cut[:last_dot + 1]
    return cut

def send_to_telegram(text, image_url=None, source_url=None):
    # Подпись и кнопка
    signature = f'\n\n📌 <a href="{CHANNEL_URL}"><b>{CHANNEL_NAME}</b></a>'
    MAX_MSG = 4096 - len(signature) - 50
    
    # Формируем кнопки
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Все прогнозы", "url": CHANNEL_URL}]
        ]
    }
    if source_url:
         keyboard["inline_keyboard"][0].append({"text": "🔗 Источник", "url": source_url})

    if image_url and len(text) + len(signature) <= 1024:
        try:
            img_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('image.jpg', img_data)}
            data = {
                'chat_id': CHAT_ID, 
                'caption': text + signature, 
                'parse_mode': 'HTML',
                'reply_markup': str(keyboard).replace("'", '"') # Telegram ждёт JSON
            }
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            r = requests.post(url, files=files, data=data, timeout=30)
            print("Telegram ответ (фото с caption):", r.status_code)
            if r.status_code == 200:
                return
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
            time.sleep(20)
        except Exception as e:
            print(f"Ошибка фото: {e}")
    
    final_text = smart_cut(text, MAX_MSG) + signature
    data = {
        'chat_id': CHAT_ID, 
        'text': final_text, 
        'parse_mode': 'HTML',
        'reply_markup': str(keyboard).replace("'", '"')
    }
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data=data, timeout=15)
    print("Telegram ответ (текст):", r.status_code)

def main():
    if os.path.exists(LOCK_FILE):
        print("Обнаружен параллельный запуск. Пропускаем.")
        return
    
    with open(LOCK_FILE, "w") as f:
        f.write("locked")
    
    try:
        published_keys = load_published_keys()
        print(f"В памяти {len(published_keys)} ключей.")
        
        all_news = []
        
        for vk_group in VK_GROUPS:
            print(f"Загружаем ВК {vk_group}...")
            news = parse_vk(vk_group, count=NEWS_PER_SOURCE)
            print(f"  → {len(news)} постов")
            all_news.extend(news)
        
        all_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        print(f"Всего постов: {len(all_news)}")
        
        found_news = None
        for news in all_news:
            title = news['title']
            summary = news['summary']
            url = news['url']
            guid = news['guid']
            text_hash = news['text_hash']
            title_hash = news['title_hash']
            
            pub_date = datetime.fromtimestamp(news.get('timestamp', 0)).strftime('%d.%m %H:%M') if news.get('timestamp') else '?'
            
            if guid in published_keys:
                print(f"[{pub_date}] ⛔ GUID: {title[:50]}...")
                continue
            
            if url in published_keys:
                print(f"[{pub_date}] ⛔ URL: {title[:50]}...")
                continue
            
            if text_hash in published_keys:
                print(f"[{pub_date}] ⛔ TEXTHASH: {title[:50]}...")
                continue
            
            if not is_bet_post(title, summary):
                print(f"[{pub_date}] Пропускаем (не ставка): {title[:50]}...")
                continue
            
            found_news = news
            break
        
        if not found_news:
            print("Подходящих постов не найдено.")
            return
        
        print(f"✅ Найдена ставка: {found_news['title']}")
        
        image_url = found_news.get('image')
        print(f"Картинка: {image_url or 'НЕТ'}")
        
        post_text = rewrite_text(found_news['title'], found_news['summary'])
        print(f"Размер поста: {len(post_text)} символов")
        
        try:
            # Передаём ссылку на пост ВК для кнопки
            send_to_telegram(post_text, image_url, source_url=found_news['url'])
            print("Пост отправлен!")
        except Exception as e:
            print(f"ОШИБКА отправки: {e}")
        finally:
            published_keys.append(found_news['guid'])
            published_keys.append(found_news['url'])
            published_keys.append(found_news['text_hash'])
            save_published_keys(published_keys)
            print(f"Сохранено. Всего ключей: {len(published_keys)}")
    
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()