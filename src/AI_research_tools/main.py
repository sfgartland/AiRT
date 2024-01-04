import datetime
import time
from .UI import genPriceTable
import typer
from typing import List

from .PDFContentExtractor import pdf2md

from .summarizer import (
    generatePicklePath,
    getSummaryInOutPaths,
    saveResponseToMd,
    saveObjectToPkl,
    summarizeLectureTranscript,
)


from .price import gpt_4_1106_preview, whisper, Price
from .fileHandler import base_getInOutPaths, getLength, makeSureFolderExists, runCommand
from .transcriber import generateTranscriptWithApi, getTranscriptInOutPaths, writeToFile
from .textStructurer import sectionListToMarkdown, getStructureFromGPT
from loguru import logger

from pathlib import Path


from rich.prompt import Confirm
from rich.live import Live
from rich.progress import Progress


logger.add("logs/transcriber-{time}.log")

app = typer.Typer()


def filter_manyVersionsInFolder(fileList):
    """Filters through a list of Path objects and returns only the last file in the same folder"""

    def getFilesInSameFolder(current):
        return [file for file in fileList if current.parent == file.parent]

    return [file for file in fileList if file.samefile(getFilesInSameFolder(file)[-1])]


# TODO add fileFilter choice in typer function
@app.command()
def transcribeWithAPI(inputpath: List[Path], outputfolder: Path = None):
    fileFilter = lambda x: x  # TODO Make accessible to CLI
    filePairs = getTranscriptInOutPaths(inputpath, outputfolder, "api", fileFilter)
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    priceEntries = [[pair, None] for pair in filePairs]
    priceTable = lambda: genPriceTable(
        priceEntries, hideOutputPrice=True, hideInputPrice=True
    )
    with Live(priceTable(), refresh_per_second=4) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputFile = priceEntry[0][0]
            costEstimate = whisper().calcPrice(getLength(inputFile) / 60)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    with Progress() as progress:
        trans_task = progress.add_task(
            "Transcribing audio files...", total=len(filePairs)
        )
        for inputFile, outputFile in filePairs:
            # Uses the last generated mp3
            logger.info(f'Transcribing with API with file "{inputFile}"')
            try:
                start = time.time()
                transcript = generateTranscriptWithApi(inputFile)
                end = time.time()
                logger.info(
                    f"Transcription time: {datetime.timedelta(seconds=(end-start))}"
                )
                writeToFile(transcript, outputFile)
            except Exception as err:
                logger.error(
                    f"Encountered error while transcribing and saving '{outputFile}'"
                )
                logger.error(err)
            progress.update(trans_task, advance=1)


@app.command()
def summarizeTranscripts(inputpath: List[Path], outputfolder: Path = None):
    filePairs = getSummaryInOutPaths(
        inputpath, outputfolder, pattern="**/*.txt", prefix="summarized_"
    )
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    priceEntries = [[pair, None] for pair in filePairs]
    ignoredEntries = [[pair, None] for pair in ignoreFilePairs]
    priceTable = lambda: genPriceTable(priceEntries, ignoredEntries=ignoredEntries)
    with Live(priceTable(), refresh_per_second=4) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputpath = priceEntry[0][0]
            with open(inputpath, "r", encoding="utf-8") as f:
                length = len(f.read())
                costEstimate = gpt_4_1106_preview().calcPrice(length, 3600)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    with Progress() as progress:
        summarize_task = progress.add_task("Summarizing...", total=len(filePairs))

        estimatedEndPrice = Price(0, 0)
        for inputFile, outputFile in filePairs:
            # TODO add so that the full response object is saved to a pickle file, makes it easier to revisit it later on
            response = summarizeLectureTranscript(inputFile)
            estimatedEndPrice += gpt_4_1106_preview().calcPriceFromResponse(response)
            content = response.choices[0].message.content
            saveResponseToMd(content, outputFile)
            saveObjectToPkl(response, generatePicklePath(outputFile))
            progress.update(summarize_task, advance=1)

    print(f"Finished, estimated spending is: {estimatedEndPrice}")


