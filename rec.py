import pyaudio
import subprocess
import io
import argparse

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 1024
CODEC2_MODE = "700C"
CODEC2_FILENAME = "recording.c2"

def list_input_devices(audio):
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print(f"Input Device id {i} - {audio.get_device_info_by_host_api_device_index(0, i).get('name')}")

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
parser.add_argument('--list', action='store_true', help='List available input devices.')
parser.add_argument('--mic', type=int, help='Input device ID for recording.')

args = parser.parse_args()

audio = pyaudio.PyAudio()

if args.list:
    list_input_devices(audio)
else:
    record_audio(args.mic)
