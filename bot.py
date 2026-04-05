import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime
 
# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN", "TU_TOKEN_AQUI")
DATA_FILE = "data.json"
 
# Puntos fijos por tipo de cueva en Fjordur
CUEVAS_FIJAS = {
    "Cueva del Hielo (Fácil)": 5,
    "Cueva del Hielo (Media)": 10,
    "Cueva del Hielo (Difícil)": 20,
    "Cueva Acuática": 15,
    "Cueva de Lava": 25,
    "Cueva Asgard": 30,
    "Cueva Jotunheim": 35,
    "Cueva Vanaheim": 30,
    "Cueva del Jefe (Beyla)": 50,
    "Cueva del Jefe (Steinbjörn)": 60,
    "Cueva del Jefe (Skoll & Hati)": 70,
}
 
# ─── DATOS ────────────────────────────────────────────────────────────────────
def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {"tribus": {}, "solicitudes_pendientes": [], "log_channel": None}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
 
# ─── BOT SETUP ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
 
bot = commands.Bot(command_prefix="!", intents=intents)
 
# ─── HELPERS ──────────────────────────────────────────────────────────────────
def es_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or \
           any(r.name.lower() in ["admin", "administrador", "moderador", "mod"] 
               for r in interaction.user.roles)
 
def es_lider(interaction: discord.Interaction, datos) -> str | None:
    """Devuelve el nombre de la tribu si el usuario es líder, None si no."""
    uid = str(interaction.user.id)
    for nombre, tribu in datos["tribus"].items():
        if tribu["lider_id"] == uid:
            return nombre
    return None
 
def embed_base(titulo, descripcion="", color=0x00b4d8):
    embed = discord.Embed(title=f"🦕 {titulo}", description=descripcion, color=color)
    embed.set_footer(text="ARK Survival Evolved • Fjordur PS4")
    return embed
 
async def notificar_log(guild, mensaje):
    datos = cargar_datos()
    ch_id = datos.get("log_channel")
    if ch_id:
        ch = guild.get_channel(int(ch_id))
        if ch:
            await ch.send(mensaje)
 
# ═══════════════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
 
