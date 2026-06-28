import datetime as dt
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Union

import maxlab as mx


def _port_is_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@dataclass
class TunnelConfig:
    ssh_user: str = "mxwbio"
    ssh_host: str = "132.77.68.106"
    local_port: int = 7215
    remote_host: str = "127.0.0.1"
    remote_port: int = 7215


class SshTunnelRecordingManager:
    """
    Replacement for RemoteRecordingManager that:
      - ensures an SSH local-port-forward is up (Windows -> Linux server)
      - uses maxlab Python API (mx.Saving) to enable raw-trace groups when requested

    Public API intentionally mirrors RemoteRecordingManager:
      connect(), disconnect(), start_recording(prefix), stop_recording()
    """

    def __init__(
        self,
        save_dir: str,
        file_prefix: str,
        tunnel: TunnelConfig = TunnelConfig(),
        wells: Optional[List[int]] = None,
        # default behavior:
        raw_enabled_default: bool = True,
        raw_channels_default: Union[str, Iterable[int]] = "all",
        group_name_default: str = "all_channels",
        # if True, we start a tunnel process ourselves; if False, we assume user started it manually
        manage_tunnel_process: bool = True,
        tunnel_start_timeout_s: float = 5.0,
    ):
        self.save_dir = save_dir
        self.file_prefix = file_prefix

        self.tunnel = tunnel
        self.wells = wells if wells is not None else [0]  # MaxOne safe default

        self.raw_enabled_default = raw_enabled_default
        self.raw_channels_default = raw_channels_default
        self.group_name_default = group_name_default

        self.manage_tunnel_process = manage_tunnel_process
        self.tunnel_start_timeout_s = tunnel_start_timeout_s

        self._ssh_proc: Optional[subprocess.Popen] = None
        self._saving: Optional[mx.Saving] = None

        self._recording_started = False
        self._file_started = False

    # ---------------- core lifecycle ----------------

    def connect(self) -> None:
        """
        Ensure tunnel is up, then initialize mx and create Saving object.
        """
        self._ensure_tunnel()

        # mx.initialize() must be able to reach localhost:7215 (the tunnel endpoint).
        mx.initialize()
        self._saving = mx.Saving() # _saving is the main API object we'll use for recording commands.

        mx.send(mx.system.GPIODirection(0b00000000))

    def disconnect(self) -> None:
        """
        Stop any active recording/file best-effort, then stop tunnel if we own it.
        """
        # Best-effort close
        try:
            if self._saving is not None:
                if self._recording_started:
                    try:
                        self._saving.stop_recording()
                    except Exception:
                        pass
                    self._recording_started = False
                if self._file_started:
                    try:
                        self._saving.stop_file()
                    except Exception:
                        pass
                    self._file_started = False
        finally:
            self._saving = None
            self._stop_tunnel_if_owned()

    # ---------------- recording API ----------------

    def start_recording(
        self,
        stage_index_or_prefix: Union[int, str],
        raw_enabled: Optional[bool] = None,
        raw_channels: Optional[Union[str, Iterable[int]]] = None,
        group_name: Optional[str] = None,
        set_offset: bool = True,
        offset_wait_s: float = 11.0,
    ) -> str:
        """
        Start a recording file and start recording.
        Returns the file name used.

        - raw_enabled=True: use new format + define group before start_recording() (raw traces enabled).
        - raw_enabled=False: use legacy format (no group_define; raw traces not stored).

        Docs: when using new format and wanting traces, must declare electrodes with group_define().
        Example ordering: start_file -> group_define -> start_recording -> stop_recording -> stop_file.
        """
        self.ensure_tunnel_alive() # ensure tunnel is alive before trying to record
        if self._saving is None:
            raise RuntimeError("Recorder not connected. Call connect() first.")

        raw_enabled = self.raw_enabled_default if raw_enabled is None else raw_enabled
        raw_channels = self.raw_channels_default if raw_channels is None else raw_channels
        group_name = self.group_name_default if group_name is None else group_name

        # Optional offset (you were doing this in RemoteRecordingManager).
        if set_offset:
            try:
                mx.offset()
                print("System offset applied.")
            except Exception as e:
                raise RuntimeError(f"Failed to apply system offset: {e}")

            time.sleep(offset_wait_s)

        # Build file name
        file_suffix = str(stage_index_or_prefix)
        file_name = f"{self.file_prefix}_{file_suffix}"

        # Open directory + start file
        self._saving.open_directory(self.save_dir)
        self._saving.start_file(file_name)
        self._file_started = True

        # Select format and optionally define group
        if raw_enabled:
            # Use new file format. API name in docs is set_legacy_format(use: bool).
            try:
                self._saving.set_legacy_format(False)
            except Exception:
                # Some versions expose it differently; if this fails, group_define may still work depending on defaults.
                pass

            # In new format, define at least one group (and for traces you define the channels).
            self._saving.group_delete_all()

            ch_list = self._normalize_channels(raw_channels)
            self._saving.group_define(0, group_name, ch_list)

        else:
            # Legacy format (no raw traces)
            try:
                self._saving.group_define(0, group_name, ch_list)
                self._saving.set_legacy_format(True)
                print("record spikes only (legacy format)")
            except Exception:
                pass

        try:
            mx.send(mx.system.GPIODirection(0b00000000))
            print("GPIO set to INPUT mode (bits recording enabled).")
        except Exception as e:
            print(f"Warning: Failed to set GPIO direction: {e}")
        
        # Start recording (wells param is optional per docs; safe to pass [0]).
        try:
            self._saving.start_recording(self.wells)
        except TypeError:
            self._saving.start_recording()

        self._recording_started = True
        return file_name

    def stop_recording(self) -> None:
        """
        Stop recording and close file.
        Mirrors your old behavior (stop_recording then stop_file).
        """
        if self._saving is None:
            return

        if self._recording_started:
            self._saving.stop_recording()
            self._recording_started = False

        if self._file_started:
            self._saving.stop_file()
            self._file_started = False

        # Optional: clear groups for next recording (matches example pattern).
        try:
            self._saving.group_delete_all()
        except Exception:
            pass

    # ---------------- helpers ----------------

    def _normalize_channels(self, ch: Union[str, Iterable[int]]) -> List[int]:
        if ch == "all":
            return list(range(1024))
        return [int(x) for x in ch]

    def _ensure_tunnel(self) -> None:
        if _port_is_open("127.0.0.1", self.tunnel.local_port):
            return

        if not self.manage_tunnel_process:
            raise RuntimeError(
                f"SSH tunnel not detected on 127.0.0.1:{self.tunnel.local_port}. "
                f"Start it manually first."
            )

        cmd = [
            "ssh",
            "-N",
            "-o", "ServerAliveInterval=60",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-L", f"{self.tunnel.local_port}:{self.tunnel.remote_host}:{self.tunnel.remote_port}",
            f"{self.tunnel.ssh_user}@{self.tunnel.ssh_host}",
        ]

        self._ssh_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for port to open
        t0 = time.time()
        while time.time() - t0 < self.tunnel_start_timeout_s:
            if _port_is_open("127.0.0.1", self.tunnel.local_port):
                return
            time.sleep(0.05)

        # Failed
        self._stop_tunnel_if_owned()
        raise RuntimeError("Tunnel failed to start (local port did not open).")
    
    def ensure_tunnel_alive(self) -> None:
        # If we spawned ssh and it exited, clear the handle
        if self._ssh_proc is not None and self._ssh_proc.poll() is not None:
            self._ssh_proc = None

        # If local port is not reachable, (re)start tunnel (or raise)
        if not _port_is_open("127.0.0.1", self.tunnel.local_port):
            self._ensure_tunnel()


    def _stop_tunnel_if_owned(self) -> None:
        if self._ssh_proc is not None:
            try:
                self._ssh_proc.terminate()
                self._ssh_proc.wait(timeout=5)
            except Exception:
                pass
            self._ssh_proc = None
