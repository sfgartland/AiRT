import datetime
import time
import os
# import typer

from .summarizer import generatePicklePath, getSummaryInOutPaths, saveResponseToMd, saveObjectToPkl, summarizeLectureTranscript

# from .PDFContentExtractor import pdf2md

from .price import gpt_4_1106_preview, whisper, Price
from .fileHandler import ToMp3, getLength, makeSureFolderExists, runCommand
from .fileFetcher import getFromYoutube
from .transcriber import createWhisperModel, batchTranscribeMp3sLocally, batchProcessMediaFiles, generateTranscriptWithApi, getTranscriptInOutPaths, writeToFile
from .textStructurer import checkSimilarityToOriginal, sectionListToMarkdown, getStructureFromGPT
from loguru import logger

from pathlib import Path
import glob


from rich.prompt import Confirm
from rich import print
from rich.live import Live
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

import pickle

logger.add("logs/transcriber-{time}.log")


def genPriceRow(entry, hideInputPrice, hideOutputPrice):
    inputFile = entry[0][0]
    row = [inputFile.as_posix()]
    if entry[1]:
        cost = entry[1]
        row.append(f"[b]{Price.readablePrice(cost.totalPrice)}[/b]")
        if not hideInputPrice:
            row.append(Price.readablePrice(cost.inputPrice))
        if not hideOutputPrice:
            row.append(Price.readablePrice(cost.outputPrice))
    else:
        row.append("...")
        if not hideInputPrice:
            row.append("...")
        if not hideOutputPrice:
            row.append("...")

    return row

def genPriceTable(entries, ignoredEntries=[], hideInputPrice=False, hideOutputPrice=False) -> Table:
    totalLength = len(entries)
    totalPrice = Price.sumPrices([entry[1] for entry in entries if entry[1]])

    progress = Progress()
    task = progress.add_task("Estimating costs...", total=totalLength)
    progress.update(task, completed=len(entries))

    priceTable = Table(show_footer=True)
    # priceTable.add_column(None, len(entries))
    priceTable.add_column(f"File (count: {totalLength})", progress)
    priceTable.add_column("Total Price", "[green]"+Price.readablePrice(totalPrice.totalPrice))
    if not hideInputPrice:
        priceTable.add_column("Input Price", Price.readablePrice(totalPrice.inputPrice))
    if not hideOutputPrice:
        priceTable.add_column("Output Price", Price.readablePrice(totalPrice.outputPrice))

    for entry in entries:
        row = genPriceRow(entry, hideInputPrice, hideOutputPrice)
        priceTable.add_row(*row)

    # if len(ignoredEntries) > 0:
    #     priceTable.add_section()
    #     for entry in ignoredEntries:
    #         row = genPriceRow(entry, hideInputPrice, hideOutputPrice)
    #         priceTable.add_row(*row)

    return priceTable


def filter_manyVersionsInFolder(fileList):
    """Filters through a list of Path objects and returns only the last file in the same folder"""
    def getFilesInSameFolder(current): return [
        file for file in fileList if current.parent == file.parent]

    return [file for file in fileList if file.samefile(getFilesInSameFolder(file)[-1])]


def batchTranscribeWithAPI(inputFolder, outputFolder, fileFilter=lambda x: x):
    filePairs = getTranscriptInOutPaths(
        inputFolder, outputFolder, "api", fileFilter)
    # filePairs = [filePair for filePair in filePairs if not filePair[1].is_file()] # Get only the ones that aren't processed

    priceEntries = [[pair, None] for pair in filePairs]
    priceTable = lambda: genPriceTable(priceEntries, hideOutputPrice=True, hideInputPrice=True)
    with Live(priceTable(), refresh_per_second=4) as live:
        
        for index,priceEntry in enumerate(priceEntries):
            inputFile = priceEntry[0][0]
            costEstimate = whisper().calcPrice(getLength(inputFile)/60)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask(f"Accept the cost and proceed?"):
        return

    with Progress() as progress:
        trans_task = progress.add_task(
            "Transcribing audio files...", total=len(filePairs))
        for inputFile, outputFile in filePairs:
            # Uses the last generated mp3
            logger.info(f"Transcribing with API with file \"{inputFile}\"")
            try:
                start = time.time()
                transcript = generateTranscriptWithApi(inputFile)
                end = time.time()
                logger.info(
                    f"Transcription time: {datetime.timedelta(seconds=(end-start))}")
                writeToFile(transcript, outputFile)
            except Exception as err:
                logger.info(
                    f"Encountered error while transcribing and saving '{outputFile}'")
                logger.error(err)
            progress.update(trans_task, advance=1)


