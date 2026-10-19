"""Comandos del bot: playlists."""

import random

from config import bot, make_spotify_client_for_user


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
