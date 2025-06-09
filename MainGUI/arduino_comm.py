import time
import serial

class ArduinoComm:
    def __init__(self, serial_port, timeout=5):
        self.serial = serial_port
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
        """
        Sends message like: [1,2,3],1000,200\n
        """
        indices_str = ','.join(map(str, indices))
        message = f"[{indices_str}],{period},{on_time}\n"

        if len(message.encode()) > 60:
            raise ValueError("Message too long for Arduino serial buffer (max ~60 bytes)")

        self.serial.reset_input_buffer()
        self.serial.write(message.encode())
        print(f"Sent to Arduino: {message.strip()}")

        return self._wait_for_ack()

    def _wait_for_ack(self):
        start = time.time()
        while time.time() - start < self.timeout:
            if self.serial.in_waiting > 0:
                try:
                    response = self.serial.readline().decode().strip()
                    if response == "Message received":
                        return True
                except Exception as e:
                    print(f"Serial read error: {e}")
                    break
        print("Timeout: Arduino did not acknowledge message")
        return False

    def wait_for_sequence_end(self):
        start = time.time()
        while time.time() - start < self.timeout * 10:  # Allow long sequence
            if self.serial.in_waiting > 0:
                try:
                    response = self.serial.readline().decode().strip()
                    if "Sequence finished" in response:
                        return response
                except Exception as e:
                    print(f"Error waiting for Arduino sequence end: {e}")
                    break
        return None
    def close(self):
        """Close the serial connection."""
        if self.serial.is_open:
            self.serial.close()
            print("Arduino serial connection closed.")
        else:
            print("Arduino serial connection was already closed.")