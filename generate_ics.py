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
response = requests.get(IMG_URL)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')

# --- Parsing da agenda ---
events = []
for line in texto.splitlines():
    line = line.strip()
    if not line or len(line) < 5:
        continue

    # Regex: captura hora, título, comentário e canal (opcional)
    m = re.match(r'(\d{2}h\d{2})\s+(.+?)(?:\s+(Jogos.*?))?(?:\s+([A-Z0-9, ]+))?$', line)
    if m:
        hora, titulo, comentario, canal = m.groups()
        
        # Descartar títulos muito curtos ou apenas símbolos/números
        if len(titulo) < 3 or re.fullmatch(r'[\d\?\|]', titulo.strip()):
            continue

        events.append({
            "hora": hora,
            "titulo": titulo.strip(),
            "comentario": comentario.strip() if comentario else "",
            "canal": canal.strip() if canal else ""
        })

# --- Criar calendário ---
cal = Calendar()
today_str = datetime.now().strftime('%Y-%m-%d')
for ev in events:
    e = Event()
    e.name = ev["titulo"]
    e.begin = f"{today_str} {ev['hora']}"
    descricao = ev["comentario"]
    if ev["canal"]:
        descricao += f" | {ev['canal']}"
    e.description = descricao
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
