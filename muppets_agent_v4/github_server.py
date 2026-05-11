"""
MCP server — GitHub Show Runsheet.
Reads Show_Runsheet.md from the muppets-show GitHub repo.
Spawned as a subprocess by ADK's MCPToolset (stdio transport).

Set GITHUB_TOKEN env var to avoid rate limits (not required for public repos).
"""

import base64
import os

import requests
from mcp.server.fastmcp import FastMCP

_REPO = "taffeh/muppets-show"
_FILE = "Show_Runsheet.md"

mcp = FastMCP("muppets-github")


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@mcp.tool()
def get_show_runsheet() -> str:
    """Read tonight's Muppet Show runsheet from GitHub. Returns the full markdown."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{_REPO}/contents/{_FILE}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        content = base64.b64decode(resp.json()["content"]).decode("utf-8")
        return content
    except Exception as exc:
        return f"Runsheet unavailable: {exc}"


@mcp.tool()
def create_github_issue(title: str, body: str) -> str:
    """Create a new issue in the muppets-show repo. Returns the issue number and URL."""
    try:
        if not os.environ.get("GITHUB_TOKEN"):
            return "Cannot create issue: GITHUB_TOKEN not set."
        resp = requests.post(
            f"https://api.github.com/repos/{_REPO}/issues",
            headers=_headers(),
            json={"title": title, "body": body},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return f"Issue #{data['number']} created: {data['html_url']}"
    except Exception as exc:
        return f"Failed to create issue: {exc}"


@mcp.tool()
def close_github_issue(issue_number: int, comment: str) -> str:
    """Add a comment to an issue then close it. Returns confirmation."""
    try:
        if not os.environ.get("GITHUB_TOKEN"):
            return "Cannot close issue: GITHUB_TOKEN not set."
        base = f"https://api.github.com/repos/{_REPO}/issues/{issue_number}"
        requests.post(f"{base}/comments", headers=_headers(), json={"body": comment}, timeout=10)
        resp = requests.patch(base, headers=_headers(), json={"state": "closed"}, timeout=10)
        resp.raise_for_status()
        return f"Issue #{issue_number} closed."
    except Exception as exc:
        return f"Failed to close issue: {exc}"


@mcp.tool()
def reopen_github_issue(issue_number: int, comment: str) -> str:
    """Add a comment to an issue then reopen it. Returns confirmation."""
    try:
        if not os.environ.get("GITHUB_TOKEN"):
            return "Cannot reopen issue: GITHUB_TOKEN not set."
        base = f"https://api.github.com/repos/{_REPO}/issues/{issue_number}"
        requests.post(f"{base}/comments", headers=_headers(), json={"body": comment}, timeout=10)
        resp = requests.patch(base, headers=_headers(), json={"state": "open"}, timeout=10)
        resp.raise_for_status()
        return f"Issue #{issue_number} reopened."
    except Exception as exc:
        return f"Failed to reopen issue: {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
