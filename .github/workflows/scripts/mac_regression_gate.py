#!/usr/bin/env python3
"""Decide which Mac Regression tiers to run for the current trigger."""

from __future__ import annotations

import os
from typing import NamedTuple


class GateDecision(NamedTuple):
    run_smoke: bool
    run_full: bool
    run_review_formulas: bool
    reason: str


def _suite_decision(suite_input: str, *, verb: str) -> GateDecision:
    """Shared full/needs-mac/else tiering for workflow_dispatch and workflow_call.

    Both trigger types expose the same `suite` input and the same tiering;
    only the reason's verb differs, to keep the two provenances
    distinguishable in logs.
    """
    if suite_input == "full":
        return GateDecision(True, True, True, f"{verb} (suite=full)")
    if suite_input == "needs-mac":
        return GateDecision(True, True, False, f"{verb} (suite=needs-mac)")
    return GateDecision(True, False, False, f"{verb} (suite=smoke)")


def decide(
    *,
    event_name: str,
    suite_input: str,
    pr_head_repo: str,
    repository: str,
    pr_draft: str,
    needs_label: str,
    path_hit: str,
) -> GateDecision:
    """Port of the `gate` job's "Decide which tiers should run" step.

    Mirrors the prior inline bash exactly, plus the workflow_call branch
    the bash never had -- workflow_call fell through every elif to the
    unmatched default ("no trigger matched", every tier false), silently
    no-opping rc-gate.yml's mac_regression job. That is the bug this
    module fixes.
    """
    if event_name == "schedule":
        return GateDecision(True, True, True, "nightly schedule")
    if event_name == "workflow_dispatch":
        return _suite_decision(suite_input, verb="manual dispatch")
    if event_name == "workflow_call":
        return _suite_decision(suite_input, verb="reusable workflow call")
    if event_name == "pull_request":
        if pr_head_repo != repository:
            return GateDecision(False, False, False, "pull request from a fork, skipping")
        if pr_draft == "true":
            return GateDecision(False, False, False, "draft pull request, skipping")
        if needs_label == "true":
            return GateDecision(True, True, False, "pull request carries needs-mac label")
        if path_hit == "true":
            return GateDecision(
                True,
                False,
                False,
                "pull request touches mac-sensitive paths without needs-mac label, running smoke tier",
            )
        return GateDecision(
            False,
            False,
            False,
            f"pull request without needs-mac label (path hit: {path_hit})",
        )
    return GateDecision(False, False, False, "no trigger matched")


def append_outputs(decision: GateDecision, *, github_output: str | None = None) -> None:
    """Append the gate decision fields to GITHUB_OUTPUT."""
    output_path = github_output if github_output is not None else os.environ["GITHUB_OUTPUT"]
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"run_smoke={str(decision.run_smoke).lower()}\n")
        output.write(f"run_full={str(decision.run_full).lower()}\n")
        output.write(f"run_review_formulas={str(decision.run_review_formulas).lower()}\n")
        output.write(f"reason={decision.reason}\n")


def main() -> None:
    decision = decide(
        event_name=os.environ.get("EVENT_NAME", ""),
        suite_input=os.environ.get("SUITE_INPUT", ""),
        pr_head_repo=os.environ.get("PR_HEAD_REPO", ""),
        repository=os.environ.get("REPOSITORY", ""),
        pr_draft=os.environ.get("PR_DRAFT", ""),
        needs_label=os.environ.get("NEEDS_LABEL", ""),
        path_hit=os.environ.get("PATH_HIT", ""),
    )
    append_outputs(decision)
    print(f"gate: {decision.reason}")


if __name__ == "__main__":
    main()
