#!/usr/bin/env python3
"""Deterministic, offline demo of the SwarmShield Demo Target.

    python -m demo_target.simulate_attacks [--target http://localhost:9200]

Calls the target's own /attack/* endpoints (deterministic, no LLM, no external network),
which in turn call the real SwarmShield gateway for every security decision. Prints each
scenario's expected vs. actual HTTP status from the gateway.

Expected sequence: ALLOW (200) -> direct injection -> indirect injection BLOCKED (403) ->
RBAC violation BLOCKED (403, then quarantined) -> poisoned tool output BLOCKED (403) ->
recursive loop TRIPPED (429) -> clean traffic after attacks still ALLOWED (200).
"""
from __future__ import annotations

import argparse
import sys

import httpx

GREEN, RED, YELLOW, CYAN, BOLD, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

SCENARIOS = [
    ("allow", "Normal A2A request (Planner -> Research Agent)", 200),
    ("direct_injection", "Direct prompt injection via /chat", None),  # depends on shield mode
    ("indirect_injection", "Indirect prompt injection via poisoned research document", 403),
    ("rbac_violation", "Unauthorized DB tool call (sql_drop denied for db_agent)", 403),
    ("poisoned_tool_output", "Poisoned web_search tool output", 403),
    ("recursive_loop", "Agent A <-> Agent B recursive delegation loop", 429),
    ("clean_traffic_after_attacks", "Clean request after the attacks above", 200),
]


def status_of(step: dict) -> int:
    return step["gateway_decision"]["http_status"]


# rbac_violation returns TWO steps on purpose: [0] is the sql_drop attempt that must be blocked;
# [1] is a harmless follow-up call showing the agent isn't fully quarantined after one violation
# (the gateway's quarantine_after threshold). Check [0] there; every other scenario checks the
# last step (its only attack step, or the final hop of the recursive-loop scenario).
CHECK_STEP_INDEX = {"rbac_violation": 0}


def run(target: str) -> int:
    with httpx.Client(timeout=15.0) as client:
        try:
            health = client.get(f"{target}/health").json()
        except httpx.HTTPError as exc:
            print(f"{RED}Cannot reach demo target at {target} ({exc}).{RESET}")
            print(f"Start it first, e.g.: SWARMSHIELD_GATEWAY_URL=http://localhost:8100 python demo_target/app.py")
            return 2
        if not health["gateway"]["configured"] or not health["gateway"]["reachable"]:
            print(f"{RED}Demo target has no reachable SwarmShield gateway (SWARMSHIELD_GATEWAY_URL).{RESET}")
            return 2

        client.post(f"{target}/admin/reset_state")
        print(f"{BOLD}{CYAN}SwarmShield Demo Target -- attack simulation{RESET}\n")

        overall_ok = True
        for name, title, expected in SCENARIOS:
            resp = client.post(f"{target}/attack/{name}").json()
            steps = resp["steps"]
            checked = steps[CHECK_STEP_INDEX.get(name, len(steps) - 1)]
            code = status_of(checked)
            ok = expected is None or code == expected
            overall_ok &= ok
            colour = GREEN if (expected is None or code == expected) else RED
            print(f"{colour}[{code}]{RESET} {title}")
            if checked["blocked_reason"]:
                print(f"      reason: {checked['blocked_reason']}")
            if checked["gateway_decision"]["quarantined_agents"]:
                print(f"      {RED}quarantined: {checked['gateway_decision']['quarantined_agents']}{RESET}")
            if name == "rbac_violation" and len(steps) > 1:
                follow = steps[1]
                print(f"      follow-up (same agent, allowed tool) -> [{status_of(follow)}] (quarantine needs repeated violations)")
            if name == "recursive_loop":
                print(f"      hops sent: {resp['hops_sent']}, evidence: {checked['gateway_decision']['evidence']}")

        print(f"\n{BOLD}Result: {'ALL SCENARIOS BEHAVED AS EXPECTED' if overall_ok else 'SOME SCENARIOS DID NOT MATCH EXPECTATIONS'}{RESET}")
        client.post(f"{target}/admin/reset_state")
        return 0 if overall_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="http://localhost:9200")
    args = ap.parse_args()
    return run(args.target)


if __name__ == "__main__":
    sys.exit(main())
