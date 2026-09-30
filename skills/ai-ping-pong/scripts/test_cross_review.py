"""Protocol and transport regression tests; no model requests are made."""

import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid

import cross_review as bridge


def packet():
    return {
        "brief": "Plan a local text export. Preserve Unicode and do not send data remotely.",
        "plan": "Write a UTF-8 file, read it back, and compare its contents.",
        "evidence": ["An existing export containing café round-trips correctly."],
        "objections": [],
        "responses": [],
    }


def review(digest, request_id=None):
    return {
        "request_id": request_id or str(uuid.uuid4()),
        "snapshot_sha256": digest,
        "verdict": "approve",
        "summary": "The plan preserves the brief's requirements and has sufficient evidence.",
        "objections": [],
        "evidence_needed": [],
    }


def objection():
    return {
        "id": "unicode-round-trip",
        "severity": "major",
        "detail": "An untested encoding could corrupt Unicode characters.",
        "requested_change": "Verify non-ASCII content survives an export and import.",
    }


def record(provider, digest, origin="cli", effort="high"):
    model = bridge.MODELS[provider]
    return {
        "schema_version": 1,
        "status": "success",
        "origin": origin,
        "provider": provider,
        "model": model,
        "observed_model": model,
        "model_verification": "host_attestation" if origin == "host" else "runtime",
        "requested_effort": effort,
        "effort": bridge.effective_effort(provider, effort),
        "effort_source": "Current task's explicit reasoning selection",
        "review": review(digest),
    }


def claude_envelope(result, model=None):
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "modelUsage": {model or bridge.MODELS["claude"]: {"inputTokens": 100}},
        "structured_output": result,
    }


def codex_events(result, model=None):
    started = {"type": "thread.started", "thread_id": str(uuid.uuid4())}
    if model is not None:
        started["model"] = model
    return "\n".join(json.dumps(item) for item in [
        started,
        {"type": "turn.started"},
        {"type": "item.completed", "item": {
            "id": "review-output", "type": "agent_message", "text": json.dumps(result),
        }},
        {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 100}},
    ])


class SnapshotTests(unittest.TestCase):
    def test_every_material_input_invalidates_prior_approval(self):
        original = packet()
        digest = bridge.snapshot_sha256(original)
        amendments = {
            "brief": original["brief"] + " Finish within one minute.",
            "evidence": ["The Unicode round-trip failed."],
            "objections": ["The export overwrites an existing file."],
            "responses": ["Revise the plan to preserve an existing file."],
            "plan": original["plan"] + " Use exclusive file creation.",
        }
        for field, value in amendments.items():
            with self.subTest(field=field):
                amended = dict(original, **{field: value})
                self.assertNotEqual(digest, bridge.snapshot_sha256(amended))
                with self.assertRaises(bridge.ReviewError):
                    bridge.validate_review(review(digest), bridge.snapshot_sha256(amended))

    def test_serialization_key_order_does_not_invalidate_approval(self):
        original = packet()
        reordered = dict(reversed(list(original.items())))
        self.assertEqual(bridge.snapshot_sha256(original), bridge.snapshot_sha256(reordered))

    def test_ambiguous_duplicate_json_fields_are_rejected(self):
        with self.assertRaises(bridge.ReviewError):
            bridge.parse_json('{"verdict":"revise","verdict":"approve"}', "response")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.digest = bridge.snapshot_sha256(packet())

    def test_valid_approval_is_bound_to_request_and_snapshot(self):
        result = review(self.digest)
        self.assertEqual(bridge.validate_review(result, self.digest, result["request_id"]), result)

    def test_stale_request_and_snapshot_are_rejected(self):
        result = review(self.digest)
        for digest, request_id in [
            ("0" * 64, result["request_id"]),
            (self.digest, str(uuid.uuid4())),
        ]:
            with self.subTest(digest=digest, request_id=request_id):
                with self.assertRaises(bridge.ReviewError):
                    bridge.validate_review(result, digest, request_id)

    def test_approval_cannot_have_objections_or_missing_evidence(self):
        for field, value in [
            ("objections", [objection()]),
            ("evidence_needed", ["Run the Unicode round-trip."]),
        ]:
            with self.subTest(field=field):
                result = review(self.digest)
                result[field] = value
                with self.assertRaises(bridge.ReviewError):
                    bridge.validate_review(result, self.digest)

    def test_nonapproval_verdicts_require_actionable_explanation(self):
        for verdict in ("revise", "needs_evidence"):
            with self.subTest(verdict=verdict):
                result = review(self.digest)
                result["verdict"] = verdict
                with self.assertRaises(bridge.ReviewError):
                    bridge.validate_review(result, self.digest)
                if verdict == "revise":
                    result["objections"] = [objection()]
                else:
                    result["evidence_needed"] = ["Run the Unicode round-trip."]
                self.assertEqual(bridge.validate_review(result, self.digest), result)

    def test_host_attestation_cannot_be_relabelled_as_cli_evidence(self):
        result = record("codex", self.digest, origin="host")
        bridge.validate_record(result, "codex", bridge.MODELS["codex"], self.digest)
        result["origin"] = "cli"
        with self.assertRaises(bridge.ReviewError):
            bridge.validate_record(result, "codex", bridge.MODELS["codex"], self.digest)

    def test_different_host_model_cannot_supply_selected_model_approval(self):
        result = record("codex", self.digest, origin="host")
        result["observed_model"] = "gpt-6-sol"
        with self.assertRaises(bridge.ReviewError):
            bridge.validate_record(result, "codex", bridge.MODELS["codex"], self.digest)

    def test_unknown_effort_never_uses_a_default(self):
        for provider in ("claude", "codex"):
            for effort in (None, "", "automatic", "unlimited", "none"):
                with self.subTest(provider=provider, effort=effort):
                    with self.assertRaises(bridge.ReviewError):
                        bridge.effective_effort(provider, effort)


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet_path = self.root / "packet.json"
        self.write_json(self.packet_path, packet())
        self.digest = bridge.snapshot_sha256(packet())

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")