# ─── /registrar-tribu ─────────────────────────────────────────────────────────
@bot.tree.command(name="registrar-tribu", description="Registra tu tribu en el servidor")
@app_commands.describe(
    nombre="Nombre de la tribu",
    tag="Tag/abreviatura de la tribu (ej: [ARK])",
    miembros="PSN IDs de los miembros separados por comas",
    nombre_cueva="Nombre de la cueva base de la tribu (ej: Cueva del Hielo)",
    coordenadas="Coordenadas de la cueva base (ej: 35.2 / 56.8)"
)
async def registrar_tribu(interaction: discord.Interaction, nombre: str, tag: str, miembros: str,
                           nombre_cueva: str, coordenadas: str):
    datos = cargar_datos()
 
    # Validar que no sea ya líder de otra tribu
    tribu_actual = es_lider(interaction, datos)
    if tribu_actual:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"Ya eres líder de la tribu **{tribu_actual}**.", 0xff4444),
            ephemeral=True
        )
        return
 
    # Validar nombre único
    if nombre.lower() in [t.lower() for t in datos["tribus"]]:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"Ya existe una tribu con el nombre **{nombre}**.", 0xff4444),
            ephemeral=True
        )
        return
 
    lista_miembros = [m.strip() for m in miembros.split(",") if m.strip()]
    if len(lista_miembros) < 1 or len(lista_miembros) > 6:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Las tribus deben tener entre 1 y 6 miembros.", 0xff4444),
            ephemeral=True
        )
        return
 
    # Crear solicitud pendiente
    solicitud = {
        "tipo": "registro_tribu",
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "nombre": nombre,
        "tag": tag,
        "lider_id": str(interaction.user.id),
        "lider_discord": interaction.user.display_name,
        "miembros_psn": lista_miembros,
        "nombre_cueva": nombre_cueva,
        "coordenadas": coordenadas,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    datos["solicitudes_pendientes"].append(solicitud)
    guardar_datos(datos)
 
    embed = embed_base("✅ Solicitud enviada", 
        f"Tu tribu **{nombre}** [{tag}] está pendiente de aprobación por un admin.\n\n"
        f"**Miembros PSN:** {', '.join(lista_miembros)}\n"
        f"**Cueva base:** {nombre_cueva}\n"
        f"**Coordenadas:** `{coordenadas}`", 0xffa500)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await notificar_log(interaction.guild, 
        f"📋 Nueva solicitud de tribu: **{nombre}** [{tag}] por {interaction.user.mention}\n"
        f"🗺️ Cueva: {nombre_cueva} | 📍 Coords: `{coordenadas}`")
 
# ─── /aprobar-tribu ───────────────────────────────────────────────────────────
@bot.tree.command(name="aprobar-tribu", description="[ADMIN] Aprueba o rechaza una solicitud de tribu")
@app_commands.describe(id_solicitud="ID de la solicitud", accion="aprobar o rechazar")
@app_commands.choices(accion=[
    app_commands.Choice(name="Aprobar", value="aprobar"),
    app_commands.Choice(name="Rechazar", value="rechazar"),
])
async def aprobar_tribu(interaction: discord.Interaction, id_solicitud: str, accion: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    sol = next((s for s in datos["solicitudes_pendientes"] 
                if s["id"] == id_solicitud and s["tipo"] == "registro_tribu"), None)
 
    if not sol:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la solicitud `{id_solicitud}`.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos["solicitudes_pendientes"].remove(sol)
 
    if accion == "aprobar":
        datos["tribus"][sol["nombre"]] = {
            "tag": sol["tag"],
            "lider_id": sol["lider_id"],
            "lider_discord": sol["lider_discord"],
            "miembros_psn": sol["miembros_psn"],
            "discord_miembros": {},
            "nombre_cueva": sol.get("nombre_cueva", "No especificada"),
            "coordenadas": sol.get("coordenadas", "No especificadas"),
            "puntos": 0,
            "raids": [],
            "fecha_registro": sol["fecha"]
        }
        guardar_datos(datos)
        embed = embed_base("✅ Tribu aprobada", 
            f"La tribu **{sol['nombre']}** [{sol['tag']}] ha sido **aprobada** por {interaction.user.mention}.", 0x00ff88)
        
        # Notificar al líder
        lider = interaction.guild.get_member(int(sol["lider_id"]))
        if lider:
            try:
                await lider.send(embed=embed_base("🎉 ¡Tribu aprobada!", 
                    f"Tu tribu **{sol['nombre']}** ha sido aprobada en el servidor ARK Fjordur PS4."))
            except:
                pass
    else:
        guardar_datos(datos)
        embed = embed_base("❌ Tribu rechazada", 
            f"La solicitud de tribu **{sol['nombre']}** ha sido **rechazada**.", 0xff4444)
 
    await interaction.response.send_message(embed=embed)
 
# ─── /solicitudes-pendientes ───────────────────────────────────────────────────
@bot.tree.command(name="solicitudes-pendientes", description="[ADMIN] Ver todas las solicitudes pendientes")
async def solicitudes_pendientes(interaction: discord.Interaction):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    solic = datos["solicitudes_pendientes"]
    if not solic:
        await interaction.response.send_message(
            embed=embed_base("📋 Solicitudes", "No hay solicitudes pendientes."), ephemeral=True)
        return
 
    embed = embed_base("📋 Solicitudes Pendientes", f"Total: **{len(solic)}**", 0xffa500)
    for s in solic:
        if s["tipo"] == "registro_tribu":
            embed.add_field(
                name=f"[{s['id']}] 🏕️ {s['nombre']} [{s['tag']}]",
                value=f"👑 Líder: {s['lider_discord']}\n"
                      f"🎮 PSN: {', '.join(s['miembros_psn'])}\n"
                      f"🗺️ Cueva: {s.get('nombre_cueva', 'No especificada')} | 📍 `{s.get('coordenadas', 'N/A')}`\n"
                      f"📅 {s['fecha']}\n"
                      f"✅ `/aprobar-tribu {s['id']} aprobar` | ❌ `/aprobar-tribu {s['id']} rechazar`",
                inline=False
            )
        elif s["tipo"] == "raid":
            embed.add_field(
                name=f"[{s['id']}] ⚔️ Raid de {s['tribu']}",
                value=f"🗺️ Cueva: {s['cueva']}\n"
                      f"🏆 Puntos: {s['puntos']}\n"
                      f"📝 {s.get('notas', 'Sin notas')}\n"
                      f"📅 {s['fecha']}\n"
                      f"✅ `/aprobar-raid {s['id']} aprobar` | ❌ `/aprobar-raid {s['id']} rechazar`",
                inline=False
            )
 
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
# ─── /añadir-raid ─────────────────────────────────────────────────────────────
@bot.tree.command(name="añadir-raid", description="Registra una raid completada por tu tribu")
@app_commands.describe(
    tipo_cueva="¿La cueva tiene puntos fijos o variables?",
    cueva="Nombre de la cueva",
    puntos_variables="Puntos (solo si es cueva variable)",
    notas="Notas adicionales (opcional)"
)
@app_commands.choices(tipo_cueva=[
    app_commands.Choice(name="Cueva con puntos fijos", value="fija"),
    app_commands.Choice(name="Cueva con puntos variables (admin decide)", value="variable"),
])
async def añadir_raid(interaction: discord.Interaction, tipo_cueva: str, cueva: str, 
                       puntos_variables: int = 0, notas: str = ""):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
 
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes de tribu pueden registrar raids.", 0xff4444),
            ephemeral=True
        )
        return
 
    puntos = 0
    cueva_display = cueva
 
    if tipo_cueva == "fija":
        # Buscar la cueva (búsqueda flexible)
        match = next((k for k in CUEVAS_FIJAS if cueva.lower() in k.lower()), None)
        if not match:
            lista = "\n".join([f"• {k} ({v} pts)" for k, v in CUEVAS_FIJAS.items()])
            await interaction.response.send_message(
                embed=embed_base("❌ Cueva no encontrada", 
                    f"Cuevas disponibles:\n{lista}", 0xff4444),
                ephemeral=True
            )
            return
        cueva_display = match
        puntos = CUEVAS_FIJAS[match]
    else:
        if puntos_variables <= 0:
            await interaction.response.send_message(
                embed=embed_base("❌ Error", "Debes indicar los puntos para una cueva variable.", 0xff4444),
                ephemeral=True
            )
            return
        puntos = puntos_variables
 
    solicitud = {
        "tipo": "raid",
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "tribu": nombre_tribu,
        "cueva": cueva_display,
        "puntos": puntos,
        "tipo_cueva": tipo_cueva,
        "notas": notas,
        "lider_id": str(interaction.user.id),
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    datos["solicitudes_pendientes"].append(solicitud)
    guardar_datos(datos)
 
    embed = embed_base("⚔️ Raid registrada", 
        f"Tu raid en **{cueva_display}** ({puntos} pts) está **pendiente de validación** por un admin.\n\n"
        f"{'📝 ' + notas if notas else ''}", 0xffa500)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await notificar_log(interaction.guild, 
        f"⚔️ Nueva raid pendiente: **{nombre_tribu}** → {cueva_display} ({puntos} pts)")
 
# ─── /aprobar-raid ────────────────────────────────────────────────────────────
@bot.tree.command(name="aprobar-raid", description="[ADMIN] Aprueba o rechaza una raid")
@app_commands.describe(id_solicitud="ID de la solicitud", accion="aprobar o rechazar")
@app_commands.choices(accion=[
    app_commands.Choice(name="Aprobar", value="aprobar"),
    app_commands.Choice(name="Rechazar", value="rechazar"),
])
async def aprobar_raid(interaction: discord.Interaction, id_solicitud: str, accion: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    sol = next((s for s in datos["solicitudes_pendientes"] 
                if s["id"] == id_solicitud and s["tipo"] == "raid"), None)
 
    if not sol:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la raid `{id_solicitud}`.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos["solicitudes_pendientes"].remove(sol)
 
    if accion == "aprobar":
        tribu = datos["tribus"].get(sol["tribu"])
        if not tribu:
            await interaction.response.send_message(
                embed=embed_base("❌ Error", "La tribu ya no existe.", 0xff4444), ephemeral=True)
            return
 
        tribu["puntos"] += sol["puntos"]
        tribu["raids"].append({
            "cueva": sol["cueva"],
            "puntos": sol["puntos"],
            "fecha": sol["fecha"],
            "validado_por": interaction.user.display_name
        })
        guardar_datos(datos)
        embed = embed_base("✅ Raid aprobada", 
            f"Raid de **{sol['tribu']}** en **{sol['cueva']}** aprobada. "
            f"+**{sol['puntos']} puntos**", 0x00ff88)
        await notificar_log(interaction.guild,
            f"✅ Raid aprobada: **{sol['tribu']}** +{sol['puntos']} pts ({sol['cueva']})")
    else:
        guardar_datos(datos)
        embed = embed_base("❌ Raid rechazada", 
            f"La raid de **{sol['tribu']}** en **{sol['cueva']}** ha sido rechazada.", 0xff4444)
 
    await interaction.response.send_message(embed=embed)
 
# ─── /marcador ────────────────────────────────────────────────────────────────
@bot.tree.command(name="marcador", description="Ver el ranking de tribus por puntos de raid")
async def marcador(interaction: discord.Interaction):
    datos = cargar_datos()
    if not datos["tribus"]:
        await interaction.response.send_message(
            embed=embed_base("🏆 Marcador", "Aún no hay tribus registradas."), ephemeral=False)
        return
 
    sorted_tribus = sorted(datos["tribus"].items(), key=lambda x: x[1]["puntos"], reverse=True)
    
    medallas = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, (nombre, t) in enumerate(sorted_tribus):
        medalla = medallas[i] if i < 3 else f"`#{i+1}`"
        raids_count = len(t["raids"])
        desc += f"{medalla} **{t['tag']} {nombre}** — **{t['puntos']} pts** ({raids_count} raids)\n"
 
    embed = embed_base("🏆 Alpha Cluster Ranking — Fjordur PS4", desc, 0xffd700)
    embed.set_thumbnail(url="https://i.imgur.com/9xKMqSO.png")
    embed.add_field(name="📅 Actualizado", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
    embed.add_field(name="🏕️ Tribus activas", value=str(len(datos["tribus"])), inline=True)
    await interaction.response.send_message(embed=embed)
 
# ─── /tribu ───────────────────────────────────────────────────────────────────
@bot.tree.command(name="tribu", description="Ver información detallada de una tribu")
@app_commands.describe(nombre="Nombre de la tribu")
async def tribu_info(interaction: discord.Interaction, nombre: str):
    datos = cargar_datos()
    
    # Búsqueda flexible
    match = next((k for k in datos["tribus"] if nombre.lower() in k.lower()), None)
    if not match:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la tribu **{nombre}**.", 0xff4444),
            ephemeral=True
        )
        return
 
    t = datos["tribus"][match]
    lider = interaction.guild.get_member(int(t["lider_id"]))
    lider_mention = lider.mention if lider else t["lider_discord"]
 
    embed = embed_base(f"🏕️ {t['tag']} {match}", color=0x00b4d8)
    embed.add_field(name="👑 Líder", value=lider_mention, inline=True)
    embed.add_field(name="🏆 Puntos", value=f"**{t['puntos']}**", inline=True)
    embed.add_field(name="⚔️ Raids", value=str(len(t["raids"])), inline=True)
    embed.add_field(name="🎮 Miembros PSN", value="\n".join([f"• {m}" for m in t["miembros_psn"]]) or "N/A", inline=False)
    # Cueva y coords solo visibles para admins o el propio líder
    es_lider_tribu = str(interaction.user.id) == t["lider_id"]
    if es_admin(interaction) or es_lider_tribu:
        embed.add_field(name="🗺️ Cueva Base", value=t.get("nombre_cueva", "No especificada"), inline=True)
        embed.add_field(name="📍 Coordenadas", value=f"`{t.get('coordenadas', 'No especificadas')}`", inline=True)
    embed.add_field(name="📅 Registrada", value=t["fecha_registro"], inline=True)
 
    if t["raids"]:
        ultimas = t["raids"][-3:][::-1]
        raids_txt = "\n".join([f"• {r['cueva']} (+{r['puntos']} pts) — {r['fecha']}" for r in ultimas])
        embed.add_field(name="🗺️ Últimas raids", value=raids_txt, inline=False)
 
    await interaction.response.send_message(embed=embed)
 
# ─── /mis-tribus ──────────────────────────────────────────────────────────────
@bot.tree.command(name="mis-tribus", description="Ver tu tribu registrada")
async def mis_tribus(interaction: discord.Interaction):
    datos = cargar_datos()
    uid = str(interaction.user.id)
    tribu_nombre = es_lider(interaction, datos)
    
    if not tribu_nombre:
        await interaction.response.send_message(
            embed=embed_base("ℹ️ Sin tribu", "No eres líder de ninguna tribu registrada.", 0x888888),
            ephemeral=True
        )
        return
 
    t = datos["tribus"][tribu_nombre]
    embed = embed_base(f"🏕️ Tu tribu: {t['tag']} {tribu_nombre}", 
        f"**Puntos:** {t['puntos']}\n**Raids completadas:** {len(t['raids'])}", 0x00b4d8)
    embed.add_field(name="🎮 Miembros PSN", value="\n".join([f"• {m}" for m in t["miembros_psn"]]), inline=False)
    embed.add_field(name="🗺️ Cueva Base", value=t.get("nombre_cueva", "No especificada"), inline=True)
    embed.add_field(name="📍 Coordenadas", value=f"`{t.get('coordenadas', 'No especificadas')}`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
# ─── /cuevas ──────────────────────────────────────────────────────────────────
@bot.tree.command(name="cuevas", description="Ver la lista de cuevas y sus puntos fijos en Fjordur")
async def cuevas(interaction: discord.Interaction):
    embed = embed_base("🗺️ Cuevas de Fjordur — Puntos Fijos", color=0x7b2d8b)
    for nombre, pts in CUEVAS_FIJAS.items():
        embed.add_field(name=nombre, value=f"**{pts} puntos**", inline=True)
    embed.add_field(
        name="⚙️ Cuevas Variables", 
        value="Los admins asignan los puntos según dificultad y contexto.", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)
 
# ─── /añadir-miembro ──────────────────────────────────────────────────────────
@bot.tree.command(name="añadir-miembro", description="Añade un miembro PSN a tu tribu")
@app_commands.describe(psn_id="PSN ID del nuevo miembro")
async def añadir_miembro(interaction: discord.Interaction, psn_id: str):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes pueden añadir miembros.", 0xff4444),
            ephemeral=True
        )
        return
 
    tribu = datos["tribus"][nombre_tribu]
    if len(tribu["miembros_psn"]) >= 6:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "El máximo es 6 miembros por tribu.", 0xff4444),
            ephemeral=True
        )
        return
 
    if psn_id in tribu["miembros_psn"]:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"**{psn_id}** ya es miembro de la tribu.", 0xff4444),
            ephemeral=True
        )
        return
 
    tribu["miembros_psn"].append(psn_id)
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("✅ Miembro añadido", f"**{psn_id}** añadido a la tribu **{nombre_tribu}**.", 0x00ff88),
        ephemeral=True
    )
 
