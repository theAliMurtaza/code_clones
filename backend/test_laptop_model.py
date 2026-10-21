"""Safety/lifecycle checks for the laptop launcher; no cloud or model required."""
import os
import socket
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.error

from deploy import laptop_model as laptop


class LaptopLauncherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.runtime = Path(self.directory.name)
        patcher = patch.object(laptop, "RUNTIME", self.runtime)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_lock_prevents_duplicate_servers_and_releases(self):
        self.assertFalse(laptop.is_running())
        with laptop.session_lock():
            self.assertTrue(laptop.is_running())
            with self.assertRaisesRegex(RuntimeError, "already running"):
                with laptop.session_lock():
                    pass
        self.assertFalse(laptop.is_running())

    def test_stop_and_child_exit_interrupt_startup(self):
        process = Mock()
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "model exited"):
            laptop.wait_until(lambda: True, [("model", process)], 1, "model")
        (self.runtime / "stop").touch()
        with self.assertRaises(InterruptedError):
            laptop.wait_until(lambda: True, [], 1, "model")

    def test_laptop_overrides_remote_or_lightweight_environment(self):
        with patch.dict(os.environ, DETECTION_ENGINE="remote", BATCH_SIZE="80"):
            env = laptop.model_environment("secret")
            self.assertEqual(env["DETECTION_ENGINE"], "full")
            self.assertEqual(env["BATCH_SIZE"], "1")
            self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "")
            self.assertEqual(env["SEMANTIC_API_KEY"], "secret")
            self.assertEqual(os.environ["DETECTION_ENGINE"], "remote")

    def test_public_endpoint_must_require_authentication(self):
        info = {"protocol": 1, "mode": "embedding"}
        with patch.object(laptop, "api", return_value=info):
            with self.assertRaisesRegex(RuntimeError, "unauthenticated"):
                laptop.verify_model("https://example.test", "key")
        unauthorized = urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, None)
        with patch.object(laptop, "api", side_effect=[info, unauthorized]):
            self.assertEqual(laptop.verify_model("https://example.test", "key"), info)

    def test_failed_start_removes_stale_render_settings(self):
        (self.runtime / "render.env").write_text("old tunnel", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Install-LaptopTunnel"):
            laptop.serve()
        self.assertFalse((self.runtime / "render.env").exists())
        self.assertIn('"phase": "failed"', (self.runtime / "status.json").read_text())
        self.assertFalse(laptop.is_running())

    def test_export_does_not_replace_database_or_app_signing_key(self):
        text = laptop.render_settings("https://example.test", "model-secret")
        self.assertIn("DETECTION_ENGINE=remote\n", text)
        self.assertIn("SEMANTIC_API_KEY=model-secret\n", text)
        self.assertNotIn("DATABASE_URL", text)
        self.assertNotIn("\nSECRET_KEY=", text)

    def test_dns_fallback_is_scoped_to_https_quick_tunnel(self):
        failure = urllib.error.URLError(socket.gaierror("No such host"))
        with patch.object(laptop.urllib.request, "urlopen", side_effect=failure), \
                patch.object(laptop, "tunnel_api_with_public_dns", return_value={"status": "ready"}) as fallback:
            self.assertEqual(laptop.api("https://test.trycloudflare.com", "/health"), {"status": "ready"})
            self.assertEqual(fallback.call_args.args[0], "test.trycloudflare.com")
            fallback.reset_mock()
            for url in ["http://test.trycloudflare.com", "https://example.com", "http://127.0.0.1:8765"]:
                with self.assertRaises(urllib.error.URLError):
                    laptop.api(url, "/health")
            fallback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
