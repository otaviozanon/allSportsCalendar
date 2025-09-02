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

    # Regex para capturar: hora + título + comentário (opcional) + canal (opcional)
    m = re.match(r'(\d{2}h\d{2})\s+([^\d\|][^\|]*?)(?:\s+(Jogos.*?))?(?:\s*\|\s*(\S+))?$', line)
    if m:
        hora, titulo, comentario, canal = m.groups()
        # Ignorar títulos muito curtos ou caracteres sozinhos
        if not titulo or len(titulo.strip()) <= 1:
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
# Tentar pegar a data correta da agenda (ex: "EIRA, 02/09/2025")
data_match = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
if data_match:
    today_str = datetime.strptime(data_match.group(1), "%d/%m/%Y").strftime("%Y-%m-%d")
else:
    today_str = datetime.now().strftime('%Y-%m-%d')

for ev in events:
    e = Event()
    e.name = ev["titulo"]
    # Transformar hora 06h00 -> 06:00
    hora_iso = ev["hora"].replace("h", ":")
    e.begin = f"{today_str} {hora_iso}"
    e.description = f"{ev['comentario']} | {ev['canal']}" if ev["comentario"] or ev["canal"] else ""
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