def batchSummarizeLectureTranscripts(inputFolder, outputFolder, pattern="**/*.txt"):
    filePairs = getSummaryInOutPaths(
        inputFolder, outputFolder, pattern=pattern)
    # Get only the ones that aren't processed
    filePairs = [
        filePair for filePair in filePairs if not filePair[1].is_file()]

    with Live(genPriceTable([], len(filePairs)), refresh_per_second=4) as live:
        prices = []
        for inputFile, outputFile in filePairs:
            with open(inputFile, "r") as f:
                cost = gpt_4_1106_preview().calcPrice(len(f.read()), 3600)
                prices.append((inputFile, cost))
            live.update(genPriceTable(prices, len(filePairs)))



    if not Confirm.ask(f"Accept the cost and proceed?"):
        return

    with Progress() as progress:
        summarize_task = progress.add_task(
            "Summarizing...", total=len(filePairs))

        estimatedEndPrice = Price(0,0)
        for inputFile, outputFile in filePairs:
            # TODO add so that the full response object is saved to a pickle file, makes it easier to revisit it later on
            response = summarizeLectureTranscript(inputFile)
            estimatedEndPrice += gpt_4_1106_preview().calcPriceFromResponse(response)
            content = response.choices[0].message.content
            saveResponseToMd(content, outputFile)
            saveObjectToPkl(response, generatePicklePath(outputFile))
            progress.update(summarize_task, advance=1)

    print(f"Finished, estimated spending is: {estimatedEndPrice}")


def batchStructureTranscripts(inputFolder, outputFolder, pattern="**/*.txt"):
    filePairs = getSummaryInOutPaths(inputFolder, outputFolder, pattern=pattern, prefix="structured_")
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if not filePair in ignoreFilePairs]

    priceEntries = [[pair, None] for pair in filePairs]
    ignoredEntries = [[pair, None] for pair in ignoreFilePairs]
    priceTable = lambda: genPriceTable(priceEntries, ignoredEntries=ignoredEntries)
    with Live(priceTable(), refresh_per_second=4) as live:
        for index,priceEntry in enumerate(priceEntries):
            inputPath = priceEntry[0][0]
            with open(inputPath, "r", encoding="utf-8") as f:
                length = len(f.read())
                costEstimate = gpt_4_1106_preview().calcPrice(length, length/6)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask(f"Accept the cost and proceed?"):
        return

    with Progress() as progress:
        structuring_task = progress.add_task(
            "Structuring...", total=len(filePairs))
        estimatedEndPrice = Price(0,0)
        for inputPath, outputPath in filePairs:
            sections, responses = getStructureFromGPT(inputPath)

            estimatedEndPrice += Price.sumPrices([gpt_4_1106_preview().calcPriceFromResponse(response) for response in responses])

            makeSureFolderExists(outputPath)
            with open(outputPath, "w", encoding="utf-8") as outputFile:
                outputFile.write(sectionListToMarkdown(sections))
            saveObjectToPkl(responses, outputPath.parent /
                            f"text-struct-responses_{outputPath.stem}.pkl")
            progress.update(structuring_task, advance=1)

    print(f"Finished, estimated spending is: {estimatedEndPrice}")

if __name__ == "__main__":
    # getFromYoutube("https://www.youtube.com/watch?v=3tvfq8ehHOk&embeds_referring_euri=https%3A%2F%2Fphilosophy.columbia.edu%2F&source_ve_path=OTY3MTQ&feature=emb_imp_woyt", "testout")
    # copyFilesToGoogleColab("output/PHILOS133", "G:/Min disk/google-Collab-testing-folder/PHILOS133", fileFilter=filter)
    # runCommand("nougat test.pdf -o output_directory -m 0.1.0-base", output_stdout=True)

    # batchProcessMediaFiles("output/PHILOS25A", "output/PHILOS25A", ADD_FILTER)
    # batchTranscribeWithAPI("output/PHILOS25A", "output/PHILOS25A")
    # batchSummarizeLectureTranscripts("output/PHILOS25A", "output/PHILOS25A", "**/*_api.txt")

    # batchTranscribeWithAPI("output/Opptak FIL2505", "output/Opptak FIL2505")
    # batchSummarizeLectureTranscripts("output/Opptak FIL2505", "inputs/Opptak FIL2505", "**/*_api.txt")

    batchStructureTranscripts("testing", "testing")
    print(checkSimilarityToOriginal("./testing/trans.txt", "./testing/outputtest.md"))

    # TODO move to function, does batch conversion of audio files
    # files = glob.glob("inputs/Opptak FIL2505/*.m4a")
    # print(f"Converting {len(files)} audio files to mp3")
    # with Progress() as progress:
    #     conversion_task = progress.add_task("Converting audio files to mp3...", total=len(files))
    #     for file in files:
    #         ToMp3(file)
    #         progress.update(conversion_task, advance=1)