# ─── /eliminar-tribu ──────────────────────────────────────────────────────────
@bot.tree.command(name="eliminar-tribu", description="[ADMIN] Elimina una tribu del servidor")
@app_commands.describe(nombre="Nombre de la tribu a eliminar")
async def eliminar_tribu(interaction: discord.Interaction, nombre: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden eliminar tribus.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    match = next((k for k in datos["tribus"] if nombre.lower() in k.lower()), None)
    if not match:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la tribu **{nombre}**.", 0xff4444),
            ephemeral=True
        )
        return
 
    del datos["tribus"][match]
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("🗑️ Tribu eliminada", f"La tribu **{match}** ha sido eliminada.", 0xff4444)
    )
 
# ─── /listar-tribus ───────────────────────────────────────────────────────────
@bot.tree.command(name="listar-tribus", description="[ADMIN] Ver todas las tribus registradas con sus miembros")
async def listar_tribus(interaction: discord.Interaction):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    if not datos["tribus"]:
        await interaction.response.send_message(
            embed=embed_base("🏕️ Tribus registradas", "No hay ninguna tribu registrada aún."),
            ephemeral=True
        )
        return
 
    sorted_tribus = sorted(datos["tribus"].items(), key=lambda x: x[1]["puntos"], reverse=True)
    total_miembros = sum(len(t["miembros_psn"]) for _, t in sorted_tribus)
 
    # Si hay muchas tribus, dividir en varios embeds
    embeds = []
    embed = embed_base(
        f"🏕️ Tribus Registradas — {len(sorted_tribus)} tribus · {total_miembros} jugadores",
        color=0x00b4d8
    )
 
    for i, (nombre, t) in enumerate(sorted_tribus):
        lider = interaction.guild.get_member(int(t["lider_id"]))
        lider_txt = lider.mention if lider else f"@{t['lider_discord']}"
        miembros_txt = "\n".join([f"  🎮 `{m}`" for m in t["miembros_psn"]])
        raids_count = len(t["raids"])
 
        campo = (
            f"👑 Líder Discord: {lider_txt}\n"
            f"🏆 Puntos: **{t['puntos']}** · ⚔️ Raids: **{raids_count}**\n"
            f"🗺️ Cueva: {t.get('nombre_cueva', 'No especificada')} | 📍 `{t.get('coordenadas', 'N/A')}`\n"
            f"👥 Miembros PSN ({len(t['miembros_psn'])}/6):\n{miembros_txt}\n"
            f"📅 Registrada: {t['fecha_registro']}"
        )
 
        embed.add_field(
            name=f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '▫️'} {t['tag']} {nombre}",
            value=campo,
            inline=False
        )
 
        # Discord permite max 25 fields por embed
        if (i + 1) % 10 == 0:
            embeds.append(embed)
            embed = embed_base(f"🏕️ Tribus Registradas (cont.)", color=0x00b4d8)
 
    embeds.append(embed)
 
    await interaction.response.send_message(embed=embeds[0], ephemeral=True)
    for extra in embeds[1:]:
        await interaction.followup.send(embed=extra, ephemeral=True)
 
