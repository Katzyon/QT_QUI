//Arduino serial buffer is 64 bytes 

// Pin assignments
const int lightPin = 3;       // Light pin 3
const int digipinsPin = 4;    // Digipins pin 4
const int polygonPin = 5;     // Polygon pin 

// Configuration parameters
unsigned long period = 0;             // Period in ms
unsigned long ledOnTime = 0;        // Time in ms for the Light to stay active
unsigned long polygonDelay_us = 1000; // in microseconds

// Timing variables
unsigned long lastTriggerTime = 0;    // Tracks time for each trigger
unsigned long previousMicros = 0;     // Tracks time for Digipins bitstream

// State variables
int currentRandIndex = 0;             // Tracks the current index of the rand_vector
bool sequenceComplete = false;        // Flag to indicate sequence completion
bool sending = false;                 // Flag to start/stop sending the bitstream

// Variables for Digipins encoding
const unsigned long dt = 200;         // Interval for each bit (200 microseconds ~=4 frames at 20KHz)
bool phase = true;                    // Bit transmission phase
int bitIndex = -1;                    // Bit index for Digipins

const int MAX_VECTOR_SIZE = 19;      // Maximum size of rand_vector due to arduino serial buffer limitations
int randVector[MAX_VECTOR_SIZE];      // Fixed-size array for rand_vector
int randVectorSize = 0;               // Number of integers in rand_vector

void setup() {
  pinMode(lightPin, OUTPUT);
  pinMode(digipinsPin, OUTPUT);
  pinMode(polygonPin, OUTPUT);
  Serial.begin(19200);
}

void loop() {
  // Check for incoming serial message to update settings
  readSerialInput();

  // Check if the sequence has completed
  if (sequenceComplete) {
    Serial.println("Sequence finished"); // Send completion message to Python
    sequenceComplete = false;            // Reset for the next cycle
  }

  // bitIndex = -1;                        // Reset bit index for new number
  // sending = true;                       // Start sending the bitstream
  // phase = true;                         // Start with HIGH phase
  // previousMicros = micros();            // Set initial timing for bitstream

  // // Check if it's time to initiate the next trigger in the sequence
  // if (period > 0 && micros() - lastTriggerTime >= period && currentRandIndex < randVectorSize) {
  //   lastTriggerTime = micros();

  //   while (sending) {
  //     unsigned long currentMicros = micros();  // Get the current time

  //     // Check if the 200-microsecond interval has passed
  //     if (currentMicros - previousMicros >= dt) {
  //       previousMicros = currentMicros;  // Reset the previous time

  //       if (phase) {
  //         // First phase: Send the start bit or data bit
  //         if (bitIndex == -1) {
  //           // Send the start bit (HIGH)
  //           digitalWrite(digipinsPin, HIGH);
  //         } 
  //         else if (bitIndex >= 0 && bitIndex < 7) {
  //           // Send the 7 data bits from LSB to MSB
  //           bool bitValue = bitRead(randVector[currentRandIndex], bitIndex); // Read the next bit
  //           digitalWrite(digipinsPin, bitValue);  // Set the pin according to the bit
  //         }
  //         // Move to the next phase (LOW state after bit transmission)
  //         phase = false;
  //       } else {
  //         // Second phase: Set the pin to LOW after the bit
  //         if (bitIndex < 8) {
  //           digitalWrite(digipinsPin, LOW);  // Ensure LOW state after every bit
  //         }

  //         // Move to the next bit
  //         bitIndex++;
  //         phase = true;  // Return to the sending phase

  //         // If all bits have been sent (start bit + 7 data bits)
  //         if (bitIndex > 7) {
  //           sending = false;  // Stop sending
  //         }
  //       }
  //     }
  //   }

  if (period > 0 && micros() - lastTriggerTime >= period*1000 && currentRandIndex < randVectorSize) {
    lastTriggerTime = micros();
    startTrigger();                      // Trigger the Light sequence
    startDigipinsBitstream();            // Start sending the bitstream to Digipins
    //Serial.println("Sent digipins");
    currentRandIndex++;                 // Move to the next index
    if (currentRandIndex + 1 == randVectorSize){
      sequenceComplete = true;
    }
  }
}

// Reads serial input and parses it if available
void readSerialInput() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    parseInput(input);
    Serial.println("Message received"); // Acknowledge message receipt
    // Clear serial buffer to prevent residual input
    // while (Serial.available() > 0) {
    //   Serial.read(); // Clear any leftover characters from the buffer
  }
}

