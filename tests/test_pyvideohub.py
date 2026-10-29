import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "smartvideohub"
    / "pyvideohub.py"
)
SPEC = importlib.util.spec_from_file_location("pyvideohub", MODULE_PATH)
pyvideohub = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pyvideohub)


class SmartVideoHubCallbackTest(unittest.TestCase):
    def test_callback_can_be_unsubscribed(self):
        client = pyvideohub.SmartVideoHub("127.0.0.1", 9990)
        updates = []

        unsubscribe = client.add_update_callback(
            lambda output_id: updates.append(output_id)
        )
        client._send_update_callback(output_id=14)
        unsubscribe()
        client._send_update_callback(output_id=15)

        self.assertEqual(updates, [14])

    def test_routing_update_notifies_the_changed_output(self):
        client = pyvideohub.SmartVideoHub("127.0.0.1", 9990)
        client.inputs[3] = "IPTV"
        client.initialised.set()
        updates = []
        client.add_update_callback(lambda output_id: updates.append(output_id))

        client.data_received(b"VIDEO OUTPUT ROUTING:\n13 2\n\n")

        self.assertEqual(client.outputs[14]["input"], 3)
        self.assertEqual(client.outputs[14]["input_name"], "IPTV")
        self.assertEqual(updates, [14])


if __name__ == "__main__":
    unittest.main()


def _prelude():
    text = (
        "PROTOCOL PREAMBLE:\nVersion: 2.8\n\n"
        "VIDEOHUB DEVICE:\nDevice present: true\nFriendly Name: Hub\n"
        "Unique ID: 7C2E0D0A0514\n\n"
        "INPUT LABELS:\n" + "".join(f"{i} In {i + 1}\n" for i in range(40)) + "\n"
        "OUTPUT LABELS:\n" + "".join(f"{i} Out {i + 1}\n" for i in range(40)) + "\n"
        "VIDEO OUTPUT ROUTING:\n"
        + "".join(f"{i} {(i * 7) % 40}\n" for i in range(40))
        + "\nEND PRELUDE:\n\n"
    )
    return text.replace("\n", "\r\n").encode()


class SmartVideoHubChunkedPreludeTest(unittest.TestCase):
    """TCP may split the prelude anywhere; nothing must get lost."""

    def test_prelude_split_at_every_position(self):
        data = _prelude()
        for cut in range(1, len(data), 7):
            client = pyvideohub.SmartVideoHub("127.0.0.1", 9990)
            client.data_received(data[:cut])
            client.data_received(data[cut:])
            self.assertTrue(client.is_initialised)
            self.assertEqual(len(client.inputs), 40)
            self.assertEqual(len(client.outputs), 40)
            for output in client.outputs.values():
                self.assertIn("input", output)
            self.assertEqual(client.get_selected_input(3), 15)

    def test_routing_update_split_mid_line(self):
        client = pyvideohub.SmartVideoHub("127.0.0.1", 9990)
        client.data_received(_prelude())
        client.data_received(b"VIDEO OUTPUT ROUTING:\r\n5 1")
        client.data_received(b"2\r\n\r\n")
        self.assertEqual(client.get_selected_input(6), 13)
