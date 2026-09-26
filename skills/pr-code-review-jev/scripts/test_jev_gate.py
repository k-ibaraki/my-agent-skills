"""jev_gate.py の単体テスト。HTTP・キーチェーン・gh はすべて差し替えて動かす。

実行: python3 -m unittest discover -s <このディレクトリ>
"""

import json
import os
import tempfile
import unittest
from unittest import mock

import jev_gate as g


def file_diff(path, body_lines, new=False):
    head = [f"diff --git a/{path} b/{path}"]
    if new:
        head += ["new file mode 100644", "--- /dev/null", f"+++ b/{path}"]
    else:
        head += [f"--- a/{path}", f"+++ b/{path}"]
    return "\n".join(head + ["@@ -1,3 +1,3 @@"] + body_lines) + "\n"


MODIFIED = file_diff("src/app.py", [" ctx", "-old = 1", "+new = 2", " ctx"])
ADDED = file_diff("src/new.py", ["+print('hi')"], new=True)
LOCK = file_diff("package-lock.json", ["-a", "+b"])
BINARY = "diff --git a/img.png b/img.png\nBinary files a/img.png and b/img.png differ\n"


def answers_for(questions, value):
    return {qid: {"type": "noul", "noul": value} for qid in questions}


def fake_post(value_by_qid=None, default=0.0):
    """質問 id ごとに固定値を返す偽の API。呼び出しを記録する。"""
    calls = []

    def post(payload):
        calls.append(payload)
        ans = {}
        for qid in payload["questions"]:
            v = (value_by_qid or {}).get(qid, default)
            ans[qid] = {"type": "noul", "noul": v}
        return {"model": "jev-1.13.0", "answers": ans, "usage": {"input_tokens": 100, "output_tokens": 0}}

    post.calls = calls
    return post


class SplitDiffTest(unittest.TestCase):
    def test_splits_per_file_and_excludes_noise(self):
        files, excluded = g.split_diff(MODIFIED + LOCK + BINARY + ADDED)
        self.assertEqual([f.path for f in files], ["src/app.py", "src/new.py"])
        self.assertEqual(sorted(excluded), ["img.png", "package-lock.json"])

    def test_detects_new_files_and_removed_lines(self):
        files, _ = g.split_diff(MODIFIED + ADDED)
        app, new = files
        self.assertFalse(app.is_new)
        self.assertTrue(app.removes_lines)
        self.assertTrue(new.is_new)
        self.assertFalse(new.removes_lines)
        self.assertEqual(app.changed_lines, 2)


class RulesTest(unittest.TestCase):
    def test_history_runs_only_when_existing_lines_change(self):
        files, _ = g.split_diff(ADDED)
        self.assertFalse(g.decide_rules(files)["history"]["run"])
        files, _ = g.split_diff(MODIFIED)
        self.assertTrue(g.decide_rules(files)["history"]["run"])

    def test_size_runs_on_many_files_or_many_lines(self):
        small, _ = g.split_diff(MODIFIED)
        self.assertFalse(g.decide_rules(small)["size"]["run"])
        many = "".join(file_diff(f"f{i}.py", ["+x"], new=True) for i in range(g.SIZE_MIN_FILES))
        files, _ = g.split_diff(many)
        self.assertTrue(g.decide_rules(files)["size"]["run"])
        long = file_diff("big.py", ["+x"] * g.SIZE_MIN_LINES, new=True)
        files, _ = g.split_diff(long)
        self.assertTrue(g.decide_rules(files)["size"]["run"])


