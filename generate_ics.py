import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timedelta, timezone
from PIL import Image
import pytesseract
import re

# --- Configurações ---
IMG_URL = "https://pbs.twimg.com/media/GzzG3I2XIAAioyI.png"  # Imagem fixa para teste
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

    # Regex para capturar hora, título, comentário e canal
    m = re.match(r'(\d{2}h\d{2})\s+(.*?)\s*(Jogos.*)?\s*(\S+)?', line, re.IGNORECASE)
    if m:
        hora, titulo, comentario, canal = m.groups()
        # Ignorar títulos curtos/números/sozinhos
        if len(titulo.strip()) <= 1 or re.match(r'^[\d\|\(\)\?]$', titulo.strip()):
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

    # Corrige formato hora "06h00" -> "06:00"
    hora_formatada = ev["hora"].replace("h", ":")
    e.begin = f"{today_str} {hora_formatada}"

    descricao = ev["comentario"]
    if ev["canal"]:
        descricao += f" | {ev['canal']}"
    e.description = descricao

    e.duration = timedelta(hours=MAX_EVENT_DURATION_HOURS)
    e.uid = ev["titulo"]
    cal.events.add(e)
    print(f"✅ Adicionado: {ev['titulo']} - {hora_formatada}")

# --- Salvar arquivo ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in cal.serialize_iter():
        f.write(line + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
