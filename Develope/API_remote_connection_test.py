"""
Run this from the repo root:
$ python tools/connection_monitor.py
"""

import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "..", "MainGUI")))

from remote_recording_manager import RemoteRecordingManager


def main():
    print("=== Maxwell 24-hour link-test ===")
    rrm = RemoteRecordingManager()

    try:
        rrm.connect()
        # 24 h = 86 400 s; adjust heartbeat to taste (here: every 60 s).
        uptime = rrm.monitor_until_timeout(check_interval_sec=600,
                                           max_duration_sec=60* 60 * 24,
                                           csv_path="mxw_uptime.csv")
        print(f"\nSummary: connection stayed up for "
              f"{uptime/3600:,.2f} hours.")
    finally:
        rrm.disconnect()


if __name__ == "__main__":
    main()
