"""Comandos del bot: estadisticas."""

import discord

from config import bot, make_spotify_client_for_user


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
