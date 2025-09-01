import os
import re
from datetime import datetime, timezone, timedelta
import pytz
import requests
from PIL import Image
from io import BytesIO
import pytesseract
from ics import Calendar, Event
import snscrape.modules.twitter as sntwitter

# ----------------- CONFIG -----------------
X_USER = "EsportesNaTV"
ESPORTES = ["futebol", "tenis", "surf", "futsal", "volei"]
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30
CALENDAR_FILE = "calendar.ics"

# ----------------- FUNÇÕES -----------------
def remove_emojis(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text)

def get_last_image_url(user: str) -> str:
    """Pega a URL da última imagem postada pelo usuário usando snscrape"""
    for i, tweet in enumerate(sntwitter.TwitterUserScraper(user).get_items()):
        if tweet.media:
            for m in tweet.media:
                if hasattr(m, "fullUrl"):
                    return m.fullUrl
    raise Exception("Não foi possível encontrar a última imagem")

# ----------------- CARREGAR CALENDÁRIO EXISTENTE -----------------
my_calendar = Calendar()
if os.path.exists(CALENDAR_FILE):
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        try:
            my_calendar.events.update(Calendar(f.read()).events)
            print("🔹 Calendário antigo carregado")
        except Exception as e:
            print(f"⚠️ Erro ao carregar calendário antigo: {e}")

# ----------------- REMOVER EVENTOS ANTIGOS -----------------
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
my_calendar.events = {ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time}

# ----------------- PEGAR IMAGEM DO ÚLTIMO POST -----------------
print(f"🔹 Pegando última imagem de {X_USER}")
img_url = get_last_image_url(X_USER)
print(f"🔹 URL da imagem: {img_url}")

response = requests.get(img_url)
if response.status_code != 200:
    raise Exception(f"Erro ao baixar imagem: {response.status_code}")

img = Image.open(BytesIO(response.content))

# ----------------- OCR -----------------
texto = pytesseract.image_to_string(img, lang='por')
print("📝 Texto extraído da imagem:")
print(texto)

# ----------------- FILTRAR ESPORTES -----------------
texto_lower = texto.lower()
esportes_presentes = [e for e in ESPORTES if e in texto_lower]
print(f"🏷️ Esportes encontrados: {esportes_presentes}")

# ----------------- ADICIONAR EVENTO -----------------
if esportes_presentes:
    event = Event()
    event.name = f"Esportes: {', '.join(esportes_presentes)}"
    event.begin = now_utc
    event.uid = f"{now_utc.timestamp()}@{X_USER}"
    my_calendar.events.add(event)
    print(f"✅ Evento adicionado: {event.name}")
else:
    print("⚠️ Nenhum esporte encontrado no post")

# ----------------- SALVAR ICS -----------------
with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("📌 calendar.ics atualizado!")
