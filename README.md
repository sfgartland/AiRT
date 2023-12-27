# AI_research_tools
As a undergraduate student in the humanities I deal with a lot of materials in the form of lectures and academic reading. This project was started as an effort to explore the possibilities of using AI models to make reviewing such material more efficient.

## Features
- Transcribe lectures
  - using the OpenAI whisper models either locally or using their model
- Generate summaries of text sources
  - using OpenAI's GPT-4
- Preprocessing video and audio files for transcription
- Structure unstructured texts such as raw transcripts into paragraphs with headings
  - Using OpenAI's GPT-4 model
  - *This feature is currently somewhat unstable, might need to be run multiple times to get a good output*

### Upcoming features
- Batch download Youtube videos from CLI
- Better task progress UI in CLI
- More stable transcript structuring script
- Better output file organization
- Convert PDF versions of papers and books to markdown, preserving heading but ignoring layout elements such as page headers
  - Close to finished, the code is mostly done, only lacking CLI command
- Adding `filefilter` functions.
  - E.g. allow for processing files saved in folders with multiple versions of the lecture. It is useful in cases where the lecture is ripped from source with screencap and lecture hall recording where they are separate video files.

## Installation
Simply run this command `pip install git+https://github.com/sfgartland/AI_research_tools` 

## Usage
For now see `AI_research_tools --help` for information.

Basic usage is to place the files you want to process in a directory, then call the desired command on either the specific file or folder that you want to process.

As I'm still in the early stages of setting up the CLI UI there will be a lot of changes. When the CLI structure has been settled in I will update this section with more details.

## Requirements
- `python` installation
- `ffmpeg` command line tool
- Tesseract?
  - This one might be required for PDF handling as it is a requirement for the OCR setup. I need to look further into this
- A OpenAI API key set as an environment variable. See OpenAI API documentation for how to set it up

