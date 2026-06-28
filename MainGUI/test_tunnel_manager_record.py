import time
import subprocess

# Import your class (adjust the module name to where you put it)
# e.g. from ssh_tunnel_recording_manager import SshTunnelRecordingManager, TunnelConfig
from ssh_tunnel_recording_manager import SshTunnelRecordingManager, TunnelConfig


def main():
    save_dir = "/home/mxwbio/Data/recordings"
    file_prefix = "TUNNEL_TEST"

    rec = SshTunnelRecordingManager(
        save_dir=save_dir,
        file_prefix=file_prefix,
        tunnel=TunnelConfig(
            ssh_user="mxwbio",
            ssh_host="132.77.68.106",
            local_port=7215,
            remote_host="127.0.0.1",
            remote_port=7215,
        ),
        wells=[0],                  # MaxOne
        manage_tunnel_process=True, # auto-start tunnel
        raw_enabled_default=True,
        raw_channels_default="all",
    )

    print("1) Connecting (tunnel + mx.initialize)...")
    rec.connect()
    print("   Connected.")

    try:
        print("2) Start RAW recording for 5 seconds...")
        fname = rec.start_recording("raw5s", raw_enabled=True)
        print("   File name:", fname)

        time.sleep(5)

        print("3) Stop recording...")
        rec.stop_recording()
        print("   Stopped.")

    finally:
        print("4) Disconnecting...")
        rec.disconnect()
        print("   Disconnected.")

    # Optional: verify on server that something new appeared in the save directory
    print("5) Server-side check (ls -lt):")
    cmd = ["ssh", "mxwbio@132.77.68.106", "bash", "-lc", f"ls -lt {save_dir} | head -n 5"]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
