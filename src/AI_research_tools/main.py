import typer
from typing_extensions import Annotated

from typing import List, Tuple, TypeAlias
from enum import Enum

from loguru import logger

from pathlib import Path

from rich.prompt import Confirm
from rich.live import Live
from rich.progress import Progress
from rich.console import Console


console = Console()
logger.remove()


def _log_formatter(record: dict) -> str:
    """Log message formatter"""
    color_map = {
        "TRACE": "dim blue",
        "DEBUG": "cyan",
        "INFO": "bold",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
    }
    lvl_color = color_map.get(record["level"].name, "cyan")
    return (
        "[not bold green]{time:YYYY/MM/DD HH:mm:ss}[/not bold green] | {level.icon}"
        + f"  - [{lvl_color}]{{message}}[/{lvl_color}]"
    )


logger.add(
    console.print,
    level="TRACE",
    format=_log_formatter,
    colorize=True,
)
logger.add("logs/transcriber-{time}.log")

app = typer.Typer()


def filter_manyVersionsInFolder(fileList):
    """Filters through a list of Path objects and returns only the last file in the same folder"""

    def getFilesInSameFolder(current):
        return [
            filePair[0] for filePair in fileList if current.parent == filePair[0].parent
        ]

    return [
        filePair
        for filePair in fileList
        if filePair[0].samefile(getFilesInSameFolder(filePair[0])[-1])
    ]


def filter_noFilter(fileList):
    return fileList


class FileFilters(str, Enum):
    none = "no_filter"
    manyVersionsInFolder = "ManyVersionsInFolder"

    @classmethod
    def getFilter(filter):
        map = {
            FileFilters.none: filter_noFilter,
            FileFilters.manyVersionsInFolder: filter_manyVersionsInFolder,
        }
        return map[filter]

def template_enum_completer(enum_class, incomplete: str):
    completion = []
    for name in [filter.value for filter in enum_class]:
        if name.startswith(incomplete):
            completion.append(name)
    return completion


class InputTypes(Enum):
    inputpaths: TypeAlias = Annotated[
        List[Path],
        typer.Argument(
            help="File, directory or list of files to process, you can use glob patterns to select multiple files.",
        ),
    ]
    inputpath_single: TypeAlias = Annotated[
        Path,
        typer.Argument(
            help="File to process",
        ),
    ]

    outputfolder: TypeAlias = Annotated[
        Path,
        typer.Option(
            help="Folder to output to, will match the structure of the files relative to the lowest common folder of the input files."
        ),
    ]
    outputpath_single: TypeAlias = Annotated[
        Path,
        typer.Option(help="Output file"),
    ]

    filefilter: TypeAlias = Annotated[
        FileFilters,
        typer.Option(
            help="Select a filter to apply to the list of input files",
            autocompletion=lambda incomplete: template_enum_completer(FileFilters, incomplete),
        ),
    ]

    pdf: TypeAlias = Annotated[bool, typer.Option(help="Set for converting markdown file to PDF once done")]


def templateCommand(
    processing_method: callable,
    filePairs: List[Tuple[Path, Path]],
    priceEstimateMethod: callable
):
    from .UI import genPriceTable, genProgressTable
    from .price import Price

    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    # TODO Move all of these tabel Live view functions into a common function for all CLI commands
    priceEntries = [[pair, None] for pair in filePairs]
    ignoredEntries = [[pair, None] for pair in ignoreFilePairs]
    priceTable = lambda: genPriceTable(priceEntries, ignoredEntries=ignoredEntries)
    with Live(priceTable(), refresh_per_second=4, console=console) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputpath = priceEntry[0][0]
            costEstimate = priceEstimateMethod(inputpath)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    entries = [[str(pair[0]), Progress(console=console)] for pair in filePairs]
    progressTable = lambda completed: genProgressTable(entries, completed)
    outputs = []
    with Live(progressTable(0), refresh_per_second=4, console=console) as live:
        for index, entry in enumerate(entries):
            _, progress = entry
            inputFile, outputFile = filePairs[index]
            processing_method(progress, inputFile, outputFile)
            live.update(progressTable(index + 1))




