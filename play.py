import pyaudio
import subprocess
import io

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 1024
CODEC2_FILENAME = "recording.c2"

audio = pyaudio.PyAudio()

stream = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, output=True)

print("Playing back recording...")

pcm_data = io.BytesIO()
command = ["c2dec", "700C", CODEC2_FILENAME, "-"]
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
