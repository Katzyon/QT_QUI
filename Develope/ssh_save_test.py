import socket
import subprocess
import time
import maxlab as mx


def port_is_open(host="127.0.0.1", port=7215, timeout=0.2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_ssh_tunnel():
    if port_is_open():
        print("Tunnel already running")
        return None

    cmd = [
        "ssh",
        "-N",
        "-o", "ExitOnForwardFailure=yes",
        "-L", "7215:127.0.0.1:7215",
        "mxwbio@132.77.68.106",
    ]
    proc = subprocess.Popen(cmd)

    for _ in range(100):
        if port_is_open():
            print("Tunnel ready")
            return proc
        time.sleep(0.1)

    raise RuntimeError("SSH tunnel failed to start")


def main():
    ssh_proc = start_ssh_tunnel()

    try:
        mx.initialize()

        wells = [0]
        mx.activate(wells)

        # Example: route some electrodes first.
        # Replace this with your real electrode list or config.
        electrodes = [4885, 4666, 4886, 4022, 5327, 5328, 5106, 5326, 5562, 5563]

        array = mx.Array("recording")
        array.select_electrodes(electrodes)
        array.route()
        array.download()
        time.sleep(mx.Timing.waitAfterDownload)

        # mx.offset()
        # time.sleep(mx.Timing.waitInMX2Offset)

        # This is the documented spike/event threshold API.
        mx.set_event_threshold(3.5)
        mx.clear_events()

        s = mx.Saving()
        s.open_directory("/home/mxwbio/Data/recordings/")   # change this
        s.set_legacy_format(True)     # spikes
        s.start_file("test_spikes")
        time.sleep(1)
        s.start_recording(wells)

        print("Recording spikes for 10 s...")
        time.sleep(10)

        s.stop_recording()
        s.stop_file()
        print("Done")

    finally:
        if ssh_proc is not None:
            ssh_proc.terminate()


if __name__ == "__main__":
    main()