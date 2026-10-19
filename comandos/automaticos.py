"""Comandos del bot: automaticos."""

import random

from config import bot, make_spotify_client_for_user


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