@app.command(rich_help_panel="Youtube")
def downloadYoutube(outputfolder: InputTypes.outputfolder.value, urls: Annotated[List[str], typer.Argument(help="Urls to be downloaded")]):
    """Download one or more videos from youtube"""
    from .fileFetcher import getFromYoutube
    from .UI import genProgressTable

    if outputfolder.suffix != "":
        Exception(
            "Can only write Youtube files to folder, filename will be autogenerated"
        )

    entries = [[url, Progress(console=console)] for url in urls]
    progressTable = lambda completed: genProgressTable(entries, completed)
    with Live(progressTable(0), refresh_per_second=4, console=console) as live:
        for index, entry in enumerate(entries):
            url, progress = entry
            output = getFromYoutube(url, outputfolder, progressObject=progress)
            entries[index][1] = output
            live.update(progressTable(index + 1))


@app.command(rich_help_panel="Youtube")
def downloadYoutubePlaylist(outputfolder: Annotated[Path, typer.Argument(help="Folder to place downloaded files")], url: Annotated[str, typer.Argument(help="Url to playlist")]):
    """Download full Youtube playlist"""
    from pytube import Playlist

    urls = Playlist(url)
    downloadYoutube(outputfolder, urls)

class ConcatMethods(str, Enum):
    moviepy = "moviepy"
    ffmpeg = "ffmpeg"

@app.command(rich_help_panel="Media file manipulation")
def concatmp4s(
    outputpath: InputTypes.outputpath_single.value,
    inputpaths: InputTypes.inputpaths.value,
    recode: Annotated[bool, typer.Option(help="Set if you want ffmpeg to recode the video, might solve issues, but takes much longer.")] = False,
    method: Annotated[str, typer.Option(help="Method to process concat with.", autocompletion=lambda incomplete: template_enum_completer(ConcatMethods, incomplete))]="moviepy",
):
    """Concat mp4 videos into single video using either ffmpeg or moviepy-package"""
    from .fileHandler import (
        concatMp4s_ffmpeg,
        concatMp4s_moviepy,
    )
    import asyncio

    # TODO check if identity check works or if I should switch back to == for 'method' check
    if method is ConcatMethods.ffmpeg:
        with Progress(console=console) as p:
            concat_task = p.add_task("Concating the videos...", total=None)

            def initProgress(total):
                p.update(concat_task, total=total)

            def updateProg(completed):
                if completed is not None:
                    p.update(concat_task, completed=completed)

            asyncio.run(
                concatMp4s_ffmpeg(
                    inputpaths,
                    outputpath,
                    progressCallback=updateProg,
                    initProgress=initProgress,
                    recode=recode,
                )
            )
    elif method is ConcatMethods.moviepy:
        concatMp4s_moviepy(inputpaths, outputpath)


# TODO add fileFilter choice in typer function
@app.command(rich_help_panel="AI commands")
def transcribeWithAPI(
    inputpath: InputTypes.inputpaths.value,
    outputfolder: InputTypes.outputfolder.value = None,
    filefilter: InputTypes.filefilter.value= FileFilters.none,
):
    """Transcribe files with OpenAI whisper API"""
    import datetime
    import time

    from .UI import genPriceTable, genProgressTable
    from .price import whisper
    from .transcriber import (
        generateTranscriptWithApi,
        getTranscriptInOutPaths,
        writeToFile,
    )
    from .fileHandler import getLength_old

    filefilter = FileFilters.getFilter(filefilter)

    def getPairs(inputPaths, outputFolder):
        filePairs = getTranscriptInOutPaths(inputPaths, outputFolder, "api", filefilter)
        # Get only the ones that aren't processed
        ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
        filePairs = [
            filePair for filePair in filePairs if filePair not in ignoreFilePairs
        ]
        return filePairs

    filePairs = getPairs(inputpath, outputfolder)
    if len(list(filter(lambda x: x[0].suffix != ".mp3", filePairs))) > 0:
        logger.info(
            "Detected that some of the input files were not mp3's. Converting them first."
        )
        outputs = mp4tomp3([pair[0] for pair in filePairs])
        print(outputs)
        mp3files = [
            *outputs,
            *[pair[0] for pair in filePairs if pair[0].suffix == ".mp3"],
        ]  # TODO make this code a bit better, now it's quite janky
        filePairs = getPairs(mp3files, outputfolder)

    priceEntries = [[pair, None] for pair in filePairs]
    priceTable = lambda: genPriceTable(
        priceEntries, hideOutputPrice=True, hideInputPrice=True
    )
    with Live(priceTable(), refresh_per_second=4, console=console) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputFile = priceEntry[0][0]
            costEstimate = whisper().calcPrice(getLength_old(inputFile) / 60)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    entries = [[str(pair[0]), Progress(console=console)] for pair in filePairs]
    progressTable = lambda completed: genProgressTable(entries, completed)

    with Live(progressTable(0), refresh_per_second=4, console=console) as live:
        for index, entry in enumerate(entries):
            _, progress = entry
            inputFile, outputFile = filePairs[index]
            logger.info(f'Transcribing with API with file "{inputFile}"')

            try:
                start = time.time()
                transcript = generateTranscriptWithApi(inputFile, progress=progress)
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
            live.update(progressTable(index + 1))


