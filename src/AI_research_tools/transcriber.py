import shutil
from openai import OpenAI
import whisper

import os
import glob
from pathlib import Path

from .fileHandler import base_getInOutPaths, cutAudio, ToMp3, trimLeadingSilence, generateWorkbenchPath, makeSureFolderExists

from rich import print

from loguru import logger

import time
import datetime


# TODO This pipeline needs to be updated to work witht the workbench workflow
def generateTranscriptWithApi(inputFile, lengths=15*60):
    inputFile = Path(inputFile)
    client = OpenAI()

    logger.info(f"Cutting up '{input}' into {lengths}s chunck to feed to api!")
    outputFolderClippings = generateWorkbenchPath(f"cut_audio-{lengths}")
    cutAudio(inputFile,
             outputFolderClippings, lengths)
    logger.info(f"Finished cutting up the input file!")
    segments = glob.glob(str(Path(outputFolderClippings / "*.mp3").as_posix()))

    transcript = ""
    for segment in segments:
        audio_file = open(segment, "rb")
        apiResponse = client.audio.translations.create(
            model="whisper-1",
            file=audio_file,
            response_format="json",
            prompt=transcript
        )
        transcript = transcript+apiResponse.text
    return transcript

def generateTranscriptLocally(input, model):
    # Using `verbose=False` to get progressbar
    result = model.transcribe(str(input), verbose=False)
    # logger.info(result)
    return result["text"]

# TODO Should this be moved to the fileHandler file?
def writeToFile(transcript, output):
    makeSureFolderExists(output)
    with open(output, "w", encoding="utf-8") as outputFile:
        outputFile.write(str(transcript))


#TODO This currently stops when it encounters an error, could be better for it to keep going on next file
    # I've tried, does it work?
# TODO Should this be moved to the fileHandler file?
def batchProcessMediaFiles(inputFolder, outputFolder, fileFilter=lambda x: x):
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)
    logger.info(
        f"Batch processing media files in \"{inputFolder}\" and outputting to \"{outputFolder}\"")
    inputFolders = [Path(file) for file in glob.glob(
        f"{inputFolder}/*") if os.path.isdir(file)]

    for folder in inputFolders:
        files = [Path(file) for file in glob.glob(f"{folder}/*.mp4")]
        for inputFile in files:
            logger.info(f"Working on file: {inputFile}")
            outputPathVideo = outputFolder / inputFile.parent.relative_to(inputFolder) / inputFile.name
            outputPathAudio = outputFolder / inputFile.parent.relative_to(inputFolder) / f"{inputFile.stem}.mp3"
            try:
                if not outputPathVideo.is_file():
                    logger.info(f"Trimming leading silence")
                    trimLeadingSilence(inputFile, outputPathVideo)
                if not outputPathAudio.is_file():
                    logger.info(f"Converting trimmed video to mp3")
                    ToMp3(outputPathVideo, outputPathAudio)
            except Exception as err:
                logger.info(f"Encountered error while processing '{inputFile}'")
                logger.error(err)


def getTranscriptInOutPaths(inputPath, outputFolder, modelName, fileFilter=lambda x: x):
    """Reusable function to get input and output paths for transcriptions"""
    return fileFilter(base_getInOutPaths(inputPath, outputFolder, "**/*.mp3", "transcript_", f"_{modelName}", "txt"))



def batchTranscribeMp3sLocally(inputFolder, outputFolder, model, modelName):
    logger.info(
        f"Batch transcribing files in \"{inputFolder}\" and outputting to \"{outputFolder}\"")
    
    filePairs = getTranscriptInOutPaths(inputFolder, outputFolder, modelName)

    for inputFile,outputFile in filePairs:
        if not outputFile.is_file():
            logger.info(f"Transcribing locally with file \"{inputFile}\"") # Uses the last generated mp3
            try:
                start = time.time()
                transcript = generateTranscriptLocally(inputFile, model)
                end = time.time()
                logger.info(f"Transcription time: {datetime.timedelta(seconds=(end-start))}")
                writeToFile(transcript, outputFile)
            except Exception as err:
                logger.info(f"Encountered error while transcribing and saving '{outputFile}'")
                logger.error(err)

def createWhisperModel(modelName="base.en"):
    return whisper.load_model(modelName),modelName