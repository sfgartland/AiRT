import asyncio
import math
import subprocess
import shutil
from types import NoneType
from typing import List
from pydub import AudioSegment
from pydub.silence import detect_leading_silence, detect_nonsilent
import glob
import datetime


from pathlib import Path


from rich import print

from loguru import logger

import ffmpeg

from .Types import FilePairType, FilePairsType, ToMp3_FileTypes

from .CommandRunners import runCommand, runFfmpegCommandAsync

from .helpers import USER_DIR

from moviepy.editor import concatenate_videoclips, VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

# from ffmpeg_progress_yield import FfmpegProgress

DEFAULT_WORKBENCH_FOLDER = USER_DIR / "workbench"


def generateWorkbenchPath(inputFile, workbenchPath=DEFAULT_WORKBENCH_FOLDER):
    makeSureFolderExists(workbenchPath)
    return (
        Path(workbenchPath)
        / f"{Path(inputFile).stem}-temp-{'{:%Y-%b-%d--%H-%M-%S-%f}'.format(datetime.datetime.now())}{Path(inputFile).suffix}"
    )


def cleanupWorkbench(workbenchPath=DEFAULT_WORKBENCH_FOLDER):
    shutil.rmtree(workbenchPath)


def makeSureFolderExists(folderPath):
    folderPath = Path(folderPath)
    if folderPath.suffix != "" and not folderPath.parent.exists():
        folderPath.parent.mkdir(parents=True)
    elif folderPath.suffix == "" and not folderPath.exists():
        folderPath.mkdir(parents=True)


def m3u8UrlToMp4(url, output):
    runCommand(f'ffmpeg -loglevel error -i "{url}" -codec copy {output}')


def ToMp3(input, output=None, progress=None):
    input = Path(input)
    if output:
        output = Path(output)
    else:
        output = input.parent / f"{input.stem}.mp3"

    tempOut = generateWorkbenchPath(output)

    filetype = ToMp3_FileTypes(input.suffix.replace(".", ""))

    if progress is not None:
        totalLength = getLength(input)
        rip_task = progress.add_task("Ripping mp3 file...", total=totalLength)

    progressCallback = (
        lambda x: progress.update(rip_task, completed=x)
        if progress is not None
        else None
    )

    if filetype is ToMp3_FileTypes.mp4:
        asyncio.run(
            runFfmpegCommandAsync(
                f'ffmpeg -i "{input}" -vn "{tempOut}"',
                progressCallback=progressCallback,
            )
        )
    elif filetype is ToMp3_FileTypes.m4a:
        asyncio.run(
            runFfmpegCommandAsync(
                f'ffmpeg -i "{input}" -c:v copy -c:a libmp3lame -q:a 4 "{tempOut}"',
                progressCallback=progressCallback,
            )
        )
    elif filetype is ToMp3_FileTypes.ogg:
        asyncio.run(
            runFfmpegCommandAsync(
                f'ffmpeg -i "{input}" "{tempOut}"', progressCallback=progressCallback
            )
        )  ## E.g. .ogg

    if progress is not None:
        progress.update(rip_task, completed=totalLength)

    shutil.move(tempOut, output)
    return output


def ripAudioFromFolder(inputFolder, outputFolder):
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)

    makeSureFolderExists(outputFolder)
    inputFiles = [Path(file) for file in glob.glob(f"{inputFolder}/*.mp4")]
    print(f"Handling input files: {inputFiles}")
    for inputFile in inputFiles:
        print(f"Handling file: {inputFile}")
        ToMp3(inputFile, outputFolder / f"{inputFile.stem}.mp3")


# TODO check that I can migrate this to the new function, should be just to pop it in place
def getLength_old(path):
    p = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{str(path)}"',
        capture_output=True,
        shell=True,
        universal_newlines=True,
    )
    return float(p.stdout.replace("\n", ""))


def getLength(path: Path) -> float:
    return float(ffmpeg.probe(path)["format"]["duration"])


def cutAudio(input: Path, outputFolder: Path, lengthDuration: int, progress=None):
    # TODO Add option for setting approx file size instead, would be better for use with the API
    totalLength = getLength_old(input)
    lengths = math.ceil(totalLength / lengthDuration)

    logger.info(f"Total length is: {totalLength}")

    lengths = [
        (
            i * lengthDuration,
            (i + 1) * lengthDuration
            if (i + 1) * lengthDuration < totalLength
            else totalLength,
        )
        for i in range(0, lengths)
    ]
    logger.info(f"Will create {len(lengths)} clips")

    makeSureFolderExists(outputFolder)
    # TODO This generates a corrupted (empty?) audio file at the end fix it! However, it is not needed for local processing so I don't use it anymore
    ffmpeg_task = progress.add_task(
        "Splitting up current file for processing...", total=totalLength
    )

    for index, length in enumerate(lengths):
        outputPath = outputFolder / f"{input.stem}-{index}{input.suffix}"
        processedLengths = lengths[index - 1][1] if index > 0 else 0

        asyncio.run(
            runFfmpegCommandAsync(
                f'ffmpeg -ss {length[0]} -to {length[1]} -i "{input}" "{outputPath}" -acodec copy',
                progressCallback=lambda x: progress.update(
                    ffmpeg_task, completed=x + processedLengths
                ),
            )
        )
    progress.update(ffmpeg_task, completed=totalLength)

    return outputFolder


