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
current_event = None

for line in texto.splitlines():
    line = line.strip()
    if not line or len(line) < 5:
        continue

    # Detecta linha que começa com hora
    m = re.match(r'(\d{2}h\d{2})\s+(.*)', line)
    if m:
        hora, rest = m.groups()
        # Se houver evento anterior, adiciona à lista
        if current_event:
            events.append(current_event)

        # Cria novo evento
        current_event = {
            "hora": hora,
            "titulo": rest.split('|')[0].strip(),  # título antes de |
            "descricao": '',                        # será preenchido nas linhas seguintes
            "canal": rest.split('|')[1].strip() if '|' in rest else ''
        }
    else:
        # Linhas seguintes são descrições adicionais
        if current_event:
            if current_event["descricao"]:
                current_event["descricao"] += " | " + line
            else:
                current_event["descricao"] = line

# Adiciona último evento
if current_event:
    events.append(current_event)

print("✅ Eventos parseados:")
for ev in events:
    print(ev)

# --- Criar calendário ---
cal = Calendar()
today_str = datetime.now().strftime('%Y-%m-%d')

for ev in events:
    # Ignora eventos com título vazio ou só símbolos
    if not re.search(r'[A-Za-z0-9]', ev["titulo"]):
        continue

    e = Event()
    e.name = ev["titulo"]
    # Ajusta hora para formato ISO
    hora_iso = ev["hora"].replace('h', ':')
    e.begin = f"{today_str} {hora_iso}"
    e.description = ev["descricao"] + (" | " + ev["canal"] if ev["canal"] else "")
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
