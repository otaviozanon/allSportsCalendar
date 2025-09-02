import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image
import pytesseract
import re

# --- Configurações ---
IMG_URL = "https://pbs.twimg.com/media/GzzG3I2XIAAioyI.png"
MAX_EVENT_DURATION_HOURS = 2

# --- Baixar imagem ---
print(f"🔹 Baixando imagem de teste: {IMG_URL}")
response = requests.get(IMG_URL)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Parsing da agenda ---
events = []
for line in texto.splitlines():
    line = line.strip()
    if not line or len(line) < 5:
        continue
    # Regex simplificada: pega hora e tudo que vem depois como título
    m = re.match(r'(\d{2}h\d{2})\s+(.+)', line)
    if m:
        hora, titulo = m.groups()
        # Ignorar títulos curtos / apenas símbolos ou números
        if len(titulo.strip()) < 2 or re.fullmatch(r'[\d\|\(\)\?]', titulo.strip()):
            continue
        events.append({
            "hora": hora,
            "titulo": titulo.strip(),
            "comentario": "",  # podemos preencher depois
            "canal": ""        # podemos preencher depois
        })

print("✅ Eventos parseados:")
for ev in events:
    print(ev)

# --- Criar calendário ---
cal = Calendar()
today_str = "2025-09-01"
for ev in events:
    e = Event()
    e.name = ev["titulo"]
    e.begin = f"{today_str} {ev['hora'].replace('h', ':')}"
    e.description = ev["comentario"] + (" | " + ev["canal"] if ev["canal"] else "")
    e.duration = timedelta(hours=MAX_EVENT_DURATION_HOURS)
    e.uid = ev["titulo"]
    cal.events.add(e)
    print(f"✅ Adicionado: {ev['titulo']} - {ev['hora']}")

# --- Salvar arquivo ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in cal.serialize_iter():
        f.write(line + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
