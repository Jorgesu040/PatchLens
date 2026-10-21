import copy
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from AI import analyze_report
from Main import find_report, main, run_ghidriff
from parser.NormalizerEngine import find_conflicts, merge_changes, normalize_record, link_conflicts
from GridriffParser import ENGINES, parse_reports


FIXTURES = Path(__file__).parent / "fixtures" / "tienda"


def function(address, code="return 1;"):
    return {"name": f"fn_{address}", "address": address, "code": code}


def change(kind, old=None, new=None, engine="SimpleDiff", index=0):
    raw = {"old": old, "new": new, "diff_type": ["code"]} if kind == "modified" else (
        new if kind == "added" else old
    )
    return normalize_record(kind, raw, engine, index)


class MultimotorTests(unittest.TestCase):
    def setUp(self):
        self.reports = {engine: FIXTURES / f"{engine}.json" for engine in ENGINES}

    def test_real_outputs_are_grouped_and_conflicts_linked_both_ways(self):
        result = parse_reports(self.reports)
        self.assertEqual(len(result["changes"]), 7)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(sum(len(c["sources"]) for c in result["changes"]), 14)
        self.assertTrue(all(set(a) == {"report", "stats"} for a in result["analyses"].values()))
        conflict = result["conflicts"][0]
        self.assertEqual(conflict["type"], "added_vs_modified")
        by_id = {c["change_id"]: c for c in result["changes"]}
        implicated = [by_id[change_id] for change_id in conflict["change_ids"]]
        self.assertNotIn("change_indices", conflict)
        self.assertEqual({c["type"] for c in implicated}, {"added", "modified"})
        self.assertEqual({c["change_id"] for c in implicated}, set(conflict["change_ids"]))
        for record in implicated:
            self.assertIn(conflict["conflict_id"], record["conflict_ids"])
        added = next(c for c in implicated if c["type"] == "added")
        self.assertEqual(len(added["sources"]), 2)
        self.assertEqual(len({s["analysis"] for s in added["sources"]}), 2)

    def test_every_source_points_to_the_original_record(self):
        result = parse_reports(self.reports)
        originals = {engine: json.loads(path.read_text()) for engine, path in self.reports.items()}
        for record in result["changes"]:
            for source in record["sources"]:
                group, index = source["json_path"].removeprefix("$.functions.").rstrip("]").split("[")
                raw = originals[source["analysis"]]["functions"][group][int(index)]
                for side, raw_side in (("old_function", "old"), ("new_function", "new")):
                    if record[side] is None:
                        continue
                    self.assertNotIn("function_variants", source)
                    exported = record[side]
                    expected = raw[raw_side] if group == "modified" else raw
                    self.assertEqual(exported["address"], expected["address"])
                    self.assertEqual(exported["code"], expected["code"])
                    for field in ("called", "calling"):
                        if field in expected:
                            self.assertEqual(exported[field], expected[field])
                    self.assertNotIn("callees", exported)
                    self.assertNotIn("callers", exported)

    def test_incompatible_or_missing_hash_is_rejected(self):
        original = json.loads(self.reports[ENGINES[0]].read_text())
        for field, value in (("Executable SHA256", "different"), ("Executable SHA256", None)):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                report = copy.deepcopy(original)
                report["new_meta"][field] = value
                path = Path(directory) / "incompatible.json"
                path.write_text(json.dumps(report))
                with self.assertRaises(ValueError):
                    parse_reports({ENGINES[0]: self.reports[ENGINES[0]], ENGINES[1]: path})

    def test_unknown_engine_and_empty_input_are_rejected(self):
        for reports in ({}, {"TypoDiff": self.reports[ENGINES[0]]}):
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                parse_reports(reports)

    def test_ai_forwards_multimotor_report_without_network(self):
        report = parse_reports(self.reports)
        adapter = MagicMock()
        adapter.generate.return_value = "informe simulado"
        self.assertEqual(analyze_report(report, adapter), "informe simulado")
        # JSON serializa las claves-tupla de los conflictos como listas.
        self.assertEqual(json.loads(adapter.generate.call_args.args[0]), json.loads(json.dumps(report)))

