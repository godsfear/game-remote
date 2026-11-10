"""Milestone 0 risk check: does injected input reach your games, and how fast?

Run on the Windows PC, from the repository root:

    pip install -e .
    python tools/input_check.py key KeyM --delay 5
        Switch to the game within 5 seconds; the script taps M three times and
        prints which program had focus and whether it runs as administrator.

    python tools/input_check.py serve
        Prints a link to open on the phone (same Wi-Fi). The link carries a
        secret, so other devices on the network cannot press keys. The page has tap
        and hold buttons, sends them over WebSocket and shows the round trip.
        Allow Python through Windows Firewall on private networks if asked.

Record the results in docs/input-check.md (template in that file).
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import itertools
import json
import secrets
import socket
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game_remote.input import Combo, InputController, InputError  # noqa: E402
from game_remote.input.backend import default_backend  # noqa: E402
from game_remote.input.windows import (  # noqa: E402
    foreground_info,
    input_blocked_by_elevation,
    self_is_elevated,
)


def describe_foreground() -> dict:
    info = foreground_info()
    return {
        "exe": info.exe_name,
        "title": info.title,
        "elevated": info.elevated,
        "blocked": input_blocked_by_elevation(info),
    }


async def run_key(args: argparse.Namespace) -> None:
    combo = Combo.parse(args.combo)
    controller = InputController(default_backend(), tap_ms=args.hold)
    print(f"Game Remote running as administrator: {self_is_elevated()}")
    for left in range(args.delay, 0, -1):
        print(f"Switch to the game... {left}", flush=True)
        await asyncio.sleep(1)
    for i in range(args.repeat):
        fg = describe_foreground()
        print(f"[{i + 1}/{args.repeat}] {combo.label()} -> {fg}")
        if fg["blocked"]:
            print("  The focused program runs as administrator: Windows will drop this input.")
        try:
            await controller.tap(combo)
        except InputError as exc:
            print(f"  SendInput failed: {exc}")
        await asyncio.sleep(args.gap / 1000)
    print("Done. Did the game react each time?")


PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>Input check</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#15171c;color:#e8e9ec;
 -webkit-user-select:none;user-select:none}
#status{margin-bottom:12px;color:#9aa0ab}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
button{font-size:20px;padding:28px 8px;border-radius:14px;border:0;background:#2b3040;color:#fff;
 touch-action:none}
button.on{background:#3d6df2}
input{font-size:18px;padding:8px;width:60%;margin-right:8px}
#log{font:12px monospace;white-space:pre-wrap;margin-top:12px;color:#9aa0ab;max-height:40vh;overflow:auto}
</style></head><body>
<div id="status">connecting...</div>
<div class="grid">
 <button data-mode="tap" data-combo="KeyM">Tap M</button>
 <button data-mode="tap" data-combo="ControlLeft+KeyR">Tap Ctrl+R</button>
 <button data-mode="hold" data-combo="KeyW">Hold W</button>
 <button data-mode="hold" data-combo="ShiftLeft">Hold Shift</button>
 <button data-mode="hold" data-combo="Space">Hold Space</button>
 <button data-mode="tap" data-combo="Escape">Tap Esc</button>
</div>
<p><input id="custom" value="KeyF" placeholder="KeyF or ControlLeft+KeyS">
<button id="customBtn" data-mode="tap" data-combo="KeyF" style="padding:10px 16px">Tap</button></p>
<div id="log"></div>
<script>
const status = document.getElementById('status');
const logEl = document.getElementById('log');
const log = m => { logEl.textContent = m + '\\n' + logEl.textContent.slice(0, 4000); };
let ws, rtts = [], seq = 0;
const pending = new Map();
function connect(){
  ws = new WebSocket(`ws://${location.host}/ws${location.search}`);
  ws.onopen = () => { status.textContent = 'connected'; };
  ws.onclose = () => { status.textContent = 'disconnected, retrying...'; setTimeout(connect, 1000); };
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.type === 'pong') {
      rtts.push(performance.now() - m.t); if (rtts.length > 20) rtts.shift();
      const s = [...rtts].sort((a,b)=>a-b);
      status.textContent = `connected, round trip median ${s[s.length>>1].toFixed(0)} ms, max ${s[s.length-1].toFixed(0)} ms`;
    } else if (m.type === 'ack') {
      const t0 = pending.get(m.id); pending.delete(m.id);
      const ms = t0 ? (performance.now() - t0).toFixed(0) : '?';
      const fg = m.foreground || {};
      log(`${m.action} ${m.combo}: ${m.ok ? 'sent' : 'REJECTED ' + m.error} in ${ms} ms ` +
          `(server ${m.server_ms} ms) -> ${fg.exe} ${fg.blocked ? '[ADMIN: input dropped]' : ''}`);
      if (navigator.vibrate && m.ok && m.action !== 'up') navigator.vibrate(15);
    }
  };
}
function send(action, combo){
  if (!ws || ws.readyState !== 1) return;
  const id = ++seq; pending.set(id, performance.now());
  ws.send(JSON.stringify({type: action, id, combo}));
}
setInterval(() => { if (ws && ws.readyState === 1) ws.send(JSON.stringify({type:'ping', t: performance.now()})); }, 1000);
document.querySelectorAll('button[data-mode]').forEach(b => {
  const combo = () => b.id === 'customBtn' ? document.getElementById('custom').value.trim() : b.dataset.combo;
  if (b.dataset.mode === 'tap') {
    b.addEventListener('pointerdown', e => { e.preventDefault(); send('tap', combo()); });
  } else {
    let down = false;
    const up = () => { if (down) { down = false; b.classList.remove('on'); send('up', combo()); } };
    b.addEventListener('pointerdown', e => { e.preventDefault(); b.setPointerCapture(e.pointerId);
      down = true; b.classList.add('on'); send('down', combo()); });
    b.addEventListener('pointerup', up); b.addEventListener('pointercancel', up);
  }
});
document.addEventListener('contextmenu', e => e.preventDefault());
connect();
</script></body></html>
"""


