from enum import Enum


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
