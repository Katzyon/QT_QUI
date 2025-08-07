import time
import serial

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

        if len(message.encode()) > 60:
            raise ValueError("Message too long for Arduino serial buffer (max ~60 bytes)")

        self.arduino.reset_input_buffer()
        self.arduino.write(message.encode())
        print(f"Sent to Arduino: {message.strip()}")

        return self._wait_for_ack()

    def _wait_for_ack(self):
        start = time.time()
        while time.time() - start < self.timeout:
            if self.arduino.in_waiting > 0:
                try:
                    response = self.arduino.readline().decode().strip()
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
