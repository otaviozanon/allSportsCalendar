import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timedelta
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

    # Regex para capturar: hora | título | comentário | canal
    m = re.match(r'(\d{2}h\d{2})\s+(.*)', line)
    if not m:
        continue

    hora, resto = m.groups()

    # Ignorar linhas que começam com símbolo estranho ou números isolados
    if resto.startswith('|') or re.match(r'^\d+$', resto.strip().split()[0]):
        continue

    # Separar título, comentário e canal se houver '|'
    partes = resto.split('|')
    titulo = partes[0].strip()
    descricao = " | ".join(p.strip() for p in partes[1:]).strip() if len(partes) > 1 else ""
    canal = ""  # Podemos preencher se houver lista específica de canais

    events.append({
        "hora": hora,
        "titulo": titulo,
        "descricao": descricao,
        "canal": canal
    })

# --- Criar calendário ---
cal = Calendar()
today_str = datetime.now().strftime('%Y-%m-%d')
for ev in events:
    e = Event()
    e.name = ev["titulo"]
    e.begin = datetime.strptime(f"{today_str} {ev['hora']}", "%Y-%m-%d %Hh%M")
    e.description = f"{ev['descricao']} | {ev['canal']}" if ev['canal'] else ev['descricao']
    e.duration = timedelta(hours=MAX_EVENT_DURATION_HOURS)
    e.uid = ev["titulo"]
    cal.events.add(e)
    print(f"✅ Adicionado: {ev['titulo']} - {ev['hora']}")

# --- Salvar arquivo ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in cal.serialize_iter():
        f.write(line + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now().isoformat()}\n")

print("🔹 calendar.ics atualizado!")
