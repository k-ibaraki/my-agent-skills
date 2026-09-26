"""jev_gate.py score（段階式採点）の単体テスト。"""

import json
import tempfile
import unittest

import jev_gate as g

FILE_TEXT = "\n".join(f"line {i}" for i in range(1, 101)) + "\n"
DIFF = (
    "diff --git a/src/app.py b/src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n"
    "@@ -10,2 +10,3 @@ def f():\n line 10\n+line 11\n line 12\n"
    "@@ -50,1 +51,2 @@\n line 51\n+line 52\n"
)
FINDING = {"id": "f1", "category": "Bug", "file": "src/app.py", "line": 11,
           "description": "secret-description", "reason": "secret-reason"}


def jev_answers(evidence="supported", ev_conf=0.95, severity=3.2, sev_conf=0.85):
    return {
        "model": "jev-1.13.0",
        "usage": {"input_tokens": 10, "output_tokens": 0},
        "answers": {
            "evidence": {"type": "choice", "choice": evidence, "confidence": ev_conf,
                         "probabilities": {evidence: 1.0}},
            "severity": {"type": "score", "score": severity, "confidence": sev_conf,
                         "probabilities": {}, "legend": {}},
        },
    }


class SnippetTest(unittest.TestCase):
    def test_numbers_lines_around_the_citation(self):
        s = g.extract_snippet(FILE_TEXT, 11, 11, radius=2)
        self.assertEqual(s.splitlines(), ["9: line 9", "10: line 10", "11: line 11", "12: line 12", "13: line 13"])

    def test_clamps_at_file_edges(self):
        self.assertTrue(g.extract_snippet(FILE_TEXT, 1, 1, radius=3).startswith("1: line 1"))

    def test_out_of_range_is_none(self):
        self.assertIsNone(g.extract_snippet(FILE_TEXT, 500, 500, radius=3))


class HunkTest(unittest.TestCase):
    def test_finds_hunk_covering_new_side_line(self):
        files, _ = g.split_diff(DIFF)
        self.assertIn("+line 11", g.find_hunk(files, "src/app.py", 11))
        self.assertIn("+line 52", g.find_hunk(files, "src/app.py", 52))
        self.assertIsNone(g.find_hunk(files, "src/app.py", 30))
        self.assertIsNone(g.find_hunk(files, "other.py", 11))


class RouteTest(unittest.TestCase):
    def route(self, **kw):
        return g.route_finding(jev_answers(**kw)["answers"])

    def test_confident_real_high_finding_is_settled_by_jev(self):
        self.assertEqual(self.route(), ("jev", 80))

    def test_everything_else_goes_to_scorer(self):
        for kw in [dict(ev_conf=0.75), dict(evidence="unsupported"), dict(evidence="contradicted"),
                   dict(severity=2.9), dict(sev_conf=0.7)]:
            self.assertEqual(self.route(**kw)[0], "scorer", kw)

    def test_jev_never_drops_a_finding(self):
        self.assertEqual(self.route(evidence="contradicted", ev_conf=0.99, severity=0.0, sev_conf=0.99)[0],
                         "scorer")


class RunScoreTest(unittest.TestCase):
    def run_score(self, findings, post, key="k", files=None):
        files = {"src/app.py": FILE_TEXT} if files is None else files
        return g.run_score(findings=findings, diff=DIFF, get_file=files.get, post=post, api_key=key)

    def test_settled_finding_carries_score(self):
        out = self.run_score([FINDING], lambda p: jev_answers())
        r = out["results"][0]
        self.assertEqual((r["id"], r["route"], r["score"]), ("f1", "jev", 80))

    def test_scorer_route_gets_wider_context(self):
        out = self.run_score([FINDING], lambda p: jev_answers(evidence="unsupported"))
        r = out["results"][0]
        self.assertEqual(r["route"], "scorer")
        self.assertIn("51: line 51", r["context"]["code"])
        self.assertIn("+line 11", r["context"]["hunk"])

    def test_jev_sees_narrow_snippet_only(self):
        seen = []
        self.run_score([FINDING], lambda p: seen.append(p) or jev_answers())
        code = seen[0]["state"]["code"]
        self.assertIn("11: line 11", code)
        self.assertNotIn("40: line 40", code)

    def test_finding_without_line_skips_jev(self):
        calls = []
        f = {"id": "f2", "category": "Issue: scope", "file": None, "line": None, "description": "d", "reason": "r"}
        out = self.run_score([f], lambda p: calls.append(p) or jev_answers())
        self.assertEqual(out["results"][0]["route"], "scorer")
        self.assertEqual(calls, [])

    def test_missing_cited_file_goes_to_scorer(self):
        out = self.run_score([FINDING], lambda p: jev_answers(), files={})
        r = out["results"][0]
        self.assertEqual(r["route"], "scorer")
        self.assertIn("見つからない", r["note"])

    def test_no_key_or_api_error_routes_all_to_scorer(self):
        out = self.run_score([FINDING], lambda p: jev_answers(), key=None)
        self.assertEqual(out["status"], "unavailable")
        self.assertEqual(out["results"][0]["route"], "scorer")

        def boom(_):
            raise g.GateError("HTTP 529")

        out = self.run_score([FINDING], boom)
        self.assertEqual(out["status"], "unavailable")
        self.assertEqual(out["results"][0]["route"], "scorer")
        self.assertIn("+line 11", out["results"][0]["context"]["hunk"])

    def test_evidence_refs_reach_jev_and_scorer(self):
        seen = []
        f = dict(FINDING, evidence_refs=[{"file": "infra/waf.tf", "start_line": 5, "line": 6}])
        files = {"src/app.py": FILE_TEXT, "infra/waf.tf": FILE_TEXT}
        out = self.run_score([f], lambda p: seen.append(p) or jev_answers(evidence="unsupported"), files=files)
        related = seen[0]["state"]["related_code"]
        self.assertEqual(related[0]["file"], "infra/waf.tf")
        self.assertIn("6: line 6", related[0]["code"])
        self.assertNotIn("40: line 40", related[0]["code"])
        r = out["results"][0]
        self.assertEqual(r["refs"], 1)
        self.assertIn("40: line 40", r["context"]["related"][0]["code"])

    def test_missing_ref_is_skipped_and_primary_still_asked(self):
        seen = []
        f = dict(FINDING, evidence_refs=[{"file": "gone.tf", "line": 3}])
        out = self.run_score([f], lambda p: seen.append(p) or jev_answers())
        self.assertNotIn("related_code", seen[0]["state"])
        self.assertEqual((out["results"][0]["route"], out["results"][0]["refs"]), ("jev", 0))

    def test_refs_are_capped(self):
        seen = []
        refs = [{"file": "src/app.py", "line": n} for n in (20, 30, 40)]
        self.run_score([dict(FINDING, evidence_refs=refs)], lambda p: seen.append(p) or jev_answers())
        self.assertEqual(len(seen[0]["state"]["related_code"]), g.MAX_EVIDENCE_REFS)

    def test_log_has_no_finding_text_or_paths(self):
        out = self.run_score([FINDING], lambda p: jev_answers())
        with tempfile.TemporaryDirectory() as d:
            path = g.append_score_log(out, run_id="r1", state_dir=d)
            with open(path) as fh:
                text = fh.read()
        rec = json.loads(text)
        self.assertEqual(rec["type"], "score")
        self.assertEqual(rec["findings"][0]["route"], "jev")
        for secret in ("secret-description", "secret-reason", "src/app.py", "line 11"):
            self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
