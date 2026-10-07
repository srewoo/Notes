"""Fixture-backed stdio MCP server standing in for Jira / GitLab / EnggX / Figma.

Env: MOCK_SERVER (catalogue key), MOCK_FIXTURE (scenario mocks.json), MOCK_LOG (jsonl of calls).
mocks.json: {"<server>": {"only": [tool, ...]?, "tools": {"<tool>": {"response": X} |
             {"by": "<arg>", "responses": {"<value>": X}, "default": X}}}}
Tools without a fixture answer {"ok": true} (writes) or an error (reads), and every call is logged,
so a grader can see a write the skill must never make.
"""
import asyncio
import json
import os

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

CATALOGUE = {
    "atlassian_rovo": {
        "read": ["getAccessibleAtlassianResources", "getJiraIssue", "getJiraIssueRemoteIssueLinks",
                 "getConfluencePage", "searchJiraIssuesUsingJql"],
        "write": ["addCommentToJiraIssue", "transitionJiraIssue", "editJiraIssue", "createJiraIssue"],
    },
    "gitlab": {
        "read": ["search", "get_repository_file", "get_merge_request", "get_merge_request_notes",
                 "list_merge_requests", "list_repository_tree", "get_project"],
        "write": ["add_commit", "add_branch", "save_merge_request", "save_note", "accept_merge_request"],
    },
    "mindtickle_engineering": {
        "read": ["explore_capabilities_tool", "describe_capability_tool", "execute_capability_tool"],
        "write": [],
    },
    "figma": {"read": ["get_design_context", "get_screenshot"], "write": []},
    "auth_only": {"read": ["authenticate", "complete_authentication"], "write": []},
}

SERVER = os.environ["MOCK_SERVER"]
FIXTURE = json.load(open(os.environ["MOCK_FIXTURE"])).get(SERVER, {})
LOG = os.environ.get("MOCK_LOG")
cat = CATALOGUE[SERVER]
TOOLS = FIXTURE.get("only") or cat["read"] + cat["write"]

app = Server(f"mock-{SERVER}")


def answer(name: str, args: dict):
    spec = FIXTURE.get("tools", {}).get(name)
    if spec is None:
        if name in cat["write"]:
            return {"ok": True}
        if SERVER == "auth_only":
            return {"status": "authentication required"}
        raise ValueError(f"{name}: no data for these arguments")
    if "by" in spec:
        key = str(args.get(spec["by"], ""))
        if key in spec["responses"]:
            return spec["responses"][key]
        if "default" in spec:
            return spec["default"]
        raise ValueError(f"{name}: nothing found for {spec['by']}={key}")
    return spec["response"]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name=t, description=f"{t} ({SERVER})",
                       inputSchema={"type": "object", "additionalProperties": True}) for t in TOOLS]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps({"server": SERVER, "tool": name, "arguments": arguments}) + "\n")
    result = answer(name, arguments or {})
    text = result if isinstance(result, str) else json.dumps(result)
    return [types.TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
