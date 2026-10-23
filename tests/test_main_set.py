import sys
import unittest
from unittest.mock import MagicMock, patch

from model_tools import main_set


class MainSetErrorTests(unittest.TestCase):
    def test_missing_function_raises(self):
        program = MagicMock()
        program.getFunctionManager.return_value.getFunctionAt.return_value = None
        with patch.object(main_set, "session", {"old": program}):
            with self.assertRaisesRegex(ValueError, "No se encontró función"):
                main_set.get_function("old", "00101000")

    def test_missing_name_raises(self):
        session = MagicMock()
        session.flat_new.getGlobalFunctions.return_value = []
        with patch.object(main_set, "session", session):
            with self.assertRaisesRegex(ValueError, "No se encontró ninguna función"):
                main_set.get_function_by_name("new", "missing")

    def test_decompiler_failures_propagate_and_release_resources(self):
        for failure in ("open", "decompile", "missing_c"):
            with self.subTest(failure=failure):
                decompiler = MagicMock()
                decompiler.openProgram.return_value = failure != "open"
                decompiler.getLastMessage.return_value = "No se pudo abrir"
                result = decompiler.decompileFunction.return_value
                result.decompileCompleted.return_value = failure != "decompile"
                result.getErrorMessage.return_value = "No se pudo descompilar"
                result.getDecompiledFunction.return_value = None
                module = MagicMock()
                module.DecompInterface.return_value = decompiler
                with patch.object(main_set, "session", {"old": MagicMock()}), patch.dict(sys.modules, {
                    "ghidra.app.decompiler": module,
                    "ghidra.util.task": MagicMock(),
                }):
                    with self.assertRaises(RuntimeError):
                        main_set.get_function("old", "00101000")
                decompiler.dispose.assert_called_once()

    def test_invalid_reference_direction_raises(self):
        with patch.object(main_set, "session", {"old": MagicMock()}):
            with self.assertRaisesRegex(ValueError, "Dirección inválida"):
                main_set.get_references("old", "00101000", "invalid")
