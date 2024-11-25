import serial
import time
import random

class SerialArduinoTriggers:

    def __init__(self, port='COM13', baudrate=19200, timeout=2):
        """!
        Initialize the SerialArduinoTriggers class.
        """
        self.n_trigger = 10 # number of triggers
        self.running = True
        self.arduino = None
        #self.rand_vector = [random.randint(13, 16) for _ in range(self.n_trigger)]
        self.rand_vector = [random.randint(1,15) for _ in range(self.n_trigger)]
# Check Arduino buffer overflow - send more than 64 bytes: length of the input= (n numbers+commas)*3 + period (2) + on_time (2) + newline (1) = 3*n + 5 = 64
# 3*n = 59, n = 19 - maximum length of the vector
        self.period = 2000 # time between triggers in ms
        self.on_time = 1000 # presentation time in ms

        # Initialize Arduino connection
        if self.connect_arduino(port, baudrate, timeout):
            self.start_sequence()

    def connect_arduino(self, port, baudrate, timeout):
        """
        Connect to the Arduino via serial port.!
        """
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # Wait for Arduino to initialize
            print("Arduino connected.")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to Arduino: {e}")
            self.arduino = None
            return False

    def start_sequence(self):
        """
        Start the sequence by sending the initial message and waiting for responses.
        """
        try:
            # Send initial message to Arduino
            self.send_message(self.rand_vector, self.period, self.on_time)

            # Wait for Arduino responses
            while self.running:
                self.check_arduino_response()
        except Exception as e:
            print(f"Error during sequence: {e}")
        
            

    def send_message(self, rand_vector, period, on_time):
        """
        Create and send a message to the Arduino.
        """
        if not self.arduino:
            print("Arduino is not connected. Cannot send message.")
            return

        message = f"{rand_vector},{period},{on_time}\n" # Create message string
        self.arduino.write(message.encode()) # Send message to Arduino
        print(f"Sent to Arduino: Sequence {rand_vector} with period {period} ms and on_time {on_time} ms")

    def check_arduino_response(self):
        """
        Check for messages from the Arduino and handle them.
        """
        if self.arduino.in_waiting > 0:  # Check if there's data to read
            response = self.arduino.readline().decode().strip()
            print(f"Arduino response: {response}")

            if response == "Message received":
                print("Arduino confirmed message received. Starting sequence.")
            elif response == "Sequence finished":
                print("Sequence repeat completed by Arduino.")
                self.running = False  # Stop the loop
                self.cleanup()

    def cleanup(self):
        """
        Clean up resources before exiting.
        """
        if self.arduino:
            self.arduino.close()
            print("Arduino connection closed.")
        else:
            print("No active Arduino connection to close.")


# Run the class
if __name__ == "__main__":
    SerialArduinoTriggers()
