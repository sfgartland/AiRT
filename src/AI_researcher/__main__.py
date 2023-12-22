from .transcriber import copyFilesToGoogleColab, createWhisperModel, batchTranscribeMp3s, batchProcessMediaFiles
from loguru import logger

from pathlib import Path
import glob


logger.add("logs/transcriber-{time}.log")


# batchTranscribeMp3s("output/PHILOS133", "output/PHILOS133")
# batchProcessMediaFiles("PHILOS133", "output/PHILOS133")

# model,modelName = createWhisperModel()


# batchTranscribeMp3s("oxford_CPR", "oxford_CPR", model, modelName)
# batchProcessMediaFiles("PHILOS133", "output/PHILOS133")

def filter(fileList):
    """Filters through a list of Path objects and returns only the last file in the same folder"""
    getFilesInSameFolder = lambda current: [file for file in fileList if current.parent == file.parent]
    
    return [file for file in fileList if file.samefile(getFilesInSameFolder(file)[-1])]

if __name__ == "__main__":
    print("hello")
    # copyFilesToGoogleColab("output/PHILOS133", "G:/Min disk/google-Collab-testing-folder/PHILOS133", fileFilter=filter)