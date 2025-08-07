import csv
import datetime as dt
import time
from maxlab.comm import ApiComm
from maxlab.system import DelaySamples 

class RemoteRecordingManager:
    def __init__(self,
                 host="132.77.68.106",
                 port=7215,
                 save_dir="/home/mxwbio/Data/recordings",
                 file_prefix="protocol_stage"):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.file_prefix = file_prefix
        self.api = None
        self.send = None

    def connect(self) -> None:
        self.api = ApiComm(self.host, self.port)
        self.send = self.api.send
        print(f"[{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}] Disconnected from Maxwell server.")


    def disconnect(self) -> None:
        if self.api:
            self.api.shutdown()
            self.api = None
            self.send = None
            print(f"[{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}] Disconnected from Maxwell server.")


    def start_recording(self, stage_index):
        file_name = f"{self.file_prefix}_{stage_index}"

        print("Sending offset command...")
        self.send("system_offset")
        print("Waiting 11 seconds for offset to complete...")
        time.sleep(11)

        print(f"Opening directory: {self.save_dir}")
        self.send(f"saving_open_dir {self.save_dir}")
    
        print(f"Starting file: {file_name}")
        self.send(f"saving_start_file {file_name}") 

        time.sleep(1) 

        print("Starting recording...")
        self.send("saving_start_recording")
        print("Recording started...")

    def stop_recording(self):
        print("Stopping recording...")
        self.send("saving_stop_recording")

        print("Closing file...")
        self.send("saving_stop_file")

    def ping(self, timeout_s: float = 2.0) -> bool:
        """
        Ask the server for its command list (`help`).
        If we get any reply at all, the link is alive.
        """
        if self.send is None:
            raise RuntimeError("Not connected.")
        try:
            #reply = self.send("maxlab.system.StatusOut")
            #reply = DelaySamples(0).send(self.api)
            #reply = DelaySamples(0).send(self.api)
            reply = self.send("saving_stop_recording")
            print(f"Ping reply: {reply}")
            ans = True
            
        except Exception as e:
            print(f"Ping failed: {e}")
            ans = False

        return ans

    def monitor_until_timeout(self,
                              check_interval_sec: int = 30,
                              max_duration_sec: int | None = None,
                              csv_path: str | None = None) -> float:
        """
        Loop until the link dies (ping fails) or until `max_duration_sec`
        elapses.  Returns the number of seconds the connection stayed alive.

        * check_interval_sec  heartbeat frequency
        * max_duration_sec    stop after N seconds even if still alive
        * csv_path            if given, append rows:
                               timestamp, ok_flag (0/1), uptime_sec
        """
        if self.send is None:
            raise RuntimeError("Not connected.")

        logf = open(csv_path, "w", newline="") if csv_path else None
        writer = csv.writer(logf) if logf else None
        if writer:
            writer.writerow(["timestamp_now", "ok", "uptime_sec"])

        print("Monitoring connection …")
        t_start = time.monotonic()
        while True:
            ok = self.ping()
            uptime = time.monotonic() - t_start
            ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            print(f"{ts}  alive={ok}  uptime={uptime:,.0f}s")

            if writer:
                writer.writerow([ts, int(ok), round(uptime, 1)])

            if not ok:
                print("Lost heartbeat — exiting monitor loop.")
                break
            if max_duration_sec and uptime >= max_duration_sec:
                print("Reached max_duration without error.")
                break

            time.sleep(check_interval_sec)

        if logf:
            logf.close()
        return uptime
