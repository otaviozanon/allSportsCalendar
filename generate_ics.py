import os
import requests
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timezone, timedelta
import pytz
import re
from PIL import Image
import pytesseract
import warnings

warnings.filterwarnings(
    "ignore", category=FutureWarning, message=r"Behaviour of str\(Component\) will change in version 0.9.*"
)

# --- Configurações ---
X_USER_ID = "1112832962486329344"  # EsportesNaTV
BR_TZ = pytz.timezone('America/Sao_Paulo')
MAX_AGE_DAYS = 30

# --- Funções ---
def remove_emojis(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]+', '', text)

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

def parse_event_line(line: str):
    """Extrai hora, título, comentário e canal da linha"""
    line = line.strip()
    # Separar pelo pipe ou espaços múltiplos
    parts = [p.strip() for p in re.split(r'\s+\|\s+|\s{2,}', line) if p.strip()]
    if len(parts) >= 2:
        hour = parts[0]
        title = parts[1]
        comment = parts[2] if len(parts) >= 3 else ""
        channel = parts[3] if len(parts) >= 4 else ""
        if channel:
            comment = f"{comment} | {channel}" if comment else channel
        return hour, title, comment
    return None, None, None

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

# --- Baixar última imagem ---
print(f"🔹 Pegando última imagem de EsportesNaTV")
img_url = get_last_image_url(X_USER_ID)
print(f"🔹 URL da imagem: {img_url}")
response = requests.get(img_url)
img = Image.open(BytesIO(response.content))

# --- OCR ---
texto = pytesseract.image_to_string(img, lang='por')
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Extrair eventos ---
added_count = 0
for line in texto.splitlines():
    hour_str, title, comment = parse_event_line(line)
    if not hour_str or not title:
        continue

    # Criar evento
    try:
        ev = Event()
        # Substitui possíveis ":" ou "." por "h" para evitar erro
        hour_str = hour_str.replace(":", "h").replace(".", "h")
        ev_time = datetime.strptime(hour_str, "%Hh%M").replace(
            year=now_utc.year, month=now_utc.month, day=now_utc.day,
            tzinfo=BR_TZ
        )
        ev.name = title
        ev.begin = ev_time
        ev.duration = timedelta(hours=2)
        ev.description = comment
        ev.uid = f"{title}-{hour_str}"
        
        # Evita duplicação
        if not any(e.uid == ev.uid for e in my_calendar.events):
            my_calendar.events.add(ev)
            print(f"✅ Adicionado: {title}")
            added_count += 1
    except Exception as e:
        print(f"⚠️ Erro ao processar linha: {line} | {e}")

print(f"📌 {added_count} novos eventos adicionados.")

# --- Salvar calendar.ics ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")

print("🔹 calendar.ics atualizado!")
