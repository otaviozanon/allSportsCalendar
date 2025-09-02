import os
import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import re
from PIL import Image
import pytesseract

# --- Configurações ---
X_USER_ID = "1112832962486329344"  # EsportesNaTV
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30

# --- Funções ---
def get_last_image_url(user_id: str):
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        raise Exception("X_BEARER_TOKEN não configurado")

    headers = {"Authorization": f"Bearer {bearer}"}
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&expansions=attachments.media_keys&media.fields=url,type"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    for tweet in data.get("data", []):
        media_keys = tweet.get("attachments", {}).get("media_keys", [])
        for key in media_keys:
            for m in data.get("includes", {}).get("media", []):
                if m["media_key"] == key and m["type"] == "photo":
                    return m["url"]
    raise Exception("Não foi possível encontrar a URL da imagem")

def parse_events(text: str):
    """
    Extrai eventos do OCR:
    Formato esperado na imagem:
    06h00 | WTA125 Montreux | Jogos de 1º Rodada | XSPORTS
    """
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Regex para extrair hora, título, comentário/canal
        match = re.match(r"(\d{2}h\d{2})\s*[|]\s*(.+?)\s*[|]\s*(.+?)(?:\s*[|]\s*(.+))?$", line)
        if match:
            hora, titulo, comentario, canal = match.groups()
            events.append({
                "hora": hora,
                "titulo": titulo.strip(),
                "comentario": comentario.strip(),
                "canal": canal.strip() if canal else ""
            })
    return events

# --- Data e horário ---
now_utc = datetime.now(pytz.utc)
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
                print("🔹 calendar.ics antigo carregado.")
            except Exception as e:
                print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

# --- Limpar eventos antigos ---
old_count = len(my_calendar.events)
my_calendar.events = { ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time }
print(f"🧹 Removidos {old_count - len(my_calendar.events)} eventos antigos.")

# --- Baixar última imagem ---
print(f"🔹 Pegando última imagem de EsportesNaTV")
img_url = get_last_image_url(X_USER_ID)
print(f"🔹 URL da imagem: {img_url}")
response = requests.get(img_url)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Parsear eventos ---
parsed_events = parse_events(texto)

# --- Adicionar eventos ao calendário ---
added_count = 0
for ev_info in parsed_events:
    # Converter hora Brasil -> UTC
    today = datetime.now(BR_TZ).date()
    hour, minute = map(int, ev_info["hora"].replace("h", ":").split(":"))
    dt_local = BR_TZ.localize(datetime(today.year, today.month, today.day, hour, minute))
    dt_utc = dt_local.astimezone(pytz.utc)

    uid = f"{ev_info['titulo'].replace(' ','-')}-{dt_local.strftime('%Y%m%dT%H%M')}"
    if any(ev.uid == uid for ev in my_calendar.events):
        continue  # Evitar duplicação

    ev = Event()
    ev.begin = dt_utc
    ev.duration = timedelta(hours=2)
    ev.name = ev_info["titulo"]
    ev.description = f"{ev_info['comentario']}" + (f" - Canal: {ev_info['canal']}" if ev_info['canal'] else "")
    ev.uid = uid
    my_calendar.events.add(ev)
    print(f"✅ Adicionado: {ev.name} às {ev_info['hora']}")
    added_count += 1

print(f"📌 {added_count} novos eventos adicionados.")

# --- Salvar ICS ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(line + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(pytz.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
