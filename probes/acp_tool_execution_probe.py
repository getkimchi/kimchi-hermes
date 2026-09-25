"""Manual probe: does the Kimchi harness execute its own tools over ACP?

Drives `kimchi --mode acp --yolo` the same way the plugin (via Hermes'
CopilotACPClient shim) does: initialize -> session/new -> session/prompt,
then checks the filesystem artifact.

OQ-B4 verdict recorded 2026-09-25 (kimchi 1.1.35): harness-side execution
is REAL — tool_call session updates observed, artifact verified. No
permission requests fired under YOLO.

Usage: python3 probes/acp_tool_execution_probe.py
"""

import json
import os
import queue
import subprocess
import threading
import time

PROMPT = (
    "Create the file /tmp/kimchi_acp_probe.txt containing exactly PROBE_OK_20260925 "
    "and nothing else. Do it now with a real tool call."
)


def main() -> None:
    proc = subprocess.Popen(
        ["kimchi", "--mode", "acp", "--yolo"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        cwd="/tmp",
        env=dict(os.environ),
    )
    inbox: queue.Queue = queue.Queue()
    stderr_tail: list = []
    threading.Thread(target=lambda: [inbox.put(line) for line in proc.stdout], daemon=True).start()
    threading.Thread(target=lambda: [stderr_tail.append(line) for line in proc.stderr], daemon=True).start()

    ids = iter(range(1, 1 << 30))
    deadline = time.monotonic() + 240
    text_parts, tool_activity = [], []

    def respond(msg):
        if msg.get("method") == "session/request_permission":
            tool_activity.append("PERMISSION_REQUEST (YOLO should suppress): " + json.dumps(msg.get("params", {}))[:160])
            options = (msg.get("params") or {}).get("options") or []
            outcome = (
                {"outcome": {"outcome": "selected", "optionId": options[0].get("optionId", "")}}
                if options
                else {"outcome": {"outcome": "cancelled"}}
            )
            response = {"jsonrpc": "2.0", "id": msg["id"], "result": outcome}
        else:
            response = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "probe: unimplemented"}}
        proc.stdin.write(json.dumps(response) + "\n")
        proc.stdin.flush()

    def request(method, params):
        rid = next(ids)
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n")
        proc.stdin.flush()
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                line = inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "method" in msg:
                if msg.get("id") is not None:
                    respond(msg)
                else:
                    update = (msg.get("params") or {}).get("update") or {}
                    kind = update.get("sessionUpdate")
                    if kind == "tool_call":
                        tool_activity.append("TOOL_CALL: " + str(update.get("title") or update.get("kind")))
                    content = update.get("content") or {}
                    if isinstance(content, dict) and content.get("text") and kind == "agent_message_chunk":
                        text_parts.append(content["text"])
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(method + " failed: " + json.dumps(msg["error"]))
                return msg.get("result")
        raise TimeoutError(method + "; stderr tail: " + repr("".join(stderr_tail)[-300:]))

    try:
        init = request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {"fs": {"readTextFile": True, "writeTextFile": True}},
                "clientInfo": {"name": "kimchi-acp-probe", "title": "OQ-B4 probe", "version": "0"},
            },
        )
        print("agentInfo:", init.get("agentInfo"))
        session = request("session/new", {"cwd": "/tmp", "mcpServers": []})
        print("sessionId:", session.get("sessionId"))
        request("session/prompt", {"sessionId": session["sessionId"], "prompt": [{"type": "text", "text": PROMPT}]})
        print("--- reply text (first 500 chars) ---")
        print("".join(text_parts)[:500])
        print("--- tool activity observed ---")
        print("\n".join("  " + t for t in tool_activity) if tool_activity else "  (none)")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("--- artifact check ---")
    exists = os.path.exists("/tmp/kimchi_acp_probe.txt")
    print("/tmp/kimchi_acp_probe.txt exists:", exists)
    if exists:
        print("content:", repr(open("/tmp/kimchi_acp_probe.txt").read()[:60]))
        os.remove("/tmp/kimchi_acp_probe.txt")
        print("(probe artifact removed)")


if __name__ == "__main__":
    main()
