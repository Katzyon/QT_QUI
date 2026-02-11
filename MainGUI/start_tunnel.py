import subprocess
import time
import socket

SSH_USER = "mxwbio"
SSH_HOST = "132.77.68.106"
LOCAL_PORT = 7215
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 7215

def port_is_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def start_tunnel() -> subprocess.Popen:
    # -N: no remote command, just forwarding
    # -L: local port forward
    cmd = [
        "ssh",
        "-N",
        "-L", f"{LOCAL_PORT}:{REMOTE_HOST}:{REMOTE_PORT}",
        f"{SSH_USER}@{SSH_HOST}",
    ]
    # Start in background; keep handle so you can terminate later
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    if port_is_open("127.0.0.1", LOCAL_PORT):
        print(f"Tunnel already active on 127.0.0.1:{LOCAL_PORT}")
        raise SystemExit(0)

    p = start_tunnel()

    # wait briefly for tunnel to come up
    for _ in range(30):
        if port_is_open("127.0.0.1", LOCAL_PORT):
            print(f"Tunnel started (PID {p.pid}) on 127.0.0.1:{LOCAL_PORT}")
            break
        time.sleep(0.1)
    else:
        p.terminate()
        raise RuntimeError("Tunnel failed to start (port did not open).")

    input("Press Enter to stop the tunnel...")
    p.terminate()
    p.wait(timeout=5)
    print("Tunnel stopped.")
