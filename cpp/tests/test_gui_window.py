"""Construct the real Qt window and exercise Q1-Q4 against the compiled CLI.

Missing PySide6 returns 77 (CTest: skipped), never a successful GUI test.
--require-qt makes missing Qt an error for the dedicated GUI CI job.
Map HTML is captured before navigation so these tests need no tile/CDN network.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--require-qt", action="store_true")
    args = parser.parse_args()
    if importlib.util.find_spec("PySide6") is None:
        print("SKIP: PySide6 is not installed; GUI was NOT exercised.", flush=True)
        return 1 if args.require_qt else 77

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Import failures with an installed Qt must fail, not become skips.
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QComboBox
    from shiboken6 import delete
    from python.gui import app as gui

    application = QApplication.instance() or QApplication([])

    class WindowTests(unittest.TestCase):
        def setUp(self):
            self.window = gui.MainWindow()
            self.addCleanup(self.close_window)
            self.window.show()
            application.processEvents()

        def close_window(self):
            window = self.window
            if window.worker is not None:
                self.assertTrue(window.worker.wait(10000), "Backend worker did not stop")
                application.processEvents()
            if window.result_dialog is not None:
                window.result_dialog.close()
            window.close()
            # No application.exec() here: explicitly destroy native WebEngine
            # children instead of leaving deferred deletion for interpreter exit.
            delete(window)
            application.processEvents()

        def test_construct_all_four_forms(self):
            window = self.window
            expected = {
                "q1": {"from", "to", "max_connections"},
                "q2": {"from", "via_b", "via_c", "to"},
                "q3": {"round_trip"},
                "q4": {"meeting_a", "meeting_b", "meeting_c"},
            }
            self.assertEqual(window.form_stack.count(), 4)
            self.assertEqual(set(window.inputs), set(expected))
            self.assertEqual(len(window.city_rows), 12)
            for index, (question, keys) in enumerate(expected.items()):
                with self.subTest(question=question):
                    self.assertEqual(set(window.inputs[question]), keys)
                    window.nav_buttons[index].click()
                    self.assertEqual(window.selected_question, question)
                    self.assertEqual(window.form_stack.currentIndex(), index)
                    for widget in window.inputs[question].values():
                        if isinstance(widget, QComboBox):
                            self.assertEqual(widget.count(), 12)
                            self.assertTrue(widget.currentText())
            self.assertEqual(window.inputs["q1"]["max_connections"].value(), 3)

        def test_dataset_error_then_recovery(self):
            window = self.window
            with patch.object(gui, "read_cities", side_effect=ValueError("bad data")):
                window.load_dataset()
            self.assertFalse(window.search_button.isEnabled())
            self.assertEqual(window.city_rows, [])
            self.assertIn("bad data", window.status.text())
            window.load_dataset()
            self.assertEqual(len(window.city_rows), 12)
            self.assertTrue(window.search_button.isEnabled())

        def test_searches_worker_results_and_map_ownership(self):
            window = self.window
            rendered = []
            def capture_html(source, _base_url):
                rendered.append(source)

            # Keep the real WebEngine widget and dialog ownership; prevent web loads.
            with patch.object(gui, "find_executable", return_value=args.executable.resolve()):
                if window.map_view is not None:
                    context = patch.object(window.map_view, "setHtml", side_effect=capture_html)
                else:
                    from contextlib import nullcontext
                    context = nullcontext()
                with context:
                    for index, question in enumerate(("q1", "q2", "q3", "q4")):
                        with self.subTest(question=question):
                            window.nav_buttons[index].click()
                            window.search_button.click()
                            self.assertIsNotNone(window.worker)
                            self.assertFalse(window.dataset.isEnabled())
                            deadline = time.monotonic() + 15
                            while window.worker is not None and time.monotonic() < deadline:
                                QTest.qWait(10)
                            self.assertIsNone(window.worker, "Search did not finish")
                            result = json.loads(window.output.toPlainText())
                            self.assertEqual(result["query"], question)
                            self.assertEqual(result["status"], "found")
                            self.assertIn("search complete", window.status.text())
                            window.details_button.click()
                            self.assertTrue(window.output.isVisible())
                            self.assertEqual(json.loads(window.output.toPlainText()), result)
                            if window.map_view is not None:
                                self.assertIn("leaflet", rendered[-1].lower())
                                dialog = window.result_dialog
                                self.assertIsNotNone(dialog)
                                self.assertIs(window.map_view.parent(), dialog)
                                self.assertFalse(window.search_button.isEnabled())
                                dialog.close()
                                application.processEvents()
                                self.assertIsNone(window.result_dialog)
                                self.assertGreaterEqual(window.map_holder.indexOf(window.map_view), 0)
                            else:
                                self.assertIn("Map unavailable", window.map_blank.text())
                            self.assertTrue(window.search_button.isEnabled())
                            self.assertTrue(window.dataset.isEnabled())
                            window.change_question(question)
                            self.assertEqual(window.output.toPlainText(), "")
                            self.assertFalse(window.output.isVisible())
                            self.assertIn("Run a search", window.map_blank.text())

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WindowTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