class NormalizerTests(unittest.TestCase):
    def test_union_preserves_order_provenance_and_input(self):
        first = change("modified", function("10"), function("20"), index=0)
        second = copy.deepcopy(first)
        second["aspects"] = ["length", "code"]
        second["sources"][0]["json_path"] = "$.functions.modified[1]"
        second["sources"][0]["aspects"] = ["length", "code"]
        inputs = [first, second, copy.deepcopy(second)]
        before = copy.deepcopy(inputs)
        merged = merge_changes(inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["aspects"], ["code", "length"])
        self.assertEqual(len(merged[0]["sources"]), 2)
        self.assertEqual(merged[0]["sources"][0]["aspects"], ["code"])

    def test_different_exports_raise_without_mutating_inputs(self):
        first = change("deleted", old=function("10"), engine=ENGINES[0])
        second = change("deleted", old=function("10", ""), engine=ENGINES[1])
        records = [first, second]
        before = copy.deepcopy(records)
        with self.assertRaisesRegex(ValueError, "Exportaciones distintas"):
            merge_changes(records)
        self.assertEqual(records, before)

    def test_only_normalize_record_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            normalize_record("unknown", function("10"), "SimpleDiff", 0)

    def test_match_types_are_copied_without_duplicates(self):
        raw = {"old": function("10"), "new": function("20"),
               "diff_type": ["code"], "match_types": ["FullName:Param", "FullName:Param"]}
        result = normalize_record("modified", raw, "SimpleDiff", 0)
        self.assertEqual(result["sources"][0]["match_types"], ["FullName:Param"])
        result["sources"][0]["match_types"].append("other")
        self.assertEqual(raw["match_types"], ["FullName:Param", "FullName:Param"])

    def test_old_and_new_can_differ_in_length(self):
        old, new = function("10"), function("20")
        old["length"], new["length"] = 10, 30
        first = change("modified", old, new)
        result = merge_changes([first, copy.deepcopy(first)])
        self.assertEqual(result[0]["old_function"]["length"], 10)
        self.assertEqual(result[0]["new_function"]["length"], 30)

    def test_link_conflicts_publishes_ids_instead_of_indices(self):
        records = [change("modified", function("10"), function("20")),
                   change("added", new=function("20"))]
        conflicts = find_conflicts(records)
        link_conflicts(records, conflicts)
        self.assertNotIn("change_indices", conflicts[0])
        self.assertEqual(conflicts[0]["change_ids"], ["change_0001", "change_0000"])
        self.assertTrue(all(c["conflict_ids"] == ["conflict_0000"] for c in records))

    def test_all_classification_combinations(self):
        modified = change("modified", function("10"), function("20"))
        added = change("added", new=function("20"))
        deleted = change("deleted", old=function("10"))
        cases = [([modified, added], "added_vs_modified"),
                 ([modified, deleted], "deleted_vs_modified"),
                 ([modified, added, deleted], "added_modified_deleted")]
        for records, expected in cases:
            before = copy.deepcopy(records)
            with self.subTest(expected=expected):
                conflicts = find_conflicts(records)
                self.assertEqual([c["type"] for c in conflicts], [expected])
                self.assertEqual(set(conflicts[0]["change_indices"]), set(range(len(records))))
                self.assertEqual(records, before)
        self.assertEqual(find_conflicts([added, deleted]), [])

    def test_ambiguous_correspondences(self):
        cases = [
            ([change("modified", function("10"), function("20")),
              change("modified", function("10"), function("30"))], "same_old_to_multiple_new"),
            ([change("modified", function("10"), function("20")),
              change("modified", function("30"), function("20"))], "multiple_old_to_same_new"),
        ]
        for records, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual([c["type"] for c in find_conflicts(records)], [expected])
        self.assertEqual(find_conflicts([change("added", new=function("10")),
                                         change("modified", function("10"), function("20"))]), [])


class RunnerTests(unittest.TestCase):
    def test_main_runs_three_engines_and_parses_once(self):
        reports = [FIXTURES / f"{engine}.json" for engine in ENGINES]
        with patch("sys.argv", ["Main.py", "old", "new", "--project-name", "test"]), \
             patch("Main.run_ghidriff", side_effect=[Path(engine) for engine in ENGINES]) as run, \
             patch("Main.find_report", side_effect=reports), \
             patch("Main.parse_reports", wraps=parse_reports) as parse, \
             patch("Main.Path.write_text") as write, patch("builtins.print"):
            result = main()
        self.assertEqual([c.args[3] for c in run.call_args_list], list(ENGINES))
        parse.assert_called_once_with(dict(zip(ENGINES, reports)))
        self.assertEqual(len(result["changes"]), 7)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(json.loads(write.call_args.args[0]), json.loads(json.dumps(result)))

    def test_main_stops_if_an_engine_fails(self):
        with patch("sys.argv", ["Main.py", "old", "new", "--project-name", "test"]), \
             patch("Main.run_ghidriff", side_effect=[Path("first"), subprocess.CalledProcessError(1, "ghidriff")]) as run, \
             patch("Main.find_report", return_value=FIXTURES / "VersionTrackingDiff.json"), \
             patch("Main.parse_reports") as parse, patch("Main.Path.write_text") as write, \
             patch("builtins.print"):
            with self.assertRaises(subprocess.CalledProcessError):
                main()
        self.assertEqual(run.call_count, 2)
        parse.assert_not_called()
        write.assert_not_called()

    def test_does_not_select_an_unrelated_json(self):
        with tempfile.TemporaryDirectory() as directory:
            json_dir = Path(directory) / "json"
            json_dir.mkdir()
            (json_dir / "unrelated.ghidriff.json").write_text("{}")
            with self.assertRaises(FileNotFoundError):
                find_report(directory, "old", "new")
            expected = json_dir / "old-new.ghidriff.json"
            expected.write_text("{}")
            self.assertEqual(find_report(directory, "old", "new"), expected)

    def test_unique_run_directories_engine_and_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / "old", root / "new"
            old.touch()
            new.touch()
            with patch("Main.shutil.which", return_value="/test/ghidriff"), \
                 patch("Main.subprocess.run") as run, \
                 patch("Main.tempfile.mkdtemp", side_effect=[str(root / "first"), str(root / "second")]), \
                 patch("Main.Path.mkdir"):
                first = run_ghidriff(old, new, "test", "SimpleDiff", 12)
                second = run_ghidriff(old, new, "test", "SimpleDiff", 12)
            self.assertNotEqual(first, second)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--engine") + 1], "SimpleDiff")
            self.assertEqual(command[command.index("-o") + 1], str(second))
            self.assertEqual(run.call_args.kwargs, {"check": True, "timeout": 12})

    def test_invalid_arguments_do_not_launch_ghidriff(self):
        with tempfile.TemporaryDirectory() as directory, patch("Main.subprocess.run") as run:
            binary = Path(directory) / "bin"
            binary.touch()
            for engine, timeout in (("unknown", 12), ("SimpleDiff", 0)):
                with self.subTest(engine=engine, timeout=timeout), self.assertRaises(ValueError):
                    run_ghidriff(binary, binary, "test", engine, timeout)
            with self.assertRaises(FileNotFoundError):
                run_ghidriff(binary, binary.parent / "missing", "test")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
