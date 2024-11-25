# interact with Arduino/Serial_count.py:

import serial

arduino = serial.Serial('COM13', 19200, timeout=2)
arduino.flushInput()
# When connects to arduino, the DTR will reset the arduino


while True:
    if arduino.in_waiting > 0:  # Check if there's data to read
        line = arduino.readline().decode('utf-8').strip()
        print(f"Received: {line}")

        if line == "Done":
            print("Arduino finished counting")
            # close the serial connection
            arduino.close()

            # exit the loop
            break


        