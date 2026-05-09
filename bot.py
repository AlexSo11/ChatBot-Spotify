"""
⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢰⣿⡿⠗⠀⠠⠄⡀⠀⠀⠀⠀
⠀⠀⠀⠀⡜⠁⠀⠀⠀⠀⠀⠈⠑⢶⣶⡄
⢀⣶⣦⣸⠀⢼⣟⡇⠀⠀⢀⣀⠀⠘⡿⠃
⠀⢿⣿⣿⣄⠒⠀⠠⢶⡂⢫⣿⢇⢀⠃⠀
⠀⠈⠻⣿⣿⣿⣶⣤⣀⣀⣀⣂⡠⠊⠀⠀
⠀⠀⠀⠃⠀⠀⠉⠙⠛⠿⣿⣿⣧⠀⠀⠀
⠀⠀⠘⡀⠀⠀⠀⠀⠀⠀⠘⣿⣿⡇⠀⠀
⠀⠀⠀⣷⣄⡀⠀⠀⠀⢀⣴⡟⠿⠃⠀⠀
⠀⠀⠀⢻⣿⣿⠉⠉⢹⣿⣿⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠉⠁⠀⠀⠀⠉⠁

Desarrollo AlexWhite USER GIT AlexSo11
"""

import os
import re 
import json
import time
import asyncio
import random
import ia_agent
import discord
import spotipy
import requests
from dotenv import load_dotenv
load_dotenv(dotenv_path="./.env")
from discord.ext import commands
from spotipy.oauth2 import SpotifyOAuth
from google import genai
from google.genai import types

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

# ------------------- Eventos -------------------

@bot.event
async def on_ready():
    print(f"✅ Bot listo como {bot.user}")
    print(f"📡 Conectado a {len(bot.guilds)} servidor(es)")
    print(f"🔗 Servicio de auth: {SPOTIFY_SERVICE_URL}")

