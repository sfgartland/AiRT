from enum import Enum
from openai import OpenAI

try:
    import whisper
except ImportError:
    whisper = None

import os
import glob
from pathlib import Path

from .fileHandler import (
    FilePairsType,
    base_getInOutPaths,
    cutAudio,
    ToMp3,
    trimSilence,
    generateWorkbenchPath,
    makeSureFolderExists,
)


from loguru import logger

import time
import datetime


# TODO This pipeline needs to be updated to work witht the workbench workflow
def generateTranscriptWithApi(inputFile, lengths=15*60, progress=None):
    inputFile = Path(inputFile)
    client = OpenAI()

    logger.info(f"Cutting up '{inputFile}' into {lengths}s chunck to feed to api!")
    outputFolderClippings = generateWorkbenchPath(f"cut_audio-{lengths}")
    cutAudio(inputFile, outputFolderClippings, lengths, progress=progress)
    logger.info("Finished cutting up the input file!")
    # outputFolderClippings = Path("workbench/cut_audio-900-temp-2024-Jan-11--12-47-23-299137")
    segments = glob.glob(str(Path(outputFolderClippings / "*.mp3").as_posix()))
    if progress is not None:
        api_task = progress.add_task("Transcribing chunks through api... ", total=len(segments))

    transcript = ""
    for segment in segments:
        audio_file = open(segment, "rb")
        apiResponse = client.audio.translations.create(
            model="whisper-1",
            file=audio_file,
            response_format="json",
            prompt=transcript,
        )
        transcript = transcript + apiResponse.text
        if progress is not None:
            progress.update(api_task, advance=1)
    return transcript


class WhisperModels(str, Enum):
    moviepy = "moviepy"
    ffmpeg = "ffmpeg"

# TODO Make the models into a proper type
def generateTranscriptLocally(input, model="large", progress=None):
    if whisper is None:
        raise ImportError("The Whisper package is not installed, it is needed to do local transcription. Please install the right optional dependencies!")

    # Using `verbose=False` to get progressbar
    # TODO I removed the verbose param to test a bit, add again if I want progressbar

    logger.info("loading whisper model...")
    model = whisper.load_model(model)
    logger.info("Loaded model, starting transcription...")

    if progress is not None:
        trans_task = progress.add_task("Transcribing file", total=None)
    result = model.transcribe(str(input))
    if progress is not None:
        progress.update(trans_task, completed=1, total=1)
    # logger.info(result)
    return result["text"]


# TODO Should this be moved to the fileHandler file?
def writeToFile(transcript, output):
    makeSureFolderExists(output)
    with open(output, "w", encoding="utf-8") as outputFile:
        outputFile.write(str(transcript))


# TODO This currently stops when it encounters an error, could be better for it to keep going on next file
# I've tried, does it work?
# TODO Should this be moved to the fileHandler file?
def batchProcessMediaFiles(inputFolder, outputFolder, fileFilter=lambda x: x):
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)
    logger.info(
        f'Batch processing media files in "{inputFolder}" and outputting to "{outputFolder}"'
    )
    inputFolders = [
        Path(file) for file in glob.glob(f"{inputFolder}/*") if os.path.isdir(file)
    ]

    for folder in inputFolders:
        files = [Path(file) for file in glob.glob(f"{folder}/*.mp4")]
        for inputFile in files:
            logger.info(f"Working on file: {inputFile}")
            outputPathVideo = (
                outputFolder
                / inputFile.parent.relative_to(inputFolder)
                / inputFile.name
            )
            outputPathAudio = (
                outputFolder
                / inputFile.parent.relative_to(inputFolder)
                / f"{inputFile.stem}.mp3"
            )
            try:
                if not outputPathVideo.is_file():
                    logger.info("Trimming leading silence")
                    trimSilence(inputFile, outputPathVideo, only_leading=True)
                if not outputPathAudio.is_file():
                    logger.info("Converting trimmed video to mp3")
                    ToMp3(outputPathVideo, outputPathAudio)
            except Exception as err:
                logger.info(f"Encountered error while processing '{inputFile}'")
                logger.error(err)


def getTranscriptInOutPaths(inputPath: Path, outputFolder: Path, modelName, fileFilter=lambda x: x) -> FilePairsType:
    """Reusable function to get input and output paths for transcriptions"""
    return fileFilter(
        base_getInOutPaths(
            inputPath, outputFolder, "**/*.mp3", "transcript_", f"_{modelName}", "txt"
        )
    )


def batchTranscribeMp3sLocally(inputFolder, outputFolder, model, modelName):
    logger.info(
        f'Batch transcribing files in "{inputFolder}" and outputting to "{outputFolder}"'
    )

    filePairs = getTranscriptInOutPaths(inputFolder, outputFolder, modelName)

    for inputFile, outputFile in filePairs:
        if not outputFile.is_file():
            logger.info(
                f'Transcribing locally with file "{inputFile}"'
            )  # Uses the last generated mp3
            try:
                start = time.time()
                transcript = generateTranscriptLocally(inputFile, model)
                end = time.time()
                logger.info(
                    f"Transcription time: {datetime.timedelta(seconds=(end-start))}"
                )
                writeToFile(transcript, outputFile)
            except Exception as err:
                logger.info(
                    f"Encountered error while transcribing and saving '{outputFile}'"
                )
                logger.error(err)


def createWhisperModel(modelName="base.en"):
    return whisper.load_model(modelName), modelName
