"""Comandos del bot: tematicas."""

from config import bot, make_spotify_client_for_user


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
