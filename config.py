"""Configuración central del bot.

Carga las variables de entorno (.env), construye el cliente Spotify OAuth y la
instancia compartida de Discord (`bot`), y expone los helpers reutilizados por
los módulos de `comandos` y `events`.
"""

import os

import discord
import requests
import spotipy
from discord.ext import commands
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv(dotenv_path="./.env")


# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=  CONFIGURACIÓN FUNCIONAL  +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=

# ----------------- Cargar .env -----------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# URL de tu web service en Render
SPOTIFY_SERVICE_URL = os.getenv("SPOTIFY_SERVICE_URL", "https://chatbot-spotify.onrender.com")

print(f"🔗 Conectando al servicio: {SPOTIFY_SERVICE_URL}")

# ----------------- SpotifyOAuth helper -----------------
sp_oauth_helper = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=(
        "user-read-private "
        "user-read-email "
        "user-top-read "
        "playlist-modify-private "
        "playlist-modify-public "
        "playlist-read-private "
        "playlist-read-collaborative "
        "user-read-recently-played "
        "user-read-playback-state "
        "user-modify-playback-state "
        "user-read-currently-playing "
        "user-library-read "
        "user-library-modify "
        "streaming"
    ),
    open_browser=False
)

# ----------------- Discord bot -----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------- Helpers para tokens -----------------
def get_access_token_for_user(discord_id):
    """
    Obtiene token desde el web service remoto (con PostgreSQL)
    """
    url = f"{SPOTIFY_SERVICE_URL}/get_token?discord_id={discord_id}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        token_info = r.json()
        
        # El web service ya maneja el refresh automáticamente
        access = token_info.get("access_token")
        
        if access:
            print(f"✅ Token obtenido para {discord_id}")
        
        return access
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Usuario {discord_id} no tiene token (no ha hecho login)")
        else:
            print(f"❌ Error HTTP al obtener token: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al obtener token: {e}")
        return None

def make_spotify_client_for_user(discord_id):
    """Crea cliente Spotify con token del web service"""
    token = get_access_token_for_user(discord_id)
    if not token:
        return None
    return spotipy.Spotify(auth=token)


def extraer_link_spotify(resultado_busqueda):
    """Extrae el link de Spotify de un resultado de búsqueda"""
    try:
        if 'external_urls' in resultado_busqueda:
            return resultado_busqueda['external_urls']['spotify']
        return None
    except:
        return None


def proceso_crear_playlist_pesado(sp, nombre_pl, canciones):
    # Esta función contiene todo el código BLOQUEANTE de Spotify
    user_sp = sp.current_user()['id']
    pl = sp.user_playlist_create(user_sp, name=nombre_pl, public=True)
    uris = []
    for c in canciones:
        # Búsqueda síncrona (está bien porque estamos en otro hilo)
        r = sp.search(q=c, limit=1)
        if r['tracks']['items']:
            uris.append(r['tracks']['items'][0]['uri'])
    
    if uris:
        sp.playlist_add_items(pl['id'], uris)
    
    return pl['external_urls']['spotify']
