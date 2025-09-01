import os
import requests
import re
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta
import pytz
from io import BytesIO
from PIL import Image
import pytesseract

# ---------------- CONFIGURAÇÃO ----------------
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
if not X_BEARER_TOKEN:
    raise Exception("X_BEARER_TOKEN não definido nos secrets!")

USER_NAME = "EsportesNaTV"
BRAZILIAN_TEAMS = ["Futebol", "Tênis", "Surf", "Futsal", "Vôlei"]
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30

# ---------------- UTIL ----------------
def remove_emojis(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text)

def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["data"]["id"]

def get_last_image_url(user_id):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "max_results": 5,
        "expansions": "attachments.media_keys",
        "media.fields": "url,type"
    }
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("data"):
        raise Exception("Nenhum tweet encontrado")

    media_map = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}
    for tweet in data["data"]:
        if "attachments" in tweet:
            for key in tweet["attachments"].get("media_keys", []):
                media = media_map.get(key)
                if media and media["type"] == "photo":
                    print(f"🔹 URL da imagem: {media['url']}")
                    return media["url"]
    raise Exception("Não foi possível encontrar a URL da imagem")

# ---------------- INÍCIO ----------------
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
print(f"🕒 Agora (UTC): {now_utc}")
print(f"🗑️ Jogos anteriores a {cutoff_time} serão removidos.")

# Carregar calendário existente
my_calendar = Calendar()
if os.path.exists("calendar.ics"):
    with open("calendar.ics", "r", encoding="utf-8") as f:
        cleaned_lines = [line for line in f.readlines() if not line.startswith(";")]
        for cal in Calendar.parse_multiple("".join(cleaned_lines)):
            my_calendar.events.update(cal.events)
    print("🔹 calendar.ics antigo carregado.")

# ---------------- PEGAR ÚLTIMA IMAGEM ----------------
user_id = get_user_id(USER_NAME)
img_url = get_last_image_url(user_id)

response = requests.get(img_url)
response.raise_for_status()
img = Image.open(BytesIO(response.content))

# ---------------- OCR ----------------
texto = pytesseract.image_to_string(img, lang='por')
texto = remove_emojis(texto).lower()
print(f"🔹 Texto extraído: {texto}")

# ---------------- FILTRAR POR ESPORTES ----------------
event_names = [e for e in BRAZILIAN_TEAMS if e.lower() in texto]

# ---------------- ADICIONAR NO CALENDÁRIO ----------------
added_count = 0
for name in event_names:
    event = Event()
    event.name = name
    event.begin = now_utc.astimezone(BR_TZ)
    # UID para evitar duplicação
    event.uid = f"{name}-{int(now_utc.timestamp())}"
    my_calendar.events.add(event)
    print(f"✅ Adicionado: {name}")
    added_count += 1

print(f"📌 {added_count} novos eventos adicionados.")

# ---------------- SALVAR ----------------
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
