import traceback
import asyncio
import pyaudio
import subprocess
import io

from pubsub import pub

import meshtastic
from meshtastic import serial_interface
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError


def prompt_for_device(ports):
    port_descriptions = [f"{i + 1}. {port}" for i, port in enumerate(ports)]

    class PortCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text.lower()
            if text.isdigit():
                matching_enums = [description for description in port_descriptions if description.startswith(text)]
                for enum in matching_enums:
                    yield Completion(enum, start_position=-len(document.text))
                remaining_matches = [description for description in port_descriptions if
                                     description not in matching_enums]
                for match in remaining_matches:
                    yield Completion(match, start_position=-len(document.text))
            else:
                for description in port_descriptions:
                    if text in description.lower():
                        yield Completion(description, start_position=-len(document.text))

    class PortValidator(Validator):
        def validate(self, document):
            input_text = document.text.strip()
            if not any(input_text in description for description in port_descriptions):
                raise ValidationError(message='Invalid port selected, please select from the list.',
                                      cursor_position=len(document.text))

    port_completer = PortCompleter()
    selected_description = prompt("Select a port: ", completer=port_completer, validator=PortValidator())
    selected_port = selected_description.split(' ')[1]
    return selected_port


def select_port():
    ports = meshtastic.util.findPorts(True)
    if len(ports) == 0:
        print("No Serial Meshtastic device detected. Please ensure your device is connected and try again.")
        exit()
    elif len(ports) > 1:
        print("Multiple serial ports detected.")
        port_descriptions = [f"{i + 1}. {port}" for i, port in enumerate(ports)]
        print("Port Descriptions:")
        for description in port_descriptions:
            print(description)
        selected_port = prompt_for_device(ports)
    else:
        selected_port = ports[0]
    return selected_port


packets = {}


def save_and_play_file(sender, data):
    filename = f"{sender}.c2"
    with open(filename, "wb") as file:
        file.write(data)

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 8000
    CHUNK = 1024

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


def onReceive(packet, interface):
    sender = packet['from']
    packet_id = packet['id']
    payload = packet['decoded']['payload']

    if sender not in packets:
        packets[sender] = []

    packets[sender].append((packet_id, payload))
    packets[sender].sort()

    assembled_payload = bytearray()
    start_sequence = bytearray([0xC0, 0xDE, 0xC2])
    end_sequence = start_sequence * 2

    start_found = False
    end_found = False

    for _, p in packets[sender]:
        assembled_payload.extend(p)
        if p.startswith(start_sequence):
            start_found = True
        if p.endswith(end_sequence):
            end_found = True

    if start_found and end_found:
        packets[sender] = []
        save_and_play_file(sender, assembled_payload)


async def main(selected_port):
    try:
        interface = serial_interface.SerialInterface(devPath=selected_port)

        port = 456
        pub.subscribe(onReceive, f"meshtastic.receive.data.{port}")

        while True:
            await asyncio.sleep(1)

    except Exception as e:
        tb = traceback.format_exc()
        print(f"An error occurred: {e}\nTraceback details:\n{tb}")


if __name__ == "__main__":
    selected_port = select_port()
    asyncio.run(main(selected_port))
