"""Offline tests for the PR feedback helper; no GitHub requests are made."""

import argparse
import base64
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import post_review_comments as poster

REPO = "owner/name"
HEAD = "a" * 40
MOVED = "b" * 40
# New-side lines 10-15 and line 43 are in the diff.
PATCH = "@@ -10,3 +10,6 @@\n line\n+one\n+two\n+three\n line\n line\n@@ -40 +43 @@\n-old\n+new\n"


def pr_comment(key="7-pr", body="Thanks, Sam! Could we add a test for the empty case?"):
    return {"key": key, "pr": 7, "kind": "pr", "body": body}


def inline_comment(key="7-line", line=12, body="Nit: could we name this `maxWaitMs`?", commit=HEAD, **extra):
    return {"key": key, "pr": 7, "kind": "inline", "path": "src/app.ts", "line": line,
            "commit_id": commit, "body": body, **extra}


class FakeGitHub:
    """Answers the few `gh api` calls the helper makes, for one open PR (#7)."""

    def __init__(self):
        self.head = HEAD
        self.pending_review = False
        self.comments = {"pr": [], "inline": []}
        self.posted = []
        self.next_id = 100

    def run_gh(self, args, payload=None, raw=False):
        if args == ["user"]:
            return {"login": "me"}
        if args[:2] == ["--method", "POST"]:
            path = args[2]
            self.next_id += 1
            self.posted.append((path, payload))
            item = {"user": {"login": "me"}, "body": payload["body"], "id": self.next_id,
                    "html_url": f"https://example.test/{self.next_id}"}
            self.comments["inline" if "/pulls/" in path else "pr"].append(item)
            return {"id": item["id"], "html_url": item["html_url"]}
        path = args[0]
        if path == f"repos/{REPO}/pulls/7":
            return {"head": {"sha": self.head}, "state": "open", "user": {"login": "author"}, "title": "Change"}
        if path.startswith(f"repos/{REPO}/contents/src/app.ts"):
            text = "\n".join(f"line {number}" for number in range(1, 60))
            return {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}
        for kind, prefix in (("pr", f"repos/{REPO}/issues/comments/"), ("inline", f"repos/{REPO}/pulls/comments/")):
            if path.startswith(prefix):
                for item in self.comments[kind]:
                    if item["id"] == int(path[len(prefix):]):
                        return {**item, "created_at": "2026-01-01T00:00:00Z", "path": "src/app.ts", "line": 12}
                raise RuntimeError("HTTP 404: Not Found")
        raise AssertionError(f"unexpected gh api call: {args}")

    def gh_list(self, path):
        if path.startswith(f"repos/{REPO}/pulls/7/reviews"):
            return [{"state": "PENDING", "user": {"login": "me"}}] if self.pending_review else []
        if path.startswith(f"repos/{REPO}/pulls/7/files"):
            return [{"filename": "src/app.ts", "patch": PATCH}]
        if path.startswith(f"repos/{REPO}/issues/7/comments"):
            return list(self.comments["pr"])
        if path.startswith(f"repos/{REPO}/pulls/7/comments"):
            return list(self.comments["inline"])
        raise AssertionError(f"unexpected gh list call: {path}")


