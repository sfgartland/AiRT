
import asyncio
import subprocess
from typing import Callable

from loguru import logger
import regex


async def _read_stream(stream, cb):
    while True:
        line = (await stream.readline()).decode("utf-8").rstrip()
        if line:
            cb(line)
        else:
            break


async def runFfmpegCommandAsync(
    command, output_stdout=False, progressCallback: Callable[[float], None] = None
):
    # Ensure that the overwrite and loglevel flags are set correctly on ffmpeg commands
    if len(regex.findall("^ffmpeg ", command)) > 0:
        command = regex.sub(
            "^ffmpeg ", "ffmpeg -y -loglevel error -progress pipe:1 ", command
        )


    logger.debug(f"Running command: {command}")
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    def outHandler(std):
        if output_stdout:
            logger.debug(std)

        currentTime = regex.match("out_time_us=(\d+)", std)
        if currentTime is not None and progressCallback is not None:
            progressCallback(int(currentTime.group(1))/1000000)

    def errorHandler(std):
        logger.error(std)

    await asyncio.gather(
        _read_stream(proc.stdout, outHandler), _read_stream(proc.stderr, errorHandler)
    )


def runCommand(command, output_stdout=False):
    # Ensure that the overwrite and loglevel flags are set correctly on ffmpeg commands
    if len(regex.findall("^ffmpeg ", command)) > 0:
        command = regex.sub("^ffmpeg ", "ffmpeg -y -loglevel error ", command)

    logger.debug(f"Running command: {command}")
    p = subprocess.run(
        command, capture_output=True, shell=True, universal_newlines=True
    )

    if p.stdout != "":
        if output_stdout:
            logger.info(p.stdout)
        else:
            logger.debug(p.stdout)

    if p.stderr != "":
        logger.error(p.stderr)

    return p.stdout