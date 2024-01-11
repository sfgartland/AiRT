from pathlib import Path
from pytube import YouTube

from .CommandRunners import runCommand

from .fileHandler import generateWorkbenchPath, makeSureFolderExists


# TODO update so it also checks for captions automatically
def getFromYoutube(url: str, outputFolder: Path, progressObject=None):
    makeSureFolderExists(outputFolder)

    # TODO Move UI stuff to main function?
    def progess_callback(stream, bytes, left):
        progressObject.update(download_task, completed=stream.filesize - left)

    y = YouTube(url)
    if progressObject:
        y.register_on_progress_callback(progess_callback)
    s = y.streams.filter(adaptive=True)
    

    v = s.filter(file_extension="mp4").order_by("resolution").desc().first()
    a = s.filter(only_audio=True).order_by("abr").desc().first()

    outputPath = outputFolder / v.default_filename

    if not outputPath.is_file():
        videoPath = generateWorkbenchPath(v.default_filename)
        audioPath = generateWorkbenchPath(a.default_filename)

        if progressObject:
            video_task = progressObject.add_task("Downloading video....", total=v.filesize)
            audio_task = progressObject.add_task("Downloading audio....", total=a.filesize)
            download_task = video_task
        v.download(output_path=videoPath.parent, filename=videoPath.name)
        if progressObject:
            download_task = audio_task
        a.download(output_path=audioPath.parent, filename=audioPath.name)

        if progressObject:
            progressObject.add_task("Merging video and audio files...", total=None)
        runCommand(
            f'ffmpeg -i "{videoPath}" -i "{audioPath}" -c:v copy -c:a aac "{outputPath}"'
        )
        progressObject.stop()
    return outputPath
