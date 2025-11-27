"""bot.py - Bot de Discord completo integrado con Spotify
Requisitos:
- Tener .env con DISCORD_TOKEN, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
- Tener spotify_auth.py ejecutado al menos una vez para generar tokens.json (el login guarda tokens por usuario)
- pip install discord.py spotipy python-dotenv

Este archivo usa tokens.json (guardado por spotify_auth) para autenticar a cada usuario individualmente.
"""

import os
import json
import time
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests

# Cargar .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
# URL de tu web service en Render
SPOTIFY_SERVICE_URL = "https://spotify-auth-55xa.onrender.com"

TOKENS_FILE = "tokens.json"

# SpotifyOAuth helper (usado solo para refrescar si tenemos refresh_token)
sp_oauth_helper = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope = (
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
    "streaming"),
    open_browser=False
)

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_spotify_token(discord_id):
    url = f"{SPOTIFY_SERVICE_URL}/get_token?discord_id={discord_id}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener token: {e}")
        return None

@bot.command()
async def login(ctx):
    auth_url = f"{SPOTIFY_SERVICE_URL}/login?discord_id={ctx.author.id}"
    await ctx.send(f"🔗 Inicia sesión en Spotify:\n{auth_url}")

@bot.command()
async def test_token(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado.")
        return
    
    try:
        # Probar diferentes endpoints
        user = sp.current_user()
        await ctx.send(f"✅ Usuario: {user.get('display_name', user.get('id'))}")
        await ctx.send(f"✅ País: {user.get('country', 'N/A')}")
        
        # Probar búsqueda simple
        search = sp.search(q="test", limit=1, type="track")
        await ctx.send(f"✅ Búsqueda funciona")
        
        # Probar recomendaciones con género simple
        recs = sp.recommendations(seed_genres=["pop"], limit=5, market=user.get('country', 'US'))
        await ctx.send(f"✅ Recomendaciones funcionan: {len(recs['tracks'])} canciones")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# ------------------- Helpers para tokens -------------------

def read_tokens():
    if not os.path.exists(TOKENS_FILE):
        return {}
    with open(TOKENS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def write_tokens(data):
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_raw_token_entry(discord_id):
    data = read_tokens()
    return data.get(str(discord_id))


def normalize_token_entry(entry):
    """Normaliza varias formas de token guardado:
    - Si entry es string -> {'access_token': entry}
    - Si entry es dict con access_token -> devuelve tal cual
    - Si entry es dict con other keys -> devuelve tal cual
    """
    if not entry:
        return None
    if isinstance(entry, str):
        return {"access_token": entry}
    if isinstance(entry, dict):
        return entry
    return None


def refresh_if_needed(token_entry):
    """Si tenemos refresh_token y expires_at, refresca y guarda.
    Devuelve access_token o None si no es posible.
    """
    if not token_entry:
        return None
    access = token_entry.get("access_token")
    refresh = token_entry.get("refresh_token")
    expires_at = token_entry.get("expires_at")

    # Si no hay info de expiración, devolver el access tal cual (sujeto a caducidad)
    if not refresh or not expires_at:
        return access

    if time.time() < expires_at - 60:
        return access

    # Refrescar usando helper
    try:
        new = sp_oauth_helper.refresh_access_token(refresh)
        # new normalmente contiene 'access_token' y 'expires_in'
        token_entry["access_token"] = new.get("access_token")
        token_entry["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600))
        # si viene refresh_token, actualizar
        if new.get("refresh_token"):
            token_entry["refresh_token"] = new.get("refresh_token")

        # guardar en tokens.json
        data = read_tokens()
        # buscar la clave que contiene este entry (por valor)
        for k, v in data.items():
            # comparar por access_token o refresh_token
            if isinstance(v, dict) and v.get("refresh_token") == refresh or v == refresh:
                data[k] = token_entry
                break
        write_tokens(data)

        return token_entry.get("access_token")
    except Exception as e:
        print("Error al refrescar token:", e)
        return None


def get_access_token_for_user(discord_id):
    entry = get_raw_token_entry(discord_id)
    normalized = normalize_token_entry(entry)
    if not normalized:
        return None
    token = refresh_if_needed(normalized)
    return token


def make_spotify_client_for_user(discord_id):
    token = get_access_token_for_user(discord_id)
    if not token:
        return None
    return spotipy.Spotify(auth=token)

# ------------------- Eventos y comandos -------------------

@bot.event
async def on_ready():
    print(f"Bot listo como {bot.user}")


@bot.command()
async def comandos(ctx):
    """Menú principal de comandos - Muestra todas las categorías"""
    embed = discord.Embed(
        title="🎧 Comandos del Bot de Spotify",
        description="Usa `!comandos_<categoría>` para ver comandos específicos",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📋 Categorías Disponibles", 
        value=(
            "`!comandos_basicos` - Autenticación y reproducción\n"
            "`!comandos_playlists` - Crear y gestionar playlists\n"
            "`!comandos_busqueda` - Buscar música y podcasts\n"
            "`!comandos_stats` - Estadísticas y análisis\n"
            "`!comandos_social` - Comparar con otros usuarios\n"
            "`!comandos_tematicas` - Playlists por ocasión\n"
            "`!comandos_auto` - Generadores automáticos\n"
            "`!comandos_colaboracion` - Playlists colaborativas"
        ),
        inline=False
    )
    
    embed.set_footer(text="💡 Ejemplo: !comandos_stats para ver comandos de estadísticas")

    await ctx.send(embed=embed)


@bot.command()
async def comandos_basicos(ctx):
    embed = discord.Embed(title="🎵 Comandos Básicos", color=discord.Color.green())
    
    embed.add_field(
        name="🔐 Autenticación", 
        value=(
            "`!login` - Iniciar sesión\n"
            "`!verificar` - Ver estado de conexión"
        ),
        inline=False
    )
    
    embed.add_field(
        name="▶️ Reproducción", 
        value=(
            "`!play <canción>` - Reproducir\n"
            "`!pause` - Pausar\n"
            "`!resume` - Reanudar\n"
            "`!next` - Siguiente\n"
            "`!prev` - Anterior\n"
            "`!song` - Canción actual\n"
            "`!volume <0-100>` - Ajustar volumen"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_playlists(ctx):
    embed = discord.Embed(title="📝 Gestión de Playlists", color=discord.Color.blue())
    
    embed.add_field(
        name="➕ Crear y Modificar", 
        value=(
            "`!crear_playlist <nombre>` - Crear playlist vacía\n"
            "`!agregar_playlist <playlist> <canción>` - Agregar canción\n"
            "`!playlist <mood>` - Crear automática por mood\n"
            "`!radio <artista/tema>` - Crear radio\n"
            "`!mix <tema>` - Crear mix temático"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 Organización", 
        value=(
            "`!fusion <playlist1> <playlist2>` - Fusionar playlists\n"
            "`!limpiarplaylist <nombre>` - Quitar duplicados\n"
            "`!limpiar_biblioteca` - Limpiar todas las playlists\n"
            "`!duplicados` - Ver duplicados en biblioteca"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_busqueda(ctx):
    embed = discord.Embed(title="🔍 Búsqueda y Biblioteca", color=discord.Color.orange())
    
    embed.add_field(
        name="🔎 Buscar", 
        value=(
            "`!buscar_cancion <texto>` - Buscar canciones\n"
            "`!buscar_artista <texto>` - Buscar artistas\n"
            "`!buscar_album <texto>` - Buscar álbumes"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💾 Biblioteca", 
        value=(
            "`!guardar <link>` - Guardar canción\n"
            "`!like <texto>` - Buscar y guardar\n"
            "`!unlike <texto>` - Eliminar guardada\n"
            "`!mislikes` - Ver canciones guardadas"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎙️ Podcasts", 
        value=(
            "`!podcast_tendencias` - Podcasts populares\n"
            "`!podcast_episodios <nombre>` - Ver episodios"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_stats(ctx):
    embed = discord.Embed(title="📊 Estadísticas y Análisis", color=discord.Color.purple())
    
    embed.add_field(
        name="📈 Tu Perfil Musical", 
        value=(
            "`!estadisticas` - Resumen completo\n"
            "`!wrapped` - Tu Spotify Wrapped\n"
            "`!top_artistas` - Top 5 artistas\n"
            "`!top_tracks` - Top 5 canciones\n"
            "`!historial [cantidad]` - Últimas canciones (máx 50)\n"
            "`!obsesion` - Tu canción más repetida"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔬 Análisis de Audio", 
        value=(
            "`!analizar <canción>` - BPM, energía, positividad\n"
            "`!similares <canción>` - Canciones parecidas\n"
            "`!energia` - Playlist de alta energía\n"
            "`!relajante` - Playlist tranquila"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_social(ctx):
    embed = discord.Embed(title="👥 Comandos Sociales", color=discord.Color.gold())
    
    embed.add_field(
        name="🤝 Comparaciones", 
        value=(
            "`!compatibilidad @usuario` - % de gustos similares\n"
            "`!vs @usuario` - Comparar perfiles musicales\n"
            "`!batalla <artista1> vs <artista2>` - Votar\n"
            "`!ranking_servidor` - Top del servidor"
        ),
        inline=False
    )
    
    """embed.add_field(
        name="🎮 Juegos", 
        value=(
            "`!adivina` - Adivina el artista\n"
            "`!trivia` - Trivia musical\n"
            "`!ruleta` - Canción aleatoria"
        ),
        inline=False
    )"""

    await ctx.send(embed=embed)


@bot.command()
async def comandos_tematicas(ctx):
    embed = discord.Embed(title="🎨 Playlists Temáticas", color=discord.Color.teal())
    
    embed.add_field(
        name="🏃 Actividades", 
        value=(
            "`!gym` - Para entrenar\n"
            "`!estudio` - Para concentrarse\n"
            "`!cocinar` - Música para cocinar\n"
            "`!dormir` - Para dormir\n"
            "`!viaje` - Road trip playlist"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💝 Ocasiones", 
        value=(
            "`!romantica` - Canciones románticas\n"
            "`!fiesta` - Para fiestas\n"
            "`!cumpleanos` - Celebración\n"
            "`!navidad` - Música navideña (temporada)"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_auto(ctx):
    embed = discord.Embed(title="🤖 Generadores Automáticos", color=discord.Color.magenta())
    
    embed.add_field(
        name="🎭 Por Estado de Ánimo", 
        value=(
            "`!mood <emoji>` - Playlist según emoji\n"
            "Emojis: 😊😢😡🔥💤💪❤️🎉☕🌙🏖️🎮"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🌍 Contextuales", 
        value=(
            "`!playlist_clima` - Según el clima actual\n"
            "`!playlist_hora` - Según la hora del día\n"
            "`!decada <año>` - Música de los 80s, 90s, etc.\n"
            "`!retro` - Clásicos aleatorios"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Personalizadas", 
        value=(
            "`!descubre` - Recomendaciones personalizadas\n"
            "`!explorar` - Géneros nuevos para ti\n"
            "`!recomienda_artista` - Artista aleatorio\n"
            "`!recomienda_canciones` - Por género aleatorio"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def comandos_colaboracion(ctx):
    embed = discord.Embed(title="🤝 Playlists Colaborativas", color=discord.Color.red())
    
    embed.add_field(
        name="👥 Crear y Compartir", 
        value=(
            "`!colaborativa <nombre>` - Crear playlist colaborativa\n"
            "`!invitar @usuario <playlist>` - Invitar a editar\n"
            "`!publicas` - Ver tus playlists públicas\n"
            "`!hacer_publica <playlist>` - Hacer pública\n"
            "`!hacer_privada <playlist>` - Hacer privada"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 Sugerencias", 
        value=(
            "`!sugerir <playlist> <canción>` - Sugerir canción\n"
            "`!ver_sugerencias <playlist>` - Ver sugerencias\n"
            "`!aceptar_sugerencia <playlist> <#>` - Aceptar\n"
            "`!rechazar_sugerencia <playlist> <#>` - Rechazar"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎵 Sesiones Grupales", 
        value=(
            "`!sesion_grupal <nombre>` - Crear sesión\n"
            "`!unirse_sesion <nombre>` - Unirse\n"
            "`!votar_cancion <canción>` - Votar siguiente\n"
            "`!cola_grupal` - Ver cola de votación"
        ),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def verificar(ctx):
    token = get_raw_token_entry(ctx.author.id)
    if not token:
        await ctx.send("🔴 No estás logueado. Usa !login y sigue el link que te envía el bot.")
        return
    normalized = normalize_token_entry(token)
    access = normalized.get("access_token") if normalized else None
    if not access:
        await ctx.send("🟡 Tienes un token guardado pero incompleto. Usa !login.")
        return
    # verificar llamando a spotify
    try:
        sp = spotipy.Spotify(auth=access)
        user = sp.current_user()
        await ctx.send(f"🟢 Estás logueado como **{user.get('display_name', user.get('id'))}**")
    except Exception as e:
        await ctx.send("🔴 Token inválido o expirado. Usa !login para renovar.")


# ------------------- Comandos de reproducción -------------------
@bot.command()
async def play(ctx, *, query):
    if query is None:
        await ctx.send("❌ Debes escribir una canción.\nEjemplo: `!play viva la vida`")
        return

    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login para conectar tu cuenta de Spotify.")
        return

    results = sp.search(q=query, limit=1, type="track")
    if not results["tracks"]["items"]:
        await ctx.send("❌ No encontré la canción.")
        return
    track = results["tracks"]["items"][0]

    devices = sp.devices().get("devices", [])
    if not devices:
        await ctx.send("⚠️ No hay dispositivos activos. Abre Spotify en un dispositivo y reintenta.")
        return
    device_id = devices[0]["id"]
    sp.start_playback(device_id=device_id, uris=[track["uri"]])
    await ctx.send(f"▶️ Reproduciendo **{track['name']}** — {track['artists'][0]['name']}")


@bot.command()
async def pause(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.pause_playback()
        await ctx.send("⏸️ Pausado")
    except Exception:
        await ctx.send("⚠️ No se pudo pausar.")


@bot.command()
async def resume(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.start_playback()
        await ctx.send("▶️ Reanudado")
    except Exception:
        await ctx.send("⚠️ No se pudo reanudar.")


@bot.command()
async def next(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.next_track()
        await ctx.send("⏭️ Siguiente")
    except Exception:
        await ctx.send("⚠️ No se pudo saltar.")


@bot.command()
async def prev(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.previous_track()
        await ctx.send("⏮️ Anterior")
    except Exception:
        await ctx.send("⚠️ No se pudo regresar.")


@bot.command()
async def song(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    current = sp.current_playback()
    if not current or not current.get("item"):
        await ctx.send("❌ No hay nada reproduciéndose.")
        return

    t = current["item"]
    url = t["external_urls"]["spotify"]

    await ctx.send(
        f"🎧 Sonando ahora:\n**{t['name']}** — {t['artists'][0]['name']}\n{url}"
    )

@bot.command()
async def volume(ctx, level: int):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    if level < 0 or level > 100:
        await ctx.send("🔊 El volumen debe estar entre 0 y 100.")
        return

    try:
        sp.volume(level)
        await ctx.send(f"🔊 Volumen ajustado al {level}%")
    except Exception:
        await ctx.send("⚠️ No se pudo cambiar el volumen.")

# ------------------- Playlists y recomendaciones -------------------
@bot.command()
async def playlist(ctx, *, mood):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    results = sp.search(q=mood, type="track", limit=30)
    tracks = [t["uri"] for t in results["tracks"]["items"]]
    if not tracks:
        await ctx.send("❌ No encontré canciones para ese mood.")
        return
    user = sp.current_user()["id"]
    pl = sp.user_playlist_create(user, f"Playlist: {mood}", public=False)
    sp.playlist_add_items(pl["id"], tracks[:50])
    await ctx.send(f"✅ Playlist creada: {pl['external_urls']['spotify']}")


@bot.command()
async def radio(ctx, *, base):
    """
    Comando !radio que funciona SIN el endpoint de recommendations
    Usa búsquedas avanzadas y playlists de Spotify en su lugar
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send(f"🔍 Creando radio para: **{base}**...")
    
    all_tracks = []
    
    # Estrategia 1: Buscar el término directamente y obtener tracks relacionados
    try:
        # Buscar artista
        artist_search = sp.search(q=base, limit=1, type="artist")
        if artist_search.get("artists", {}).get("items"):
            artist = artist_search["artists"]["items"][0]
            artist_id = artist["id"]
            artist_name = artist["name"]
            
            print(f"🎤 Artista encontrado: {artist_name}")
            
            # Obtener álbumes del artista
            albums = sp.artist_albums(artist_id, limit=5, album_type='album,single')
            
            for album in albums.get("items", [])[:3]:  # Primeros 3 álbumes
                tracks = sp.album_tracks(album["id"], limit=10)
                for track in tracks.get("items", []):
                    if len(all_tracks) < 30:
                        all_tracks.append(track["uri"])
            
            print(f"✅ {len(all_tracks)} tracks del artista agregados")
    except Exception as e:
        print(f"❌ Error buscando artista: {e}")
    
    # Estrategia 2: Si no hay suficientes, buscar canciones relacionadas
    if len(all_tracks) < 20:
        try:
            track_search = sp.search(q=base, limit=20, type="track")
            for track in track_search.get("tracks", {}).get("items", []):
                if track["uri"] not in all_tracks and len(all_tracks) < 30:
                    all_tracks.append(track["uri"])
            
            print(f"✅ Total con búsqueda de tracks: {len(all_tracks)}")
        except Exception as e:
            print(f"❌ Error buscando tracks: {e}")
    
    # Estrategia 3: Buscar playlists públicas relacionadas
    if len(all_tracks) < 30:
        try:
            playlist_search = sp.search(q=base, limit=3, type="playlist")
            for playlist in playlist_search.get("playlists", {}).get("items", []):
                if len(all_tracks) >= 30:
                    break
                
                pl_tracks = sp.playlist_tracks(playlist["id"], limit=15)
                for item in pl_tracks.get("items", []):
                    if item.get("track") and item["track"].get("uri"):
                        if item["track"]["uri"] not in all_tracks and len(all_tracks) < 30:
                            all_tracks.append(item["track"]["uri"])
            
            print(f"✅ Total con playlists: {len(all_tracks)}")
        except Exception as e:
            print(f"❌ Error buscando playlists: {e}")
    
    # Verificar que tenemos tracks
    if len(all_tracks) == 0:
        await ctx.send(f"❌ No pude encontrar música para '{base}'.\nIntenta con un artista más conocido o un género en inglés.")
        return
    
    # Eliminar duplicados manteniendo orden
    unique_tracks = []
    seen = set()
    for uri in all_tracks:
        if uri not in seen:
            unique_tracks.append(uri)
            seen.add(uri)
    
    print(f"📊 Tracks únicos finales: {len(unique_tracks)}")
    
    try:
        # Crear la playlist
        user = sp.current_user()["id"]
        pl = sp.user_playlist_create(user, f"Radio: {base}", public=False)
        
        # Agregar tracks en lotes de 100 (límite de Spotify)
        for i in range(0, len(unique_tracks), 100):
            batch = unique_tracks[i:i+100]
            sp.playlist_add_items(pl["id"], batch)
        
        msg = f"📻 **Radio creada**: {pl['external_urls']['spotify']}\n\n"
        msg += f"🎵 **{len(unique_tracks)} canciones** agregadas\n"
        msg += f"✨ Mix basado en búsquedas y playlists relacionadas"
        
        await ctx.send(msg)
        print(f"✅ Playlist creada exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando playlist: {e}")
        await ctx.send(f"❌ Error al crear la playlist: {str(e)}")


# Comando alternativo usando géneros predefinidos
@bot.command()
async def radio_genero(ctx, *, genero):
    """
    Radio por género - usa playlists curadas de Spotify
    Ejemplo: !radio_genero rock, !radio_genero reggaeton
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send(f"🔍 Buscando playlists de **{genero}**...")
    
    try:
        # Buscar playlists oficiales del género
        search_queries = [
            f"{genero} mix",
            f"{genero} hits",
            f"best of {genero}",
            f"{genero} essentials"
        ]
        
        all_tracks = []
        
        for query in search_queries:
            if len(all_tracks) >= 30:
                break
                
            playlists = sp.search(q=query, limit=2, type="playlist")
            
            for playlist in playlists.get("playlists", {}).get("items", []):
                if len(all_tracks) >= 30:
                    break
                
                # Obtener tracks de la playlist
                pl_tracks = sp.playlist_tracks(playlist["id"], limit=20)
                
                for item in pl_tracks.get("items", []):
                    if len(all_tracks) >= 30:
                        break
                    
                    if item.get("track") and item["track"].get("uri"):
                        if item["track"]["uri"] not in all_tracks:
                            all_tracks.append(item["track"]["uri"])
        
        if len(all_tracks) == 0:
            await ctx.send(f"❌ No encontré playlists de '{genero}'.\nIntenta con: pop, rock, hip-hop, jazz, electronic, reggaeton, latin")
            return
        
        # Crear playlist
        user = sp.current_user()["id"]
        pl = sp.user_playlist_create(user, f"Radio {genero.title()}", public=False)
        sp.playlist_add_items(pl["id"], all_tracks)
        
        msg = f"📻 **Radio de {genero.title()}**: {pl['external_urls']['spotify']}\n\n"
        msg += f"🎵 **{len(all_tracks)} canciones** de playlists curadas"
        
        await ctx.send(msg)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en radio_genero: {e}")


@bot.command()
async def recomienda_artista(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    artists = ["The Weeknd", "Bad Bunny", "Ariana Grande", "Daft Punk", "Kendrick Lamar", "Duki", "Peso Pluma"]
    choice = random.choice(artists)
    res = sp.search(q=choice, type="artist", limit=1)
    if not res.get("artists", {}).get("items"):
        await ctx.send("No encontré artistas.")
        return
    a = res["artists"]["items"][0]
    await ctx.send(f"🎤 Recomendado: **{a['name']}** — {a['external_urls']['spotify']}")


@bot.command()
async def recomienda_canciones(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    genres = ["pop", "rock", "rap", "edm", "latin", "reggaeton", "indie"]
    g = random.choice(genres)
    res = sp.search(q=f"genre:{g}", type="track", limit=5)
    items = res["tracks"]["items"]
    if not items:
        await ctx.send("No encontré recomendaciones.")
        return
    msg = f"🎶 Recomendaciones ({g}):"
    for t in items:
        msg += f"- {t['name']} — {t['artists'][0]['name']} ({t['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def guardar(ctx, link):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        tid = link.split('/')[-1].split('?')[0]
        sp.current_user_saved_tracks_add([tid])
        await ctx.send("💾 Guardado en tu biblioteca.")
    except Exception:
        await ctx.send("No pude guardar la canción.")


@bot.command()
async def wrapped(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    tracks = sp.current_user_top_tracks(limit=5)
    artists = sp.current_user_top_artists(limit=5)

    msg = "**🎧 Tu Spotify Wrapped Personal**\n\n"

    msg += "__👥 Top Artistas:__\n"
    for a in artists['items']:
        msg += f"- {a['name']}\n"

    msg += "\n__🎵 Top Canciones:__\n"
    for t in tracks['items']:
        msg += f"- {t['name']} — {t['artists'][0]['name']}\n"

    await ctx.send(msg)

# ------------------- Búsqueda y Biblioteca avanzada -------------------
@bot.command()
async def buscar_cancion(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type="track", limit=5)
    if not res['tracks']['items']:
        await ctx.send('No encontré canciones')
        return
    msg = '**Canciones encontradas:**'
    for t in res['tracks']['items']:
        msg += f"- {t['name']} — {t['artists'][0]['name']} ({t['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def buscar_artista(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='artist', limit=5)
    if not res['artists']['items']:
        await ctx.send('No encontré artistas')
        return
    msg = '**Artistas encontrados:**'
    for a in res['artists']['items']:
        msg += f"- {a['name']} ({a['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def buscar_album(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='album', limit=5)
    if not res['albums']['items']:
        await ctx.send('No encontré álbumes')
        return
    msg = '**Álbumes encontrados:**'
    for a in res['albums']['items']:
        msg += f"- {a['name']} — {a['artists'][0]['name']} ({a['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def like(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    tid = res['tracks']['items'][0]['id']
    sp.current_user_saved_tracks_add([tid])
    await ctx.send(f"Guardado: {res['tracks']['items'][0]['name']}")


@bot.command()
async def unlike(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    tid = res['tracks']['items'][0]['id']
    sp.current_user_saved_tracks_delete([tid])
    await ctx.send('Eliminado')


@bot.command()
async def mislikes(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    saved = sp.current_user_saved_tracks(limit=10)
    if not saved['items']:
        await ctx.send('No tienes canciones guardadas')
        return
    msg = '**Tus últimas canciones guardadas:**'
    for it in saved['items']:
        t = it['track']
        msg += f"- {t['name']} — {t['artists'][0]['name']}"
    await ctx.send(msg)

# ------------------- Podcasts, Playlists avanzadas y exploración -------------------
@bot.command()
async def podcast_tendencias(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    shows = sp.search(q="podcast", type='show', limit=5)
    msg = '**Podcasts populares:**'
    for s in shows['shows']['items']:
        msg += f"- {s['name']} ({s['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def podcast_episodios(ctx, *, show):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=show, type='show', limit=1)
    if not res['shows']['items']:
        await ctx.send('No encontré ese podcast')
        return
    sid = res['shows']['items'][0]['id']
    eps = sp.show_episodes(sid, limit=5)
    msg = f"**Episodios de {res['shows']['items'][0]['name']}:**"
    for e in eps['items']:
        msg += f"- {e['name']} ({e['external_urls']['spotify']})"
    await ctx.send(msg)


@bot.command()
async def crear_playlist(ctx, *, nombre):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    user = sp.current_user()['id']
    pl = sp.user_playlist_create(user, nombre, public=False)
    await ctx.send(f'Playlist creada: {pl["external_urls"]["spotify"]}')


@bot.command()
async def agregar_playlist(ctx, nombre, *, track):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    pls = sp.current_user_playlists()
    pid = None
    for p in pls['items']:
        if p['name'].lower() == nombre.lower():
            pid = p['id']
            break
    if not pid:
        await ctx.send('No encontré esa playlist')
        return
    res = sp.search(q=track, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    sp.playlist_add_items(pid, [res['tracks']['items'][0]['uri']])
    await ctx.send('Añadido')


@bot.command()
async def fusion(ctx, playlist1, playlist2):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    def buscar(nombre):
        pls = sp.current_user_playlists()
        for p in pls['items']:
            if p['name'].lower() == nombre.lower():
                return p['id']
        return None
    p1 = buscar(playlist1)
    p2 = buscar(playlist2)
    if not p1 or not p2:
        await ctx.send('Una de las playlists no existe')
        return
    t1 = sp.playlist_items(p1)['items']
    t2 = sp.playlist_items(p2)['items']
    all_uris = list({x['track']['uri'] for x in t1 + t2})
    user = sp.current_user()['id']
    new = sp.user_playlist_create(user, f'Fusion {playlist1}+{playlist2}', public=False)
    sp.playlist_add_items(new['id'], all_uris)
    await ctx.send(f'Fusion creada: {new["external_urls"]["spotify"]}')


@bot.command()
async def limpiarplaylist(ctx, *, nombre):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    pls = sp.current_user_playlists()
    pid = None
    for p in pls['items']:
        if p['name'].lower() == nombre.lower():
            pid = p['id']
            break
    if not pid:
        await ctx.send('No encontré esa playlist')
        return
    items = sp.playlist_items(pid)['items']
    uris = [i['track']['uri'] for i in items]
    unique = list(dict.fromkeys(uris))
    sp.playlist_replace_items(pid, unique)
    await ctx.send('Playlist limpiada')


@bot.command()
async def top_artistas(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.current_user_top_artists(limit=5)
    msg = '**Tus artistas más escuchados:**'
    for a in res['items']:
        msg += f"- {a['name']}"
    await ctx.send(msg)


@bot.command()
async def top_tracks(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.current_user_top_tracks(limit=5)
    msg = '**Tus canciones más escuchadas:**'
    for t in res['items']:
        msg += f"- {t['name']} — {t['artists'][0]['name']}"
    await ctx.send(msg)


@bot.command()
async def descubre(ctx):
    """
    Recomendaciones personalizadas SIN usar el endpoint de recommendations
    Usa tus artistas favoritos para buscar música similar
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("🔍 Buscando recomendaciones personalizadas...")
    
    try:
        # Obtener tus top 5 artistas
        top_artists = sp.current_user_top_artists(limit=5, time_range='medium_term')
        
        if not top_artists.get('items'):
            await ctx.send("❌ No tienes historial suficiente. Escucha más música en Spotify y vuelve a intentar.")
            return
        
        all_tracks = []
        artist_names = []
        
        for artist in top_artists['items'][:3]:  # Usar top 3
            artist_names.append(artist['name'])
            artist_id = artist['id']
            
            # Obtener artistas relacionados
            try:
                related = sp.artist_related_artists(artist_id)
                
                # De cada artista relacionado, obtener sus top tracks
                for rel_artist in related['artists'][:2]:  # 2 artistas relacionados
                    top_tracks = sp.artist_top_tracks(rel_artist['id'], country='US')
                    
                    for track in top_tracks['tracks'][:3]:  # 3 canciones de cada uno
                        if track['uri'] not in all_tracks and len(all_tracks) < 20:
                            all_tracks.append({
                                'uri': track['uri'],
                                'name': track['name'],
                                'artist': track['artists'][0]['name']
                            })
            except:
                pass
        
        if len(all_tracks) == 0:
            await ctx.send("❌ No pude generar recomendaciones. Intenta más tarde.")
            return
        
        # Crear mensaje con las recomendaciones
        msg = f"**🎵 Recomendaciones basadas en: {', '.join(artist_names)}**\n\n"
        
        for i, track in enumerate(all_tracks[:10], 1):
            msg += f"{i}. **{track['name']}** — {track['artist']}\n"
        
        # Crear playlist opcional
        if len(all_tracks) >= 10:
            msg += f"\n💡 ¿Quieres que cree una playlist con estas {len(all_tracks)} canciones? Usa `!crear_descubrimiento`"
        
        await ctx.send(msg)
        
        # Guardar temporalmente para el comando de crear playlist
        # (guardar en memoria del bot)
        if not hasattr(bot, 'temp_discoveries'):
            bot.temp_discoveries = {}
        bot.temp_discoveries[ctx.author.id] = [t['uri'] for t in all_tracks]
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en descubre: {e}")


@bot.command()
async def crear_descubrimiento(ctx):
    """Crea una playlist con las últimas recomendaciones de !descubre"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    # Verificar si hay descubrimientos guardados
    if not hasattr(bot, 'temp_discoveries') or ctx.author.id not in bot.temp_discoveries:
        await ctx.send("❌ Primero usa `!descubre` para generar recomendaciones.")
        return
    
    tracks = bot.temp_discoveries[ctx.author.id]
    
    try:
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, "Mis Descubrimientos", public=False)
        sp.playlist_add_items(pl['id'], tracks)
        
        await ctx.send(f"✅ Playlist creada: {pl['external_urls']['spotify']}\n🎵 {len(tracks)} canciones agregadas")
        
        # Limpiar
        del bot.temp_discoveries[ctx.author.id]
        
    except Exception as e:
        await ctx.send(f"❌ Error al crear playlist: {str(e)}")


@bot.command()
async def mix(ctx, *, tema):
    """
    Mix temático SIN usar recommendations
    Busca canciones y playlists relacionadas al tema
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send(f"🎨 Creando mix de **{tema}**...")
    
    all_tracks = []
    
    try:
        # Estrategia 1: Buscar canciones directamente
        search = sp.search(q=tema, type='track', limit=20)
        for track in search['tracks']['items']:
            if len(all_tracks) < 25:
                all_tracks.append(track['uri'])
        
        print(f"✅ {len(all_tracks)} tracks de búsqueda directa")
        
        # Estrategia 2: Buscar playlists relacionadas
        pl_search = sp.search(q=tema, type='playlist', limit=3)
        for playlist in pl_search['playlists']['items']:
            if len(all_tracks) >= 30:
                break
            
            pl_tracks = sp.playlist_tracks(playlist['id'], limit=10)
            for item in pl_tracks['items']:
                if len(all_tracks) >= 30:
                    break
                if item.get('track') and item['track'].get('uri'):
                    uri = item['track']['uri']
                    if uri not in all_tracks:
                        all_tracks.append(uri)
        
        print(f"✅ Total con playlists: {len(all_tracks)}")
        
        # Estrategia 3: Si el tema parece ser un artista, agregar álbumes
        artist_search = sp.search(q=tema, type='artist', limit=1)
        if artist_search['artists']['items']:
            artist_id = artist_search['artists']['items'][0]['id']
            albums = sp.artist_albums(artist_id, limit=3, album_type='album,single')
            
            for album in albums['items']:
                if len(all_tracks) >= 30:
                    break
                tracks = sp.album_tracks(album['id'], limit=5)
                for track in tracks['items']:
                    if len(all_tracks) >= 30:
                        break
                    if track['uri'] not in all_tracks:
                        all_tracks.append(track['uri'])
        
        print(f"✅ Total final: {len(all_tracks)}")
        
        if len(all_tracks) == 0:
            await ctx.send(f"❌ No encontré música relacionada con '{tema}'")
            return
        
        # Eliminar duplicados
        unique_tracks = list(dict.fromkeys(all_tracks))
        
        # Crear playlist
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, f'Mix: {tema}', public=False)
        
        # Agregar en lotes
        for i in range(0, len(unique_tracks), 100):
            batch = unique_tracks[i:i+100]
            sp.playlist_add_items(pl['id'], batch)
        
        msg = f"🎨 **Mix creado**: {pl['external_urls']['spotify']}\n\n"
        msg += f"🎵 **{len(unique_tracks)} canciones** relacionadas con '{tema}'"
        
        await ctx.send(msg)
        
    except Exception as e:
        await ctx.send(f"❌ Error al crear mix: {str(e)}")
        print(f"Error en mix: {e}")

# 5. LIMPIAR DUPLICADOS DE TODA LA BIBLIOTECA
@bot.command()
async def limpiar_biblioteca(ctx):
    """Encuentra y elimina canciones duplicadas de TODAS tus playlists
    ⚠️ Esto puede tomar varios minutos
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("🔍 Analizando todas tus playlists... Esto puede tardar un poco.")
    
    try:
        # Obtener todas las playlists
        playlists = []
        offset = 0
        
        while True:
            batch = sp.current_user_playlists(limit=50, offset=offset)
            playlists.extend(batch['items'])
            
            if not batch['next']:
                break
            offset += 50
        
        total_removed = 0
        playlists_cleaned = 0
        
        for playlist in playlists:
            # Solo limpiar playlists propias
            if playlist['owner']['id'] != sp.current_user()['id']:
                continue
            
            # Obtener tracks
            tracks = sp.playlist_tracks(playlist['id'])
            uris = [item['track']['uri'] for item in tracks['items'] if item.get('track')]
            
            # Encontrar duplicados
            unique_uris = []
            seen = set()
            duplicates = 0
            
            for uri in uris:
                if uri not in seen:
                    unique_uris.append(uri)
                    seen.add(uri)
                else:
                    duplicates += 1
            
            # Si hay duplicados, limpiar
            if duplicates > 0:
                sp.playlist_replace_items(playlist['id'], unique_uris)
                total_removed += duplicates
                playlists_cleaned += 1
        
        if total_removed > 0:
            await ctx.send(f"✅ **Limpieza completada**\n🗑️ {total_removed} duplicados eliminados\n📝 {playlists_cleaned} playlists limpiadas")
        else:
            await ctx.send("✨ ¡Tu biblioteca está limpia! No se encontraron duplicados.")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
    
# ============================================
# COMANDOS SOCIALES
# ============================================

@bot.command()
async def compatibilidad(ctx, usuario: discord.Member):
    """Compara tu gusto musical con otro usuario"""
    if usuario.id == ctx.author.id:
        await ctx.send("❌ No puedes compararte contigo mismo.")
        return
    
    sp1 = make_spotify_client_for_user(ctx.author.id)
    sp2 = make_spotify_client_for_user(usuario.id)
    
    if not sp1:
        await ctx.send("🔴 Tú no estás logueado. Usa !login.")
        return
    if not sp2:
        await ctx.send(f"🔴 {usuario.name} no está logueado.")
        return
    
    try:
        await ctx.send(f"🔍 Comparando gustos musicales entre {ctx.author.name} y {usuario.name}...")
        
        # Obtener top artistas de ambos
        top1 = sp1.current_user_top_artists(limit=20, time_range='medium_term')
        top2 = sp2.current_user_top_artists(limit=20, time_range='medium_term')
        
        artists1 = set([a['id'] for a in top1['items']])
        artists2 = set([a['id'] for a in top2['items']])
        
        # Calcular coincidencias
        common = artists1.intersection(artists2)
        total = artists1.union(artists2)
        
        if len(total) == 0:
            await ctx.send("❌ No hay suficientes datos para comparar.")
            return
        
        compatibility = int((len(common) / len(total)) * 100)
        
        # Crear embed
        embed = discord.Embed(
            title="🤝 Compatibilidad Musical",
            color=discord.Color.purple()
        )
        
        # Meter de compatibilidad
        if compatibility >= 70:
            emoji = "💚"
            message = "¡Son almas gemelas musicales!"
        elif compatibility >= 50:
            emoji = "💛"
            message = "¡Tienen bastante en común!"
        elif compatibility >= 30:
            emoji = "🧡"
            message = "Algunos gustos compartidos"
        else:
            emoji = "💙"
            message = "Gustos muy diferentes, ¡descubran música juntos!"
        
        embed.add_field(
            name=f"{emoji} Compatibilidad",
            value=f"**{compatibility}%**\n{message}",
            inline=False
        )
        
        embed.add_field(
            name="👥 Usuarios",
            value=f"{ctx.author.mention} ↔️ {usuario.mention}",
            inline=False
        )
        
        if common:
            common_artists = []
            for artist_id in list(common)[:5]:
                for a in top1['items']:
                    if a['id'] == artist_id:
                        common_artists.append(a['name'])
                        break
            
            if common_artists:
                embed.add_field(
                    name="🎤 Artistas en común",
                    value="\n".join([f"• {a}" for a in common_artists]),
                    inline=False
                )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en compatibilidad: {e}")


@bot.command()
async def ranking_servidor(ctx):
    """Muestra los artistas más escuchados en el servidor"""
    await ctx.send("📊 Analizando gustos del servidor...")
    
    # Contador de artistas
    artist_counts = {}
    users_analyzed = 0
    
    # Iterar por miembros del servidor
    for member in ctx.guild.members:
        if member.bot:
            continue
        
        sp = make_spotify_client_for_user(member.id)
        if not sp:
            continue
        
        try:
            top = sp.current_user_top_artists(limit=10, time_range='short_term')
            users_analyzed += 1
            
            for artist in top['items']:
                artist_id = artist['id']
                if artist_id not in artist_counts:
                    artist_counts[artist_id] = {
                        'name': artist['name'],
                        'count': 0
                    }
                artist_counts[artist_id]['count'] += 1
        except:
            continue
    
    if users_analyzed == 0:
        await ctx.send("❌ No hay suficientes usuarios con Spotify conectado.")
        return
    
    # Ordenar por popularidad
    top_artists = sorted(artist_counts.values(), key=lambda x: x['count'], reverse=True)[:10]
    
    embed = discord.Embed(
        title=f"🏆 Top Artistas de {ctx.guild.name}",
        description=f"Basado en {users_analyzed} usuarios",
        color=discord.Color.gold()
    )
    
    ranking = "\n".join([
        f"**{i+1}.** {artist['name']} - {artist['count']} {'usuario' if artist['count'] == 1 else 'usuarios'}"
        for i, artist in enumerate(top_artists)
    ])
    
    embed.add_field(name="🎤 Ranking", value=ranking, inline=False)
    
    await ctx.send(embed=embed)


# ============================================
# PLAYLISTS TEMÁTICAS
# ============================================

@bot.command()
async def gym(ctx):
    """Crea una playlist motivacional para entrenar"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("💪 Creando playlist para el gym...")
    
    try:
        # Buscar playlists de workout
        queries = ["workout motivation", "gym pump", "fitness energy"]
        all_tracks = []
        
        for query in queries:
            playlists = sp.search(q=query, type='playlist', limit=3)
            
            for playlist in playlists['playlists']['items']:
                if len(all_tracks) >= 30:
                    break
                
                tracks = sp.playlist_tracks(playlist['id'], limit=15)
                for item in tracks['items']:
                    if item.get('track') and item['track'].get('uri'):
                        if item['track']['uri'] not in all_tracks and len(all_tracks) < 30:
                            all_tracks.append(item['track']['uri'])
        
        if not all_tracks:
            await ctx.send("❌ No pude crear la playlist.")
            return
        
        # Crear playlist
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, "💪 Gym Motivation", public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"💪 **Playlist para gym creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones para entrenar duro")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def estudio(ctx):
    """Playlist para concentrarse y estudiar"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("📚 Creando playlist para estudiar...")
    
    try:
        queries = ["study music", "focus concentration", "deep focus"]
        all_tracks = []
        
        for query in queries:
            playlists = sp.search(q=query, type='playlist', limit=3)
            
            for playlist in playlists['playlists']['items']:
                if len(all_tracks) >= 30:
                    break
                
                tracks = sp.playlist_tracks(playlist['id'], limit=15)
                for item in tracks['items']:
                    if item.get('track') and item['track'].get('uri'):
                        if item['track']['uri'] not in all_tracks and len(all_tracks) < 30:
                            all_tracks.append(item['track']['uri'])
        
        if not all_tracks:
            await ctx.send("❌ No pude crear la playlist.")
            return
        
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, "📚 Estudio y Concentración", public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"📚 **Playlist de estudio creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones para concentrarte")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def viaje(ctx):
    """Road trip playlist"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("🚗 Creando playlist para tu viaje...")
    
    try:
        queries = ["road trip", "driving music", "travel songs"]
        all_tracks = []
        
        for query in queries:
            playlists = sp.search(q=query, type='playlist', limit=3)
            
            for playlist in playlists['playlists']['items']:
                if len(all_tracks) >= 35:
                    break
                
                tracks = sp.playlist_tracks(playlist['id'], limit=15)
                for item in tracks['items']:
                    if item.get('track') and item['track'].get('uri'):
                        if item['track']['uri'] not in all_tracks and len(all_tracks) < 35:
                            all_tracks.append(item['track']['uri'])
        
        if not all_tracks:
            await ctx.send("❌ No pude crear la playlist.")
            return
        
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, "🚗 Road Trip", public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"🚗 **Playlist de viaje creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones para el camino")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def romantica(ctx):
    """Playlist romántica"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    await ctx.send("❤️ Creando playlist romántica...")
    
    try:
        queries = ["romantic love songs", "amor romance", "love ballads"]
        all_tracks = []
        
        for query in queries:
            playlists = sp.search(q=query, type='playlist', limit=3)
            
            for playlist in playlists['playlists']['items']:
                if len(all_tracks) >= 30:
                    break
                
                tracks = sp.playlist_tracks(playlist['id'], limit=12)
                for item in tracks['items']:
                    if item.get('track') and item['track'].get('uri'):
                        if item['track']['uri'] not in all_tracks and len(all_tracks) < 30:
                            all_tracks.append(item['track']['uri'])
        
        if not all_tracks:
            await ctx.send("❌ No pude crear la playlist.")
            return
        
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, "❤️ Romántica", public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"❤️ **Playlist romántica creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones para el amor")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


# ============================================
# GENERADORES AUTOMÁTICOS
# ============================================

@bot.command()
async def mood(ctx, emoji: str):
    """Crea playlist según emoji
    Uso: !mood 😊  o  !mood 😢  o  !mood 🔥
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    mood_map = {
        '😊': ('happy', 'feliz alegre positivo'),
        '😢': ('sad', 'triste melancólico'),
        '😡': ('angry', 'rock metal intenso'),
        '🔥': ('fire', 'reggaeton trap urbano'),
        '💤': ('sleep', 'chill relajante dormir'),
        '💪': ('workout', 'gym motivación energético'),
        '❤️': ('love', 'romántico amor'),
        '🎉': ('party', 'fiesta dance'),
        '☕': ('coffee', 'café mañana acústico'),
        '🌙': ('night', 'noche nocturno'),
        '🏖️': ('beach', 'playa summer verano'),
        '🎮': ('gaming', 'videojuegos epic'),
    }
    
    if emoji not in mood_map:
        emojis_disponibles = ' '.join(mood_map.keys())
        await ctx.send(f"❌ Emoji no reconocido.\n💡 Disponibles: {emojis_disponibles}")
        return
    
    genre, search_term = mood_map[emoji]
    
    await ctx.send(f"🎨 Creando playlist {emoji}...")
    
    try:
        all_tracks = []
        playlists = sp.search(q=search_term, type='playlist', limit=5)
        
        for playlist in playlists['playlists']['items']:
            if len(all_tracks) >= 30:
                break
            
            tracks = sp.playlist_tracks(playlist['id'], limit=10)
            for item in tracks['items']:
                if len(all_tracks) >= 30:
                    break
                if item.get('track') and item['track'].get('uri'):
                    uri = item['track']['uri']
                    if uri not in all_tracks:
                        all_tracks.append(uri)
        
        if len(all_tracks) == 0:
            await ctx.send(f"❌ No pude crear playlist para {emoji}")
            return
        
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, f'Mood {emoji}', public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"{emoji} **Playlist creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def decada(ctx, año: str):
    """Música de una década específica
    Uso: !decada 80  o  !decada 90s  o  !decada 2000
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    # Limpiar input
    año = año.replace('s', '').replace("'", '')
    
    if not año.isdigit():
        await ctx.send("❌ Formato incorrecto. Usa: !decada 80, !decada 90, !decada 2000")
        return
    
    await ctx.send(f"📻 Buscando música de los {año}s...")
    
    try:
        queries = [f"{año}s hits", f"{año}s music", f"best of {año}s"]
        all_tracks = []
        
        for query in queries:
            if len(all_tracks) >= 30:
                break
            
            playlists = sp.search(q=query, type='playlist', limit=3)
            
            for playlist in playlists['playlists']['items']:
                if len(all_tracks) >= 30:
                    break
                
                tracks = sp.playlist_tracks(playlist['id'], limit=15)
                for item in tracks['items']:
                    if len(all_tracks) >= 30:
                        break
                    if item.get('track') and item['track'].get('uri'):
                        if item['track']['uri'] not in all_tracks:
                            all_tracks.append(item['track']['uri'])
        
        if not all_tracks:
            await ctx.send(f"❌ No encontré música de los {año}s")
            return
        
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, f"🕰️ Los {año}s", public=False)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"📻 **Playlist de los {año}s creada:** {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} clásicos")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

# ============================================
# COMANDOS DE ESTADÍSTICAS
# ============================================

@bot.command()
async def estadisticas(ctx):
    """Muestra un resumen completo de tu perfil musical"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        await ctx.send("📊 Analizando tu perfil musical...")
        
        # Top artistas
        top_artists = sp.current_user_top_artists(limit=5, time_range='medium_term')
        # Top canciones
        top_tracks = sp.current_user_top_tracks(limit=5, time_range='medium_term')
        # Canciones guardadas
        saved = sp.current_user_saved_tracks(limit=1)
        total_saved = saved['total']
        # Playlists
        playlists = sp.current_user_playlists(limit=1)
        total_playlists = playlists['total']
        
        # Calcular géneros favoritos
        genres = {}
        for artist in top_artists['items']:
            for genre in artist['genres'][:3]:
                genres[genre] = genres.get(genre, 0) + 1
        
        top_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:5]
        
        embed = discord.Embed(
            title="📊 Tus Estadísticas Musicales",
            color=discord.Color.green()
        )
        
        # Top artistas
        artists_text = "\n".join([f"{i+1}. {a['name']}" for i, a in enumerate(top_artists['items'])])
        embed.add_field(name="🎤 Top Artistas", value=artists_text, inline=False)
        
        # Top canciones
        tracks_text = "\n".join([f"{i+1}. {t['name'][:30]}..." if len(t['name']) > 30 else f"{i+1}. {t['name']}" for i, t in enumerate(top_tracks['items'])])
        embed.add_field(name="🎵 Top Canciones", value=tracks_text, inline=False)
        
        # Géneros
        if top_genres:
            genres_text = "\n".join([f"• {g[0].title()}" for g in top_genres])
            embed.add_field(name="🎸 Géneros Favoritos", value=genres_text, inline=True)
        
        # Stats generales
        stats_text = f"📀 Canciones guardadas: {total_saved}\n📝 Playlists: {total_playlists}"
        embed.add_field(name="📈 General", value=stats_text, inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en estadisticas: {e}")


@bot.command()
async def historial(ctx, limite: int = 10):
    """Muestra tus últimas canciones escuchadas
    Uso: !historial [cantidad] (máximo 50)
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    if limite > 50:
        limite = 50
    if limite < 1:
        limite = 10
    
    try:
        recent = sp.current_user_recently_played(limit=limite)
        
        if not recent['items']:
            await ctx.send("📭 No tienes historial reciente.")
            return
        
        msg = f"**📜 Tus últimas {len(recent['items'])} canciones:**\n\n"
        
        for i, item in enumerate(recent['items'], 1):
            track = item['track']
            msg += f"{i}. **{track['name']}** - {track['artists'][0]['name']}\n"
            
            # Dividir mensajes largos
            if i % 15 == 0 and i < len(recent['items']):
                await ctx.send(msg)
                msg = ""
        
        if msg:
            await ctx.send(msg)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en historial: {e}")


@bot.command()
async def analizar(ctx, *, cancion):
    """Analiza las características de audio de una canción"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        # Buscar la canción
        results = sp.search(q=cancion, limit=1, type='track')
        
        if not results['tracks']['items']:
            await ctx.send(f"❌ No encontré '{cancion}'")
            return
        
        track = results['tracks']['items'][0]
        track_id = track['id']
        
        # Obtener características de audio
        features = sp.audio_features(track_id)[0]
        
        if not features:
            await ctx.send("❌ No se pudieron obtener las características.")
            return
        
        # Crear embed
        embed = discord.Embed(
            title=f"🔬 Análisis: {track['name']}",
            description=f"Por **{track['artists'][0]['name']}**",
            color=discord.Color.blue()
        )
        
        if track['album']['images']:
            embed.set_thumbnail(url=track['album']['images'][0]['url'])
        
        # Características visuales
        energia = "🔥" * int(features['energy'] * 5)
        bailabilidad = "💃" * int(features['danceability'] * 5)
        positividad = "😊" * int(features['valence'] * 5)
        
        embed.add_field(
            name="⚡ Energía",
            value=f"{energia} {int(features['energy']*100)}%",
            inline=True
        )
        embed.add_field(
            name="💃 Bailabilidad",
            value=f"{bailabilidad} {int(features['danceability']*100)}%",
            inline=True
        )
        embed.add_field(
            name="😊 Positividad",
            value=f"{positividad} {int(features['valence']*100)}%",
            inline=True
        )
        
        embed.add_field(name="🎵 BPM", value=f"{int(features['tempo'])}", inline=True)
        embed.add_field(name="🔊 Volumen", value=f"{int(features['loudness'])} dB", inline=True)
        embed.add_field(name="⏱️ Duración", value=f"{int(features['duration_ms']/1000)}s", inline=True)
        
        extras = f"🎸 Acústica: {int(features['acousticness']*100)}%\n"
        extras += f"🎺 Instrumental: {int(features['instrumentalness']*100)}%\n"
        extras += f"🗣️ Vocales: {int(features['speechiness']*100)}%"
        
        embed.add_field(name="🎼 Extras", value=extras, inline=False)
        embed.add_field(name="🔗 Link", value=f"[Abrir en Spotify]({track['external_urls']['spotify']})", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en analizar: {e}")


@bot.command()
async def obsesion(ctx):
    """Encuentra tu canción más repetida del último mes"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        await ctx.send("🔍 Buscando tu obsesión musical...")
        
        # Obtener historial reciente
        recent = sp.current_user_recently_played(limit=50)
        
        if not recent['items']:
            await ctx.send("📭 No hay suficiente historial.")
            return
        
        # Contar reproducciones
        play_counts = {}
        for item in recent['items']:
            track = item['track']
            track_id = track['id']
            
            if track_id not in play_counts:
                play_counts[track_id] = {
                    'count': 0,
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'url': track['external_urls']['spotify']
                }
            play_counts[track_id]['count'] += 1
        
        # Encontrar la más repetida
        most_played = max(play_counts.values(), key=lambda x: x['count'])
        
        if most_played['count'] < 2:
            await ctx.send("🎵 No tienes una obsesión clara todavía. ¡Sigue escuchando música!")
            return
        
        embed = discord.Embed(
            title="🔁 Tu Obsesión Musical",
            description=f"Has escuchado esta canción **{most_played['count']} veces** recientemente",
            color=discord.Color.red()
        )
        
        embed.add_field(name="🎵 Canción", value=most_played['name'], inline=False)
        embed.add_field(name="🎤 Artista", value=most_played['artist'], inline=False)
        embed.add_field(name="🔗 Link", value=f"[Escuchar]({most_played['url']})", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en obsesion: {e}")

# ============================================
# PLAYLISTS COLABORATIVAS
# ============================================

# Sistema simple de playlists colaborativas usando memoria del bot
if not hasattr(bot, 'collab_playlists'):
    bot.collab_playlists = {}

if not hasattr(bot, 'playlist_suggestions'):
    bot.playlist_suggestions = {}


@bot.command()
async def colaborativa(ctx, *, nombre):
    """Crea una playlist colaborativa pública"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, f"🤝 {nombre}", public=True, collaborative=True)
        
        # Guardar en memoria del bot
        bot.collab_playlists[nombre.lower()] = {
            'id': pl['id'],
            'owner': ctx.author.id,
            'name': nombre,
            'url': pl['external_urls']['spotify'],
            'members': [ctx.author.id]
        }
        
        embed = discord.Embed(
            title="🤝 Playlist Colaborativa Creada",
            description=f"**{nombre}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🔗 Link", value=pl['external_urls']['spotify'], inline=False)
        embed.add_field(name="💡 Cómo compartir", value=f"Otros usuarios pueden usar `!unirse_collab {nombre}` para colaborar", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def sugerir(ctx, playlist_nombre: str, *, cancion):
    """Sugiere una canción para una playlist colaborativa"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        # Buscar la canción
        results = sp.search(q=cancion, limit=1, type='track')
        
        if not results['tracks']['items']:
            await ctx.send(f"❌ No encontré '{cancion}'")
            return
        
        track = results['tracks']['items'][0]
        
        # Guardar sugerencia
        if playlist_nombre.lower() not in bot.playlist_suggestions:
            bot.playlist_suggestions[playlist_nombre.lower()] = []
        
        bot.playlist_suggestions[playlist_nombre.lower()].append({
            'user': ctx.author.id,
            'user_name': ctx.author.name,
            'track_uri': track['uri'],
            'track_name': track['name'],
            'artist': track['artists'][0]['name'],
            'url': track['external_urls']['spotify']
        })
        
        await ctx.send(f"✅ Sugerencia enviada: **{track['name']}** - {track['artists'][0]['name']}\nEl creador puede aceptarla con `!aceptar_sugerencia {playlist_nombre} 1`")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command()
async def ver_sugerencias(ctx, playlist_nombre: str):
    """Ve las sugerencias de una playlist"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    playlist_data = bot.collab_playlists[playlist_nombre.lower()]
    
    # Solo el owner puede ver sugerencias
    if ctx.author.id != playlist_data['owner']:
        await ctx.send("❌ Solo el creador de la playlist puede ver sugerencias.")
        return
    
    if playlist_nombre.lower() not in bot.playlist_suggestions or not bot.playlist_suggestions[playlist_nombre.lower()]:
        await ctx.send("📭 No hay sugerencias pendientes.")
        return
    
    suggestions = bot.playlist_suggestions[playlist_nombre.lower()]
    
    embed = discord.Embed(
        title=f"💡 Sugerencias para: {playlist_data['name']}",
        color=discord.Color.blue()
    )
    
    for i, sug in enumerate(suggestions, 1):
        embed.add_field(
            name=f"{i}. {sug['track_name']}",
            value=f"Por: {sug['artist']}\nSugerido por: {sug['user_name']}\n[Link]({sug['url']})",
            inline=False
        )
    
    embed.set_footer(text=f"Usa !aceptar_sugerencia {playlist_nombre} <número> para agregar")
    
    await ctx.send(embed=embed)


@bot.command()
async def aceptar_sugerencia(ctx, playlist_nombre: str, numero: int):
    """Acepta y agrega una sugerencia a la playlist"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    playlist_data = bot.collab_playlists[playlist_nombre.lower()]
    
    if ctx.author.id != playlist_data['owner']:
        await ctx.send("❌ Solo el creador puede aceptar sugerencias.")
        return
    
    if playlist_nombre.lower() not in bot.playlist_suggestions:
        await ctx.send("📭 No hay sugerencias.")
        return
    
    suggestions = bot.playlist_suggestions[playlist_nombre.lower()]
    
    if numero < 1 or numero > len(suggestions):
        await ctx.send(f"❌ Número inválido. Hay {len(suggestions)} sugerencias.")
        return
    
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        suggestion = suggestions[numero - 1]
        
        # Agregar a la playlist
        sp.playlist_add_items(playlist_data['id'], [suggestion['track_uri']])
        
        # Remover de sugerencias
        suggestions.pop(numero - 1)
        
        await ctx.send(f"✅ **{suggestion['track_name']}** agregada a la playlist por sugerencia de {suggestion['user_name']}")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

# ------------------- Ejecutar -------------------
bot.run(DISCORD_TOKEN)