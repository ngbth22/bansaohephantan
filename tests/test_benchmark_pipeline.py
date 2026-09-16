"""
test_benchmark_pipeline.py - Kiem thu logic tu dong nhan dien che do self-test / remote trong run_benchmark.py.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, "benchmark")
import run_benchmark


class TestBenchmarkAutoDetection(unittest.TestCase):
    """Kiem thu co che tu dong phat hien che do self-test vs remote."""

    @patch("run_benchmark.client.run_benchmark")
    @patch("run_benchmark.analyze")
    @patch("run_benchmark.threading.Thread")
    def test_autodetect_local_default(self, mock_thread, mock_analyze, mock_client):
        """Khi khong truyen hoac truyen 127.0.0.1, tu dong bat server noi bo (self-test)."""
        mock_analyze.load_and_validate.return_value = MagicMock()
        mock_analyze.compute_statistics.return_value = (MagicMock(), MagicMock())

        run_benchmark.run_full_pipeline(host="127.0.0.1", results_dir="test_results_dummy")

        self.assertTrue(mock_thread.called)
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        self.assertEqual(kwargs.get("host"), "127.0.0.1")

    @patch("run_benchmark.client.run_benchmark")
    @patch("run_benchmark.analyze")
    @patch("run_benchmark.perform_ping_test")
    @patch("run_benchmark.threading.Thread")
    def test_autodetect_remote_ip(self, mock_thread, mock_ping, mock_analyze, mock_client):
        """Khi truyen IP tu xa, khong bat server noi bo va tu dong chuyen sang remote."""
        mock_analyze.load_and_validate.return_value = MagicMock()
        mock_analyze.compute_statistics.return_value = (MagicMock(), MagicMock())

        run_benchmark.run_full_pipeline(host="192.168.1.100", results_dir="test_results_dummy")

        self.assertFalse(mock_thread.called)
        mock_ping.assert_called_once_with("192.168.1.100", count=10)
        args, kwargs = mock_client.call_args
        self.assertEqual(kwargs.get("host"), "192.168.1.100")

    @patch("run_benchmark.client.run_benchmark")
    @patch("run_benchmark.analyze")
    @patch("run_benchmark.perform_ping_test")
    @patch("run_benchmark.threading.Thread")
    def test_force_remote_override_local_ip(self, mock_thread, mock_ping, mock_analyze, mock_client):
        """Khi truyen 127.0.0.1 nhung is_local=False (co flag --remote), khong bat server noi bo."""
        mock_analyze.load_and_validate.return_value = MagicMock()
        mock_analyze.compute_statistics.return_value = (MagicMock(), MagicMock())

        run_benchmark.run_full_pipeline(
            host="127.0.0.1",
            results_dir="test_results_dummy",
            is_local=False,
        )

        self.assertFalse(mock_thread.called)
        mock_ping.assert_called_once_with("127.0.0.1", count=10)


if __name__ == "__main__":
    unittest.main()
