from openai import OpenAI
import whisper

import os
import glob
from pathlib import Path

from lib.fileHandler import cutAudio, Mp4ToMp3, trimLeadingSilence, generateWorkbenchPath, makeSureFolderExists

from rich import print

from loguru import logger

import time
import datetime

# from fileHandler import cutAudio

logger.add("logs/transcriber-{time}.log")

def getAudioSegments(folder):
    return glob.glob(f"{folder}/*")


# TODO This pipeline needs to be updated to work witht the workbench workflow
def generateTranscriptWithApi(input, lengths=15*60):
    client = OpenAI()

    logger.info(f"Cutting up '{input}' into {lengths}s chunck to feed to api!")
    cutAudio("audio_PHILOS133_4_November 7th 2023/tester-12.mp3",
             "workbench", lengths)
    logger.info(f"Finnished cutting up the input file!")
    segments = getAudioSegments("workbench")

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


def writeToFile(transcript, output):
    makeSureFolderExists(output)
    with open(output, "w", encoding="utf-8") as outputFile:
        outputFile.write(str(transcript))


#TODO This currently stops when it encounters an error, could be better for it to keep going on next file
    # I've tried, does it work?

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
                    Mp4ToMp3(outputPathVideo, outputPathAudio)
            except Exception as err:
                logger.info(f"Encountered error while processing '{inputFile}'")
                logger.error(err)

def getMp3sToTranscribe(inputFolder, fileFilter=lambda x: x):
    inputFolder = Path(inputFolder)

    inputFiles = [Path(file) for file in glob.glob(
        f"{inputFolder}/**/*.mp3", recursive=True)]
    return fileFilter(inputFiles)

def getTranscriptInOutPaths(inputFolder, outputFolder, modelName, fileFilter=lambda x: x):
    """Reusable function to get input and output paths for transcriptions"""
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)
    logger.info(
        f"Batch transcribing files in \"{inputFolder}\" and outputting to \"{outputFolder}\"")
    inputFiles = fileFilter([Path(file) for file in glob.glob(
        f"{inputFolder}/**/*.mp3", recursive=True)])
    
    getOutputPath = lambda inputFile: outputFolder / inputFile.parent.relative_to(inputFolder) / f"{inputFile.stem}_{modelName}.txt"

    return  [(inputFile, getOutputPath(inputFile)) for inputFile in inputFiles]


def batchTranscribeMp3s(inputFolder, outputFolder, model, modelName):
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

# generateTranscriptLocally("testing/test-14-lengths-60/test-14-1.mp3")
# completePipeline("PHILOS25A/5_November 15th 2023/tester-0.mp4",
#                  "transcript-25a.txt")

# writeToFile(generateTranscriptLocally("workbench/trimmed-audio-temp-2023-Dec-18--15-19-43-988025.mp3"), "workbench/transcript.txt")


# batchTranscribeMp3s("output/PHILOS133", "output/PHILOS133")
# batchProcessMediaFiles("PHILOS133", "output/PHILOS133")

model,modelName = createWhisperModel()


batchTranscribeMp3s("oxford_CPR", "oxford_CPR", model, modelName)
# batchProcessMediaFiles("PHILOS133", "output/PHILOS133")