from loguru import logger
import subprocess
from openai import OpenAI

import time
import datetime

from rich import print

import pickle
import json
import os

import glob
from pathlib import Path


from .fileHandler import makeSureFolderExists


class Section:
    def __init__(self, heading, key):
        self.heading = heading
        self.key = key


def jsonToMd(json, orderedHeadings):
    if isinstance(json, str):
        json = json.loads(json)

    def proc_section(key):
        content = json[key]
        if (isinstance(content, list)):

            content = "\n".join([f"{i+1}. {x}" for i, x in enumerate(content)])
        return f"# {key}\n{content}"    # TODO Update to actually use Section headings and not key as heading

    return "\n\n".join([proc_section(section.key) for section in orderedHeadings])


def summarizeLectureTranscript(transcriptPath):
    transcript = open(transcriptPath, "r", encoding="utf-8").read()

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a college professor explaining to his advanced students."},
            {"role": "user", "content": transcript},
            {"role": "user", "content": "Reply in a json object. "
             + "In the key 'long_summary' return a summary of the previous message in 1000 words or less. Organize the summary into paragraphs"
                + "In the key 'sentences' return a summary of the previous message using the most imporant sentences. Include 20 or fewer sentences."
             + "In the key 'names' return all names mentioned in the previous message. The names might be misspelled, if they are, do not correct them. Names might also not be capitalized."
             + "In the key 'works' return all works such as papers and books mentioned in the previous message."
             + "In the key 'short_summary' return a summary of the previous message in 75 words or less."}
        ]
    )

    return response


def saveResponseToMd(response, outputPath):
    headingOrder = [Section("Short Summary", "short_summary"),
                    Section("Mentioned Names", "names"),
                    Section("Mentioned Works", "works"),
                    Section("Important sentences", "sentences"),
                    Section("Long Summary", "long_summary")]
    md = jsonToMd(json.loads(response), headingOrder)
    makeSureFolderExists(outputPath)
    open(outputPath, "w", encoding="utf-8").write(md)

def generatePicklePath(mdFile):
    return mdFile.parent / f"gptresponse_{mdFile.stem}.pkl"

def saveObjectToPkl(response, outputPath):
    outputPath = Path(outputPath)
    makeSureFolderExists(outputPath)
    if outputPath.is_file():
        os.remove(outputPath)
    pickle.dump(response, open(outputPath, "wb"))

# TODO Make one main function that implements this logic, currently atleast transcriber.py also has its own function like this
def getSummaryInOutPaths(inputPath, outputFolder, pattern="**/*.txt", prefix="", filetype="md"):
    """Reusable function to get input and output paths for summaries"""
    inputPath = Path(inputPath)
    outputFolder = Path(outputFolder)
    if inputPath.suffix == "":
        inputFolder = inputPath
        inputFiles = [Path(file) for file in glob.glob(
            f"{inputPath}/{pattern}", recursive=True)] # TODO Filter so no dups are made
    else:
        inputFolder = inputPath.parent
        inputFiles = [inputPath]

    if outputFolder.suffix != "":
        raise Exception("'outputFolder' has to be a folder, not file. You cannot choose the output path yourself.")
    getOutputPath = lambda inputFile: outputFolder / inputFile.parent.relative_to(inputFolder) / f"{prefix}{inputFile.stem}.{filetype}"
    

    return  [(inputFile, getOutputPath(inputFile)) for inputFile in inputFiles]