@app.command(rich_help_panel="Media file manipulation")
def mp4tomp3(inputpaths: InputTypes.inputpaths.value, outputfolder: InputTypes.outputfolder.value = None):
    """Convert mp4 to mp3"""
    from .fileHandler import base_getInOutPaths, ToMp3
    from .UI import genProgressTable

    filePairs = base_getInOutPaths(inputpaths, outputfolder, "**/*.mp4", "", "", "mp3")
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    entries = [[str(pair[0]), Progress(console=console)] for pair in filePairs]
    progressTable = lambda completed: genProgressTable(entries, completed)
    outputs = []
    with Live(progressTable(0), refresh_per_second=4, console=console) as live:
        for index, entry in enumerate(entries):
            _, progress = entry
            inputFile, outputFile = filePairs[index]
            logger.info("Converting mp4's to mp3's")

            output = ToMp3(inputFile, outputFile, progress=progress)
            outputs.append(output)
            live.update(progressTable(index + 1))

    return outputs


@app.command(rich_help_panel="AI commands")
def summarizeTranscripts(
    inputpaths: InputTypes.inputpaths.value, outputfolder: InputTypes.outputfolder.value = None, pdf: InputTypes.pdf.value = False
):
    """Sumarize text transcript using GPT-4 API"""
    from .UI import genPriceTable
    from .summarizer import (
        generatePicklePath,
        getSummaryInOutPaths,
        saveResponseToMd,
        saveObjectToPkl,
        summarizeLectureTranscript,
    )
    from .price import gpt_4_1106_preview, Price

    filePairs = getSummaryInOutPaths(
        inputpaths, outputfolder, pattern="**/*.txt", prefix="summarized_"
    )
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    priceEntries = [[pair, None] for pair in filePairs]
    ignoredEntries = [[pair, None] for pair in ignoreFilePairs]
    priceTable = lambda: genPriceTable(priceEntries, ignoredEntries=ignoredEntries)
    with Live(priceTable(), refresh_per_second=4, console=console) as live:
        for index, priceEntry in enumerate(priceEntries):
            inputpaths = priceEntry[0][0]
            with open(inputpaths, "r", encoding="utf-8") as f:
                length = len(f.read())
                costEstimate = gpt_4_1106_preview().calcPrice(length, 3600)
            priceEntries[index][1] = costEstimate
            live.update(priceTable())

    if not Confirm.ask("Accept the cost and proceed?"):
        return

    with Progress(console=console) as progress:
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

    if pdf:
        mdToPdf([pair[1] for pair in filePairs])



