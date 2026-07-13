import math
import time
import serial


def build_stdp_message_payload(period_ms, on_time_ms, isi_ms):
    """
    Build the STDP parameters for the Arduino 4-field pair-playback mode.
    
    Arduino 4-field mode expects: [img1,img2],period_ms,on_time_ms,ISI_ms
    
    Args:
        period_ms: Period between repetitions of the pair (in milliseconds)
        on_time_ms: Light/trigger ON time (in milliseconds)
        isi_ms: Inter-stimulus interval between image 1 and image 2 (in milliseconds)
    
    Returns:
        (period_ms, on_time_ms, isi_ms) - validated and ready to send
    """
    period_ms = max(1, int(period_ms))
    on_time_ms = max(1, int(on_time_ms))
    isi_ms = max(1, int(isi_ms))
    
    return period_ms, on_time_ms, isi_ms


class ArduinoComm:
    def __init__(self, arduino, timeout=5):
        self.arduino = arduino  # This is now the serial.Serial object
        self.timeout = timeout

    @staticmethod
    def connect(port='COM13', baudrate=19200, timeout=2):
        """Establish and return an ArduinoComm object."""
        try:
            ser = serial.Serial(port, baudrate, timeout=timeout)
            print(f"Arduino connected on {port}")
            return ArduinoComm(ser)
        except serial.SerialException as e:
            print(f"Failed to connect to Arduino on {port}: {e}")
            return None

    def send_message(self, indices, period, on_time):
        indices_str = ','.join(map(str, indices))
        message = f"[{indices_str}],{period},{on_time}\n"
        #print(f"Sent to Arduino: {message.strip()}")

        if len(message.encode()) > 62:
            raise ValueError("Message too long for Arduino serial buffer (max ~62 bytes)")

        self.arduino.reset_input_buffer()
        self.arduino.write(message.encode())
        

        return self._wait_for_ack()

    def send_stdp_message(
        self,
        period_ms,
        on_time_ms,
        isi_ms,
        pair_count,
    ):
        """
        Send a 4-field STDP pair-playback command in the format:
        [0,1],period_ms,on_time_ms,ISI_ms
        
        This tells Arduino to:
        1. Display image 0 (stdp_mask_1)
        2. Wait ISI_ms
        3. Display image 1 (stdp_mask_2)
        4. Wait until full period_ms from start of image 0
        5. Repeat the pair
        
        Args:
            period_ms: Period between pair repetitions (in milliseconds)
            on_time_ms: Light ON time (in milliseconds)
            isi_ms: Inter-stimulus interval between image 0 and image 1 (in milliseconds)
        """
        period_ms = max(1, int(period_ms))
        on_time_ms = max(1, int(on_time_ms))
        isi_ms = max(1, int(isi_ms))
        pair_count = max(1, int(pair_count))

        # Use 1 and 2 to match regular protocol's 1-based digipin IDs.
        message = (
            f"[1,2],{period_ms},{on_time_ms},"
            f"{isi_ms},{pair_count}\n"
        )

        if len(message.encode()) > 62:
            raise ValueError("STDP message too long for Arduino serial buffer (max ~62 bytes)")

        print(f"Sending STDP message to Arduino: {message.strip()}")
        self.arduino.reset_input_buffer()
        self.arduino.write(message.encode())

        return self._wait_for_ack()

    def _wait_for_ack(self):
        start = time.time()
        while time.time() - start < self.timeout:
            if self.arduino.in_waiting > 0:
                try:
                    response = self.arduino.readline().decode().strip()
                    print(f"Arduino response: {response}")
                    if response == "Message received":
                        return True
                except Exception as e:
                    print(f"Serial read error: {e}")
                    break
        print("Timeout: Arduino did not acknowledge message")
        return False

    def wait_for_sequence_end(self):
        start = time.time()
        while time.time() - start < self.timeout * 2:
            if self.arduino.in_waiting > 0:
                try:
                    response = self.arduino.readline().decode().strip()
                    if "Sequence finished" in response:
                        return response
                except Exception as e:
                    print(f"Error waiting for Arduino sequence end: {e}")
                    break
        return None
    
    def wait_for_sequence_end_blocking(self, stop_event=None):
        while stop_event is None or not stop_event.is_set():
            if self.arduino.in_waiting > 0:
                try:
                    response = self.arduino.readline().decode().strip()
                    if "Sequence finished" in response:
                        return response
                except Exception as e:
                    print(f"Error reading Arduino response: {e}")
                    break
        return None  # Either stopped or failed
