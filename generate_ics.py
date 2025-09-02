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

warnings.filterwarnings(
    "ignore", category=FutureWarning, message=r"Behaviour of str\(Component\) will change in version 0.9.*"
)

# --- Configurações ---
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30

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
                my_calendar.events.update(Calendar(content).events)
                print("🔹 calendar.ics antigo carregado (mantendo eventos anteriores).")
            except Exception as e:
                print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

# --- Limpar eventos antigos ---
old_count = len(my_calendar.events)
my_calendar.events = { ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time }
print(f"🧹 Removidos {old_count - len(my_calendar.events)} eventos antigos.")

# --- Baixar imagem de teste ---
TEST_IMAGE_URL = "https://pbs.twimg.com/media/Gztj6PpXgAAzVQh.png"  # coloque uma imagem real de teste
print(f"🔹 Baixando imagem de teste: {TEST_IMAGE_URL}")
response = requests.get(TEST_IMAGE_URL)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Extrair esportes ---
sports = extract_sports(texto)

# --- Adicionar eventos ---
added_count = 0
for sport in sports:
    # Evita duplicação pelo UID
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