@app.command(rich_help_panel="AI commands")
def structureTranscripts(
    inputpath: InputTypes.inputpaths.value,
    outputfolder: InputTypes.outputfolder.value = None,
    pdf: InputTypes.pdf.value = False,
):
    """Note: Experimental! Structures a raw text transcript into paragraphs with headings using GPT-4 API"""
    from .price import gpt_4_1106_preview, Price
    from .summarizer import getSummaryInOutPaths, saveObjectToPkl
    from .fileHandler import makeSureFolderExists
    from .textStructurer import sectionListToMarkdown, getStructureFromGPT

    def processing(progress: Progress, inputPath: Path, outputPath: Path):
        sections, responses = getStructureFromGPT(inputPath, progress=progress)

        # TODO fix this estimated price stuff
        estimatedEndPrice += Price.sumPrices(
            [
                gpt_4_1106_preview().calcPriceFromResponse(response)
                for response in responses
            ]
        )

        makeSureFolderExists(outputPath)
        with open(outputPath, "w", encoding="utf-8") as outputPath:
            outputPath.write(sectionListToMarkdown(sections))
        saveObjectToPkl(
            responses,
            outputPath.parent / f"text-struct-responses_{outputPath.stem}.pkl",
        )

    def priceEstimateMethod(input: Path):
        with open(input, "r", encoding="utf-8") as f:
            length = len(f.read())
            costEstimate = gpt_4_1106_preview.calcPrice(length, length / 6)
            return costEstimate
        

    filePairs = getSummaryInOutPaths(
        inputpath, outputfolder, pattern="**/*.txt", prefix="structured_"
    )

    estimatedEndPrice = Price(0, 0)
    logger.info("Structuring transcripts")

    templateCommand(processing, filePairs, priceEstimateMethod)

    print(f"Finished, estimated spending is: {estimatedEndPrice}")

    if pdf:
        mdToPdf([pair[1] for pair in filePairs])


@app.command(rich_help_panel="Media file manipulation")
def trimsilence(
    inputpaths: InputTypes.inputpaths.value, outputfolder: InputTypes.outputfolder.value = None, only_leading: Annotated[bool, typer.Option(help="Set to only trim the silence at start of clip")] = False
):
    """Trim the silence from mp4 video, AI transcription can often get confused if there are to much silence in a clip and start halucinating"""
    from .fileHandler import base_getInOutPaths, trimSilence
    from .UI import genProgressTable

    filePairs = base_getInOutPaths(
        inputpaths,
        outputfolder,
        "**/*.mp4",
        "trimmed_silence_" if not only_leading else "trimmed_leading_silence_",
        "",
        "mp4",
    )
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    entries = [[str(pair[0]), Progress(console=console)] for pair in filePairs]
    progressTable = lambda completed: genProgressTable(entries, completed)
    outputs = []
    with Live(progressTable(0), refresh_per_second=4, console=console) as live:
        for index, entry in enumerate(entries):
            _, progress = entry
            inputFile, outputFile = filePairs[index]
            logger.info("Structuring transcripts")

            trimSilence(
                inputFile, outputFile, only_leading=only_leading, progress=progress
            )

            live.update(progressTable(index + 1))


@app.command(rich_help_panel="Text file manipulation")
def mdToPdf(inputpaths: InputTypes.inputpaths.value, outputfolder: InputTypes.outputfolder.value = None):
    """Convert markdown to pdf using pandoc"""
    from .CommandRunners import runCommand
    from .fileHandler import (
        base_getInOutPaths,
        makeSureFolderExists,
    )

    filePairs = base_getInOutPaths(inputpaths, outputfolder, "**/*.md", "", "", "pdf")
    # Get only the ones that aren't processed
    ignoreFilePairs = [filePair for filePair in filePairs if filePair[1].is_file()]
    filePairs = [filePair for filePair in filePairs if filePair not in ignoreFilePairs]

    with Progress(console=console) as progress:
        pandoc_task = progress.add_task("Converting to pdfs....", total=len(filePairs))
        for inputFile, outputFile in filePairs:
            makeSureFolderExists(outputFile)
            runCommand(f'pandoc "{inputFile}" -o "{outputFile}"')
            progress.update(pandoc_task, advance=1)


@app.command()
def development():
    """Placeholder command for development purposes"""
    print("Dev")


# @app.command()
# def pdfToMd(inputfile: Path, outputfile: Path):
#     pdf2md(inputfile, outputfile)


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
