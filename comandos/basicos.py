"""Comandos del bot: basicos."""

import discord
import spotipy

from config import bot, SPOTIFY_SERVICE_URL, get_access_token_for_user


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
