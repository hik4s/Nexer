import io
import unittest
from unittest.mock import Mock, patch

from app.config import Settings


class PairingDeliveryTests(unittest.TestCase):
    def test_console_is_default_and_keeps_existing_operator_output(self):
        from app.pairing_delivery import deliver_pairing_code
        with patch("builtins.print") as output:
            deliver_pairing_code("synthetic-code", Settings())
        self.assertIn("synthetic-code", output.call_args.args[0])
        self.assertTrue(output.call_args.kwargs["flush"])

    def test_window_receives_code_only_through_private_stdin(self):
        from app.pairing_delivery import deliver_pairing_code
        stream = io.StringIO()
        stream.close = lambda: None
        process = Mock(stdin=stream, stdout=io.StringIO("READY\n"))
        with patch("app.pairing_delivery.subprocess.Popen", return_value=process) as spawn, patch("builtins.print") as output:
            deliver_pairing_code("synthetic-private-code", Settings(pairing_code_display="window"))
        self.assertNotIn("synthetic-private-code", repr(spawn.call_args))
        self.assertIn("synthetic-private-code", stream.getvalue())
        self.assertIn("show_pairing_code.py", spawn.call_args.args[0][-1])
        self.assertNotIn("env", spawn.call_args.kwargs)
        output.assert_not_called()

    def test_window_must_confirm_creation_before_delivery_succeeds(self):
        from app.pairing_delivery import deliver_pairing_code
        process = Mock(stdin=io.StringIO(), stdout=io.StringIO(""))
        with patch("app.pairing_delivery.subprocess.Popen", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "^PAIRING_DELIVERY_FAILED$"):
                deliver_pairing_code("synthetic-private-code", Settings(pairing_code_display="window"))

    def test_window_delivery_failure_is_sanitized(self):
        from app.pairing_delivery import deliver_pairing_code
        with patch("app.pairing_delivery.subprocess.Popen", side_effect=OSError("synthetic-private-code")), patch("builtins.print") as output:
            with self.assertRaisesRegex(RuntimeError, "^PAIRING_DELIVERY_FAILED$"):
                deliver_pairing_code("synthetic-private-code", Settings(pairing_code_display="window"))
        output.assert_not_called()
