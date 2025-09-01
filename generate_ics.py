import os
import requests
from ics import Calendar, Event
from datetime import datetime, timedelta, timezone
import pytz
import re
from io import BytesIO
from PIL import Image
import pytesseract

# --- Configurações ---
X_USER = "EsportesNaTV"
BR_TZ = pytz.timezone("America/Sao_Paulo")
MAX_AGE_DAYS = 30

# --- Palavras-chave para esportes ---
SPORT_KEYWORDS = {
    # Futebol
    "brasileirao": "Futebol",
    "camp. japones": "Futebol",
    "premierleague": "Futebol",
    "la liga": "Futebol",
    "bundesliga": "Futebol",
    "serie a italiana": "Futebol",
    "serie b italiana": "Futebol",

    # Tênis
    "us open (masc)": "Tênis Masculino",
    "us open (fem)": "Tênis Feminino",
    "wta": "Tênis",

    # Beisebol
    "mlb": "Beisebol",

    # Basquete
    "eurobasket": "Basquete",

    # Vôlei
    "mundial de vlei": "Vôlei",

    # Surf e Futsal
    "surf": "Surf",
    "futsal": "Futsal",

    # Corrida
    "f1 academy": "Corrida",
    "formula 1": "Corrida",
    "porsche endurance": "Corrida",
    "moto gp": "Corrida",

    # Ciclismo
    "ciclismo": "Ciclismo"
}

def identificar_esportes(texto: str) -> list:
    texto_lower = texto.lower()
    encontrados = []
    for key, esporte in SPORT_KEYWORDS.items():
        if key in texto_lower:
            encontrados.append(esporte)
    return list(set(encontrados))  # Remove duplicados

# --- Helpers ---
def remove_emojis(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text)

def get_last_image_url(user: str) -> str:
    """
    Busca a última imagem do usuário usando X/Twitter API v2
    Precisa de X_BEARER_TOKEN no env
    """
    headers = {"Authorization": f"Bearer {os.environ['X_BEARER_TOKEN']}"}
    # Pegando ID do usuário
    resp_user = requests.get(f"https://api.twitter.com/2/users/by/username/{user}", headers=headers)
    resp_user.raise_for_status()
    user_id = resp_user.json()["data"]["id"]

    # Pegando últimos tweets com mídia
    resp = requests.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        headers=headers,
        params={
            "max_results": 5,
            "expansions": "attachments.media_keys",
            "media.fields": "url,type"
        }
    )
    resp.raise_for_status()
    data = resp.json()
    if "includes" in data and "media" in data["includes"]:
        for media in data["includes"]["media"]:
            if media["type"] == "photo":
                return media["url"]
    raise Exception("Não foi possível encontrar a URL da imagem")

# --- Carregar ou criar calendar.ics ---
my_calendar = Calendar()
if os.path.exists("calendar.ics"):
    with open("calendar.ics", "r", encoding="utf-8") as f:
        try:
            cleaned_lines = [line for line in f.readlines() if not line.startswith(";")]
            for cal in Calendar.parse_multiple("".join(cleaned_lines)):
                my_calendar.events.update(cal.events)
        except Exception as e:
            print(f"⚠️ Não foi possível carregar o calendário antigo: {e}")

# --- Limpar eventos antigos ---
now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(days=MAX_AGE_DAYS)
my_calendar.events = {ev for ev in my_calendar.events if ev.begin and ev.begin > cutoff_time}

# --- Baixar imagem e ler texto ---
print(f"🔹 Pegando última imagem de {X_USER}")
img_url = get_last_image_url(X_USER)
print(f"🔹 URL da imagem: {img_url}")
response = requests.get(img_url)
response.raise_for_status()
img = Image.open(BytesIO(response.content))

texto = pytesseract.image_to_string(img, lang="por")
texto = remove_emojis(texto)
print(f"🔹 Texto extraído da imagem:\n{texto}")

# --- Identificar esportes ---
esportes = identificar_esportes(texto)
added_count = 0
for esporte in esportes:
    ev = Event()
    ev.name = esporte
    ev.begin = now_utc  # Pode ajustar se quiser hora do evento
    ev.duration = timedelta(hours=2)
    ev.uid = f"{ev.name}-{ev.begin.timestamp()}"
    my_calendar.events.add(ev)
    print(f"✅ Adicionado: {esporte}")
    added_count += 1

print(f"📌 {added_count} novos eventos adicionados.")

# --- Salvar calendar.ics ---
with open("calendar.ics", "w", encoding="utf-8") as f:
    for line in my_calendar.serialize_iter():
        f.write(remove_emojis(line) + "\n")
    f.write(f"X-GENERATED-TIME:{datetime.now(timezone.utc).isoformat()}\n")
print("🔹 calendar.ics atualizado!")
