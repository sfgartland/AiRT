import datetime
import time
import typer

from .price import whisper
from .fileHandler import getLength, runCommand
from .fileFetcher import getFromYoutube
from .transcriber import createWhisperModel, batchTranscribeMp3sLocally, batchProcessMediaFiles, generateTranscriptWithApi, getTranscriptInOutPaths, writeToFile
from loguru import logger

from pathlib import Path
import glob

from rich.progress import Progress

from rich.prompt import Confirm
from rich import print


logger.add("logs/transcriber-{time}.log")


def filter_manyVersionsInFolder(fileList):
    """Filters through a list of Path objects and returns only the last file in the same folder"""
    getFilesInSameFolder = lambda current: [file for file in fileList if current.parent == file.parent]
    
    return [file for file in fileList if file.samefile(getFilesInSameFolder(file)[-1])]

def batchTranscribeWithAPI(inputFolder, outputFolder):
    filePairs = getTranscriptInOutPaths(inputFolder, outputFolder, "api", filter_manyVersionsInFolder)
    
    with Progress() as progress:
        length_task = progress.add_task("Calculating price of transcribing audio files...", total=len(filePairs))
        
        lengths = []
        for filePair in filePairs:
            lengths.append(getLength(filePair[0])/60)
            progress.update(length_task, advance=1)
        costs = []
        for length in lengths:
            costs.append(whisper().calcPrice(length).totalPrice) # So fast that I don't need a progressbar

    

    costEstimate = sum(costs)
    print(f"Estimated cost is: [b]${round(costEstimate, 2)}[/b]")
    if not Confirm.ask(f"Accept the cost and proceed?"):
        return

    for inputFile,outputFile in filePairs:
        if not outputFile.is_file():
            logger.info(f"Transcribing with API with file \"{inputFile}\"") # Uses the last generated mp3
            try:
                start = time.time()
                transcript = generateTranscriptWithApi(inputFile)
                end = time.time()
                logger.info(f"Transcription time: {datetime.timedelta(seconds=(end-start))}")
                writeToFile(transcript, outputFile)
            except Exception as err:
                logger.info(f"Encountered error while transcribing and saving '{outputFile}'")
                logger.error(err)


if __name__ == "__main__":
    # PDFToMd("test.pdf", "test.md")
    # getFromYoutube("https://www.youtube.com/watch?v=3tvfq8ehHOk&embeds_referring_euri=https%3A%2F%2Fphilosophy.columbia.edu%2F&source_ve_path=OTY3MTQ&feature=emb_imp_woyt", "testout")
    # copyFilesToGoogleColab("output/PHILOS133", "G:/Min disk/google-Collab-testing-folder/PHILOS133", fileFilter=filter)
    # runCommand("nougat test.pdf -o output_directory -m 0.1.0-base", output_stdout=True)
    # print(generateTranscriptWithApi("testing-clip-kant.mp3"))
    # batchProcessMediaFiles("output/PHILOS25A", "output/PHILOS25A")
    batchTranscribeWithAPI("output/PHILOS25A", "output/PHILOS25A")