from pathlib import Path
from pytube import YouTube

from rich.progress import Progress


# TODO update so it also checks for captions automatically
def getFromYoutube(url, outputFolder: Path):
    with Progress() as progress:

        def progess_callback(stream, bytes, left):
            progress.update(download_task, completed=stream.filesize - left)

        s = YouTube(url, on_progress_callback=progess_callback).streams.filter(
            adaptive=True
        )
        v = s.filter(file_extension="mp4").order_by("resolution").desc().first()
        a = s.filter(only_audio=True).order_by("abr").desc().first()
        v.filename = outputFolder
        # download_task = progress.add_task("Downloading video....", total=v.filesize)
        # v.download()
        download_task = progress.add_task("Downloading audio....", total=a.filesize)
        a.filename = outputFolder / a.default_filename
        a.download()