def ripWav(inputfile: Path, outputfile:Path=None, progress=None):
    if outputfile is None:
        outputfile = generateWorkbenchPath("audioenchanger_input.wav")

    if progress is not None:
        totalLength = getLength(inputfile)
        rip_task = progress.add_task("Ripping wav file...", total=totalLength)

    progressCallback = (
        lambda x: progress.update(rip_task, completed=x)
        if progress is not None
        else None
    )

    asyncio.run(
        runFfmpegCommandAsync(
            f'ffmpeg -i "{inputfile}" "{outputfile}"', progressCallback=progressCallback
        )
    )

    if progress is not None:
        progress.update(rip_task, completed=totalLength)

    return outputfile

def replaceAudioMp4(inputvideo: Path, inputaudio: Path, outputfile: Path = None, progress=None):
    if outputfile is None:
        outputfile = generateWorkbenchPath("replaced_audio.mp4")
    
    if progress is not None:
        totalLength = getLength(inputvideo)
        rip_task = progress.add_task("Replacing audio in mp4 file...", total=totalLength)

    progressCallback = (
        lambda x: progress.update(rip_task, completed=x)
        if progress is not None
        else None
    )
    asyncio.run(
        runFfmpegCommandAsync(
            f'ffmpeg -i "{inputvideo}" -i "{inputaudio}" -c:v copy -map 0:v:0 -map 1:a:0 "{outputfile}"', progressCallback=progressCallback
        )
    )

    if progress is not None:
        progress.update(rip_task, completed=totalLength)

    return outputfile




def trimSilence(
    videoFile,
    outputFile,
    only_leading=False,
    progress=None,
    seek_step=10,
    db_cutoff=-70,
):
    """Function that trims the silence from the videofile,
    it requires a separate ripped mp3 file to detect the silence"""
    # TODO Add check for .mp4 in in and out or modify to work with all files

    # TODO make it check if it is video or audio so that it can process both
    # Uses pydub.AudioSegment to find the time of the silence

    # initialAudio = ToMp3(videoFile, generateWorkbenchPath("initialaudio.mp3"), progress=progress)
    # initialAudio = ""
    loading_task = progress.add_task("Loading audio file...", total=None)
    audio = AudioSegment.from_file(videoFile, "mp4")
    progress.update(loading_task, completed=1, total=1)

    makeSureFolderExists(outputFile)
    silence_task = progress.add_task("Detecting silence...", total=None)
    if only_leading:
        non_silences = [
            (
                detect_leading_silence(
                    audio, silence_threshold=db_cutoff, chunk_size=seek_step
                ),
                getLength(videoFile) * 1000,
            )
        ]
    else:
        non_silences = detect_nonsilent(
            audio, seek_step=seek_step, silence_thresh=db_cutoff
        )
    progress.update(silence_task, completed=1, total=1)

    subclips = []
    for non_silence in non_silences:
        subclipPath = generateWorkbenchPath("subclip.mp4")
        ffmpeg_extract_subclip(
            videoFile, non_silence[0] / 1000, non_silence[1] / 1000, subclipPath
        )
        subclips.append(subclipPath)
    if len(subclips) > 1:
        tempOut = generateWorkbenchPath("silencetrimmedout.mp4")
        asyncio.run(concatMp4s_ffmpeg(subclips, tempOut))
        shutil.move(tempOut, outputFile)
    else:
        shutil.move(subclips[0], outputFile)
    return outputFile


# TODO change this callback handling to match the cutAudio function
async def concatMp4s_ffmpeg(
    inputPaths: List[Path],
    outputPath: Path,
    progressCallback=None,
    initProgress=None,
    recode=False,
):
    if outputPath.suffix != ".mp4":
        Exception("Output file has to be a mp4")

    for inputPath in inputPaths:
        if inputPath.suffix != ".mp4":
            Exception(f"Input path is not mp4 file: {inputPath}")

    makeSureFolderExists(outputPath)
    txtFile = generateWorkbenchPath("concatfile-ffmpeg.txt")
    with open(txtFile, "w", encoding="utf-8") as f:
        f.writelines([f"file '{file}'\n" for file in inputPaths])
    if initProgress is not None:
        totalDuration = sum([getLength(file) for file in inputPaths])
        initProgress(totalDuration)
    await runFfmpegCommandAsync(
        f'ffmpeg -safe 0 -f concat -i "{txtFile}" {"-c copy" if not recode else ""} "{outputPath}"',
        progressCallback=progressCallback,
    )