@app.command()
def structureTranscripts(inputpath: List[Path], outputfolder: Path = None):
    filePairs = getSummaryInOutPaths(
        inputpath, outputfolder, pattern="**/*.txt", prefix="structured_"
    )
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    # TODO Move all of these tabel Live view functions into a common function for all CLI commands
    priceEntries = [[pair, None] for pair in filePairs]
    ignoredEntries = [[pair, None] for pair in ignoreFilePairs]
    priceTable = lambda: genPriceTable(priceEntries, ignoredEntries=ignoredEntries)
    with Live(priceTable(), refresh_per_second=4) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputpath = priceEntry[0][0]
            with open(inputpath, "r", encoding="utf-8") as f:
                length = len(f.read())
                costEstimate = gpt_4_1106_preview().calcPrice(length, length / 6)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    with Progress() as progress:
        structuring_task = progress.add_task("Structuring...", total=len(filePairs))

        def progressCallback(x, y):
            if x == 0:
                progress.start_task(currentTask)
            progress.update(currentTask, completed=x, total=y)

        estimatedEndPrice = Price(0, 0)
        for inputpath, outputPath in filePairs:
            currentTask = progress.add_task("Current...", start=False)
            sections, responses = getStructureFromGPT(
                inputpath, progressCallback=progressCallback
            )

            estimatedEndPrice += Price.sumPrices(
                [
                    gpt_4_1106_preview().calcPriceFromResponse(response)
                    for response in responses
                ]
            )

            makeSureFolderExists(outputPath)
            with open(outputPath, "w", encoding="utf-8") as outputFile:
                outputFile.write(sectionListToMarkdown(sections))
            saveObjectToPkl(
                responses,
                outputPath.parent / f"text-struct-responses_{outputPath.stem}.pkl",
            )
            progress.update(structuring_task, advance=1)

    print(f"Finished, estimated spending is: {estimatedEndPrice}")

@app.command()
def mdToPdf(inputpath: List[Path], outputfolder: Path = None):
    filePairs = base_getInOutPaths(inputpath, outputfolder, "**/*.md", "", "", "pdf")
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    with Progress() as progress:
        pandoc_task = progress.add_task("Converting to pdfs....", total=len(filePairs))
        for inputFile,outputFile in filePairs:
            makeSureFolderExists(outputFile)
            runCommand(f"pandoc \"{inputFile}\" -o \"{outputFile}\"")
            progress.update(pandoc_task, advance=1)

@app.command()
def development():
    print("Dev")

@app.command()
def pdfToMd(inputfile: Path, outputfile: Path):
    pdf2md(inputfile, outputfile)


# if __name__ == "__main__":
# getFromYoutube("https://www.youtube.com/watch?v=3tvfq8ehHOk&embeds_referring_euri=https%3A%2F%2Fphilosophy.columbia.edu%2F&source_ve_path=OTY3MTQ&feature=emb_imp_woyt", "testout")
# copyFilesToGoogleColab("output/PHILOS133", "G:/Min disk/google-Collab-testing-folder/PHILOS133", fileFilter=filter)
# runCommand("nougat test.pdf -o output_directory -m 0.1.0-base", output_stdout=True)

# batchProcessMediaFiles("output/PHILOS25A", "output/PHILOS25A", ADD_FILTER)
# batchTranscribeWithAPI("output/PHILOS25A", "output/PHILOS25A")
# batchSummarizeLectureTranscripts("output/PHILOS25A", "output/PHILOS25A", "**/*_api.txt")

# batchTranscribeWithAPI("output/Opptak FIL2505", "output/Opptak FIL2505")
# batchSummarizeLectureTranscripts("output/Opptak FIL2505", "inputs/Opptak FIL2505", "**/*_api.txt")

# batchStructureTranscripts("output/Opptak FIL2505", "output/Opptak FIL2505")
# print(checkSimilarityToOriginal("./testing/trans.txt", "./testing/outputtest.md"))

# TODO move to function, does batch conversion of audio files
# files = glob.glob("inputs/Opptak FIL2505/*.m4a")
# print(f"Converting {len(files)} audio files to mp3")
# with Progress() as progress:
#     conversion_task = progress.add_task("Converting audio files to mp3...", total=len(files))
#     for file in files:
#         ToMp3(file)
#         progress.update(conversion_task, advance=1)
