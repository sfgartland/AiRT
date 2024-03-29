# AI_research_tools
As a undergraduate student in the humanities I deal with a lot of materials in the form of lectures and academic reading. This project was started as an effort to explore the possibilities of using AI models to make reviewing such material more efficient.

### Example data
I've included samples of the output in the `examples_data` folder. These files have been generated by the commands: `AI_research_tools transcribewithapi ./example_data/oxford_CPR/*.mp3`, `AI_research_tools structuretranscripts ./example_data/oxford_CPR/*_api.txt`, and `AI_research_tools summarizetranscripts ./example_data/oxford_CPR/*_api.txt`

The example data is a lecture series on Kant's *Critique of Pure Reason* by Dan Robinson. They can be found here: https://podcasts.ox.ac.uk/series/kants-critique-pure-reason

## Features
- Transcribe lectures
  - using the OpenAI whisper models either locally or using their API
- Generate summaries of text sources
  - using OpenAI's GPT-4
- Preprocessing video and audio files for transcription
- Structure unstructured texts such as raw transcripts into paragraphs with headings
  - Using OpenAI's GPT-4 model
  - *This feature is currently somewhat unstable, might need to be run multiple times to get a good output*
- Generate detailed price estimates for OpenAI API usage
- Add `.airtignore` file to any directory to ignore the files in it

### Upcoming features
- Convert markdown outputs into pdf's
  - Thinking to use `Pandoc` for this, but open to suggestions
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
- A OpenAI API key set as an environment variable. See [OpenAI API documentation](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety) for how to set it up

