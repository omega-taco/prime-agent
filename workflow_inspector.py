#!/usr/bin/env python3
"""workflow-inspector - Python-native sub-agent for GitHub Actions workflow investigation."""

import json
import re
from pathlib import Path
import yaml


WORKFLOW_DIR = Path("/home/user/projects/agent-governance/.github/workflows")
FACTORY_DIR = Path("/home/user/projects/agent-governance/factory")


def get_env_section(text: str) -> str:
    """Extract the env: section from workflow YAML."""
    # Find env: and everything until the next top-level key
    start = text.find("env:")
    if start == -1:
        return ""
    # Find the next top-level key (2 spaces then a word followed by : at start of line)
    remaining = text[start:]
    # Simple approach: find env section until next job: or similar
    end_markers = ["jobs:", "permissions:", "concurrency:"]
    end = len(remaining)
    for marker in end_markers:
        idx = remaining.find(marker)
        if idx != -1 and idx < end:
            end = idx
    return remaining[:end]


def inspect_workflow(workflow_path: Path) -> dict:
    """Inspect a GitHub Actions workflow file."""
    try:
        text = workflow_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"path": str(workflow_path), "error": f"Cannot read: {e}"}

    env_text = get_env_section(text)
    env_vars = {}
    if env_text:
        try:
            # Parse just the env section as YAML
            # env section is like:  GITHUB_REPOSITORY: omega-taco/agent-governance
            # we need to extract key: value pairs
            for line in env_text.strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    env_vars[key.strip()] = value.strip()
        except Exception:
            pass

    # Check for required GitHub Actions vars
    missing_standard = []
    for var in ["GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF"]:
        if var not in env_vars:
            missing_standard.append(var)

    # Check for GITHUB_REPO
    has_github_repo = "GITHUB_REPO" in env_vars

    # Check if running on local-gh-runners
    runs_on_local_gh = "runs-on" in text and "local-gh-runners" in text

    local_gh_issue = None
    if runs_on_local_gh and not has_github_repo:
        local_gh_issue = {
            "type": "missing_github_vars_on_local_runner",
            "issue": "Workflow runs on local-gh-runners but GITHUB_REPOSITORY/GITHUB_REPO not set in env",
            "recommendation": "Add GITHUB_REPOSITORY and/or GITHUB_REPO to workflow env section"
        }

    return {
        "path": str(workflow_path),
        "env_vars": env_vars,
        "missing_standard_github_vars": missing_standard,
        "has_nonstandard_github_repo": has_github_repo,
        "runs_on_local_gh_runners": runs_on_local_gh,
        "local_gh_issue": local_gh_issue
    }


def main():
    """Inspect workflows."""
    import sys

    results = []

    # Inspect all workflows in agent-governance
    if WORKFLOW_DIR.exists():
        for wf in sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml")):
            results.append(inspect_workflow(wf))

    # Also check factory manifests
    manifest_dir = Path("/home/user/projects/agent-governance/factory/manifests")
    if manifest_dir.exists():
        for mf in sorted(manifest_dir.glob("*.yaml")):
            results.append(inspect_workflow(mf))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
