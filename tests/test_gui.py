"""
test_gui.py - Kiem thu giao dien PySide6 (SenderWindow).
"""

import importlib
import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER_DIR = os.path.join(BASE_DIR, "sender")


class TestGUISanity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _import_sender(self):
        for mod in ["network", "gui", "config", "protocol", "playfair", "caesar", "aes_cbc"]:
            sys.modules.pop(mod, None)
        receiver_dir = os.path.join(BASE_DIR, "receiver")
        if receiver_dir in sys.path:
            sys.path.remove(receiver_dir)
        if SENDER_DIR in sys.path:
            sys.path.remove(SENDER_DIR)
        sys.path.insert(0, SENDER_DIR)
        return importlib.import_module("gui").SenderWindow

    def test_sender_window_operations(self):
        SenderWindow = self._import_sender()
        window = SenderWindow()
        self.assertIsNotNone(window)

        # 1. Test Playfair
        window.algo_combo.setCurrentIndex(0)
        window.playfair_key_edit.setText("MONARCHY")
        window.plaintext_edit.setPlainText("HELLOPLAYFAIR")
        window.on_encrypt()
        self.assertTrue(len(window.ciphertext_view.toPlainText().strip()) > 0)
        self.assertIn("M  O  N  A  R", window.visual_view.toPlainText())

        # 2. Test Caesar
        window.algo_combo.setCurrentIndex(1)
        window.caesar_shift_spin.setValue(3)
        window.plaintext_edit.setPlainText("ABC")
        window.on_encrypt()
        self.assertEqual(window.ciphertext_view.toPlainText().strip(), "DEF")
        self.assertIn("k = 3", window.visual_view.toPlainText())

        # 3. Test AES-128-CBC
        window.algo_combo.setCurrentIndex(2)
        window.plaintext_edit.setPlainText("AES Secret Message")
        window.on_encrypt()
        self.assertTrue(len(window.ciphertext_view.toPlainText().strip()) > 0)
        self.assertIn("AES-128-CBC", window.visual_view.toPlainText())

        window.close()


if __name__ == "__main__":
    unittest.main()
