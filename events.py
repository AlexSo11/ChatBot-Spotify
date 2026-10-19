"""Eventos de Discord: conexión, manejo de errores y despacho de la IA."""

import asyncio
import json
import re

import ia_agent
import spotipy
from discord.ext import commands

from config import bot, SPOTIFY_SERVICE_URL, get_access_token_for_user, extraer_link_spotify, proceso_crear_playlist_pesado


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
