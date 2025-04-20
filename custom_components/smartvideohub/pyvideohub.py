import asyncio
import logging
import re
import collections

from asyncio import ensure_future

_LOGGER = logging.getLogger(__name__)
SERVER_RECONNECT_DELAY = 30

MODEL_VIDEOHUB = "VideoHub"
MODEL_STREAMING = "Streaming"
MODEL_TERANEX = "TERANEX"

class SmartVideoHub(asyncio.Protocol):
    def __init__(self, host, port, loop=None):
        self._cmdServer = host
        self._cmdServerPort = port
        self._transport = None
        self._updateCallbacks = []
        self._errorMessage = None
        self._connected = False
        self._connecting = False
        self.initialised = asyncio.Event()
        self.inputs = dict()
        self.filtered_inputs = dict()
        self.outputs = collections.defaultdict(dict)
        self.attrs = dict()
        self.stream_set = dict()
        self.stream_state = dict()
        self.teranex_set = dict()
        self.model = None
        self.name = ""

        if loop:
            _LOGGER.debug("Latching onto an existing event loop")
            self._eventLoop = loop

    def connection_made(self, transport):
        """asyncio callback for a successful connection."""
        _LOGGER.debug("Connected to Black Magic Smart Video Hub API")
        self._transport = transport
        self._connected = True
        self._connecting = False

    def data_received(self, data):
        """asyncio callback when data is received on the socket"""
        if data != "":
            lines = str.splitlines(data.decode("utf-8"), 1)
            current_block = None
            for line in lines:
                # Check for blank lines, these indicate the end of a block
                if not line.strip():
                    current_block = None
                elif not line:
                    break
                else:
                    search = re.search("([A-Z ]+):[\r\n]", line)
                    line_conf = line.split(": ")

                    if search:
                        current_block = search.group(1)
                        _LOGGER.debug("Parsing block %s", current_block)
                        if current_block == "END PRELUDE":
                            self.initialised.set()
                            self._send_update_callback(output_id=0)
                    elif current_block == "INPUT LABELS":
                        input_number = int(line.split(" ", 1)[0]) + 1
                        input_label = line.split(" ", 1)[1].strip()
                        self.inputs.setdefault(input_number, input_label)
                        if input_label != "Input " + str(input_number):
                            self.filtered_inputs.setdefault(input_number, input_label)
                        _LOGGER.debug("Named input %i as %s", input_number, input_label)
                    elif current_block == "OUTPUT LABELS":
                        output_number = int(line.split(" ", 1)[0]) + 1
                        output_label = line.split(" ", 1)[1].strip()
                        self.outputs[output_number]["name"] = output_label
                        self.outputs[output_number]["output"] = output_number
                        _LOGGER.debug(
                            "Named output %i as %s", output_number, output_label
                        )
                    elif current_block == "VIDEO OUTPUT ROUTING":
                        output_id = int(line.split(" ", 1)[0]) + 1
                        input_id = int(line.split(" ", 1)[1]) + 1
                        self.outputs[output_id]["input"] = input_id
                        self.outputs[output_id]["input_name"] = self.get_input_name(input_id)
                        _LOGGER.debug(
                            "Output %i is now displaying input %i", output_id, input_id
                        )
                        if self.initialised.is_set():
                            self._send_update_callback(output_id=output_id)
                    elif current_block == "VIDEOHUB DEVICE":
                        self.model = MODEL_VIDEOHUB
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            self.attrs[line_conf[0]] = line_conf[1].strip()
                            if line_conf[0] == "Friendly Name":
                                self.name = line_conf[1].strip()
                    elif current_block == "IDENTITY":
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            self.attrs[line_conf[0]] = line_conf[1].strip()
                            if line_conf[0] == "Model":
                                if line_conf[1].startswith("Blackmagic Web Presenter"):
                                    self.model = MODEL_STREAMING
                            elif line_conf[0] == "Label":
                                self.name = line_conf[1].strip()
                    elif current_block == "STREAM SETTINGS":
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            self.stream_set[line_conf[0]] = line_conf[1].strip()
                        if self.initialised.is_set():
                            self._send_update_callback(output_id=0)
                    elif current_block == "STREAM STATE":
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            self.stream_state[line_conf[0]] = line_conf[1].strip()
                        if self.initialised.is_set():
                            self._send_update_callback(output_id=0)
                    elif current_block == "TERANEX MINI DEVICE":
                        self.model = MODEL_TERANEX
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            if line_conf[0] == "Unique ID":
                                self.attrs[line_conf[0]] = line_conf[1].strip()
                            self.teranex_set[line_conf[0]] = line_conf[1].strip()
                        if self.initialised.is_set():
                            self._send_update_callback(output_id=0)
                    elif current_block == "VIDEO OUTPUT":
                        if len(line_conf) == 2 and line_conf[1].strip() != "":
                            self.teranex_set[line_conf[0]] = line_conf[1].strip()
                        if self.initialised.is_set():
                            self._send_update_callback(output_id=0)

    def connection_lost(self, exc):
        """asyncio callback for a lost TCP connection"""
        self._connected = False
        self.initialised.set()
        self._send_update_callback()
        _LOGGER.error("Connection to the server lost")

    def connect(self):
        _LOGGER.info(
            str.format(
                "Connecting to Smart Video Hub at {0}:{1}",
                self._cmdServer,
                self._cmdServerPort,
            )
        )
        self._connecting = True
        coro = self._eventLoop.create_connection(
            lambda: self, self._cmdServer, self._cmdServerPort
        )
        return ensure_future(coro)

    def start(self):
        """Public method for initiating connectivity with the envisalink."""
        self.connect()
        _LOGGER.info("Connected to server")

    def stop(self):
        """Public method for shutting down connectivity with the envisalink."""
        self._connected = False
        self._transport.close()

    def _send_update_callback(self, output_id=False):
        """Internal method to notify all update callback subscribers."""
        if not self._updateCallbacks:
            _LOGGER.debug("Update callback has not been set by client")

        for callback in self._updateCallbacks:
            callback(output_id=output_id)

    def set_input(self, outputNumber, inputNumber):
        if (
            outputNumber <= len(self.outputs)
            and inputNumber <= len(self.inputs)
            and self.connected
        ):
            _LOGGER.debug("Setting output %i to input %i", outputNumber, inputNumber)
            command = (
                "VIDEO OUTPUT ROUTING:\n"
                + str(outputNumber - 1)
                + " "
                + str(inputNumber - 1)
                + "\n\n"
            )
            self._transport.write(command.encode("ascii"))

    def set_input_by_name(self, outputNumber, inputName):
        input_list = self.get_input_list()
        if inputName in input_list and self._connected:
            self.set_input(outputNumber, input_list.index(inputName) + 1)
            return True
        else:
            _LOGGER.debug(
                "Input %s was not found in the list of inputs or the server was disconnected",
                inputName,
            )
            return False

    def get_input_list(self, filter_inputs=False) -> list[str]:
        # Convert the dictionary to a list - remove the last value which seems to be a default object
        if filter_inputs:
            return list(self.filtered_inputs.values())
        else:
            return list(self.inputs.values())

    def get_inputs(self, filter_inputs=False):
        if filter_inputs:
            return self.filtered_inputs
        else:
            return self.inputs

    def get_input_name(self, input_number):
        if input_number in self.inputs:
            return self.inputs[input_number]
        else:
            return "Ínput %d" % input_number

    def get_selected_input(self, output_number):
        if output_number in self.outputs:
            return self.outputs[output_number]["input"]
        else:
            return None

    async def keep_alive(self):
        """Send a keepalive command to reset its watchdog timer."""
        while self._connected:
            _LOGGER.debug("Sending keepalive to the server")
            command = "PING:\n\n"
            self._transport.write(command.encode("ascii"))
            await asyncio.sleep(120)

    def get_outputs(self):
        return self.outputs

    @property
    def error_message(self):
        """Returns the last error message, or None if there were no errors."""
        return self._errorMessage

    @property
    def is_initialised(self):
        return self.initialised.is_set()

    @property
    def connected(self):
        return self._connected

    def add_update_callback(self, method):
        """Public method to add a callback subscriber."""
        self._updateCallbacks.append(method)

    def set_video_mode(self, mode):
        command = "STREAM SETTINGS:\nVideo Mode: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_stream_platform(self, platform):
        command = "STREAM SETTINGS:\nCurrent Platform: %s\n\n" % platform
        self._transport.write(command.encode("ascii"))

    def set_stream_key(self, mode):
        command = "STREAM SETTINGS:\nStream Key: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_quality_level(self, mode):
        command = "STREAM SETTINGS:\nCurrent Quality Level: %s\n\n" % mode
        self._transport.write(command.encode("ascii"))

    def set_lut(self, lut_id):
        if isinstance(lut_id, int) and int(lut_id) == 1:
            lut = "Lut 0"
        elif isinstance(lut_id, int) and int(lut_id) == 2:
            lut = "Lut 1"
        elif isinstance(lut_id, int):
            lut = "none"
        elif isinstance(lut_id, str):
            lut = lut_id
        command = "VIDEO OUTPUT:\nLut on loop: true\nLut selection: %s\n\n" % lut
        self._transport.write(command.encode("ascii"))

    def set_steam_state(self, mode):
        command = "STREAM STATE:\nAction: %s\n\n" % ("Start" if mode else "Stop")
        self._transport.write(command.encode("ascii"))
