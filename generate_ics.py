import os
import re
import requests
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta
import pytz
from PIL import Image
from io import BytesIO
import pytesseract

# ----------------- CONFIG -----------------
# URL da última imagem do post
IMG_URL = "https://x.com/EsportesNaTV/status/1962272004289036406/photo/1"

# Esportes que queremos monitorar
ESPORTES = ["futebol", "tenis", "surf", "futsal", "volei"]

# Fuso horário
BR_TZ = pytz.timezone('America/Sao_Paulo')

# Eventos antigos (em dias)
MAX_AGE_DAYS = 30

# Arquivo ICS
CALENDAR_FILE = "calendar.ics"

# ----------------- FUNÇÕES -----------------
def remove_emojis(text: str) -> str:
    """Remove emojis e caracteres não ASCII"""
    return re.sub(r'[^\x00-\x7F]+', '', text)

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

# ----------------- BAIXAR IMAGEM -----------------
print(f"🔹 Baixando imagem: {IMG_URL}")
response = requests.get(IMG_URL)
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
    event.uid = f"{now_utc.timestamp()}@EsportesNaTV"
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
