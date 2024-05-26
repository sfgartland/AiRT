# TODO Add a command to run nougat here
import datetime

try:
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models
except ImportError:
    NO_MARKER_LIB = True


import json


from loguru import logger

import time
from pathlib import Path


def pdf2md(inputPDF: Path, outputMD: Path):
    if NO_MARKER_LIB:
        raise ImportError("Marker lib is not installed. Please reinstall this package with the right optional dependencies!")

    logger.info(f"Converting PDF to Markdown: {inputPDF}->{outputMD}")
    startTime = time.time()

    model_lst = load_all_models()
    # Add in again "max_pages=args.max_pages, parallel_factor=args.parallel_factor"?
    full_text, out_meta = convert_single_pdf(str(inputPDF), model_lst)

    with open(outputMD, "w+", encoding="utf-8") as f:
        f.write(full_text)

    out_meta_filename = f"{outputMD.stem}_meta.json"
    with open(out_meta_filename, "w+") as f:
        f.write(json.dumps(out_meta, indent=4))

    endTime = time.time()
    logger.info(
        f"Finished converting PDF to Markdown in {datetime.timedelta(seconds=(endTime-startTime))}"
    )
