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


def runCommand(command):
    p = subprocess.run(command, capture_output=True, shell=True, universal_newlines=True)
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
    runCommand(f'ffmpeg -i "{url}" -codec copy {output}')


def Mp4ToMp3(input, output):
    """Uses ffmpeg to make mp3 from mp4 and return output path,
    might damage quality as it does not use 'copy' filter to ensure compatability"""
    tempOut = generateWorkbenchPath(output)
    runCommand(f"ffmpeg -i \"{input}\" -vn \"{tempOut}\"")
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


def cutAudio(input, outputFolder, lengths):
    input = Path(input)
    outputFolder = Path(outputFolder)
    outputFolder = outputFolder.parent / \
        f"{outputFolder.stem}-lengths-{lengths}"
    # totalLength = AudioSegment.from_file(input).duration_seconds
    totalLength = 5039
    print(f"Total length is: {totalLength}")
    print(f"Will create {totalLength/lengths} clips")
    traversedLength = 0
    index = 1
    spillover = totalLength % lengths

    makeSureFolderExists(outputFolder)
    # TODO This generates a corrupted (empty?) audio file at the end fix it! However, it is not needed for local processing so I don't use it anymore
    while traversedLength < totalLength+spillover:
        outputPath = outputFolder / f"{input.stem}-{index}{input.suffix}"
        runCommand(
            f"ffmpeg -ss {traversedLength} -to {traversedLength+lengths} -i \"{input}\" \"{outputPath}\" -acodec copy")
        traversedLength = traversedLength+lengths
        index = index+1


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
        f"ffmpeg -i \"{videoFile}\" -ss \"{silenceEnd}ms\" -vcodec copy -acodec copy \"{tempOut}\"")
    shutil.move(tempOut, outputFile)
    return outputFile