@bot.event
async def on_command_error(ctx, error):
    """Manejo global de errores"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignorar comandos no encontrados
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Falta un argumento. Usa `!comandos` para ver la ayuda.")
    else:
        print(f"Error en comando: {error}")
        await ctx.send(f"❌ Ocurrió un error: {str(error)}")

def extraer_link_spotify(resultado_busqueda):
    """Extrae el link de Spotify de un resultado de búsqueda"""
    try:
        if 'external_urls' in resultado_busqueda:
            return resultado_busqueda['external_urls']['spotify']
        return None
    except:
        return None
    
@bot.event
async def on_message(message):
    # Ignorar mensajes del propio bot
    if message.author.bot:
        return

    # Primero procesar comandos normales (!login, !help, etc)
    await bot.process_commands(message)
    
    # Si NO es un comando y el bot fue mencionado, usar IA
    if bot.user.mentioned_in(message) and not message.content.startswith("!"):
        user_id = message.author.id
        nombre_usuario = message.author.name
        
        # Limpiamos la mención
        texto_limpio = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        # Verificación de login
        token_acceso = get_access_token_for_user(user_id)
        sp_is_authenticated = (token_acceso is not None)

        # Datos de contexto
        context_data = {
            'bot_name': bot.user.name,
            'playlist_name': 'General',
            'playlist_size': 0
        }

        # LÓGICA IA + EJECUCIÓN SPOTIFY
        if texto_limpio:
            async with message.channel.typing():
                # 1. Obtener respuesta BRUTA de la IA
                respuesta_bruta = await ia_agent.ia_responder(
                    user_id, nombre_usuario, texto_limpio, context_data, sp_is_authenticated
                )
            
            if not respuesta_bruta:
                await message.reply("🤔 (La IA no respondió nada)")
                return

            # Patron json de la respuesta de IA
            patron_json = r"```(?:json)?\s*(.*?)\s*```"
            
            match = re.search(patron_json, respuesta_bruta, re.DOTALL)
            
            mensaje_final = respuesta_bruta # Por defecto, todo el texto
            
            if match:
                json_str = match.group(1)
                mensaje_final = respuesta_bruta.replace(match.group(0), "").strip()
                
                try:
                    comando = json.loads(json_str)
                    accion = comando.get("accion")
                    dato = comando.get("dato")
                    
                    print(f"🤖 COMANDO IA: {accion} | DATO: {dato}")

                    if not sp_is_authenticated:
                        mensaje_final += "\n🚫 *Necesitas loguearte con !login para que pueda controlar Spotify.*"
                    
                    else:
                        sp = spotipy.Spotify(auth=token_acceso)

                        # ═══════════════════════════════════════════════
                        # 🎵 COMANDOS DE REPRODUCCIÓN
                        # ═══════════════════════════════════════════════
                        
                        if accion == "reproducir":
                            res = await asyncio.to_thread(sp.search, q=dato, limit=10, type='track')
                            if res['tracks']['items']:
                                # Lógica de mejor coincidencia
                                items = res['tracks']['items']
                                track_to_play = items[0]
                                
                                query_lower = dato.lower().strip()
                                for item in items:
                                    track_name = item['name'].lower()
                                    if query_lower in track_name:
                                        track_to_play = item
                                        break
                                
                                uri = track_to_play['uri']
                                link = extraer_link_spotify(track_to_play)
                                
                                try:
                                    devices = sp.devices().get("devices", [])
                                    if not devices:
                                        mensaje_final += "\n⚠️ *No hay dispositivos activos. Abre Spotify en un dispositivo.*"
                                    else:
                                        device_id = devices[0]["id"]
                                        for d in devices:
                                            if d.get('is_active'):
                                                device_id = d['id']
                                                break
                                        
                                        sp.start_playback(device_id=device_id, uris=[uri])
                                        mensaje_final += f"\n▶️ *Reproduciendo:* **{track_to_play['name']}** - {track_to_play['artists'][0]['name']}"
                                        if link:
                                            mensaje_final += f"\n🔗 [Abrir en Spotify]({link})"
                                except Exception as e:
                                    print(f"Error reproduciendo: {e}")
                                    mensaje_final += "\n⚠️ *Error: Spotify no está activo en tus dispositivos.*"
                            else:
                                mensaje_final += f"\n❌ *No encontré '{dato}'.*"
                        
                        elif accion == "pausar":
                            try:
                                sp.pause_playback()
                                mensaje_final += "\n⏸️ *Música pausada*"
                            except:
                                mensaje_final += "\n⚠️ No pude pausar"
                        
                        elif accion == "reanudar":
                            try:
                                sp.start_playback()
                                mensaje_final += "\n▶️ *Música reanudada*"
                            except:
                                mensaje_final += "\n⚠️ *No pude reanudar*"
                    
                        elif accion == "saltar":
                            sp.next_track()
                            mensaje_final += "\n⏭️ *Siguiente canción*"
                        
                        elif accion == "anterior":
                            sp.previous_track()
                            mensaje_final += "\n⏮️ *Canción anterior*"
                        
                        elif accion == "cancion_actual":
                            current = sp.current_playback()
                            if current and current.get("item"):
                                t = current["item"]
                                mensaje_final += f"\n🎧 *Sonando: {t['name']} - {t['artists'][0]['name']}*"
                            else:
                                mensaje_final += "\n❌ *No hay nada reproduciéndose*"
                        
                        elif accion == "volumen":
                            try:
                                vol = int(dato)
                                if 0 <= vol <= 100:
                                    sp.volume(vol)
                                    mensaje_final += f"\n🔊 *Volumen ajustado al {vol}%*"
                                else:
                                    mensaje_final += "\n⚠️ *El volumen debe estar entre 0 y 100*"
                            except:
                                mensaje_final += "\n⚠️ *Formato de volumen inválido*"

                        # ═══════════════════════════════════════════════
                        # 📊 COMANDOS DE ESTADÍSTICAS
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "estadisticas":
                            ctx = await bot.get_context(message)
                            comando_estadisticas = bot.get_command('estadisticas')
                            if comando_estadisticas:
                                await comando_estadisticas.invoke(ctx)
                            else:
                                mensaje_final += "\n⚠️ *Error: No encuentro el comando 'estadisticas'*"
                        
                        elif accion == "top_artistas":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('top_artistas')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "top_tracks":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('top_tracks')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "historial":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('historial')
                            if comando:
                                try:
                                    limite = int(dato) if dato and str(dato).isdigit() else 10
                                    # Crear argumentos simulados
                                    mensaje_simulado = f"!historial {limite}"
                                    message.content = mensaje_simulado
                                    ctx = await bot.get_context(message)
                                    await ctx.invoke(comando, limite=limite)
                                except Exception as e:
                                    print(f"Error en historial: {e}")
                                    mensaje_final += f"\n⚠️ *Error mostrando historial: {str(e)}*"

                        elif accion == "analizar":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('analizar')
                            if comando:
                                try:
                                    await ctx.invoke(comando, cancion=dato)
                                except Exception as e:
                                    print(f"Error en analizar: {e}")
                                    mensaje_final += f"\n⚠️ *Error analizando canción: {str(e)}*"
                        
                        elif accion == "obsesion":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('obsesion')
                            if comando:
                                await comando.invoke(ctx)

                        # ═══════════════════════════════════════════════
                        # 📂 COMANDOS DE PLAYLISTS
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "crear_playlist":
                            user_id_sp = sp.current_user()['id']
                            pl = sp.user_playlist_create(user_id_sp, dato, public=False)
                            mensaje_final += f"\n✅ *Playlist '{dato}' creada*\n📁 {pl['external_urls']['spotify']}"
                        
                        # En bot.py -> on_message -> if match: -> if accion == "crear_mix":

                        elif accion == "crear_mix":
                            nombre_pl = dato.get("nombre_playlist", "Mix IA")
                            canciones = dato.get("canciones", [])
                            mensaje_final += f"\n📂 *Creando playlist '{nombre_pl}'... (esto puede tardar un poco)*"
                            
                            # TRUCO MAESTRO: Enviamos el mensaje de "Creando..." PRIMERO
                            await message.channel.send(mensaje_final) 
                            mensaje_final = "" # Limpiamos para no repetir

                            try:
                                # Ejecutamos la función pesada en segundo plano sin congelar el bot
                                playlist_url = await asyncio.to_thread(proceso_crear_playlist_pesado, sp, nombre_pl, canciones)
                                
                                await message.channel.send(f"✅ *¡Lista lista! Se ha guardado en tu biblioteca.*\n🔗 **Ábrela aquí:** {playlist_url}")

                            except Exception as e:
                                print(e)
                                await message.channel.send("❌ *Error creando la playlist.*")    
                        
                        elif accion == "radio":
                            # 1. Obtenemos el comando
                            comando = bot.get_command('radio')
                            
                            if comando:
                                # 2. Obtenemos el contexto actual
                                ctx = await bot.get_context(message)
                                
                                # 3. ¡CORRECCIÓN AQUÍ! 
                                # Usamos .callback en lugar de .invoke
                                # IMPORTANTE: Asegúrate de que tu comando 'radio' tenga un parámetro llamado 'base'
                                await comando.callback(ctx, base=dato) 
                                
                            else:
                                print("❌ El comando 'radio' no existe o no se encontró.")
                        
                        elif accion == "playlist_mood":
                            # El dato que envía la IA es la categoría (ej: "fiesta", "triste")
                            categoria = dato 
                            
                            # TRUCO: Modificamos el mensaje temporalmente para simular que el usuario escribió "!playlist_mood fiesta"
                            msg_original = message.content # Guardamos copia de seguridad
                            
                            # Construimos el comando falso
                            message.content = f"!playlist_mood {categoria}"
                            
                            # Generamos un nuevo contexto con este mensaje modificado
                            new_ctx = await bot.get_context(message)
                            
                            # Invocamos el comando (ahora el argumento va dentro del mensaje, no en el invoke)
                            await bot.invoke(new_ctx)
                            
                            # Restauramos el mensaje original por seguridad
                            message.content = msg_original
                        
                        elif accion == "decada":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('decada')
                            if comando:
                                await comando.invoke(ctx, entrada=dato)
                        
                        elif accion == "agregar_a_playlist":
                            partes = dato.split("|")
                            if len(partes) == 2:
                                nombre_pl, cancion = partes
                                ctx = await bot.get_context(message)
                                comando = bot.get_command('agregar_playlist')
                                if comando:
                                    await comando.invoke(ctx, nombre=nombre_pl, track=cancion)
                        
                        elif accion == "fusion":
                            partes = dato.split("|")
                            if len(partes) == 2:
                                pl1, pl2 = partes
                                ctx = await bot.get_context(message)
                                comando = bot.get_command('fusion')
                                if comando:
                                    await comando.invoke(ctx, playlist1=pl1, playlist2=pl2)
                        
                        elif accion == "limpiar_playlist":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('limpiarplaylist')
                            if comando:
                                await comando.invoke(ctx, nombre=dato)
                        
                        elif accion == "limpiar_biblioteca":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('limpiar_biblioteca')
                            if comando:
                                await comando.invoke(ctx)

                        # ═══════════════════════════════════════════════
                        # 🔍 COMANDOS DE BÚSQUEDA
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "buscar_cancion":
                            try:
                                res = await asyncio.to_thread(sp.search, q=dato, limit=10, type='track')
                                if res['tracks']['items']:
                                    mensaje_final += f"\n\n🎵 **Resultados para:** {dato}\n"
                                    for i, t in enumerate(res['tracks']['items'], 1):
                                        link = extraer_link_spotify(t)
                                        mensaje_final += f"\n{i}. **{t['name']}** - {t['artists'][0]['name']}"
                                        if link:
                                            mensaje_final += f"\n   🔗 [Link]({link})"
                                else:
                                    mensaje_final += f"\n❌ *No encontré canciones con: {dato}*"
                            except Exception as e:
                                print(f"Error buscando canción: {e}")
                                mensaje_final += f"\n⚠️ *Error en búsqueda: {str(e)}*"

                        elif accion == "buscar_artista":
                            try:
                                res = await asyncio.to_thread(sp.search, q=dato, limit=10, type='artist')
                                if res['artists']['items']:
                                    mensaje_final += f"\n\n🎤 **Artistas encontrados:**\n"
                                    for i, a in enumerate(res['artists']['items'], 1):
                                        link = extraer_link_spotify(a)
                                        mensaje_final += f"\n{i}. **{a['name']}**"
                                        if link:
                                            mensaje_final += f"\n   🔗 [Link]({link})"
                                else:
                                    mensaje_final += f"\n❌ *No encontré artistas: {dato}*"
                            except Exception as e:
                                mensaje_final += f"\n⚠️ *Error: {str(e)}*"
                        
                        elif accion == "buscar_album":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('buscar_album')
                            if comando:
                                await comando.invoke(ctx, texto=dato)
                        
                        elif accion == "guardar":
                            if dato == "current":
                                current = sp.current_playback()
                                if current and current.get("item"):
                                    tid = current["item"]["id"]
                                    sp.current_user_saved_tracks_add([tid])
                                    mensaje_final += "\n💾 *Canción actual guardada*"
                            else:
                                res = sp.search(q=dato, type='track', limit=1)
                                if res['tracks']['items']:
                                    tid = res['tracks']['items'][0]['id']
                                    sp.current_user_saved_tracks_add([tid])
                                    mensaje_final += f"\n💾 *Guardado: {res['tracks']['items'][0]['name']}*"
                        
                        elif accion == "eliminar_guardada":
                            res = sp.search(q=dato, type='track', limit=1)
                            if res['tracks']['items']:
                                tid = res['tracks']['items'][0]['id']
                                sp.current_user_saved_tracks_delete([tid])
                                mensaje_final += "\n🗑️ *Eliminado de guardadas*"
                        
                        elif accion == "ver_likes":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('mislikes')
                            if comando:
                                await comando.invoke(ctx)

                        # ═══════════════════════════════════════════════
                        # 🎙️ COMANDOS DE PODCASTS
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "podcast_tendencias":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('podcast_tendencias')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "podcast_episodios":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('podcast_episodios')
                            if comando:
                                await comando.invoke(ctx, show=dato)

                        # ═══════════════════════════════════════════════
                        # 🎨 COMANDOS TEMÁTICOS
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "playlist_gym":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('gym')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "playlist_estudio":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('estudio')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "playlist_viaje":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('viaje')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "playlist_romantica":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('romantica')
                            if comando:
                                await comando.invoke(ctx)

                        # ═══════════════════════════════════════════════
                        # 🤝 COMANDOS SOCIALES
                        # ═══════════════════════════════════════════════
                        
                        # En bot.py -> on_message -> if match: ...

                        elif accion == "compatibilidad":
                            # El 'dato' que envía la IA es el usuario a comparar (ej: "@Alex")
                            usuario_objetivo = dato 
                            
                            # 1. Guardamos el mensaje original por seguridad
                            msg_original = message.content 
                            
                            # 2. Reescribimos el mensaje para simular el comando
                            # Asegúrate de que tu comando en el bot se llame realmente '!compatibilidad' o '!ship'
                            message.content = f"!compatibilidad {usuario_objetivo}"
                            
                            # 3. Creamos un nuevo contexto con este mensaje "falso"
                            new_ctx = await bot.get_context(message)
                            
                            # 4. Ejecutamos el comando (ahora sí funcionará porque el argumento está en el texto)
                            await bot.invoke(new_ctx)
                            
                            # 5. Restauramos el mensaje original
                            message.content = msg_original
                        
                        elif accion == "crear_colaborativa":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('colaborativa')
                            if comando:
                                await comando.invoke(ctx, nombre=dato)
                        
                        elif accion == "sugerir_cancion":
                            partes = dato.split("|")
                            if len(partes) == 2:
                                pl_nombre, cancion = partes
                                ctx = await bot.get_context(message)
                                comando = bot.get_command('sugerir')
                                if comando:
                                    await comando.invoke(ctx, playlist_nombre=pl_nombre, cancion=cancion)
                        
                        elif accion == "ver_sugerencias":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('ver_sugerencias')
                            if comando:
                                await comando.invoke(ctx, playlist_nombre=dato)

                        # ═══════════════════════════════════════════════
                        # 🎯 COMANDOS DE DESCUBRIMIENTO
                        # ═══════════════════════════════════════════════
                        
                        elif accion == "descubre":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('descubre')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "recomendar_artista":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('recomienda_artista')
                            if comando:
                                await comando.invoke(ctx)
                        
                        elif accion == "recomendar_canciones":
                            ctx = await bot.get_context(message)
                            comando = bot.get_command('recomienda_canciones')
                            if comando:
                                await comando.invoke(ctx)
                        
                        else:
                            mensaje_final += f"\n⚠️ *Comando '{accion}' no implementado aún*"

                except Exception as e:
                    print(f"❌ Error ejecutando comando IA: {e}")
                    import traceback
                    traceback.print_exc()  # Imprimir stack trace completo
                    mensaje_final += f"\n⚠️ *Error procesando '{accion}': {str(e)}*"

        # Enviar respuesta final (CORREGIDO)
        try:
            # 1. VERIFICACIÓN DE SEGURIDAD (Esto es lo nuevo)
            # Solo intentamos enviar si hay texto real (quitando espacios vacíos)
            if mensaje_final and mensaje_final.strip():
                
                if len(mensaje_final) > 2000:
                    # Si es muy largo, lo partimos en trozos
                    chunks = [mensaje_final[i:i+1900] for i in range(0, len(mensaje_final), 1900)]
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    # Si tiene tamaño normal, lo enviamos
                    await message.reply(mensaje_final)
                    
            # Si está vacío, simplemente no hace nada (y no da error)

        except Exception as e:
            print(f"Error enviando mensaje: {e}")
            # Opcional: solo avisar si fue un error real y no un mensaje vacío
            if "Cannot send an empty message" not in str(e):
                await message.reply("Lo siento, hubo un problema enviando la respuesta.")

# ------------------- Comandos Básicos -------------------

@bot.command()
async def login(ctx):
    """Envía el link para iniciar sesión en Spotify"""
    auth_url = f"{SPOTIFY_SERVICE_URL}/login?discord_id={ctx.author.id}"
    
    embed = discord.Embed(
        title="🔐 Conecta tu cuenta de Spotify",
        description="Haz clic en el link de abajo para autorizar el bot",
        color=discord.Color.green()
    )
    embed.add_field(name="🔗 Link de autorización", value=auth_url, inline=False)
    embed.set_footer(text="Después de autorizar, podrás usar todos los comandos del bot")
    
    await ctx.send(embed=embed)

@bot.command()
async def verificar(ctx):
    """Verifica si el usuario tiene un token válido"""
    await ctx.send("🔍 Verificando conexión...")
    
    access = get_access_token_for_user(ctx.author.id)
    if not access:
        embed = discord.Embed(
            title="🔴 No estás conectado",
            description="Usa `!login` para conectar tu cuenta de Spotify",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Verificar llamando a Spotify
    try:
        sp = spotipy.Spotify(auth=access)
        user = sp.current_user()
        
        embed = discord.Embed(
            title="🟢 Conexión exitosa",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Usuario", value=user.get('display_name', user.get('id')), inline=True)
        #embed.add_field(name="🌍 País", value=user.get('country', 'N/A'), inline=True)
        #embed.add_field(name="📧 Email", value=user.get('email', 'N/A'), inline=True)
        #embed.set_footer(text=f"ID de Discord: {ctx.author.id}")
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"🔴 Token inválido o expirado. Usa `!login` para renovar.\nError: {str(e)}")


# ------------------- Eventos y comandos -------------------

@bot.event
async def listo():
    print(f"Bot listo como {bot.user}")

# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+= MENU DE COMANDOS +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=

@bot.command()
async def comandos(ctx):
    """Menú principal de comandos"""
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
    
    embed.set_footer(text="💡 Primero usa !login para conectar tu Spotify")

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
            #"`!duplicados` - Ver duplicados en biblioteca"
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
            #"`!energia` - Playlist de alta energía\n"
            #"`!relajante` - Playlist tranquila"
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
            #"`!vs @usuario` - Comparar perfiles musicales\n"
            #"`!batalla <artista1> vs <artista2>` - Votar\n"
            #"`!ranking_servidor` - Top del servidor"
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
            #"`!cocinar` - Música para cocinar\n"
            #"`!dormir` - Para dormir\n"
            "`!viaje` - Road trip playlist"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💝 Ocasiones", 
        value=(
            "`!romantica` - Canciones románticas\n"
            #"`!fiesta` - Para fiestas\n"
            #"`!cumpleanos` - Celebración\n"
            #"`!navidad` - Música navideña (temporada)"
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
            #"`!playlist_clima` - Según el clima actual\n"
            #"`!playlist_hora` - Según la hora del día\n"
            "`!decada <año>` - Música de los 80s, 90s, etc.\n"
            #"`!retro` - Clásicos aleatorios"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Personalizadas", 
        value=(
            "`!descubre` - Recomendaciones personalizadas\n"
            #"`!explorar` - Géneros nuevos para ti\n"
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
            #"`!invitar @usuario <playlist>` - Invitar a editar\n"
            #"`!publicas` - Ver tus playlists públicas\n"
            #"`!hacer_publica <playlist>` - Hacer pública\n"
            #"`!hacer_privada <playlist>` - Hacer privada"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 Sugerencias", 
        value=(
            "`!sugerir <playlist> <canción>` - Sugerir canción\n"
            "`!ver_sugerencias <playlist>` - Ver sugerencias\n"
            #"`!aceptar_sugerencia <playlist> <#>` - Aceptar\n"
            #"`!rechazar_sugerencia <playlist> <#>` - Rechazar"
        ),
        inline=False
    )
    
    """embed.add_field(
        name="🎵 Sesiones Grupales", 
        value=(
            "`!sesion_grupal <nombre>` - Crear sesión\n"
            "`!unirse_sesion <nombre>` - Unirse\n"
            "`!votar_cancion <canción>` - Votar siguiente\n"
            "`!cola_grupal` - Ver cola de votación"
        ),
        inline=False
    )"""

    await ctx.send(embed=embed)

# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+= INICIO DE COMANDOS UTILES +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=

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

    # 1. CAMBIO IMPORTANTE: Pedimos 10 resultados, no solo 1
    results = sp.search(q=query, limit=10, type="track")
    
    if not results["tracks"]["items"]:
        await ctx.send("❌ No encontré la canción.")
        return

    items = results["tracks"]["items"]
    track_to_play = items[0] # Por defecto, la primera opción (fallback)

    # 2. LÓGICA DE MEJOR COINCIDENCIA
    # Buscamos si alguna de las 10 canciones tiene el nombre EXACTO o MUY PARECIDO a lo que escribiste
    query_lower = query.lower().strip()
    
    for item in items:
        track_name = item['name'].lower()
        # Si el nombre de la canción contiene lo que escribiste (prioridad al nombre sobre la popularidad)
        if query_lower in track_name:
            track_to_play = item
            break # Encontramos una coincidencia de nombre, nos quedamos con esta

    devices = sp.devices().get("devices", [])
    if not devices:
        await ctx.send("⚠️ No hay dispositivos activos. Abre Spotify en un dispositivo y reintenta.")
        return
    
    # Usar el dispositivo activo actual o el primero de la lista
    # Intentamos buscar uno que esté activo (is_active=True)
    device_id = devices[0]["id"]
    for d in devices:
        if d['is_active']:
            device_id = d['id']
            break

    try:
        sp.start_playback(device_id=device_id, uris=[track_to_play["uri"]])
        await ctx.send(f"▶️ Reproduciendo **{track_to_play['name']}** — {track_to_play['artists'][0]['name']}")
    except Exception as e:
        await ctx.send(f"❌ Error al reproducir: {e}")


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
    """
    Crea una playlist contextual basada en una búsqueda.
    Ejemplo: !playlist rock de los 80
    Ejemplo: !playlist musica para programar
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    await ctx.send(f"🔍 Buscando el mejor contexto para: **{mood}**...")

    # 1. BÚSQUEDA INTELIGENTE: Buscamos PLAYLISTS, no canciones sueltas.
    # Esto garantiza que las canciones tengan el "contexto" del género o mood.
    results = sp.search(q=mood, type="playlist", limit=10)
    
    if not results["playlists"]["items"]:
        await ctx.send("❌ No encontré playlists relacionadas con ese contexto.")
        return

    collected_tracks = set() # Usamos un Set para evitar duplicados automáticamente
    target_count = 40 # Queremos una playlist de 40 canciones aprox

    # 2. MINERÍA DE CANCIONES (El toque "Ad Hoc")
    # Recorremos las playlists encontradas y sacamos canciones de ellas
    playlists_found = results["playlists"]["items"]
    
    # Barajamos las playlists encontradas para no sacar siempre de la primera
    random.shuffle(playlists_found)

    for pl_info in playlists_found:
        if len(collected_tracks) >= target_count:
            break
            
        try:
            # Sacamos las primeras 15 canciones de cada playlist encontrada
            tracks_in_pl = sp.playlist_tracks(pl_info["id"], limit=15)
            
            for item in tracks_in_pl["items"]:
                # Verificamos que el item tenga datos válidos
                if item.get("track") and item["track"].get("uri"):
                    uri = item["track"]["uri"]
                    collected_tracks.add(uri)
        except:
            continue # Si una playlist falla, pasamos a la siguiente

    if not collected_tracks:
        await ctx.send("❌ Encontré el estilo, pero no pude extraer canciones válidas.")
        return

    # Convertimos a lista y mezclamos para que sea una experiencia nueva
    final_track_list = list(collected_tracks)
    random.shuffle(final_track_list)
    
    # Recortamos al límite deseado
    final_track_list = final_track_list[:target_count]

    # 3. CREACIÓN
    try:
        user = sp.current_user()["id"]
        # Nombre más descriptivo
        pl_name = f"{mood.title()} Mix (Bot)"
        
        pl = sp.user_playlist_create(
            user, 
            pl_name, 
            public=False, 
            description=f"Playlist generada ad-hoc basada en '{mood}'."
        )
        
        # Añadimos las canciones
        sp.playlist_add_items(pl["id"], final_track_list)
        
        await ctx.send(f"✅ **Playlist Ad-Hoc creada:** {pl_name}\n🔗 {pl['external_urls']['spotify']}\n🎵 {len(final_track_list)} canciones seleccionadas de varias fuentes.")
    
    except Exception as e:
        await ctx.send(f"❌ Error al guardar la playlist: {e}")


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
    
    
# -------------------------------- Comandos Sociales --------------------------------

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


