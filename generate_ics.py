import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image
import pytesseract
import re

# --- Configurações ---
IMG_URL = "https://pbs.twimg.com/media/GzzG3I2XIAAioyI.png"  # URL fixa para teste
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
    # Regex: captura hora, título, comentário/canal (opcional)
    m = re.match(r'(\d{2}h\d{2})\s+(.*?)\s*(Jogos.*)?\s*(XSPORTS|ESPN[0-9]?|SPORTV[0-9]?|BANDSPORTS|GOAT|youtube|disneyplus\.com)?', line, re.IGNORECASE)
    if m:
        hora, titulo, comentario, canal = m.groups()
        # Ignora símbolos ou números soltos
        if re.fullmatch(r'[\d\|\(\)\?]', titulo.strip()):
            continue
        events.append({
            "hora": hora,
            "titulo": titulo.strip(),
            "comentario": comentario.strip() if comentario else "",
            "canal": canal.strip() if canal else ""
        })

print("✅ Eventos parseados:")
for ev in events:
    print(ev)

# --- Criar calendário ---
cal = Calendar()
# Usando a data do dia 01/09/2025 como no exemplo
today_str = "2025-09-01"
for ev in events:
    e = Event()
    e.name = ev["titulo"]
    e.begin = f"{today_str} {ev['hora'].replace('h', ':')}"
    desc = ev["comentario"]
    if ev["canal"]:
        desc += f" | {ev['canal']}" if desc else ev["canal"]
    e.description = desc
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
