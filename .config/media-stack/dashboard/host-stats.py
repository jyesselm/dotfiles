"""Write what only the Mac itself knows (CPU, memory, uptime, Tailscale peers) to $DATA_ROOT/dashboard/host.json
once a minute for the dashboard container, which mounts that folder read-only.

    python3 host-stats.py            # write once
    python3 host-stats.py install    # every minute via launchd
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABEL = "com.yesselman.dashboard-host"
TAILSCALE = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


def sh(*cmd: str) -> str:
    # SHLVL makes the Tailscale CLI talk to the running app instead of trying to launch the GUI (fails under launchd).
    env = {**os.environ, "SHLVL": "1"}
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20, env=env).stdout


def stats() -> dict:
    top = sh("top", "-l", "1", "-n", "0")
    cpu = re.search(r"CPU usage: ([\d.]+)% user, ([\d.]+)% sys", top)
    mem = re.search(r"PhysMem: (\d+)M used", top)
    load = re.search(r"Load Avg: ([\d.]+)", top)
    boot = int(re.search(r"sec = (\d+)", sh("sysctl", "-n", "kern.boottime")).group(1))
    peers = {}
    try:
        ts = json.loads(sh(TAILSCALE, "status", "--json"))
        for p in list(ts.get("Peer", {}).values()) + [ts.get("Self", {})]:
            peers[p["TailscaleIPs"][0]] = {"online": p.get("Online", True), "last_seen": p.get("LastSeen"), "os": p.get("OS")}
    except Exception as e:
        print(f"tailscale: {e}", file=sys.stderr)
    return {
        "time": time.time(),
        "cpu_pct": round(float(cpu.group(1)) + float(cpu.group(2))) if cpu else None,
        "mem_used": int(mem.group(1)) * 2**20 if mem else None,
        "mem_total": int(sh("sysctl", "-n", "hw.memsize")),
        "load": float(load.group(1)) if load else None,
        "boot": boot,
        "peers": peers,
    }


def install():
    data_root = re.search(r"^DATA_ROOT=(.*)$", (HERE.parent / ".env").read_text(), re.M).group(1)
    plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Label</key><string>{LABEL}</string>
\t<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{HERE / 'host-stats.py'}</string></array>
\t<key>StartInterval</key><integer>60</integer>
\t<key>RunAtLoad</key><true/>
\t<key>StandardErrorPath</key><string>{data_root}/dashboard/host-stats.log</string>
</dict>
</plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)], check=True)
    print(f"installed {plist}")


if __name__ == "__main__":
    if sys.argv[1:] == ["install"]:
        install()
    else:
        data_root = re.search(r"^DATA_ROOT=(.*)$", (HERE.parent / ".env").read_text(), re.M).group(1)
        out = Path(data_root) / "dashboard" / "host.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(stats()))
        tmp.replace(out)
