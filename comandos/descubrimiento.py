"""Comandos del bot: descubrimiento."""

from config import bot, make_spotify_client_for_user


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
