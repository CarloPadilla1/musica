import yt_dlp
import os
import sys
import ctypes
import json
import tkinter as tk
from tkinter import filedialog

# --- INFORMACIÓN DEL PROYECTO ---
__version__ = '2.0.0'
# -------------------------------

def obtener_ruta_base():
    """Detecta si es .exe o script para saber dónde guardar el archivo de configuración"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def cargar_configuracion():
    """Lee la carpeta guardada en config.json"""
    ruta_json = os.path.join(obtener_ruta_base(), 'config.json')
    if os.path.exists(ruta_json):
        try:
            with open(ruta_json, 'r') as f:
                data = json.load(f)
                return data.get('ruta_descarga')
        except:
            return None
    return None

def guardar_configuracion(ruta):
    """Guarda la carpeta elegida en config.json"""
    ruta_json = os.path.join(obtener_ruta_base(), 'config.json')
    try:
        with open(ruta_json, 'w') as f:
            json.dump({'ruta_descarga': ruta}, f)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")

def seleccionar_carpeta_grafica():
    """Abre una ventana de Windows para elegir carpeta"""
    print("\n📂 Abriendo ventana de selección...")
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventanita principal de tk
    root.attributes('-topmost', True)  # Poner la ventana al frente
    
    carpeta = filedialog.askdirectory(title="Selecciona dónde guardar la música y videos")
    root.destroy()
    
    if carpeta:
        guardar_configuracion(carpeta)
        return carpeta
    return None

def obtener_directorio_salida():
    """
    Gestiona la lógica de directorios:
    1. Busca en config.json
    2. Si no existe, pide al usuario que elija (una sola vez)
    """
    ruta_guardada = cargar_configuracion()
    
    if ruta_guardada and os.path.exists(ruta_guardada):
        return ruta_guardada
    
    # Si no hay ruta o la carpeta se borró, pedimos seleccionar
    print("\n⚠️  No hay carpeta de descarga configurada.")
    nueva_ruta = seleccionar_carpeta_grafica()
    
    if nueva_ruta:
        return nueva_ruta
    else:
        # Si el usuario cancela, usamos una por defecto temporal
        return os.path.join(obtener_ruta_base(), 'playlist')

# --- FUNCIONES DE FORMATO Y VERIFICACIÓN ---

def formatear_tamano(bytes):
    for unidad in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unidad}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def verificar_ffmpeg():
    try:
        import subprocess
        # Buscamos ffmpeg junto al ejecutable o en el sistema
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        resultado = subprocess.run(['ffmpeg', '-version'], 
                                 capture_output=True, 
                                 text=True,
                                 startupinfo=startupinfo, # Evita parpadeo de consola
                                 timeout=3)
        return resultado.returncode == 0
    except:
        return False

def verificar_tipo_contenido(url):
    opciones_info = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    try:
        es_playlist_url = 'list=' in url
        with yt_dlp.YoutubeDL(opciones_info) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info or es_playlist_url:
                cantidad = len(info.get('entries', [])) if 'entries' in info else 1
                return 'playlist', info.get('title', 'Sin título'), cantidad
            else:
                return 'video', info.get('title', 'Sin título'), 1
    except Exception as e:
        print(f"Error al obtener información: {e}")
        return None, None, 0

def obtener_calidades_disponibles(url):
    opciones_info = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(opciones_info) as ydl:
            info = ydl.extract_info(url, download=False)
            formatos = info.get('formats', [])
            calidades = {}
            nombres_calidad = {
                144: '144p', 240: '240p', 360: '360p', 480: '480p',
                720: '720p HD', 1080: '1080p Full HD', 1440: '1440p 2K',
                2160: '2160p 4K', 4320: '4320p 8K'
            }
            
            mejor_audio_size = 0
            for formato in formatos:
                if formato.get('vcodec') == 'none' and formato.get('acodec') != 'none':
                    audio_size = formato.get('filesize', 0) or formato.get('filesize_approx', 0)
                    if audio_size > mejor_audio_size: mejor_audio_size = audio_size
            
            duracion = info.get('duration', 0)
            for formato in formatos:
                if formato.get('vcodec') != 'none':
                    altura = formato.get('height', 0)
                    if not altura or altura < 144: continue
                    
                    video_size = formato.get('filesize', 0) or formato.get('filesize_approx', 0)
                    tamaño_total = video_size
                    if formato.get('acodec') == 'none' and mejor_audio_size > 0:
                        tamaño_total += mejor_audio_size
                    if tamaño_total == 0 and duracion > 0:
                        tbr = formato.get('tbr', 0)
                        if tbr > 0: tamaño_total = int((tbr * duracion * 1024) / 8)
                    
                    nombre_calidad = nombres_calidad.get(altura, f'{altura}p')
                    fps = formato.get('fps', 0)
                    if fps and fps > 30: nombre_calidad += f' {int(fps)}fps'
                    
                    actualizar = False
                    if altura not in calidades: actualizar = True
                    else:
                        info_existente = calidades[altura]
                        if fps > info_existente['fps']: actualizar = True
                        elif fps == info_existente['fps'] and tamaño_total > info_existente['tamaño']: actualizar = True

                    if actualizar:
                        calidades[altura] = {
                            'nombre': nombre_calidad,
                            'resolucion': f"{formato.get('width',0)}x{altura}",
                            'tamaño': tamaño_total,
                            'formato_id': formato.get('format_id'),
                            'ext': formato.get('ext', 'mp4'),
                            'fps': fps
                        }
            return calidades
    except Exception as e:
        print(f"Error: {e}")
        return {}

def descargar_contenido(url, tipo, formato_id, nombre, cantidad):
    directorio = obtener_directorio_salida()
    # Asegurar que el directorio existe
    if not os.path.exists(directorio):
        os.makedirs(directorio)

    opciones = {
        'outtmpl': os.path.join(directorio, '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,
        'nocheckcertificate': True,
    }
    
    ffmpeg_ok = verificar_ffmpeg()

    if tipo == 'musica':
        opciones['format'] = 'bestaudio/best'
        if ffmpeg_ok:
            opciones['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            print("\n⚠️ FFmpeg no detectado. Se descargará el audio original.")
            
    elif tipo == 'video':
        if formato_id:
            opciones['format'] = f'{formato_id}+bestaudio/best'
        else:
            opciones['format'] = 'bestvideo+bestaudio/best'
        
        opciones['merge_output_format'] = 'mp4'
        # --- AQUÍ ESTABA EL ERROR EN TU CÓDIGO ANTERIOR ---
        opciones['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]

    try:
        print(f"\n💾 Guardando en: {directorio}\n")
        with yt_dlp.YoutubeDL(opciones) as ydl:
            ydl.download([url])
        print("\n✓ Descarga completada!")
    except Exception as e:
        print(f"Error: {e}")

# --- MENÚ PRINCIPAL ---

def menu_interactivo():
    if os.name == 'nt':
        try: ctypes.windll.kernel32.SetConsoleTitleW(f"YouTube Downloader v{__version__}")
        except: pass

    while True:
        # Limpiar pantalla
        os.system('cls' if os.name == 'nt' else 'clear')
        
        ruta_actual = cargar_configuracion() or "Sin configurar (se pedirá al descargar)"
        
        print("=" * 60)
        print(f"  🎵 DESCARGADOR DE YOUTUBE 🎬  |  v{__version__}")
        print("=" * 60)
        print(f"📂 Carpeta actual: {ruta_actual}")
        print("-" * 60)
        
        url = input("\n📎 Ingresa URL (o escribe 'cambiar' o 'salir'): ").strip()
        
        if url.lower() == 'salir': break
        if url.lower() == 'cambiar':
            nueva = seleccionar_carpeta_grafica()
            if nueva: print(f"✓ Carpeta cambiada a: {nueva}")
            continue
            
        if not url: continue
        
        print("\n🔍 Analizando...")
        tipo_cont, nombre, cant = verificar_tipo_contenido(url)
        
        if not tipo_cont:
            input("❌ Error al leer URL. Enter para continuar...")
            continue
            
        print(f"\n✅ {tipo_cont.upper()}: {nombre} ({cant} elementos)")
        
        print("\n¿Qué deseas hacer?")
        print("1. 🎵 Descargar Música (MP3)")
        print("2. 🎬 Descargar Video (MP4)")
        print("3. ❌ Cancelar operación")
        print("4. 📂 Cambiar carpeta de descarga")
        
        op = input("\nOpción: ").strip()
        
        if op == '1':
            descargar_contenido(url, 'musica', None, nombre, cant)
            input("\nPresiona Enter para continuar...")
            
        elif op == '2':
            calidades = obtener_calidades_disponibles(url)
            if not calidades:
                descargar_contenido(url, 'video', None, nombre, cant)
            else:
                print("\n--- CALIDADES ---")
                ordenadas = sorted(calidades.items(), reverse=True)
                for i, (h, info) in enumerate(ordenadas, 1):
                    tam = formatear_tamano(info['tamaño']) if info['tamaño'] else "~"
                    print(f"{i}. {info['nombre']:20s} - {tam}")
                print(f"{len(ordenadas)+1}. Automático (Mejor)")
                
                sel = input(f"\nElige (1-{len(ordenadas)+1}): ")
                try:
                    idx = int(sel)
                    fid = ordenadas[idx-1][1]['formato_id'] if 1 <= idx <= len(ordenadas) else None
                except: fid = None
                
                descargar_contenido(url, 'video', fid, nombre, cant)
            input("\nPresiona Enter para continuar...")
            
        elif op == '4':
            seleccionar_carpeta_grafica()

if __name__ == "__main__":
    menu_interactivo()
