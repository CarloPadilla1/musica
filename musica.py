import yt_dlp
import os
import sys
import ctypes
import json
import tkinter as tk
from tkinter import filedialog
import subprocess
from typing import Optional, Tuple, Dict, Any, List

# --- INFORMACIÓN DEL PROYECTO ---
__version__ = '2.1.0'
# -------------------------------

class ConfigManager:
    """Gestiona la configuración de la aplicación y persistencia de datos."""
    
    def __init__(self):
        self.config_file = 'config.json'
        self.base_path = self._obtener_ruta_base()
        self.config_path = os.path.join(self.base_path, self.config_file)

    def _obtener_ruta_base(self) -> str:
        """Detecta si es .exe o script para saber dónde guardar archivos."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def cargar_configuracion(self) -> Optional[str]:
        """Lee la ruta de descarga desde config.json."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('ruta_descarga')
            except Exception as e:
                print(f"Error al leer configuración: {e}")
                return None
        return None

    def guardar_configuracion(self, ruta: str) -> None:
        """Guarda la ruta de descarga en config.json."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump({'ruta_descarga': ruta}, f)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

class Utils:
    """Funciones de utilidad estáticas."""
    
    @staticmethod
    def formatear_tamano(bytes_val: float) -> str:
        """Convierte bytes a un formato legible (KB, MB, GB)."""
        for unidad in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unidad}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"

    @staticmethod
    def verificar_ffmpeg() -> bool:
        """Verifica si ffmpeg está accesible en el sistema."""
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            resultado = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True,
                startupinfo=startupinfo,
                timeout=3
            )
            return resultado.returncode == 0
        except:
            return False

class YouTubeService:
    """Maneja la lógica de interacción con yt-dlp y descargas."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def verificar_tipo_contenido(self, url: str) -> Tuple[Optional[str], Optional[str], int]:
        """Analiza la URL para determinar si es video o playlist."""
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

    def obtener_calidades_disponibles(self, url: str, video_codec: str = 'any') -> Dict[int, Dict[str, Any]]:
        """
        Obtiene las calidades de video disponibles para una URL.
        video_codec: 'any' (default), 'vp9' (para WebM alta calidad), 'avc' (h264/mp4 compatible)
        """
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
                    vcodec = formato.get('vcodec', 'none')
                    if vcodec == 'none': continue
                    
                    # Filtrado por codec
                    if video_codec == 'vp9' and 'vp9' not in vcodec: continue
                    if video_codec == 'avc' and 'avc' not in vcodec and 'h264' not in vcodec: continue

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
                    
                    # Si es VP9 explícitamente, lo indicamos
                    if 'vp9' in vcodec: nombre_calidad += ' (VP9)'
                    
                    actualizar = False
                    if altura not in calidades: actualizar = True
                    else:
                        info_existente = calidades[altura]
                        # Priorizamos FPS, luego tamaño
                        if fps > info_existente['fps']: actualizar = True
                        elif fps == info_existente['fps'] and tamaño_total > info_existente['tamaño']: actualizar = True

                    if actualizar:
                        calidades[altura] = {
                            'nombre': nombre_calidad,
                            'resolucion': f"{formato.get('width',0)}x{altura}",
                            'tamaño': tamaño_total,
                            'formato_id': formato.get('format_id'),
                            'ext': formato.get('ext', 'mp4'), # Extensión base, luego se puede mergear
                            'fps': fps,
                            'vcodec': vcodec
                        }
                return calidades
        except Exception as e:
            print(f"Error: {e}")
            return {}

    def descargar(self, url: str, tipo: str, formato_id: Optional[str], audio_format: str = 'mp3', directorio: str = '', contenedor: str = 'mp4') -> None:
        """Ejecuta la descarga del contenido."""
        if not os.path.exists(directorio):
            os.makedirs(directorio)

        opciones = {
            'outtmpl': os.path.join(directorio, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            # Forzar cliente Android para evitar problemas con HLS/SABR (fragment not found)
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        ffmpeg_ok = Utils.verificar_ffmpeg()

        if tipo == 'musica':
            opciones['format'] = 'bestaudio/best'
            if ffmpeg_ok:
                opciones['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': '192',
                }]
            else:
                print("\n⚠️ FFmpeg no detectado. Se descargará el audio original sin convertir.")
                
        elif tipo == 'video':
            if formato_id:
                opciones['format'] = f'{formato_id}+bestaudio/best'
            else:
                if contenedor == 'webm':
                    opciones['format'] = 'bestvideo[vcodec*=vp9]+bestaudio/best'
                else:
                    opciones['format'] = 'bestvideo+bestaudio/best'
            
            # Solo forzar conversión si queremos un contenedor específico y tenemos ffmpeg
            if ffmpeg_ok:
                opciones['merge_output_format'] = contenedor
                # Solo convertimos si NO es el contenedor nativo deseado (aunque merge_output_format suele encargarse)
                pass 

        try:
            print(f"\n📂 Guardando en: {directorio}\n")
            with yt_dlp.YoutubeDL(opciones) as ydl:
                ydl.download([url])
            print("\n✓ Descarga completada!")
        except Exception as e:
            print(f"Error durante la descarga: {e}")

class CLIInterface:
    """Interfaz de Línea de Comandos para interação con el usuario."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.youtube_service = YouTubeService(self.config_manager)
        if os.name == 'nt':
            try: ctypes.windll.kernel32.SetConsoleTitleW(f"YouTube Downloader v{__version__}")
            except: pass

    def seleccionar_carpeta_grafica(self) -> Optional[str]:
        """Abre diálogo de selección de carpeta."""
        print("\n Abriendo ventana de selección...")
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        carpeta = filedialog.askdirectory(title="Selecciona dónde guardar la música y videos")
        root.destroy()
        
        if carpeta:
            self.config_manager.guardar_configuracion(carpeta)
            return carpeta
        return None

    def obtener_directorio_salida(self) -> str:
        """Obtiene el directorio de descarga, solicitándolo si no existe."""
        ruta_guardada = self.config_manager.cargar_configuracion()
        
        if ruta_guardada and os.path.exists(ruta_guardada):
            return ruta_guardada
        
        print("\n  No hay carpeta de descarga configurada.")
        nueva_ruta = self.seleccionar_carpeta_grafica()
        
        return nueva_ruta if nueva_ruta else os.path.join(self.config_manager.base_path, 'playlist')

    def ejecutar_menu(self):
        """Bucle principal del menú."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            ruta_actual = self.config_manager.cargar_configuracion() or "Sin configurar (se pedirá al descargar)"
            
            print("=" * 60)
            print(f"   DESCARGADOR DE YOUTUBE 🎬  |  v{__version__} (Refactored)")
            print("=" * 60)
            print(f" Carpeta actual: {ruta_actual}")
            print("-" * 60)
            
            url = input("\n Ingresa URL (o escribe 'cambiar' o 'salir'): ").strip()
            
            if url.lower() == 'salir': break
            if url.lower() == 'cambiar':
                nueva = self.seleccionar_carpeta_grafica()
                if nueva: print(f"✓ Carpeta cambiada a: {nueva}")
                continue
                
            if not url: continue
            
            print("\n Analizando...")
            tipo_cont, nombre, cant = self.youtube_service.verificar_tipo_contenido(url)
            
            if not tipo_cont:
                input(" Error al leer URL. Enter para continuar...")
                continue
                
            print(f"\n {tipo_cont.upper()}: {nombre} ({cant} elementos)")
            
            print("\n¿Qué deseas hacer?")
            print("1. Descargar Música (MP3)")
            print("2. Descargar Música (Opus) HQ")
            print("3. Descargar Video (MP4)")
            print("4. Descargar Video (VP9/WebM) HQ")
            print("5. Cancelar operación")
            print("6. Cambiar carpeta de descarga")
            
            op = input("\nOpción: ").strip()
            
            directorio = self.obtener_directorio_salida()
            
            if op == '1':
                self.youtube_service.descargar(url, 'musica', None, 'mp3', directorio)
                input("\nPresiona Enter para continuar...")

            elif op == '2':
                self.youtube_service.descargar(url, 'musica', None, 'opus', directorio)
                input("\nPresiona Enter para continuar...")
                
            elif op == '3':
                # MP4 / AVC
                calidades = self.youtube_service.obtener_calidades_disponibles(url, video_codec='avc')
                if not calidades:
                    self.youtube_service.descargar(url, 'video', None, directorio=directorio, contenedor='mp4')
                else:
                    print("\n--- CALIDADES (MP4/H264) ---")
                    ordenadas = sorted(calidades.items(), reverse=True)
                    for i, (h, info) in enumerate(ordenadas, 1):
                        tam = Utils.formatear_tamano(info['tamaño']) if info['tamaño'] else "~"
                        print(f"{i}. {info['nombre']:20s} - {tam}")
                    print(f"{len(ordenadas)+1}. Automático (Mejor MP4)")
                    
                    sel = input(f"\nElige (1-{len(ordenadas)+1}): ")
                    try:
                        idx = int(sel)
                        fid = ordenadas[idx-1][1]['formato_id'] if 1 <= idx <= len(ordenadas) else None
                    except: fid = None
                    
                    self.youtube_service.descargar(url, 'video', fid, directorio=directorio, contenedor='mp4')
                input("\nPresiona Enter para continuar...")

            elif op == '4':
                # VP9 / WebM
                calidades = self.youtube_service.obtener_calidades_disponibles(url, video_codec='vp9')
                if not calidades:
                    print("\n No se encontraron calidades VP9 específicas, intentando automático...")
                    self.youtube_service.descargar(url, 'video', None, directorio=directorio, contenedor='webm')
                else:
                    print("\n--- CALIDADES (VP9/WebM) ---")
                    ordenadas = sorted(calidades.items(), reverse=True)
                    for i, (h, info) in enumerate(ordenadas, 1):
                        tam = Utils.formatear_tamano(info['tamaño']) if info['tamaño'] else "~"
                        print(f"{i}. {info['nombre']:20s} - {tam}")
                    print(f"{len(ordenadas)+1}. Automático (Mejor VP9)")
                    
                    sel = input(f"\nElige (1-{len(ordenadas)+1}): ")
                    try:
                        idx = int(sel)
                        fid = ordenadas[idx-1][1]['formato_id'] if 1 <= idx <= len(ordenadas) else None
                    except: fid = None
                    
                    self.youtube_service.descargar(url, 'video', fid, directorio=directorio, contenedor='webm')
                input("\nPresiona Enter para continuar...")
                
            elif op == '6':
                self.seleccionar_carpeta_grafica()

if __name__ == "__main__":
    app = CLIInterface()
    app.ejecutar_menu()