# ─── /set-log-channel ─────────────────────────────────────────────────────────
@bot.tree.command(name="set-log-channel", description="[ADMIN] Establece el canal de logs del bot")
@app_commands.describe(canal="Canal donde se enviarán los logs")
async def set_log_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden configurar esto.", 0xff4444),
            ephemeral=True
        )
        return
 
    datos = cargar_datos()
    datos["log_channel"] = str(canal.id)
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("✅ Canal configurado", f"Los logs se enviarán a {canal.mention}.", 0x00ff88),
        ephemeral=True
    )
 
# ─── /ayuda ───────────────────────────────────────────────────────────────────
@bot.tree.command(name="ayuda", description="Ver todos los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = embed_base("📖 Comandos del Bot ARK Fjordur", color=0x00b4d8)
    
    embed.add_field(name="🏕️ Tribus", value=
        "`/registrar-tribu` — Registra tu tribu (requiere aprobación admin)\n"
        "`/mis-tribus` — Ver tu tribu\n"
        "`/tribu [nombre]` — Info de una tribu\n"
        "`/añadir-miembro [psn]` — Añade miembro a tu tribu",
        inline=False
    )
    embed.add_field(name="⚔️ Raids", value=
        "`/añadir-raid` — Registrar una raid (requiere aprobación admin)\n"
        "`/cuevas` — Ver cuevas y puntos fijos",
        inline=False
    )
    embed.add_field(name="🏆 Ranking", value=
        "`/marcador` — Ver ranking Alpha Cluster",
        inline=False
    )
    embed.add_field(name="🔐 Admin", value=
        "`/solicitudes-pendientes` — Ver solicitudes\n"
        "`/aprobar-tribu [id] [acción]` — Aprobar/rechazar tribu\n"
        "`/aprobar-raid [id] [acción]` — Aprobar/rechazar raid\n"
        "`/listar-tribus` — Ver todas las tribus y sus miembros\n"
        "`/eliminar-tribu [nombre]` — Eliminar tribu\n"
        "`/set-log-channel [canal]` — Canal de logs",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
 
# ─── EVENTOS ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos slash sincronizados")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="ARK Fjordur PS4 🦕")
    )
 
# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(TOKEN)
