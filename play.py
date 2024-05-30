import pyaudio
import subprocess
import io
import argparse
import os
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 1024


def list_c2_files():
    c2_files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.c2')]
    file_descriptions = [f"{i + 1}. {file}" for i, file in enumerate(c2_files)]
    return file_descriptions


def prompt_for_file(file_descriptions):
    class FileCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text.lower()
            if text.isdigit():
                matching_enums = [description for description in file_descriptions if description.startswith(text)]
                for enum in matching_enums:
                    yield Completion(enum, start_position=-len(document.text))
                remaining_matches = [description for description in file_descriptions if
                                     description not in matching_enums]
                for match in remaining_matches:
                    yield Completion(match, start_position=-len(document.text))
            else:
                for description in file_descriptions:
                    if text in description.lower():
                        yield Completion(description, start_position=-len(document.text))

    class FileValidator(Validator):
        def validate(self, document):
            input_text = document.text.strip()
            if not any(input_text in description for description in file_descriptions):
                raise ValidationError(message='Invalid file selected, please select from the list.',
                                      cursor_position=len(document.text))

    file_completer = FileCompleter()
    file_validator = FileValidator()

    selected_description = prompt("Select a .c2 file:\n" + "\n".join(file_descriptions) + "\n> ",
                                  completer=file_completer, validator=file_validator)
    selected_file = selected_description.split('. ', 1)[1]
    return selected_file


def play_c2_file(filename):
    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, output=True)

    print("Playing back recording...")

    pcm_data = io.BytesIO()
    command = ["c2dec", "700C", filename, "-"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)

    while True:
        data = process.stdout.read(CHUNK * 2)
        if not data:
            break
        pcm_data.write(data)

    pcm_data.seek(0)

    while True:
        data = pcm_data.read(CHUNK)
        if not data:
            break
        stream.write(data)

    stream.stop_stream()
    stream.close()
    audio.terminate()

    print("Playback finished.")


parser = argparse.ArgumentParser(description="Play back a Codec2 .c2 file.")
parser.add_argument('--file', type=str, help='Path to the .c2 file to play.')

args = parser.parse_args()

if args.file:
    play_c2_file(args.file)
else:
    file_descriptions = list_c2_files()
    if not file_descriptions:
        print("No .c2 files found in the current directory.")
        exit()
    selected_file = prompt_for_file(file_descriptions)
    play_c2_file(selected_file)
