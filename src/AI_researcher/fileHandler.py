import math
import os
import subprocess
import shutil
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
import glob
import datetime

from pathlib import Path

from rich import print

from loguru import logger


def runCommand(command, output_stdout=False):
    p = subprocess.run(command, capture_output=True, shell=True, universal_newlines=True)
    if output_stdout:
        logger.info(p.stdout)
    else:
        logger.debug(p.stdout)
    logger.error(p.stderr)

def generateWorkbenchPath(inputFile, workbenchPath="workbench"):
    makeSureFolderExists(workbenchPath)
    return Path(workbenchPath) / f"{Path(inputFile).stem}-temp-{'{:%Y-%b-%d--%H-%M-%S-%f}'.format(datetime.datetime.now())}{Path(inputFile).suffix}"


def cleanupWorkbench(workbenchPath="workbench"):
    shutil.rmtree(workbenchPath)


def makeSureFolderExists(folderPath):
    folderPath = Path(folderPath)
    if folderPath.suffix != "" and not folderPath.parent.exists():
        folderPath.parent.mkdir(parents=True)
    elif folderPath.suffix == "" and not folderPath.exists():
        folderPath.mkdir(parents=True)


def m3u8UrlToMp4(url, output):
    runCommand(f'ffmpeg -loglevel error -i "{url}" -codec copy {output}')


def Mp4ToMp3(input, output):
    """Uses ffmpeg to make mp3 from mp4 and return output path,
    might damage quality as it does not use 'copy' filter to ensure compatability"""
    tempOut = generateWorkbenchPath(output)
    runCommand(f"ffmpeg -loglevel error -i \"{input}\" -vn \"{tempOut}\"")
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
        Mp4ToMp3(inputFile, outputFolder / f"{inputFile.stem}.mp3")

def getLength(path):
    p = subprocess.run(f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{str(path)}\"", capture_output=True, shell=True, universal_newlines=True)
    return float(p.stdout.replace("\n", ""))

def cutAudio(input, outputFolder, lengths):
    input = Path(input)
    outputFolder = Path(outputFolder)
    # totalLength = AudioSegment.from_file(input).duration_seconds
    totalLength = getLength(input)
    numLengths = math.ceil(totalLength/lengths)
    print(f"Total length is: {totalLength}")
    print(f"Will create {totalLength/lengths} clips")

    lengths = [(i*lengths, (i+1)*lengths if (i+1)*lengths < totalLength else totalLength) for i in range(0, numLengths)]

    makeSureFolderExists(outputFolder)
    # TODO This generates a corrupted (empty?) audio file at the end fix it! However, it is not needed for local processing so I don't use it anymore
    
    for index,length in enumerate(lengths):
        outputPath = outputFolder / f"{input.stem}-{index}{input.suffix}"
        runCommand(
            f"ffmpeg -loglevel error -ss {length[0]} -to {length[1]} -i \"{input}\" \"{outputPath}\" -acodec copy")

    return outputFolder


def trimLeadingSilence(videoFile, outputFile):
    """Function that trims the leading silence from the videofile, 
    it requires a separate ripped mp3 file to detect the silence"""

    # Uses pydub.AudioSegment to find the time of the silence
    initialAudio = Mp4ToMp3(videoFile, generateWorkbenchPath("initialaudio.mp3"))
    audio = AudioSegment.from_mp3(initialAudio)
    silenceEnd = detect_leading_silence(audio)
    makeSureFolderExists(outputFile)
    tempOut = generateWorkbenchPath(outputFile)
    runCommand(
        f"ffmpeg -loglevel error -i \"{videoFile}\" -ss \"{silenceEnd}ms\" -vcodec copy -acodec copy \"{tempOut}\"")
    shutil.move(tempOut, outputFile)
    return outputFile


def copyFilesToGoogleColab(inputFolder, outputFolder, filePattern="**/*.mp3", fileFilter=lambda fileList: fileList):
    inputFolder = Path(inputFolder)
    outputFolder = Path(outputFolder)
    logger.info(f"Copying files from {inputFolder} to {outputFolder} for processing in Google Colab")

    inputFiles = fileFilter([Path(file) for file in glob.glob(
        f"{inputFolder}/{filePattern}", recursive=True)])
    
    for inputFile in inputFiles:
        outputPath = outputFolder / inputFile.relative_to(inputFolder)
        makeSureFolderExists(outputPath)
        logger.info(f"Copying {inputFile}->{outputPath}")
        shutil.copy(inputFile, outputPath)
