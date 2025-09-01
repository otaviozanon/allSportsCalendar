import os
import requests
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta
import pytz
import json
import re
import time
import random
from PIL import Image
from io import BytesIO
import pytesseract

# --- Configurações ---
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
X_USER_ID = "1112832962486329344"  # EsportesNaTV
BR_TZ = pytz.timezone("America/Sao_Paulo")
MAX_AGE_DAYS = 30
LAST_TWEET_FILE = "last_tweet.json"

# Map de esportes
SPORTS_KEYWORDS = {
    "Brasileirao": "Futebol",
    "US Open": "Tênis",
    "MLB": "Basebol",
    "EuroBasket": "Basquete",
    "Mundial de Vlei": "Vôlei",
    "WTA": "Tênis",
    "F1 Academy": "Corrida",
    "Campeonato Japonês": "Futebol",
    "Formula 1": "Corrida",
    "Porsche Endurance": "Corrida",
    "PremierLeague": "Futebol",
    "Ciclismo": "Ciclismo",
    "La Liga": "Futebol",
    "Bundesliga": "Futebol",
    "Moto GP": "Corrida",
    "Serie A Italiana": "Futebol",
    "Serie B Italiana": "Futebol"
}

def remove_emojis(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text)

# --- Carregar calendário antigo ---
my_calendar = Calendar()
if os.path.exists("calendar.ics"):
    with open("calendar.ics", "r", encoding="utf-8") as f:
        try:
            calendars = Calendar.parse_multiple(f.read())
            for cal in calendars:
                my_calendar.events.update(cal.events)
        except Exception as e:
            print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

# --- Remover eventos antigos ---
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
my_calendar.events = {ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time}

# --- Recuperar último tweet processado ---
last_tweet_id = None
if os.path.exists(LAST_TWEET_FILE):
    with open(LAST_TWEET_FILE, "r") as f:
        data = json.load(f)
        last_tweet_id = data.get("last_tweet_id")

# --- Função para pegar a última imagem ---
def get_last_image_url(user_id, max_retries=5):
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&expansions=attachments.media_keys&media.fields=url,type"
    
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            wait = 10 + random.randint(0,10)
            print(f"⚠️ 429 Too Many Requests. Tentando novamente em {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        if "includes" in data and "media" in data["includes"]:
            for media in data["includes"]["media"]:
                if media.get("type") == "photo":
                    tweet_id = data["data"][0]["id"]
                    if last_tweet_id and tweet_id <= last_tweet_id:
                        return None  # já processado
                    return media["url"], tweet_id
        raise Exception("Não foi possível encontrar a URL da imagem")
    raise Exception("Falha após várias tentativas")

# --- Pegar a última imagem ---
result = get_last_image_url(X_USER_ID)
if result:
    img_url, last_tweet_id_new = result
    print(f"🔹 URL da imagem: {img_url}")
    response = requests.get(img_url)
    img = Image.open(BytesIO(response.content))
    
    # --- Extrair texto da imagem ---
    texto = pytesseract.image_to_string(img, lang="por")
    print(f"🔹 Texto extraído da imagem:\n{texto}")
    
    # --- Separar esportes ---
    added_count = 0
    for keyword, sport in SPORTS_KEYWORDS.items():
        if re.search(keyword, texto, re.IGNORECASE):
            # Evitar duplicados
            if not any(ev.name == sport for ev in my_calendar.events):
                ev = Event()
                ev.name = sport
                ev.begin = now_utc
                ev.duration = timedelta(hours=2)
                my_calendar.events.add(ev)
                print(f"✅ Adicionado: {sport}")
                added_count += 1
    print(f"📌 {added_count} novos eventos adicionados.")
    
    # --- Atualizar último tweet processado ---
    with open(LAST_TWEET_FILE, "w") as f:
        json.dump({"last_tweet_id": last_tweet_id_new}, f)
else:
    print("⚠️ Nenhuma nova imagem encontrada.")

# --- Salvar calendar.ics ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{now_utc.isoformat()}\n")

print("🔹 calendar.ics atualizado!")