# -------------------------------- Playlist Temáticas --------------------------------

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


# -------------------------------- Generadores Automaticos --------------------------------

@bot.command()
async def mood(ctx, *, categoria: str):
    """Crea playlist según una palabra clave (mood)
    Uso: !mood feliz  o  !mood fiesta  o  !mood gym
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login para conectar tu cuenta.")
        return
    
    # Normalizamos el texto (todo a minúsculas y sin espacios extra)
    mood_input = categoria.lower().strip()
    
    # Diccionario: Palabra Clave -> (Nombre para Playlist, Término de búsqueda en Spotify)
    # He agregado sinónimos para que sea flexible
    mood_map = {
        # Felicidad
        'feliz':    ('Feliz', 'happy hits good vibes pop'),
        'alegre':   ('Feliz', 'happy hits good vibes pop'),
        'happy':    ('Feliz', 'happy hits good vibes pop'),
        
        # Tristeza
        'triste':   ('Sad', 'sad songs piano melancolia'),
        'sad':      ('Sad', 'sad songs piano melancolia'),
        'depre':    ('Sad', 'sad songs piano melancolia'),
        'llorar':   ('Sad', 'crying songs sad ballads'),

        # Energía / Gym
        'gym':      ('Gym', 'gym workout motivation phonk'),
        'entrenar': ('Gym', 'gym workout motivation phonk'),
        'power':    ('Power', 'gym workout motivation rock'),
        'workout':  ('Gym', 'gym workout motivation phonk'),

        # Fiesta
        'fiesta':   ('Fiesta', 'party hits reggaeton perreo club'),
        'party':    ('Fiesta', 'party hits reggaeton perreo club'),
        'reggaeton':('Reggaeton', 'reggaeton mix urbano'),

        # Relax / Dormir
        'relax':    ('Relax', 'chill lo-fi acoustic'),
        'chill':    ('Relax', 'chill lo-fi acoustic'),
        'dormir':   ('Sleep', 'sleep calm ambient piano'),
        'estudiar': ('Focus', 'study lofi focus beats'),

        # Amor
        'amor':     ('Amor', 'love songs romantic ballads'),
        'romantico':('Amor', 'love songs romantic ballads'),
        'sexo':     ('Intenso', 'sexy hits r&b slow'), # Opcional jaja

        # Géneros específicos como mood
        'rock':     ('Rock', 'rock classics metal hits'),
        'metal':    ('Metal', 'metalcore heavy metal'),
        'pop':      ('Pop', 'pop hits current charts'),
    }
    
    # Verificación
    if mood_input not in mood_map:
        # Mostramos algunas opciones disponibles
        opciones = "feliz, triste, fiesta, gym, relax, dormir, amor, rock"
        await ctx.send(f"❌ No reconozco el mood: '{mood_input}'.\n💡 Intenta con: {opciones}")
        return
    
    # Extraemos los datos del diccionario
    playlist_name_suffix, search_term = mood_map[mood_input]
    
    await ctx.send(f"🎨 Buscando canciones para mood: **{playlist_name_suffix}**...")
    
    try:
        all_tracks = []
        # Buscamos playlists públicas que coincidan con el término
        playlists = sp.search(q=search_term, type='playlist', limit=5)
        
        # Recolectamos canciones de esas playlists
        for playlist in playlists['playlists']['items']:
            if len(all_tracks) >= 30:
                break
            
            try:
                tracks = sp.playlist_tracks(playlist['id'], limit=10)
                for item in tracks['items']:
                    if len(all_tracks) >= 30:
                        break
                    
                    # Verificación extra para evitar errores de datos nulos
                    if item.get('track') and item['track'].get('uri'):
                        uri = item['track']['uri']
                        # Evitar duplicados
                        if uri not in all_tracks:
                            all_tracks.append(uri)
            except:
                continue # Si una playlist falla, pasamos a la siguiente
        
        if len(all_tracks) == 0:
            await ctx.send(f"❌ No encontré canciones suficientes para '{mood_input}'")
            return
        
        # Crear la playlist en la cuenta del usuario
        user_id = sp.current_user()['id']
        final_playlist_name = f"Mood {playlist_name_suffix} (Bot)"
        
        pl = sp.user_playlist_create(user_id, final_playlist_name, public=False, description=f"Creada por el bot para el mood: {mood_input}")
        
        # Agregar canciones en lotes (Spotify a veces falla si mandas muchas de golpe, pero 30 está bien)
        sp.playlist_add_items(pl['id'], all_tracks)
        
        await ctx.send(f"✅ **Playlist Creada:** {final_playlist_name}\n🔗 {pl['external_urls']['spotify']}\n🎵 {len(all_tracks)} canciones añadidas.")
        
    except Exception as e:
        print(f"Error en mood: {e}")
        await ctx.send("❌ Ocurrió un error al crear la playlist. Revisa la consola o intenta de nuevo.")

@bot.command()
async def decada(ctx, entrada: str):
    """
    Genera una playlist de una década específica.
    Uso: !decada 80 | !decada 90s | !decada 2000 | !decada 10
    """
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    # 1. LIMPIEZA Y LÓGICA DE AÑO INTELIGENTE
    raw_year = entrada.lower().replace('s', '').replace("'", '').strip()
    
    if not raw_year.isdigit():
        await ctx.send("❌ Formato incorrecto. Intenta: `!decada 80`, `!decada 90`, `!decada 2000`")
        return
    
    val = int(raw_year)
    full_year = 0
    
    # Lógica para convertir "80" -> 1980 y "10" -> 2010
    if val < 100:
        if val >= 50: # Asumimos 1950-1999
            full_year = 1900 + val
        else:         # Asumimos 2000-2049
            full_year = 2000 + val
    else:
        full_year = val

    # Validación básica (no viajar al futuro lejano o pasado muy lejano)
    if full_year < 1950 or full_year > 2029:
        await ctx.send(f"⚠️ Solo tengo buena data musical entre 1950 y 2029. (Tú pediste {full_year})")
        return

    decade_str = f"{full_year}s" # Ej: "1980s"
    await ctx.send(f"🕰️ Encendiendo la máquina del tiempo: Destino **{decade_str}**...")
    
    try:
        # 2. BÚSQUEDA DIVERSIFICADA
        # Buscamos varias frases para no obtener siempre la misma playlist "Top 50"
        queries = [
            f"Best of {decade_str}",
            f"{decade_str} smash hits",
            f"{decade_str} pop rock",
            f"Top hits {decade_str}"
        ]
        
        collected_uris = set()
        target_count = 40
        
        # Barajamos las búsquedas para variar el orden de prioridad
        random.shuffle(queries)

        for query in queries:
            if len(collected_uris) >= target_count + 10: # Buscamos un poco de sobra
                break
                
            # Buscamos playlists
            results = sp.search(q=query, type='playlist', limit=4)
            playlists_items = results['playlists']['items']
            random.shuffle(playlists_items) # Mezclar playlists encontradas
            
            for pl in playlists_items:
                if len(collected_uris) >= target_count + 10:
                    break
                
                try:
                    # Extraer canciones (limitado a 15 por playlist para tener variedad)
                    tracks = sp.playlist_tracks(pl['id'], limit=15)
                    for item in tracks['items']:
                        track = item.get('track')
                        if track and track.get('uri'):
                            # Validación opcional: Verificar fecha de lanzamiento (si está disponible)
                            # Esto asegura que no se cuelen canciones nuevas en playlists viejas
                            release_date = track.get('album', {}).get('release_date', '0000')
                            if release_date.startswith(str(full_year)[:3]): # Chequeo rápido de década (ej: 198)
                                collected_uris.add(track['uri'])
                            else:
                                # Si no coincide la fecha exacta, lo agregamos igual con probabilidad 
                                # (porque a veces las playlists tienen remasters con fecha nueva)
                                if random.random() > 0.3: 
                                    collected_uris.add(track['uri'])

                except:
                    continue

        if not collected_uris:
            await ctx.send(f"❌ No pude recopilar suficientes canciones de los {decade_str}.")
            return

        # 3. MEZCLA FINAL Y CREACIÓN
        final_track_list = list(collected_uris)
        random.shuffle(final_track_list)
        final_track_list = final_track_list[:target_count]
        
        user_id = sp.current_user()['id']
        playlist_title = f"Flashback: {decade_str} (Bot)"
        
        pl = sp.user_playlist_create(
            user_id, 
            playlist_title, 
            public=False,
            description=f"Viaje musical a los {decade_str}. Generado por tu Bot de Discord."
        )
        
        sp.playlist_add_items(pl['id'], final_track_list)
        
        await ctx.send(f"📼 **¡Cinta lista!**\n📂 Playlist: **{playlist_title}**\n🔗 {pl['external_urls']['spotify']}\n🎵 {len(final_track_list)} canciones cargadas.")
        
    except Exception as e:
        print(f"Error en decada: {e}")
        await ctx.send("❌ Ocurrió un error en la máquina del tiempo.")

# ------------------------- Comandos de Estadística ----------------------------

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


# -------------------------------- Playlists Colaborativas --------------------------------

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

# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+ EJECUTAR +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN no encontrado en .env")
        exit(1)
    
    print("🚀 Iniciando bot...")
    bot.run(DISCORD_TOKEN)

# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+ FIN  +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=
# +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+==+=+=+=
