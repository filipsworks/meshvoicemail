import pyaudio
import subprocess
import io
import argparse
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 1024
CODEC2_MODE = "700C"
CODEC2_FILENAME = "recording.c2"

def list_input_devices(audio):
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    device_descriptions = [f"{i+1}. {audio.get_device_info_by_host_api_device_index(0, i).get('name')}"
                           for i in range(numdevices) if audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0]
    for description in device_descriptions:
        print(description)
    return device_descriptions

def prompt_for_device(device_descriptions):
    class DeviceCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text.lower()
            if text.isdigit():
                matching_enums = [description for description in device_descriptions if description.startswith(text)]
                for enum in matching_enums:
                    yield Completion(enum, start_position=-len(document.text))
                remaining_matches = [description for description in device_descriptions if description not in matching_enums]
                for match in remaining_matches:
                    yield Completion(match, start_position=-len(document.text))
            else:
                for description in device_descriptions:
                    if text in description.lower():
                        yield Completion(description, start_position=-len(document.text))

    class DeviceValidator(Validator):
        def validate(self, document):
            input_text = document.text.strip()
            if not any(input_text in description for description in device_descriptions):
                raise ValidationError(message='Invalid device selected, please select from the list.', cursor_position=len(document.text))

    device_completer = DeviceCompleter()
    selected_description = prompt("Select an input device: ", completer=device_completer, validator=DeviceValidator())
    selected_device_index = int(selected_description.split('.')[0]) - 1
    return selected_device_index

def record_audio(device_index=None):
    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)

    print("Recording... Press Ctrl+C to stop.")

    frames = []

    try:
        while True:
            data = stream.read(CHUNK)
            frames.append(data)
    except KeyboardInterrupt:
        print("Recording stopped.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    pcm_data = io.BytesIO(b''.join(frames))

    command = ["c2enc", CODEC2_MODE, "-", CODEC2_FILENAME]

    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    process.communicate(input=pcm_data.getvalue())

    print(f"Converted PCM data to Codec2 {CODEC2_MODE} format as {CODEC2_FILENAME}")

parser = argparse.ArgumentParser(description="Record audio and encode to Codec2 format.")
parser.add_argument('--mic', action='store_true', help='Prompt for input device ID for recording.')

args = parser.parse_args()

audio = pyaudio.PyAudio()

if args.mic:
    device_descriptions = list_input_devices(audio)
    if not device_descriptions:
        print("No input devices found. Please ensure your microphone is connected.")
        exit()
    selected_device_index = prompt_for_device(device_descriptions)
    record_audio(selected_device_index)
else:
    record_audio()
