"""Ciclo de vida de los programas, sin arrancar una JVM."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from model_tools import GhidraSession, session


class GhidraSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project_file = Path(self.directory.name) / "test.gpr"
        self.project_file.touch()
        self.events = []
        self.programs = {"/old": MagicMock(), "/new": MagicMock()}
        self.consumers = {"/old": object(), "/new": object()}
        for path, program in self.programs.items():
            program.release.side_effect = lambda consumer, path=path: self.events.append(path)
        self.api = MagicMock()
        self.api.started.return_value = False
        self.api.open_project.return_value.close.side_effect = lambda: self.events.append("project")

        def consume_program(project, path):
            return self.programs[path], self.consumers[path]

        self.api.consume_program.side_effect = consume_program
        self.flat_module = MagicMock()
        self.modules = patch.dict(sys.modules, {
            "pyghidra": self.api,
            "ghidra.program.flatapi": self.flat_module,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.addCleanup(session.close)

    def open(self, new="/new"):
        return session.open(self.project_file, "/old", new, "/ghidra")

    def test_access_and_close_order(self):
        self.open()
        self.assertIs(session.old, self.programs["/old"])
        self.assertIs(session["new"], self.programs["/new"])
        self.assertIsNotNone(session.flat_old)
        self.api.start.assert_called_once_with(install_dir="/ghidra")
        with self.assertRaises(KeyError):
            session["C"]
        session.close()
        self.programs["/old"].release.assert_called_once_with(self.consumers["/old"])
        self.programs["/new"].release.assert_called_once_with(self.consumers["/new"])
        self.assertEqual(self.events, ["/new", "/old", "project"])
        self.assertIsNone(session.old)
        with self.assertRaises(RuntimeError):
            session["old"]
        session.close()
        self.assertEqual(len(self.events), 3)

    def test_missing_new_releases_old_and_project(self):
        with self.assertRaises(KeyError):
            self.open("/missing")
        self.assertEqual(self.events, ["/old", "project"])
        self.assertIsNone(session.old)
        self.open()
        self.assertIs(session.new, self.programs["/new"])

    def test_release_failure_still_closes_old_and_project(self):
        self.open()

        def fail_release(consumer):
            self.events.append("/new")
            raise ValueError("release")

        self.programs["/new"].release.side_effect = fail_release
        with self.assertRaisesRegex(ValueError, "release"):
            session.close()
        self.assertEqual(self.events, ["/new", "/old", "project"])
        self.assertIsNone(session.old)

    def test_existing_jvm_and_repeated_open(self):
        self.api.started.return_value = True
        self.open()
        with self.assertRaises(RuntimeError):
            self.open()
        self.assertIs(session.old, self.programs["/old"])
        self.api.open_project.assert_called_once()
        self.api.start.assert_not_called()

    def test_main_set_and_constructor_share_instance(self):
        from model_tools import main_set

        self.assertIs(GhidraSession(), session)
        self.assertIs(main_set.session, session)


if __name__ == "__main__":
    unittest.main()
