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
