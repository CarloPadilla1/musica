# Descargador de Playlist de YouTube

Hice esto porque ya me dió pereza pedirle el ytdownloader a mi pana, es tarde y no quiero esperar hasta el otro día

- Python 3.x
- yt-dlp
- FFmpeg (necesario para convertir a MP3)

python -m pip install -r requirements.txt

## Notas v2.1.0

- Se agregó el formato de opus para audios de alta calidad
- Se agregó el formato de webm para videos de alta calidad
- Tener ffmpeg sigue siendo obligatorio

### Instalar FFmpeg (esto es para pasarlo a mp3)

Descarga FFmpeg desde: https://ffmpeg.org/download.html 
Te dará dos opciones pero ve al git chaval porque el de la web tambien te mandará a git xd
Extrae el archivo y cambiale el nombre a ffmepeg
Ahora ese directorio ffmpeg muevelo al disco(o agrega al path directo, ahí ves que chanchuyo haces, te digo lo que es más recomendable bobote :p)
Agrega la carpeta `bin`(del directorio ffmpeg) a tu PATH


## Uso

```bash
python musica.py
o
ejecutar MusicaDownloader_v2.exe
```

### Ejecución

Te pedirá que pongas el enlace de la lista de reprodución de YT, ahí tu ves si quieres descargar el video o solo el audio y ya eso es todo, el menú es con números y todo es intuitivo, "creo".

## Notas

- Las canciones se guardan con el título del video como nombre de archivo
- Algo que me pasó probando es que debes tener cuidado cuando copias el enlaces, aveces copias sin querer una playlist, igual el codigo te muestra cuantas canciones de van a descargar, pero pilas con eso