def lan_addresses() -> list[str]:
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # no packet is sent; picks the default route
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if addr not in found and not addr.startswith("127."):
                found.append(addr)
    except OSError:
        pass
    return found


def build_app(controller: InputController, token: str):
    """Test page plus a WebSocket that injects keys.

    The socket accepts any key combo, so it only talks to clients that know
    ``token`` (it is part of the link printed in the console).
    """
    app = FastAPI()
    counter = itertools.count(1)
    background: set[asyncio.Task] = set()

    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse(PAGE)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        if not hmac.compare_digest(ws.query_params.get("k", ""), token):
            await ws.close(code=1008)
            return
        await ws.accept()
        source = f"phone-{next(counter)}"
        print(f"{source} connected from {ws.client}")
        try:
            while True:
                msg = json.loads(await ws.receive_text())
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong", "t": msg.get("t")}))
                    continue
                action = msg.get("type")
                started = time.perf_counter()
                reply = {
                    "type": "ack",
                    "id": msg.get("id"),
                    "action": action,
                    "combo": msg.get("combo"),
                    "ok": True,
                    "error": None,
                }
                try:
                    combo = Combo.parse(msg.get("combo", ""))
                    reply["foreground"] = describe_foreground()
                    if action == "tap":
                        # Ack once the key is down; release runs in the background.
                        task = asyncio.create_task(controller.tap(combo))
                        background.add(task)
                        task.add_done_callback(background.discard)
                    elif action == "down":
                        controller.hold(source, combo)
                    elif action == "up":
                        controller.unhold(source, combo)
                    else:
                        raise ValueError(f"unknown action {action!r}")
                except (ValueError, InputError) as exc:
                    reply.update(ok=False, error=str(exc))
                reply["server_ms"] = round((time.perf_counter() - started) * 1000, 2)
                print(f"{source}: {reply}")
                await ws.send_text(json.dumps(reply))
        except WebSocketDisconnect:
            pass
        finally:
            controller.release_all(source)
            print(f"{source} disconnected, its keys were released")

    return app


def run_serve(args: argparse.Namespace) -> None:
    import uvicorn

    controller = InputController(default_backend(), tap_ms=args.hold)
    print(f"Game Remote running as administrator: {self_is_elevated()}")
    print("Open on the phone (same Wi-Fi):")
    token = secrets.token_urlsafe(9)
    for addr in lan_addresses():
        print(f"  http://{addr}:{args.port}/?k={token}")
    print("Also try the computer name (it survives IP changes; may not work on every phone):")
    print(f"  http://{socket.gethostname()}.local:{args.port}/?k={token}")
    print("The link contains a secret for this run: without it the page cannot press keys.")
    uvicorn.run(build_app(controller, token), host="0.0.0.0", port=args.port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--hold", type=int, default=40, help="key hold time for taps, ms")
    sub = parser.add_subparsers(dest="cmd", required=True)
    key = sub.add_parser("key", help="tap a combo after a countdown")
    key.add_argument("combo", help="KeyboardEvent.code values joined by +, e.g. ControlLeft+KeyR")
    key.add_argument("--delay", type=int, default=5)
    key.add_argument("--repeat", type=int, default=3)
    key.add_argument("--gap", type=int, default=700, help="pause between taps, ms")
    serve = sub.add_parser("serve", help="serve a test page for the phone")
    serve.add_argument("--port", type=int, default=8731)
    args = parser.parse_args()
    if sys.platform != "win32":
        print("Not on Windows: key events are only recorded, nothing is injected.")
    if args.cmd == "key":
        asyncio.run(run_key(args))
    else:
        run_serve(args)


if __name__ == "__main__":
    main()
