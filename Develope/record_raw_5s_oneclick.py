import datetime as dt
import time
import socket
import subprocess
import sys

import maxlab as mx

SSH_USER = "mxwbio"
SSH_HOST = "132.77.68.106"
LOCAL_PORT = 7215
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 7215

SAVE_DIR = "/home/mxwbio/Data/recordings"
DURATION_S = 5.0

WELL = 0
GROUP_NAME = "all_channels"
CHANNELS = list(range(1024))  # 0..1023


def port_is_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_tunnel() -> subprocess.Popen:
    cmd = [
        "ssh",
        "-N",
        "-L", f"{LOCAL_PORT}:{REMOTE_HOST}:{REMOTE_PORT}",
        f"{SSH_USER}@{SSH_HOST}",
    ]
    # Hide ssh output; keep handle so we can stop it
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_tunnel(timeout_s: float = 3.0) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if port_is_open("127.0.0.1", LOCAL_PORT):
            return
        time.sleep(0.05)
    raise RuntimeError("Tunnel did not come up (local port 7215 not reachable).")


def record_raw_5s() -> str:
    mx.initialize()
    s = mx.Saving()
    s.open_directory(SAVE_DIR)

    file_name = "raw_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    s.start_file(file_name)

    s.group_delete_all()
    s.group_define(WELL, GROUP_NAME, CHANNELS)

    s.start_recording()  # MaxOne
    time.sleep(DURATION_S)
    s.stop_recording()
    s.stop_file()

    return file_name


def main() -> int:
    tunnel_proc = None
    try:
        # If you already have a tunnel running, we won't start another one
        if not port_is_open("127.0.0.1", LOCAL_PORT):
            tunnel_proc = start_tunnel()
            wait_for_tunnel(timeout_s=5.0)

        fname = record_raw_5s()
        print("Done:", fname)
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    finally:
        if tunnel_proc is not None:
            tunnel_proc.terminate()
            try:
                tunnel_proc.wait(timeout=5)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