class ArtifactTests(FixtureCase):
    def check(self, claude, codex):
        claude_path, codex_path = self.root / "claude.json", self.root / "codex.json"
        self.write_json(claude_path, claude)
        self.write_json(codex_path, codex)
        args = bridge.parser().parse_args([
            "check", "--packet", str(self.packet_path),
            "--claude-review", str(claude_path), "--codex-review", str(codex_path),
        ])
        return bridge.check_command(args)

    def test_both_models_approve_the_same_snapshot_with_truthful_origins(self):
        claude = record("claude", self.digest, effort="ultra")
        codex = record("codex", self.digest, origin="host", effort="ultra")
        result = self.check(claude, codex)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["snapshot_sha256"], self.digest)
        self.assertEqual([item["origin"] for item in result["reviews"]], ["cli", "host"])

    def test_one_nonapproval_or_stale_vote_prevents_agreement(self):
        claude = record("claude", self.digest)
        for amendment in (
            {"verdict": "revise", "objections": [objection()]},
            {"verdict": "needs_evidence", "evidence_needed": ["Run the export."]},
            {"snapshot_sha256": "0" * 64},
        ):
            with self.subTest(amendment=amendment):
                codex = record("codex", self.digest)
                codex["review"].update(amendment)
                with self.assertRaises(bridge.ReviewError):
                    self.check(claude, codex)

    def test_same_review_id_cannot_count_as_two_independent_approvals(self):
        claude, codex = record("claude", self.digest), record("codex", self.digest)
        codex["review"]["request_id"] = claude["review"]["request_id"]
        with self.assertRaises(bridge.ReviewError):
            self.check(claude, codex)

    def test_two_host_attestations_cannot_replace_external_cli_review(self):
        with self.assertRaises(bridge.ReviewError):
            self.check(record("claude", self.digest, origin="host"),
                       record("codex", self.digest, origin="host"))

    def test_two_different_selected_efforts_do_not_make_agreement(self):
        with self.assertRaises(bridge.ReviewError):
            self.check(record("claude", self.digest, effort="high"),
                       record("codex", self.digest, effort="ultra"))

    def test_codex_without_runtime_identity_is_explicitly_requested_only(self):
        result = review(self.digest)
        last = self.root / "last-message.json"
        self.write_json(last, result)
        parsed, observed, verification = bridge.codex_response(
            codex_events(result), last, bridge.MODELS["codex"])
        self.assertEqual(parsed, result)
        self.assertIsNone(observed)
        self.assertEqual(verification, "requested_only")

    def test_codex_errors_tools_incomplete_output_and_conflicting_output_fail(self):
        result = review(self.digest)
        last = self.root / "last-message.json"
        self.write_json(last, result)
        malformed = {
            "empty": "",
            "failed": json.dumps({"type": "turn.failed", "error": {"message": "rate limited"}}),
            "unfinished": json.dumps({"type": "turn.started"}),
            "tool": json.dumps({"type": "item.completed", "item": {"type": "command_execution"}}),
            "different model": codex_events(result, "gpt-6-sol"),
            "different output": codex_events(dict(result, summary="Contradictory output")),
        }
        for label, stdout in malformed.items():
            with self.subTest(label=label):
                with self.assertRaises(bridge.ReviewError):
                    bridge.codex_response(stdout, last, bridge.MODELS["codex"])

    def test_claude_fallback_or_mixed_model_usage_is_rejected(self):
        envelope = claude_envelope(review(self.digest))
        for usage in (
            {},
            {"claude-opus-5": {}},
            {bridge.MODELS["claude"]: {}, "claude-opus-5": {}},
        ):
            with self.subTest(usage=usage):
                envelope["modelUsage"] = usage
                with self.assertRaises(bridge.ReviewError):
                    bridge.claude_response(json.dumps(envelope), bridge.MODELS["claude"])

    def test_claude_additive_telemetry_does_not_change_valid_review(self):
        expected = review(self.digest)
        envelope = claude_envelope(expected)
        envelope.update(
            api_error_status=None,
            terminal_reason="end_turn",
            client_metrics={"request_count": 1},
            future_usage_summary={"served_from_cache": False},
        )
        actual, observed, verification = bridge.claude_response(
            json.dumps(envelope), bridge.MODELS["claude"])
        self.assertEqual(bridge.validate_review(actual, self.digest), expected)
        self.assertEqual(observed, bridge.MODELS["claude"])
        self.assertEqual(verification, "runtime")

    def test_claude_additive_review_fields_remain_rejected(self):
        expected = review(self.digest)
        expected["approve_different_plan"] = True
        actual, _, _ = bridge.claude_response(
            json.dumps(claude_envelope(expected)), bridge.MODELS["claude"])
        with self.assertRaises(bridge.ReviewError):
            bridge.validate_review(actual, self.digest)

    def test_claude_hidden_api_error_overrides_success_fields(self):
        for error_fields in ({"api_error_status": 401}, {"terminal_reason": "api_error"}):
            with self.subTest(error_fields=error_fields):
                envelope = claude_envelope(review(self.digest))
                envelope.update(error_fields)
                with self.assertRaises(bridge.ReviewError):
                    bridge.claude_response(json.dumps(envelope), bridge.MODELS["claude"])

    def test_known_codex_startup_advisories_preserve_valid_approval(self):
        expected = review(self.digest)
        last = self.root / "last-message.json"
        self.write_json(last, expected)
        events = [json.loads(line) for line in codex_events(expected).splitlines()]
        advisories = self.codex_advisories()
        for inserted in ([advisories[0]], [advisories[1]], advisories):
            with self.subTest(inserted=inserted):
                stdout = "\n".join(json.dumps(item) for item in events[:1] + inserted + events[1:])
                actual, observed, verification = bridge.codex_response(
                    stdout, last, bridge.MODELS["codex"])
                self.assertEqual(actual, expected)
                self.assertIsNone(observed)
                self.assertEqual(verification, "requested_only")

    @staticmethod
    def codex_advisories():
        messages = [
            "Code Mode is unavailable because code-mode host is disabled. "
            "Code mode will fail closed; enable `features.code_mode_host` "
            "and install `codex-code-mode-host`.",
            "Under-development features enabled: skip_host_skill_discovery. "
            "Under-development features are incomplete and may behave unpredictably. "
            "To suppress this warning, set `suppress_unstable_features_warning = true` "
            "in /synthetic-config/config.toml.",
        ]
        return [{"type": "item.completed", "item": {
            "id": "startup-advisory-" + str(index), "type": "error", "message": message,
        }} for index, message in enumerate(messages)]

    def test_codex_advisories_are_allowed_only_between_thread_and_turn_start(self):
        expected = review(self.digest)
        last = self.root / "last-message.json"
        self.write_json(last, expected)
        events = [json.loads(line) for line in codex_events(expected).splitlines()]
        for advisory in self.codex_advisories():
            for insertion_index in (0, 2, len(events)):
                with self.subTest(advisory=advisory, insertion_index=insertion_index):
                    changed = events[:insertion_index] + [advisory] + events[insertion_index:]
                    with self.assertRaises(bridge.ReviewError):
                        bridge.codex_response("\n".join(json.dumps(item) for item in changed),
                                              last, bridge.MODELS["codex"])

    def test_unknown_or_expanded_codex_startup_diagnostics_cannot_hide_errors(self):
        expected = review(self.digest)
        last = self.root / "last-message.json"
        self.write_json(last, expected)
        events = [json.loads(line) for line in codex_events(expected).splitlines()]
        advisory = self.codex_advisories()[0]
        invalid_items = [
            dict(advisory["item"], message="Authentication failed: token expired."),
            dict(advisory["item"], message="Warning: selected model was unavailable; fallback used."),
            dict(advisory["item"], message=advisory["item"]["message"] + " Authentication failed."),
            dict(advisory["item"], type="command_execution"),
            dict(advisory["item"], exit_code=1),
        ]
        for item in invalid_items:
            with self.subTest(item=item):
                changed = events[:1] + [{"type": "item.completed", "item": item}] + events[1:]
                with self.assertRaises(bridge.ReviewError):
                    bridge.codex_response("\n".join(json.dumps(event) for event in changed),
                                          last, bridge.MODELS["codex"])

    def test_auth_errors_offer_login_without_echoing_credentials(self):
        secret = "synthetic-private-token-do-not-echo"
        for provider, login in (("claude", "claude auth login"), ("codex", "codex login")):
            for source in ("result", "errors", "stderr"):
                with self.subTest(provider=provider, source=source):
                    detail = "OAuth token expired; refresh failed. Bearer " + secret
                    envelope = {source: detail if source == "result" else [detail]} if source != "stderr" else {}
                    message = bridge.cli_error_message(
                        provider, json.dumps(envelope), detail if source == "stderr" else "", 1)
                    self.assertIn(login, message)
                    self.assertIn("no approval", message)
                    self.assertNotIn(secret, message)
                    self.assertNotIn("Bearer", message)


