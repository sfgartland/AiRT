from enum import Enum
from pathlib import Path
from typing import Annotated, TypeAlias, List, Tuple

import typer

from .FileFilters import filter_manyVersionsInFolder, filter_noFilter

from .UI import template_enum_completer


class FileFilters(str, Enum):
    none = "no_filter"
    manyVersionsInFolder = "ManyVersionsInFolder"

    @classmethod
    def getFilter(cls, filter):
        map = {
            cls.none: filter_noFilter,
            cls.manyVersionsInFolder: filter_manyVersionsInFolder,
        }
        return map[filter]

class ToMp3_FileTypes(str, Enum):
    mp4 = "mp4"
    m4a = "m4a"
    ogg = "ogg"

FilePairType: TypeAlias = Tuple[Path, Path]
FilePairsType: TypeAlias = List[FilePairType]


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

    autoaccept_prompts: TypeAlias = Annotated[
        bool,
        typer.Option(help = "Use flag to auto-accept all prompts, e.g. for price estimate")
    ]

    tomp3_filetypes: TypeAlias = Annotated[
        List[ToMp3_FileTypes],
        typer.Option(
            help="filetypes to convert",
            autocompletion=lambda incomplete: template_enum_completer(ToMp3_FileTypes, incomplete)
        )
    ]

    pdf: TypeAlias = Annotated[bool, typer.Option(help="Set for converting markdown file to PDF once done")]