class HelperCase(unittest.TestCase):
    def setUp(self):
        self.github = FakeGitHub()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        self.plan_path = os.path.join(self.directory, "plan.json")
        for name, fake in (("run_gh", self.github.run_gh), ("gh_list", self.github.gh_list)):
            patcher = patch.object(poster, name, fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        sleeper = patch.object(poster.time, "sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def write_plan(self, comments):
        with open(self.plan_path, "w", encoding="utf-8") as handle:
            json.dump({"repo": REPO, "comments": comments}, handle)

    def run_command(self, command, **options):
        values = {"plan": self.plan_path, "min_delay": 180, "max_delay": 420, "dry_run": False}
        values.update(options)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = getattr(poster, command)(argparse.Namespace(**values))
        return code, output.getvalue()

    def recorded(self):
        path = os.path.join(self.directory, "posted.json")
        if not os.path.exists(path):
            return {}
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)


class VoiceTests(unittest.TestCase):
    def test_dashes_bold_headings_emoji_and_ai_mentions_are_errors(self):
        errors, _ = poster.lint_voice([
            {"key": "dash", "body": "One thing \u2014 another."},
            {"key": "bold", "body": "**Important** change."},
            {"key": "heading", "body": "## Summary"},
            {"key": "emoji", "body": "Nice \U0001F389"},
            {"key": "ai", "body": "Generated by Claude."},
        ])
        for key in ("dash", "bold", "heading", "emoji", "ai"):
            self.assertTrue(any(error.startswith(f"{key}:") for error in errors), key)

    def test_code_spans_and_blocks_are_not_checked(self):
        errors, warnings = poster.lint_voice([
            {"key": "code", "body": "Could we keep `a \u2014 b`?\n\n```md\n## Title **bold**\n```"},
        ])
        self.assertEqual((errors, warnings), ([], []))

    def test_thanks_is_allowed_once_in_the_first_comment(self):
        errors, warnings = poster.lint_voice([
            {"key": "first", "body": "Thanks, Sam! Looks right."},
            {"key": "second", "body": "Nit: rename this."},
        ])
        self.assertEqual((errors, warnings), ([], []))

        errors, _ = poster.lint_voice([
            {"key": "first", "body": "Thanks, Sam!"},
            {"key": "second", "body": "Thanks again."},
        ])
        self.assertTrue(any("thanks appears in 2 comments" in error for error in errors))

        errors, warnings = poster.lint_voice([
            {"key": "first", "body": "Could we add a test?"},
            {"key": "second", "body": "Thank you for this."},
        ])
        self.assertEqual(errors, [])
        self.assertTrue(any("not in the first comment" in warning for warning in warnings))

    def test_filler_and_buzzwords_are_warnings_not_errors(self):
        errors, warnings = poster.lint_voice([{"key": "filler", "body": "I noticed this could ensure order."}])
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2)


class DiffAnchorTests(unittest.TestCase):
    def test_lines_inside_a_hunk_can_be_commented_on(self):
        self.assertTrue(poster.in_diff(PATCH, 12, 12))
        self.assertTrue(poster.in_diff(PATCH, 10, 15))
        self.assertTrue(poster.in_diff(PATCH, 43, 43))

    def test_lines_outside_or_across_hunks_cannot(self):
        self.assertFalse(poster.in_diff(PATCH, 9, 9))
        self.assertFalse(poster.in_diff(PATCH, 16, 16))
        self.assertFalse(poster.in_diff(PATCH, 14, 43))


class PlanTests(unittest.TestCase):
    def load(self, comments):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "plan.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"repo": REPO, "comments": comments}, handle)
            return poster.load_plan(path)

    def test_invalid_plans_are_rejected_before_any_request(self):
        cases = {
            "duplicate key": [pr_comment(), pr_comment()],
            '"kind" must be': [{**pr_comment(), "kind": "review"}],
            '"commit_id"': [inline_comment(commit="abc123")],
            '"start_line" must be': [inline_comment(start_line=20)],
            '"body" is required': [pr_comment(body="  ")],
        }
        for message, comments in cases.items():
            with self.subTest(message), self.assertRaises(SystemExit) as raised:
                self.load(comments)
            self.assertIn(message, str(raised.exception.code))

    def test_a_valid_plan_loads(self):
        repo, comments = self.load([pr_comment(), inline_comment(start_line=10)])
        self.assertEqual(repo, REPO)
        self.assertEqual([comment["key"] for comment in comments], ["7-pr", "7-line"])


class ValidateTests(HelperCase):
    def test_reports_account_timing_and_anchored_line(self):
        self.write_plan([pr_comment(), inline_comment()])
        code, output = self.run_command("validate")
        self.assertEqual(code, 0)
        self.assertIn("2 comments as me", output)
        self.assertIn("3-7 min gaps", output)
        self.assertIn("src/app.ts:12  | line 12", output)

    def test_text_already_on_the_pr_is_an_error(self):
        self.github.comments["pr"].append({"user": {"login": "me"}, "id": 5, "html_url": "https://example.test/5",
                                           "body": "Thanks, Sam!  Could we add a test\nfor the empty case?"})
        self.write_plan([pr_comment()])
        code, output = self.run_command("validate")
        self.assertEqual(code, 1)
        self.assertIn("the same text is already on #7", output)


