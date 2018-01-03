import asyncio
import logging
import re
import collections

from asyncio import ensure_future

_LOGGER = logging.getLogger(__name__)

class SmartVideoHub(asyncio.Protocol):
    def __init__(self, cmdServer, cmdServerPort, loop=None):
        self._cmdServer = cmdServer
        self._cmdServerPort = cmdServerPort
        self._transport = None
        self._updateCallbacks = []
        self._errorMessage = None
        self._connected = False
        self.initialised = False
        self.inputs = dict()
        self.outputs = collections.defaultdict(dict)

        if loop:
            _LOGGER.debug("Latching onto an existing event loop.")
            self._eventLoop = loop
            self._ownLoop = False
        else:
            _LOGGER.debug("Creating our own event loop.")
            self._eventLoop = asyncio.new_event_loop()
            self._ownLoop = True

    def connection_made(self, transport):
        """asyncio callback for a successful connection."""
        _LOGGER.debug("Connected to Black Magic Smart Video Hub API")
        self._transport = transport
        self._connected = True

    def data_received(self, data):
        """asyncio callback when data is received on the socket"""
        if data != '':
            lines = str.splitlines(data.decode('ascii'),1)
            current_block = None
            for line in lines:
                # Check for blank lines, these indicate the end of a block
                if not line.strip():
                    current_block = None
                elif not line:
                    break
                else:
                    search = re.search('([A-Z ]+):[\r\n]',line)
                    if search:
                        current_block = search.group(1)
                        _LOGGER.debug("Parsing block %s", current_block)
                        if current_block == "END PRELUDE":
                            self.initialised = True
                    elif current_block == "INPUT LABELS":
                        input_number = int(line.split(" ",1)[0])+1
                        input_label = line.split(" ",1)[1].strip()
                        self.inputs.setdefault(input_number, input_label)
                        _LOGGER.debug('Named input %i as %s', input_number, input_label)
                    elif current_block == "OUTPUT LABELS":
                        output_number = int(line.split(" ",1)[0])+1
                        output_label = line.split(" ",1)[1].strip()
                        self.outputs[output_number]['name'] = output_label
                        self.outputs[output_number]['output'] = output_number
                        _LOGGER.debug('Named output %i as %s', output_number, output_label)
                    elif current_block == "VIDEO OUTPUT ROUTING":
                        from_output = int(line.split(" ",1)[0])+1
                        to_input = int(line.split(" ",1)[1])+1
                        self.outputs[from_output]['input'] = to_input
                        self.outputs[from_output]['input_name'] = self.inputs[to_input]
                        _LOGGER.debug('Output %i is now displaying input %i', from_output, to_input)
                        if self.initialised:
                            self._send_update_callback()

    def connection_lost(self, exc):
        """asyncio callback for a lost TCP connection"""
        self._connected = False
        _LOGGER.debug('The server closed the connection')
        self._send_update_callback()

        if self._ownLoop:
            _LOGGER.debug('Stop the event loop')
            self._eventLoop.stop()


    def connect(self):
        """Internal method for making the physical connection."""
        _LOGGER.info(str.format("Connecting to Smart Video Hub at {0}:{1}", self._cmdServer, self._cmdServerPort))
        coro = self._eventLoop.create_connection(lambda: self, self._cmdServer, self._cmdServerPort)
        ensure_future(coro, loop=self._eventLoop)

    def start(self):
        """Public method for initiating connectivity with the envisalink."""
        self.connect()

        if self._ownLoop:
            _LOGGER.debug("Starting up our own event loop.")
            self._eventLoop.run_forever()
            self._eventLoop.close()
            _LOGGER.debug("Connection shut down.")

    def stop(self):
        """Public method for shutting down connectivity with the envisalink."""
        self._connected = False
        self._transport.close()

        if self._ownLoop:
            _LOGGER.debug("Shutting down Videohub connection...")
            self._eventLoop.call_soon_threadsafe(self._eventLoop.stop)
        else:
            _LOGGER.debug("An event loop was given to us- we will shutdown when that event loop shuts down.")

    def _send_update_callback(self):
        """Internal method to notify all update callback subscribers."""
        if self._updateCallbacks == []:
            _LOGGER.debug("Update callback has not been set by client.")

        for callback in self._updateCallbacks:
            callback()

    def set_input(self, outputNumber, inputNumber):
        if(outputNumber <= len(self.outputs) and inputNumber <= len(self.inputs) and self.connected):
            _LOGGER.debug("Setting output %i to input %i", outputNumber, inputNumber)
            command = "VIDEO OUTPUT ROUTING:\n" + str(outputNumber-1) + " " + str(inputNumber-1) + "\n\n"
            self._transport.write(command.encode('ascii'))

    def set_input_by_name(self, outputNumber, inputName):
        input_list = self.get_input_list()
        if inputName in input_list and self._connected:
            self.set_input(outputNumber,input_list.index(inputName)+1)
            return True
        else:
            _LOGGER.debug("Input %s was not found in the list of inputs or the server was disconnected",inputName)
            return False

    def get_input_list(self):
        # Convert the dictionary to a list - remove the last value which seems to be a default object
        return list(self.inputs.values())

    def get_input_name(self, input_number):
        if input_number in self.inputs:
            return self.inputs[input_number]
        else:
            return 'Ínput ' + input_number

    def get_selected_input(self, output_number):
        if output_number in self.outputs:
            return self.outputs[output_number]['input']
        else:
            return None

    @asyncio.coroutine        
    def keep_alive(self):
        """Send a keepalive command to reset it's watchdog timer."""
        while self._connected:
            _LOGGER.debug("Sending keepalive to server")
            command = "PING:\n\n"
            self._transport.write(command.encode('ascii')) 
            yield from asyncio.sleep(120, loop=self._eventLoop)
    
    def get_outputs(self):
        return self.outputs

    @property
    def error_message(self):
        """Returns the last error message, or None if there were no errors."""
        return self._errorMessage

    @property
    def is_initialised(self):
        return self.initialised

    @property
    def connected(self):
        return self._connected

    def add_update_callback(self, method):
        """Public method to add a callback subscriber."""
        self._updateCallbacks.append(method)
