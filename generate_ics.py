import os
import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timezone, timedelta
import pytz
import re
import warnings
from PIL import Image
import pytesseract
import json
import time
import random

warnings.filterwarnings(
    "ignore", category=FutureWarning, message=r"Behaviour of str\(Component\) will change in version 0.9.*"
)

# --- Configurações ---
X_USER_ID = "1112832962486329344"  # EsportesNaTV
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30
LAST_TWEET_FILE = "last_tweet.json"

# Mapear palavras-chave OCR para esportes padronizados
SPORT_KEYWORDS = {
    "brasileirao": "Futebol",
    "camp. japones": "Futebol",
    "premierleague": "Futebol",
    "la liga": "Futebol",
    "serie a italiana": "Futebol",
    "serie b italiana": "Futebol",
    "us open": "Tênis",
    "wta": "Tênis",
    "mlb": "Basebol",
    "eurobasket": "Basquete",
    "mundial de vlei": "Vôlei",
    "f1 academy": "Corrida",
    "formula 1": "Corrida",
    "porshe endurance": "Corrida",
    "moto gp": "Corrida",
    "ciclismo": "Ciclismo",
    "surf": "Surf",
    "lnf futsal": "Futsal",
}

# --- Funções ---
def remove_emojis(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text)

def save_last_tweet_id(tweet_id: str):
    with open(LAST_TWEET_FILE, "w") as f:
        json.dump({"last_id": tweet_id}, f)

def load_last_tweet_id():
    if os.path.exists(LAST_TWEET_FILE):
        with open(LAST_TWEET_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("last_id")
            except:
                return None
    return None

def get_last_image_url(user_id: str, retries=5):
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        raise Exception("X_BEARER_TOKEN não configurado")
    headers = {"Authorization": f"Bearer {bearer}"}
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&expansions=attachments.media_keys&media.fields=url,type"

    for attempt in range(retries):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            wait = 10 + random.randint(0, 10)
            print(f"⚠️ 429 Too Many Requests. Tentando novamente em {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        last_id = load_last_tweet_id()
        for tweet in data.get("data", []):
            if tweet["id"] == last_id:
                continue  # já processado
            media_keys = tweet.get("attachments", {}).get("media_keys", [])
            for key in media_keys:
                for m in data.get("includes", {}).get("media", []):
                    if m["media_key"] == key and m["type"] == "photo":
                        save_last_tweet_id(tweet["id"])
                        return m["url"]
        # Se nenhum novo, pega o mais recente
        if data.get("data"):
            tweet = data["data"][0]
            media_keys = tweet.get("attachments", {}).get("media_keys", [])
            for key in media_keys:
                for m in data.get("includes", {}).get("media", []):
                    if m["media_key"] == key and m["type"] == "photo":
                        save_last_tweet_id(tweet["id"])
                        return m["url"]
    raise Exception("Não foi possível encontrar a URL da imagem")

def extract_sports(text: str):
    found = set()
    text_lower = text.lower()
    for key, sport in SPORT_KEYWORDS.items():
        if key in text_lower:
            found.add(sport)
    return list(found)

# --- Data e horário ---
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
print(f"🕒 Agora (UTC): {now_utc}")
print(f"🗑️ Jogos anteriores a {cutoff_time} serão removidos.")

# --- Carregar calendário antigo ---
my_calendar = Calendar()
if os.path.exists("calendar.ics"):
    with open("calendar.ics", "r", encoding="utf-8") as f:
        content = f.read()
        if content.strip():
            try:
                calendars = Calendar.parse_multiple(content)
                for cal in calendars:
                    my_calendar.events.update(cal.events)
                print("🔹 calendar.ics antigo carregado (mantendo eventos anteriores).")
            except Exception as e:
                print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

# --- Limpar eventos antigos ---
old_count = len(my_calendar.events)
my_calendar.events = { ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time }
print(f"🧹 Removidos {old_count - len(my_calendar.events)} eventos antigos.")

# --- Baixar última imagem ---
print(f"🔹 Pegando última imagem de EsportesNaTV")
img_url = get_last_image_url(X_USER_ID)
print(f"🔹 URL da imagem: {img_url}")
response = requests.get(img_url)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Extrair esportes ---
sports = extract_sports(texto)

# --- Adicionar eventos ---
added_count = 0
for sport in sports:
    if not any(ev.uid == sport for ev in my_calendar.events):
        ev = Event()
        ev.name = sport
        ev.begin = now_utc
        ev.duration = timedelta(hours=2)
        ev.uid = sport
        my_calendar.events.add(ev)
        print(f"✅ Adicionado: {sport}")
        added_count += 1

print(f"📌 {added_count} novos eventos adicionados.")

# --- Salvar calendar.ics ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
