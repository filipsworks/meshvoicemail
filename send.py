import traceback
import logging

import meshtastic
from meshtastic import (
    serial_interface,
    mesh_pb2)

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError

def prompt_for_device(ports):
    port_descriptions = [f"{i+1}. {port}" for i, port in enumerate(ports)]

    class PortCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text.lower()
            if text.isdigit():
                matching_enums = [description for description in port_descriptions if description.startswith(text)]
                for enum in matching_enums:
                    yield Completion(enum, start_position=-len(document.text))
                remaining_matches = [description for description in port_descriptions if description not in matching_enums]
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
                raise ValidationError(message='Invalid port selected, please select from the list.', cursor_position=len(document.text))

    port_completer = PortCompleter()
    selected_description = prompt("Select a port: ", completer=port_completer, validator=PortValidator())
    selected_port = selected_description.split(' ')[1]
    return selected_port

try:
    ports = meshtastic.util.findPorts(True)
    logging.debug(f"ports: {ports}")
    if len(ports) == 0:
        print("No Serial Meshtastic device detected. Please ensure your device is connected and try again.")
        exit()  # Exit the script if no ports are detected
    elif len(ports) > 1:
        print("Multiple serial ports detected.")
        port_descriptions = [f"{i+1}. {port}" for i, port in enumerate(ports)]
        print("Port Descriptions:")
        for description in port_descriptions:
            print(description)
        selected_port = prompt_for_device(ports)
    else:
        selected_port = ports[0]

    interface = serial_interface.SerialInterface(devPath=selected_port)

    nodes = interface.nodes

    node_descriptions = [f"{i+1}. {key} {value['user']['longName']}" for i, (key, value) in enumerate(nodes.items())]
    node_ids = [key for key in nodes.keys()]
    long_names = [value['user']['longName'] for value in nodes.values()]

    print("Node Descriptions:")
    for description in node_descriptions:
        print(description)

    if not node_descriptions:
        print("No nodes found. Ensure the device is connected and nodes are available.")
        exit()

    class NodeCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text.lower()
            if text.isdigit():
                matching_enums = [description for description in node_descriptions if description.startswith(text)]
                for enum in matching_enums:
                    yield Completion(enum, start_position=-len(document.text))
                remaining_matches = [description for description in node_descriptions if description not in matching_enums]
                for match in remaining_matches:
                    yield Completion(match, start_position=-len(document.text))
            else:
                for description in node_descriptions:
                    if text in description.lower():
                        yield Completion(description, start_position=-len(document.text))

    class NodeValidator(Validator):
        def validate(self, document):
            input_text = document.text.strip()
            if not any(input_text in description for description in node_descriptions):
                raise ValidationError(message='Invalid node selected, please select from the list.',
                                      cursor_position=len(document.text))

    node_completer = NodeCompleter()
    selected_description = prompt("Select a node: ", completer=node_completer, complete_while_typing=True, validator=NodeValidator())

    selected_node_id = selected_description.split(' ')[1]

    print(f"Selected Node ID: {selected_node_id}")

    port = 456

    with open('recording.c2', 'rb') as file:
        file_bytes = file.read()
        byte_array = bytearray(file_bytes)

    sequence = bytearray([0xC0, 0xDE, 0xC2])
    # File ending marker = twice the codec2 magic
    byte_array.extend(sequence * 2)

    msg_max_len = mesh_pb2.DATA_PAYLOAD_LEN - 37

    chunks = [bytes(byte_array[i:i + msg_max_len]) for i in range(0, len(byte_array), msg_max_len)]

    for index, chunk in enumerate(chunks):
        interface.sendData(chunk, selected_node_id, port)

except Exception as e:
    tb = traceback.format_exc()
    print(f"An error occurred: {e}\nTraceback details:\n{tb}")
