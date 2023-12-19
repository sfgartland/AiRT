# Simple script to remove duplicate files based on md5 hash match.
# It keeps the original in the first folder and deletes later matches.
# I needed it to fix an bug in my scraper that downloaded the videos initially

import hashlib
import glob

import os

import pickle

parent = "PHILOS133"


def generateHashesAndDump(parent):
    allVideos = glob.glob(f"{parent}/*/*.mp4")
    hashes = list(map(lambda x: hashlib.md5(
        open(x, 'rb').read()).hexdigest(), allVideos))

    with open("allVideos.txt", "wb") as file:
        pickle.dump(allVideos, file)
    with open("hashes.txt", "wb") as file:
        pickle.dump(hashes, file)


def loadData(filename):
    with open(filename, "rb") as file:
        return pickle.load(file)


def removeDups(parent):
    def getIndex(path): return int(path.split("\\")[1].split("_")[0])

    allVideos = loadData("allVideos.txt")
    hashes = loadData("hashes.txt")
    for i, hash in enumerate(hashes):
        currentVideo = allVideos[i]
        currentVideoIndex = getIndex(currentVideo)

        matchingHashes = [i for i, val in enumerate(hashes) if val == hash]
        matchingVideos = list(map(lambda x: allVideos[x], matchingHashes))
        for match in matchingVideos:
            matchIndex = getIndex(match)
            if matchIndex > currentVideoIndex:
                try:
                    os.remove(match)
                except:
                    print("Already removed?")
                # print(f"Would remove {match}")


# generateHashesAndDump(parent)
removeDups(parent)