// Parses the incoming serial message
void parseInput(String input) {
  // input example - "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],1000,200\n"
  // sent from runProtocol L101 
  Serial.println("Start parsing");

  // Message format: "[1,2,3,4],1000,200"
  int startBracket = input.indexOf('[');
  int endBracket = input.indexOf(']');
  int firstComma = input.indexOf(',', endBracket + 2);
  int secondComma = input.indexOf(',', firstComma + 1);

  if (firstComma != -1 && endBracket + 2 < input.length() && firstComma + 1 < input.length()) {
    String indicesStr = input.substring(startBracket + 1, endBracket);
    String periodStr = input.substring(endBracket + 2, firstComma);
    String onTimeStr = input.substring(firstComma + 1);

    // remove extra spaces
    indicesStr.trim();
    periodStr.trim();
    onTimeStr.trim();

    period = periodStr.toInt(); // ms
    ledOnTime = onTimeStr.toInt(); // ms

    // Print updated values
    Serial.print("rand vector: ");
    Serial.println(indicesStr); // Display in ms
    Serial.print("peroid (ms):");
    Serial.println(period); // Display in ms
    Serial.print("LED On Time (ms): ");
    Serial.println(ledOnTime); // Display in ms

    parseRandVector(indicesStr);

    // Reset trigger index and completion flag
    currentRandIndex = 0;
    sequenceComplete = false;
  } else {
    Serial.println("Error: Invalid message format");
  }
}

// Parses the list of integers (rand_vector)
void parseRandVector(String indicesStr) {
  randVectorSize = 0;  // Reset the count of rand_vector size

  while (indicesStr.length() > 0 && randVectorSize < MAX_VECTOR_SIZE) {
    int commaPos = indicesStr.indexOf(',');
    if (commaPos == -1) {  // Last number in the sequence
      randVector[randVectorSize++] = indicesStr.toInt();
      break;
    } else {
      randVector[randVectorSize++] = indicesStr.substring(0, commaPos).toInt();
      indicesStr = indicesStr.substring(commaPos + 1);
    }
  }


  // Debugging output
  Serial.print("Parsed randVector: ");
  for (int i = 0; i < randVectorSize; i++) {
    Serial.print(randVector[i]);
    if (i < randVectorSize - 1) Serial.print("_");
  }
  Serial.println();
}

// Helper function to check if a string contains only numeric characters
// bool isNumeric(String str) {
//   for (unsigned int i = 0; i < str.length(); i++) {
//     if (!isDigit(str[i])) {
//       return false;
//     }
//   }
//   return true;
// }

// Initiates the Light pulse sequence
void startTrigger() {
  digitalWrite(lightPin, HIGH);
  //digitalWrite(digipinsPin, HIGH);
  delayMicroseconds(polygonDelay_us); // turn the light and wait to stabilize

  digitalWrite(polygonPin, HIGH);
  

  delay(ledOnTime); // in ms -  delayMicroseconds can only be used for short periods <65ms (16bit int) 
  //delay(500); 

  digitalWrite(lightPin, LOW);         // Deactivate Light
  digitalWrite(polygonPin, LOW); 
  //digitalWrite(digipinsPin, LOW);
  //Serial.println("out");

}

// Initializes the Digipins bitstream for the current index in rand_vector
void startDigipinsBitstream() {
  //Serial.println("startDigipinsBitstream");
  bitIndex = -1;                        // Reset bit index for new number
  sending = true;                       // Start sending the bitstream
  phase = true;                         // Start with HIGH phase
  previousMicros = micros();            // Set initial timing for bitstream
  handleDigipinsBits();   // encode the current randvector int to digipins          
}

// Manages the bitstream for each integer in `randVector`
void handleDigipinsBits() {
  
  if (!sending || currentRandIndex >= randVectorSize) return; // Exit if not sending or all numbers sent
  //Serial.println("handleDigipinsBits: ");

  while (sending){  // send encoded byte to arduino

    if (phase) {
      // Send the start bit or data bit
      if (bitIndex == -1) {
        digitalWrite(digipinsPin, HIGH);
        delayMicroseconds(dt);
      } 
      else if (bitIndex >= 0 && bitIndex < 7) {
        bool bitValue = bitRead(randVector[currentRandIndex], bitIndex); // Read the next bit
        digitalWrite(digipinsPin, bitValue);                  // Set the pin according to the bit
        delayMicroseconds(dt);
        //Serial.println(bitValue);
      }
      // Move to the next phase (LOW state after bit transmission)
      phase = false;
    } else {
      // Set the pin to LOW after each bit
      if (bitIndex < 8) {
        digitalWrite(digipinsPin, LOW);    // Ensure LOW state after every bit
        delayMicroseconds(dt);
        //Serial.println(0);
      }

      // Move to the next bit
      bitIndex++;
      phase = true;

      // If all bits have been sent (start bit + 7 data bits)
      if (bitIndex > 7) {
        //Serial.print(currentRandIndex);
        //Serial.print(", ");
        //Serial.println(randVectorSize);
        sending = false;                                      // Stop sending
        if (currentRandIndex >= randVectorSize - 1) {
          Serial.println("New num2:");
          sequenceComplete = true;                            // Set sequence complete flag if all indices are processed
          
        }
      }
    }
  }
}
