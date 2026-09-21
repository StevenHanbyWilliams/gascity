import tempfile
import unittest

import mac_regression_gate


REPO = "gastownhall/gascity"


class DecideRegressionEquivalenceTests(unittest.TestCase):
    """One test per branch that already exists in the gate job's bash today.

    These pin current behavior so the port can't silently change it.
    """

    def test_schedule_runs_everything(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="schedule",
            suite_input="",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertTrue(decision.run_review_formulas)
        self.assertEqual(decision.reason, "nightly schedule")

    def test_workflow_dispatch_suite_full_runs_everything(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_dispatch",
            suite_input="full",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertTrue(decision.run_review_formulas)
        self.assertEqual(decision.reason, "manual dispatch (suite=full)")

    def test_workflow_dispatch_suite_needs_mac_skips_review_formulas(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_dispatch",
            suite_input="needs-mac",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "manual dispatch (suite=needs-mac)")

    def test_workflow_dispatch_suite_smoke_runs_only_smoke(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_dispatch",
            suite_input="smoke",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "manual dispatch (suite=smoke)")

    def test_pull_request_from_fork_skips(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="pull_request",
            suite_input="",
            pr_head_repo="someone-else/gascity",
            repository=REPO,
            pr_draft="false",
            needs_label="false",
            path_hit="false",
        )
        self.assertFalse(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "pull request from a fork, skipping")

    def test_pull_request_draft_skips(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="pull_request",
            suite_input="",
            pr_head_repo=REPO,
            repository=REPO,
            pr_draft="true",
            needs_label="false",
            path_hit="false",
        )
        self.assertFalse(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "draft pull request, skipping")

    def test_pull_request_needs_mac_label_runs_smoke_and_full(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="pull_request",
            suite_input="",
            pr_head_repo=REPO,
            repository=REPO,
            pr_draft="false",
            needs_label="true",
            path_hit="false",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "pull request carries needs-mac label")

    def test_pull_request_path_hit_without_label_runs_smoke_only(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="pull_request",
            suite_input="",
            pr_head_repo=REPO,
            repository=REPO,
            pr_draft="false",
            needs_label="false",
            path_hit="true",
        )
        self.assertTrue(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(
            decision.reason,
            "pull request touches mac-sensitive paths without needs-mac label, running smoke tier",
        )

    def test_pull_request_without_label_or_path_hit_skips(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="pull_request",
            suite_input="",
            pr_head_repo=REPO,
            repository=REPO,
            pr_draft="false",
            needs_label="false",
            path_hit="false",
        )
        self.assertFalse(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(
            decision.reason, "pull request without needs-mac label (path hit: false)"
        )

    def test_unrecognized_event_matches_nothing(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="push",
            suite_input="",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertFalse(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "no trigger matched")


class DecideWorkflowCallTests(unittest.TestCase):
    """The actual fix: workflow_call currently falls through to "no trigger
    matched" (all tiers false), which silently no-ops rc-gate.yml's
    mac_regression job even though it passes suite: full. workflow_call
    shares the same suite-input tier semantics as workflow_dispatch, since
    both trigger types expose the same `suite` input in this workflow's
    `on:` block -- only the human-readable reason differs, to keep the two
    provenances distinguishable in logs.
    """

    def test_workflow_call_suite_full_runs_everything(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_call",
            suite_input="full",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertTrue(decision.run_review_formulas)
        self.assertEqual(decision.reason, "reusable workflow call (suite=full)")

    def test_workflow_call_suite_needs_mac_skips_review_formulas(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_call",
            suite_input="needs-mac",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertTrue(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "reusable workflow call (suite=needs-mac)")

    def test_workflow_call_suite_smoke_runs_only_smoke(self) -> None:
        decision = mac_regression_gate.decide(
            event_name="workflow_call",
            suite_input="smoke",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)
        self.assertEqual(decision.reason, "reusable workflow call (suite=smoke)")

    def test_workflow_call_unrecognized_suite_fails_safe_to_smoke_only(self) -> None:
        # GitHub Actions substitutes this input's own "full" default before
        # this script ever runs, so a real call never actually leaves
        # suite_input empty -- this exercises decide()'s own defensive
        # fallback directly, mirroring workflow_dispatch's `*` case, so an
        # unexpected value can never accidentally run nothing or crash.
        decision = mac_regression_gate.decide(
            event_name="workflow_call",
            suite_input="",
            pr_head_repo="",
            repository=REPO,
            pr_draft="",
            needs_label="",
            path_hit="",
        )
        self.assertTrue(decision.run_smoke)
        self.assertFalse(decision.run_full)
        self.assertFalse(decision.run_review_formulas)


class AppendOutputsTests(unittest.TestCase):
    def test_writes_all_four_fields(self) -> None:
        decision = mac_regression_gate.GateDecision(
            run_smoke=True,
            run_full=False,
            run_review_formulas=False,
            reason="manual dispatch (suite=smoke)",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_path = f"{tmp}/github_output"
            open(output_path, "w", encoding="utf-8").close()
            mac_regression_gate.append_outputs(decision, github_output=output_path)
            content = open(output_path, encoding="utf-8").read()

        self.assertIn("run_smoke=true\n", content)
        self.assertIn("run_full=false\n", content)
        self.assertIn("run_review_formulas=false\n", content)
        self.assertIn("reason=manual dispatch (suite=smoke)\n", content)


if __name__ == "__main__":
    unittest.main()