def concatMp4s_moviepy(
    inputPaths: List[Path],
    outputPath: Path,
):
    if outputPath.suffix != ".mp4":
        Exception("Output file has to be a mp4")

    for inputPath in inputPaths:
        if inputPath.suffix != ".mp4":
            Exception(f"Input path is not mp4 file: {inputPath}")

    makeSureFolderExists(outputPath)
    # TODO This currently shows the default progressbar for moviepy, update to use rich progress
    clips = [VideoFileClip(str(file)) for file in inputPaths]
    finalclip = concatenate_videoclips(clips, method="compose")
    tempout = generateWorkbenchPath("concat.mp4")
    finalclip.write_videofile(
        str(tempout), temp_audiofile=generateWorkbenchPath("tempaudio.mp3")
    )
    shutil.move(tempout, outputPath)


def copyFilesToGoogleColab(
    inputFolder,
    outputFolder,
    filePattern="**/*.mp3",
    fileFilter=lambda fileList: fileList,
):
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)
    logger.info(
        f"Copying files from {inputFolder} to {outputFolder} for processing in Google Colab"
    )

    inputFiles = fileFilter(
        [
            Path(file)
            for file in glob.glob(f"{inputFolder}/{filePattern}", recursive=True)
        ]
    )

    for inputFile in inputFiles:
        outputPath = outputFolder / inputFile.relative_to(inputFolder)
        makeSureFolderExists(outputPath)
        logger.info(f"Copying {inputFile}->{outputPath}")
        shutil.copy(inputFile, outputPath)


def getCommonParent(files: list[Path]):
    commonFolder = files[0].parent
    for file in files:
        while commonFolder not in file.parents:
            commonFolder = commonFolder.parent

    return commonFolder


def ignoreAlreadyProcessed(filePairs: FilePairsType):
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    return [filePair for filePair in filePairs if filePair not in ignoreFilePairs]


# TODO Improve to also accept .gitignore style content in the file, allowing to name ignored files
def ignoreAirtIgnoreFiles(filePairs: FilePairType):
    def shouldIgnore(filePair):
        inputFile = filePair[0]

        currentPath = inputFile.absolute()
        lastPath = None
        ignore = False
        end = False
        while not ignore and not end:
            ignore = (currentPath / ".airtignore").is_file()
            end = (
                currentPath == lastPath
            )  # TODO This is not a great way to check if it should be ignored, recode
            lastPath = currentPath
            currentPath = currentPath.parent
        if ignore:
            logger.info(f"Detected `.airtignore` file, skipping `{inputFile}`!")
        return ignore

    return [pair for pair in filePairs if not shouldIgnore(pair)]


def base_getInOutPaths(
    inputPath: str | Path | List[Path],
    outputFolder: str | Path | NoneType,
    pattern: str | List[str],
    prefix: str,
    postfix: str,
    filetype: str,
) -> FilePairsType:
    """Reusable function to get input and output paths for summaries"""
    # Casts inputs into Path objects
    if isinstance(inputPath, str):
        inputPath = Path(inputPath)
    if len(inputPath) == 1:
        inputPath = Path(inputPath[0])

    if isinstance(outputFolder, str):
        outputFolder = Path(outputFolder)

    if isinstance(pattern, str):
        pattern = [pattern]

    # If it is a path,
    if isinstance(inputPath, Path):
        if inputPath.suffix == "":
            inputFolder = inputPath
            inputFiles = [
                [Path(file) for file in glob.glob(f"{inputPath}/{pat}", recursive=True)]
                for pat in pattern
            ]
            inputFiles = sum(inputFiles, [])  # Flatten list
        else:
            inputFolder = inputPath.parent
            inputFiles = [
                Path(file) for file in glob.glob(f"{inputPath}", recursive=True)
            ]
    elif isinstance(inputPath, List):
        inputFolder = getCommonParent(inputPath)
        inputFiles = inputPath

    if outputFolder is None:
        outputFolder = inputFolder

    if outputFolder.suffix != "":
        raise Exception(
            "'outputFolder' has to be a folder, not file. You cannot choose the output path yourself."
        )

    return [
        (
            inputFile,
            outputFolder
            / inputFile.parent.relative_to(inputFolder)
            / f"{prefix}{inputFile.stem}{postfix}.{filetype}",
        )
        for inputFile in inputFiles
    ]
