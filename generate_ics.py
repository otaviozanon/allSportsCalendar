import os
import requests
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta
import pytz
import re
import time
from io import BytesIO
from PIL import Image
import pytesseract
import warnings

# --- Suprimir FutureWarning do ics ---
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r"Behaviour of str\(Component\) will change in version 0.9.*"
)

# --- Configurações ---
ESPORTES = ["futebol", "tenis", "surf", "futsal", "volei"]
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30

X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
X_USER_ID = "1112832962486329344"  # ID de EsportesNaTV

# --- Helpers ---
def remove_emojis(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text)

def get_last_image_url(user_id: str):
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "max_results": 5,
        "expansions": "attachments.media_keys",
        "media.fields": "url,type"
    }

    retries = 5
    for attempt in range(retries):
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            wait = int(resp.headers.get("x-rate-limit-reset", 15))
            print(f"⚠️ Limite atingido. Tentando novamente em {wait} segundos...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        media = {m["media_key"]: m for m in data.get("includes", {}).get("media", []) if m["type"] == "photo"}

        for tweet in data.get("data", []):
            attachments = tweet.get("attachments", {}).get("media_keys", [])
            for key in attachments:
                if key in media:
                    return media[key]["url"]
        break
    raise Exception("Não foi possível encontrar a URL da imagem")

# --- Carregar/limpar calendário ---
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
print(f"🕒 Agora (UTC): {now_utc}")
print(f"🗑️ Jogos anteriores a {cutoff_time} serão removidos.")

my_calendar = Calendar()
if os.path.exists("calendar.ics"):
    with open("calendar.ics", "r", encoding="utf-8") as f:
        try:
            cleaned_lines = [line for line in f.readlines() if not line.startswith(";")]
            calendars = Calendar.parse_multiple("".join(cleaned_lines))
            for cal in calendars:
                my_calendar.events.update(cal.events)
            print("🔹 calendar.ics antigo carregado")
        except Exception as e:
            print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

old_count = len(my_calendar.events)
my_calendar.events = {ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time}
print(f"🧹 Removidos {old_count - len(my_calendar.events)} eventos antigos.")

# --- Baixar última imagem do X ---
print(f"🔹 Pegando última imagem de EsportesNaTV")
img_url = get_last_image_url(X_USER_ID)
print(f"🔹 URL da imagem: {img_url}")

response = requests.get(img_url)
response.raise_for_status()
img = Image.open(BytesIO(response.content))

# --- Ler texto da imagem ---
texto = pytesseract.image_to_string(img, lang='por')
texto_clean = remove_emojis(texto).lower()

# --- Criar eventos por esporte ---
added_count = 0
for esporte in ESPORTES:
    if esporte in texto_clean:
        event = Event()
        event.name = esporte.capitalize()
        event.begin = now_utc
        my_calendar.events.add(event)
        print(f"✅ Adicionado: {esporte.capitalize()}")
        added_count += 1

print(f"📌 {added_count} novos eventos adicionados.")

# --- Salvar calendário atualizado ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