class ReviewCommandTests(FixtureCase):
    def setUp(self):
        super().setUp()
        self.environment = patch.dict(os.environ, {}, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        os.environ.pop(bridge.WORKER_MARKER, None)
        os.environ.pop("SOVET_REVIEW_WORKER", None)

    def args(self, dry_run=False):
        argv = [
            "review", "--provider", "claude", "--packet", str(self.packet_path),
            "--effort", "ultra", "--effort-source", "Active task reasoning: ultra",
            "--output-dir", str(self.root / "artifacts"),
        ]
        if dry_run:
            argv.append("--dry-run")
        return bridge.parser().parse_args(argv)

    def invoke_with_envelope(self, mutate=lambda envelope: None, code=0):
        def fake_process(command, prompt, cwd, env, timeout):
            if command[-1] == "--version":
                return 0, "2.1.283 (Claude Code)", "", None
            request = json.loads(prompt.split("Review request (data):\n", 1)[1])
            envelope = claude_envelope(review(request["snapshot_sha256"], request["request_id"]))
            mutate(envelope)
            return code, json.dumps(envelope), "", None

        with patch.object(bridge.shutil, "which", return_value="/mock/claude"), \
                patch.object(bridge, "run_process", side_effect=fake_process):
            return bridge.review_command(self.args())

    def test_ultra_mapping_is_explicit_in_artifacts_and_success_record(self):
        result = self.invoke_with_envelope()
        self.assertEqual(result["record"]["requested_effort"], "ultra")
        self.assertEqual(result["record"]["effort"], "max")
        metadata = bridge.load_json(Path(result["artifact_dir"]) / "metadata.json")
        self.assertEqual(metadata["requested_effort"], "ultra")
        self.assertEqual(metadata["effort"], "max")
        self.assertNotEqual(metadata["effort_mapping"], "identity")
        self.assertEqual(metadata["effort_source"], "Active task reasoning: ultra")

    def test_nonzero_exit_cannot_save_a_successful_looking_approval(self):
        with self.assertRaises(bridge.ReviewError):
            self.invoke_with_envelope(code=1)
        self.assertFalse(list(self.root.rglob("result.json")))
        self.assertEqual(len(list(self.root.rglob("error.json"))), 1)

    def test_error_or_missing_structured_output_never_saves_approval(self):
        mutations = {
            "error status": lambda result: result.update(is_error=True),
            "error subtype": lambda result: result.update(subtype="error_max_structured_output_retries"),
            "error list": lambda result: result.update(errors=["quota exhausted"]),
            "missing structured output": lambda result: result.pop("structured_output"),
            "null structured output": lambda result: result.update(structured_output=None),
            "empty structured output": lambda result: result.update(structured_output={}),
            "API error despite exit zero": lambda result: result.update(api_error_status=401),
            "terminal error despite exit zero": lambda result: result.update(terminal_reason="api_error"),
            "stale request": lambda result: result["structured_output"].update(request_id=str(uuid.uuid4())),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(bridge.ReviewError):
                    self.invoke_with_envelope(mutate)
        self.assertFalse(list(self.root.rglob("result.json")))
        self.assertEqual(len(list(self.root.rglob("error.json"))), len(mutations))

    def test_dry_run_makes_no_subprocess_call(self):
        with patch.object(bridge, "run_process") as runner:
            result = bridge.review_command(self.args(dry_run=True))
        runner.assert_not_called()
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse(list(self.root.rglob("result.json")))

    def test_worker_cannot_start_a_recursive_review(self):
        os.environ[bridge.WORKER_MARKER] = "1"
        with patch.object(bridge, "run_process") as runner:
            with self.assertRaises(bridge.ReviewError):
                bridge.review_command(self.args())
        runner.assert_not_called()


class ProcessTests(unittest.TestCase):
    def test_prompt_is_stdin_and_shell_metacharacters_remain_data(self):
        command = ["/path with spaces/claude", "-p", "--tools", ""]
        prompt = "Review $(touch should-not-exist) and `false`; keep literal.\n"
        process = Mock(returncode=0)
        process.communicate.return_value = ("review output", "")
        with patch.object(bridge.subprocess, "Popen", return_value=process) as popen:
            result = bridge.run_process(command, prompt, "/tmp", {"EXAMPLE": "1"}, 10)
        self.assertEqual(popen.call_args.args[0], command)
        self.assertIs(popen.call_args.kwargs["shell"], False)
        self.assertIs(popen.call_args.kwargs["start_new_session"], True)
        self.assertIs(popen.call_args.kwargs["stdin"], subprocess.PIPE)
        process.communicate.assert_called_once_with(prompt, timeout=10)
        self.assertEqual(result, (0, "review output", "", None))

    def test_timeout_terminates_process_group_and_cannot_succeed(self):
        command = ["/mock/claude", "-p"]
        process = Mock(pid=87654, returncode=-signal.SIGTERM)
        process.poll.return_value = None
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(command, 1), ("partial output", ""),
        ]
        with patch.object(bridge.subprocess, "Popen", return_value=process), \
                patch.object(bridge.os, "killpg") as killpg:
            code, stdout, stderr, failure = bridge.run_process(command, "prompt", "/tmp", {}, 1)
        killpg.assert_called_once_with(process.pid, signal.SIGTERM)
        self.assertIsNotNone(failure)
        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "partial output")

    def test_unresponsive_timed_out_process_is_killed_and_reaped(self):
        process = Mock(pid=87654, returncode=-signal.SIGKILL)
        process.poll.return_value = None
        process.communicate.side_effect = [subprocess.TimeoutExpired(["mock"], 3), ("", "")]
        with patch.object(bridge.os, "killpg") as killpg:
            self.assertEqual(bridge.kill_process_group(process), ("", ""))
        self.assertEqual([call.args for call in killpg.call_args_list], [
            (process.pid, signal.SIGTERM), (process.pid, signal.SIGKILL),
        ])
        self.assertEqual(process.communicate.call_count, 2)


if __name__ == "__main__":
    unittest.main()