class PostTests(HelperCase):
    def test_posts_in_order_with_random_delays_and_records_progress(self):
        self.write_plan([pr_comment(), inline_comment("7-a", 12), inline_comment("7-b", 43, "Question: should this retry?")])
        code, _ = self.run_command("post")
        self.assertEqual(code, 0)
        self.assertEqual([path for path, _ in self.github.posted],
                         [f"repos/{REPO}/issues/7/comments"] + [f"repos/{REPO}/pulls/7/comments"] * 2)
        self.assertEqual(self.github.posted[1][1],
                         {"body": "Nit: could we name this `maxWaitMs`?", "commit_id": HEAD,
                          "path": "src/app.ts", "line": 12, "side": "RIGHT"})
        delays = [call.args[0] for call in self.sleep.call_args_list]
        self.assertEqual(len(delays), 2)
        self.assertTrue(all(180 <= delay <= 420 for delay in delays))
        self.assertEqual(sorted(self.recorded()), ["7-a", "7-b", "7-pr"])

    def test_a_range_comment_sends_its_start_line(self):
        self.write_plan([inline_comment(start_line=10)])
        self.assertEqual(self.run_command("post")[0], 0)
        payload = self.github.posted[0][1]
        self.assertEqual((payload["start_line"], payload["start_side"], payload["line"]), (10, "RIGHT", 12))

    def test_nothing_is_posted_when_a_check_fails(self):
        self.write_plan([pr_comment(), inline_comment(line=30)])
        code, output = self.run_command("post")
        self.assertEqual(code, 1)
        self.assertIn("outside the diff hunks", output)

        self.github.pending_review = True
        self.write_plan([pr_comment()])
        code, output = self.run_command("post")
        self.assertEqual(code, 1)
        self.assertIn("pending review", output)
        self.assertEqual(self.github.posted, [])

    def test_stops_when_the_author_pushes(self):
        self.write_plan([pr_comment(), inline_comment()])
        self.sleep.side_effect = lambda seconds: setattr(self.github, "head", MOVED)
        code, output = self.run_command("post")
        self.assertEqual(code, 2)
        self.assertIn("STOP", output)
        self.assertEqual(len(self.github.posted), 1)
        self.assertEqual(list(self.recorded()), ["7-pr"])

    def test_a_rerun_skips_posted_comments_and_waits_before_the_next(self):
        self.write_plan([pr_comment(), inline_comment()])
        with open(os.path.join(self.directory, "posted.json"), "w", encoding="utf-8") as handle:
            json.dump({"7-pr": {"pr": 7, "kind": "pr", "id": 1, "url": "https://example.test/1"}}, handle)
        code, _ = self.run_command("post")
        self.assertEqual(code, 0)
        self.assertEqual([path for path, _ in self.github.posted], [f"repos/{REPO}/pulls/7/comments"])
        self.assertEqual(self.sleep.call_count, 1)

    def test_text_already_on_the_pr_is_recorded_not_posted_again(self):
        self.github.comments["pr"].append({"user": {"login": "me"}, "id": 5, "html_url": "https://example.test/5",
                                           "body": pr_comment()["body"]})
        self.write_plan([pr_comment()])
        code, _ = self.run_command("post")
        self.assertEqual(code, 0)
        self.assertEqual(self.github.posted, [])
        self.assertEqual(self.recorded()["7-pr"]["id"], 5)

    def test_a_dry_run_posts_nothing(self):
        self.write_plan([pr_comment(), inline_comment()])
        code, output = self.run_command("post", dry_run=True, min_delay=1, max_delay=2)
        self.assertEqual(code, 0)
        self.assertIn("would post 7-line", output)
        self.assertEqual(self.github.posted, [])
        self.assertEqual(self.recorded(), {})


class StatusTests(HelperCase):
    def test_confirms_posted_comments_and_reports_missing_ones(self):
        self.write_plan([pr_comment(), inline_comment()])
        self.run_command("post")
        code, output = self.run_command("status")
        self.assertEqual(code, 0)
        self.assertEqual(output.count("\nOK ") + output.startswith("OK "), 2)

        self.write_plan([pr_comment(), inline_comment(), pr_comment("7-extra", "Small thing: one more.")])
        code, output = self.run_command("status")
        self.assertEqual(code, 1)
        self.assertIn("NOT POSTED 7-extra", output)


if __name__ == "__main__":
    unittest.main()
