#!/usr/bin/env python3
"""Keep test connection metadata and credentials out of command history/output."""

import argparse
import getpass
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import warnings
import urllib.parse
import urllib.request
from privacy import private_path, private_directory, state_directory, write_new
from processes import own_process_tree


STATE = state_directory()
HERE = Path(__file__).resolve().parent


def store_key():
    if not sys.stdin.isatty():
        raise ValueError("Run this command in your own interactive terminal.")
    destination = private_path(STATE / "runtime.key")
    if destination.exists():
        raise ValueError("A runtime key file already exists; it was not overwritten.")
    print("Paste the NEW tunnel runtime key here. Input is hidden; never paste it into chat.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        value = getpass.getpass("Runtime key (hidden): ").strip()
    if not value.startswith("sk-") or len(value) < 30 or any(c.isspace() for c in value):
        raise ValueError("The runtime key format was not recognized. Nothing was saved.")
    write_new(destination, value)
    value = ""
    print("Runtime key saved privately. Tell Codex: Key ready. Do not send the key.")


def health_summary(snapshot):
    """Keep operational evidence; omit URLs, identifiers, tool payloads and logs."""
    components = snapshot.get("components", {})
    def details(name):
        return components.get(name, {}).get("details", {})
    return {
        "live": snapshot.get("live", False),
        "startup_ready": snapshot.get("ready", False),
        "poll_failures": details("control-plane").get("consecutive_failures"),
        "requests_received": details("queue").get("enqueued", 0),
        "requests_completed": details("dispatcher").get("completed", 0),
        "requests_failed": details("dispatcher").get("failures", 0),
        "requests_active": details("dispatcher").get("active", 0),
    }


def local_health():
    health_file = private_path(STATE / "health.url")
    if not health_file.exists():
        return {"live": False, "reason": "client_not_started"}
    address = health_file.read_text().strip()
    parts = urllib.parse.urlsplit(address)
    if (parts.scheme != "http" or parts.hostname != "127.0.0.1" or not parts.port
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.path not in ("", "/")):
        raise ValueError("Invalid local health address.")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(address.rstrip("/") + "/health?details=true", timeout=5) as response:
            snapshot = json.loads(response.read(262144))
        return health_summary(snapshot)
    except Exception:
        return {"live": False, "reason": "health_unavailable"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("key", "status", "health", "doctor", "run"))
    parser.add_argument("--client", help="Path to the verified official tunnel-client executable.")
    args = parser.parse_args()
    try:
        os.umask(0o077)
        private_directory(STATE)
        if args.command == "key":
            store_key()
            return 0
        if args.command == "health":
            print(json.dumps(local_health()))
            return 0
        metadata_path = private_path(STATE / "connection.json")
        key_path = private_path(STATE / "runtime.key")
        if args.command == "status":
            print(json.dumps({"tunnel_configured": metadata_path.exists(), "key_file_present": key_path.exists()}))
            return 0
        if not metadata_path.exists() or not key_path.exists() or not args.client:
            raise ValueError("A saved tunnel, user-entered runtime key and verified client path are required.")
        metadata = json.loads(metadata_path.read_text())
        tunnel_id = metadata.get("tunnel_id", "")
        if not tunnel_id.startswith("tunnel_") or not all(c.isalnum() or c in "_-" for c in tunnel_id):
            raise ValueError("Invalid tunnel metadata.")
        command = [args.client, args.command,
                   "--control-plane.tunnel-id", tunnel_id,
                   "--control-plane.api-key", "file:" + str(key_path),
                   "--mcp.command", shlex.join([sys.executable, '-I', '-u', '-c',
                       "import sys,runpy; from pathlib import Path; p=Path(sys.argv.pop(1)); sys.path.insert(0,str(p.parent)); runpy.run_path(str(p),run_name='__main__')",
                       str(HERE / "relay.py"), "--state", str(STATE), "serve"])]
        if args.command == "doctor":
            command += ["--json"]
        else:
            command += ["--health.listen-addr", "127.0.0.1:0",
                        "--health.url-file", str(STATE / "health.url"), "--log.level", "warn",
                        "--log.format", "json", "--log.file", "", "--log.http-raw-unsafe=false"]
        # The vendor may include private identifiers in diagnostics. Suppress raw
        # output; use the loopback health endpoint for readiness after launch.
        print("Running the official tunnel client; raw diagnostics are suppressed.", flush=True)
        job = own_process_tree()
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        print(json.dumps({"operation": args.command, "exit_code": result.returncode}))
        return result.returncode
    except (ValueError, FileExistsError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Stopped.")
        return 130
    except Exception:
        print("Setup failed. Private details were suppressed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