class PlanTest(unittest.TestCase):
    def test_small_diff_goes_in_one_request(self):
        files, _ = g.split_diff(MODIFIED + ADDED)
        plan = g.plan_requests(files, "title", claude_md="")
        self.assertEqual(plan.mode, "single")
        self.assertEqual(len(plan.states), 1)
        self.assertIn("src/new.py", plan.states[0]["diff"])

    def test_large_diff_is_split_per_file(self):
        big = "x" * (g.TOKEN_BUDGET * g.BYTES_PER_TOKEN // 2 + 10)
        diff = file_diff("a.py", [f"+{big}"]) + file_diff("b.py", [f"+{big}"])
        files, _ = g.split_diff(diff)
        plan = g.plan_requests(files, "title", claude_md="")
        self.assertEqual(plan.mode, "per_file")
        self.assertEqual([s["file"] for s in plan.states], ["a.py", "b.py"])

    def test_single_file_over_budget_is_split_by_hunk(self):
        big = "x" * (g.TOKEN_BUDGET * g.BYTES_PER_TOKEN // 2 + 10)
        body = ["@@ -1 +1 @@", f"+{big}", "@@ -9 +9 @@", f"+{big}"]
        diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n" + "\n".join(body) + "\n"
        files, _ = g.split_diff(diff)
        plan = g.plan_requests(files, "title", claude_md="")
        self.assertEqual(len(plan.states), 2)
        self.assertEqual(plan.oversized, [])

    def test_hunk_over_budget_is_reported_not_sent(self):
        huge = "x" * (g.TOKEN_BUDGET * g.BYTES_PER_TOKEN + 10)
        files, _ = g.split_diff(file_diff("a.py", [f"+{huge}"]))
        plan = g.plan_requests(files, "title", claude_md="")
        self.assertEqual(plan.states, [])
        self.assertEqual(plan.oversized, ["a.py"])


class QuestionsTest(unittest.TestCase):
    def test_claude_md_question_only_when_rules_exist(self):
        self.assertFalse(any(q.startswith("claude_md") for q in g.build_questions("")))
        qs = g.build_questions("Use tabs.")
        self.assertIn("Use tabs.", json.dumps(qs["claude_md__violates_rule"]))

    def test_every_question_maps_to_a_gated_perspective(self):
        for qid in g.build_questions("rule"):
            self.assertIn(qid.split("__")[0], g.PERSPECTIVES)


class RunGateTest(unittest.TestCase):
    def run_gate(self, diff, post, key="k", claude_md="rule"):
        return g.run_gate(diff=diff, title="t", claude_md=claude_md, post=post, api_key=key)

    def test_missing_key_runs_everything(self):
        post = fake_post()
        out = self.run_gate(MODIFIED, post, key=None)
        self.assertEqual(out["status"], "unavailable")
        self.assertTrue(all(p["run"] for p in out["perspectives"].values()))
        self.assertEqual(post.calls, [])

    def test_api_failure_runs_everything(self):
        def post(_):
            raise g.GateError("HTTP 401")

        out = self.run_gate(MODIFIED, post)
        self.assertEqual(out["status"], "unavailable")
        self.assertIn("401", out["reason"])
        self.assertTrue(all(p["run"] for p in out["perspectives"].values()))

    def test_low_scores_skip_and_high_scores_run(self):
        post = fake_post({"design__security": 0.9})
        out = self.run_gate(MODIFIED, post)
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["perspectives"]["design"]["run"])
        self.assertFalse(out["perspectives"]["approach"]["run"])
        self.assertAlmostEqual(out["perspectives"]["design"]["score"], 0.9)

    def test_perspective_takes_max_over_requests(self):
        big = "x" * (g.TOKEN_BUDGET * g.BYTES_PER_TOKEN // 2 + 10)
        diff = file_diff("a.py", [f"+{big}"]) + file_diff("b.py", [f"+{big}"])
        def post(payload):
            v = 0.8 if payload["state"]["file"] == "b.py" else 0.05
            return {"model": "jev-1.13.0", "answers": answers_for(payload["questions"], v),
                    "usage": {"input_tokens": 1, "output_tokens": 0}}

        out = self.run_gate(diff, post)
        self.assertEqual(out["mode"], "per_file")
        self.assertAlmostEqual(out["perspectives"]["approach"]["score"], 0.8)
        self.assertEqual(out["perspectives"]["approach"]["top_file"], "b.py")

    def test_no_claude_md_skips_that_perspective_by_rule(self):
        out = self.run_gate(MODIFIED, fake_post(default=0.99), claude_md="")
        self.assertFalse(out["perspectives"]["claude_md"]["run"])
        self.assertIn("CLAUDE.md", out["perspectives"]["claude_md"]["reason"])

    def test_oversized_hunk_forces_run(self):
        huge = "x" * (g.TOKEN_BUDGET * g.BYTES_PER_TOKEN + 10)
        out = self.run_gate(file_diff("a.py", [f"+{huge}"]), fake_post())
        self.assertTrue(all(p["run"] for p in out["perspectives"].values()))
        self.assertIn("a.py", out["perspectives"]["design"]["reason"])

    def test_pins_model(self):
        post = fake_post()
        self.run_gate(MODIFIED, post)
        self.assertEqual(post.calls[0]["model"], g.MODEL)


class HttpTest(unittest.TestCase):
    def test_retries_on_429_then_succeeds(self):
        responses = [g.HttpResult(429, b"{}", {}), g.HttpResult(200, b'{"answers": {}}', {})]
        send = mock.Mock(side_effect=responses)
        with mock.patch.object(g.time, "sleep"):
            body = g.post_with_retry({"q": 1}, "key", send=send)
        self.assertEqual(body, {"answers": {}})
        self.assertEqual(send.call_count, 2)

    def test_does_not_retry_on_401(self):
        send = mock.Mock(return_value=g.HttpResult(401, b"{}", {}))
        with self.assertRaises(g.GateError) as ctx:
            g.post_with_retry({}, "key", send=send)
        self.assertIn("401", str(ctx.exception))
        self.assertEqual(send.call_count, 1)

    def test_error_message_never_contains_key(self):
        send = mock.Mock(return_value=g.HttpResult(401, b'{"detail":"bad key secret-123"}', {}))
        with self.assertRaises(g.GateError) as ctx:
            g.post_with_retry({}, "secret-123", send=send)
        self.assertNotIn("secret-123", str(ctx.exception))


class LogTest(unittest.TestCase):
    def test_log_has_scores_but_no_diff_content(self):
        with tempfile.TemporaryDirectory() as d:
            out = g.run_gate(diff=MODIFIED, title="secret title", claude_md="rule",
                             post=fake_post(), api_key="k")
            path = g.append_log(out, repo="o/r", pr=1, head="abc", state_dir=d)
            with open(path) as f:
                text = f.read()
            self.assertIn('"pr": 1', text)
            self.assertIn("design", text)
            self.assertNotIn("new = 2", text)
            self.assertNotIn("secret title", text)
            self.assertNotIn("src/app.py", text)

    def test_outcome_is_appended_under_same_run_id(self):
        with tempfile.TemporaryDirectory() as d:
            g.append_outcome("run-1", {"design": 2}, state_dir=d)
            with open(os.path.join(d, g.LOG_NAME)) as f:
                rec = json.loads(f.read().splitlines()[-1])
            self.assertEqual(rec["run_id"], "run-1")
            self.assertEqual(rec["type"], "outcome")


if __name__ == "__main__":
    unittest.main()
