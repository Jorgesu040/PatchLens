import json
import sys
import unittest
from unittest.mock import MagicMock, patch

from model_tools import companion_set, main_set


class CompanionSetTests(unittest.TestCase):
    def test_shared_address_resolution_rejects_invalid_addresses_and_versions(self):
        self.assertIs(companion_set._resolve_address, main_set._resolve_address)
        program = MagicMock()
        program.getAddressFactory.return_value.getAddress.return_value = None
        with patch.object(main_set, "session", {"old": program}):
            with self.assertRaisesRegex(ValueError, "Dirección no válida"):
                companion_set.get_disassembly("old", "invalid", 1)
            with self.assertRaisesRegex(ValueError, "version"):
                companion_set.read_data("invalid", "00100000")

    def test_disassembly_honors_instruction_count(self):
        program = MagicMock()
        instructions = [MagicMock(), MagicMock(), MagicMock()]
        for instruction, text in zip(instructions, ["MOV", "RET", "NOP"]):
            instruction.toString.return_value = text
        program.getListing.return_value.getInstructions.return_value = iter(instructions)
        with patch.object(main_set, "session", {"old": program}):
            self.assertEqual(companion_set.get_disassembly("old", "00101000", 2), ["MOV", "RET"])
        with self.assertRaises(ValueError):
            companion_set.get_disassembly("old", "00101000", 0)

    def test_defined_data_java_value_is_serializable(self):
        program = MagicMock()
        data = program.getListing.return_value.getDataContaining.return_value
        value = MagicMock()
        value.__str__.return_value = "00103000"
        data.getValue.return_value = value
        data.getDataType.return_value.getName.return_value = "pointer"
        data.getLength.return_value = 8
        program.getMemory.return_value.getBlock.return_value = None
        with patch.object(main_set, "session", {"old": program}):
            result = companion_set.read_data("old", "00102000")
            json.dumps(result)
            self.assertEqual(result["value"], "00103000")
            value.toString.assert_not_called()
            self.assertIsNone(result["block_name"])
            data.getValue.return_value = "string converted by PyGhidra"
            self.assertEqual(companion_set.read_data("old", "00102000")["value"],
                             "string converted by PyGhidra")
            data.getValue.return_value = None
            self.assertIsNone(companion_set.read_data("old", "00102000")["value"])
            program.getListing.return_value.getDataContaining.return_value = None
            with self.assertRaisesRegex(ValueError, "No hay datos"):
                companion_set.read_data("old", "00102000")

    def test_read_memory_converts_signed_bytes_using_the_selected_flat_api(self):
        for version in ("old", "new"):
            with self.subTest(version=version):
                program = MagicMock()
                addr = program.getAddressFactory.return_value.getAddress.return_value
                addr.toString.return_value = "00102000"

                session = MagicMock()
                flat = session.flat_old if version == "old" else session.flat_new
                flat.getBytes.return_value = [65, 0, -1, 126]
                with patch.object(main_set, "session", {version: program}), \
                     patch.object(companion_set, "session", session):
                    result = companion_set.read_memory(version, "00102000", 4)
                flat.getBytes.assert_called_once_with(addr, 4)
                self.assertEqual(result, {
                    "version": version, "address": "00102000", "size": 4,
                    "hex": "41 00 ff 7e", "ascii": "A..~",
                })
                addr.addNoWrap.assert_called_once_with(3)
                program.getMemory.return_value.getAllInitializedAddressSet.return_value.contains.assert_called_once_with(
                    addr, addr.addNoWrap.return_value)
                json.dumps(result)
                program.getListing.assert_not_called()

    def test_read_memory_rejects_invalid_sizes_and_propagates_access_errors(self):
        for size in (0, -1):
            with self.assertRaisesRegex(ValueError, "size"):
                companion_set.read_memory("old", "00102000", size)
        program = MagicMock()
        session = MagicMock()
        session.flat_old.getBytes.side_effect = RuntimeError("MemoryAccessException")
        with patch.object(main_set, "session", {"old": program}), \
             patch.object(companion_set, "session", session):
            with self.assertRaisesRegex(RuntimeError, "MemoryAccessException"):
                companion_set.read_memory("old", "00102000", 4)

    def test_read_memory_rejects_uninitialized_ranges_before_reading(self):
        program = MagicMock()
        program.getMemory.return_value.getAllInitializedAddressSet.return_value.contains.return_value = False
        session = MagicMock()
        with patch.object(main_set, "session", {"old": program}), \
             patch.object(companion_set, "session", session):
            with self.assertRaisesRegex(ValueError, "sin inicializar"):
                companion_set.read_memory("old", "00102000", 4)
        session.flat_old.getBytes.assert_not_called()

    def test_memory_blocks_use_ghidra_size_method(self):
        block = MagicMock(spec=["getName", "getStart", "getEnd", "getSize", "isRead",
                                "isWrite", "isExecute", "isInitialized"])
        block.getName.return_value = ".text"
        block.getStart.return_value.toString.return_value = "00101000"
        block.getEnd.return_value.toString.return_value = "001010ff"
        block.getSize.return_value = 256
        for method in ("isRead", "isWrite", "isExecute", "isInitialized"):
            getattr(block, method).return_value = True
        program = MagicMock()
        program.getMemory.return_value.getBlocks.return_value = [block]
        with patch.object(companion_set, "session", {"new": program}):
            result = companion_set.list_memory_blocks("new")
        json.dumps(result)
        self.assertEqual(result[0]["size"], 256)
        self.assertNotIn("length", result[0])
        self.assertEqual(result[0]["start"], "00101000")
        self.assertEqual(result[0]["end"], "001010ff")

    def test_data_items_use_non_nullable_value_representation(self):
        program = MagicMock()
        data = MagicMock()
        data.getAddress.return_value.toString.return_value = "00102000"
        data.getDataType.return_value.getName.return_value = "string"
        data.getLength.return_value = 1
        data.getDefaultValueRepresentation.return_value = ""
        program.getListing.return_value.getDefinedData.return_value = [data]
        with patch.object(companion_set, "session", {"old": program}), \
             patch.dict(sys.modules, {"ghidra.program.model.address": MagicMock()}):
            result = companion_set.list_data_items("old")
        self.assertEqual(result, [{
            "address": "00102000", "type": "string", "size": 1, "value_repr": "",
        }])
        data.getValue.assert_not_called()

    def test_exports_use_java_to_string_and_allow_missing_symbols(self):
        program = MagicMock()
        address = MagicMock()
        address.toString.return_value = "00101000"
        symbols = program.getSymbolTable.return_value
        symbols.getExternalEntryPointIterator.side_effect = lambda: iter([address])
        symbol = symbols.getPrimarySymbol.return_value
        symbol.getName.return_value = "entry"
        symbol.getSymbolType.return_value.toString.return_value = "Function"
        function = program.getFunctionManager.return_value.getFunctionAt.return_value
        function.getSignature.return_value.getPrototypeString.return_value = "void entry(void)"
        with patch.object(companion_set, "session", {"new": program}):
            result = companion_set.list_exports("new")[0]
            self.assertEqual(result["address"], "00101000")
            self.assertEqual(result["symbol_type"], "Function")
            self.assertEqual(result["signature"], "void entry(void)")
            self.assertIsNone(result["data_type"])
            symbols.getPrimarySymbol.return_value = None
            program.getFunctionManager.return_value.getFunctionAt.return_value = None
            program.getListing.return_value.getDefinedDataAt.return_value = None
            result = companion_set.list_exports("new")[0]
        self.assertIsNone(result["name"])
        self.assertIsNone(result["symbol_type"])
        self.assertIsNone(result["signature"])
