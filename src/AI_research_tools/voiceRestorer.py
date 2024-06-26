from voicefixer import VoiceFixer
from .fileHandler import generateWorkbenchPath

from pathlib import Path


def restoreVoice(inputfile:Path, outputfile:Path=None, cuda:bool=False, preprocess:bool=False, progress=None):
    if inputfile.suffix != ".wav":
        raise Exception("inputfile for voice restoration function needs to be wav file. Use file handler function to correct!")

    if outputfile is None:
        outputfile = generateWorkbenchPath("restored-audio.wav")

    if progress is not None:
        restore_task = progress.add_task("Restoring voice...", total=None)

    vf = VoiceFixer()
    vf.restore(input=inputfile, output=outputfile, cuda=cuda, mode=(1 if preprocess else 0))
    if progress is not None:
        progress.update(restore_task, completed=1, total=1)


    return outputfile