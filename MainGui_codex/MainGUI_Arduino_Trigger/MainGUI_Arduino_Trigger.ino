//Arduino serial buffer is 64 bytes (~19 intergers)
// Arduino Uno-COM13

// Pin assignments
const int lightPin = 3;       // Light pin 3
const int digipinsPin = 4;    // Digipins pin 4
const int polygonPin = 5;     // Polygon pin 

// Configuration parameters
unsigned long period = 0;             // Period in us
unsigned long interPeriod = 0;       // us time between polygon image presentations = period - redundant -> delete in the future
unsigned long ledOnTime = 0;        // Time in ms for the Light to stay active
unsigned long polygonDelay_us = 1000; // in microseconds

// Timing variables
unsigned long lastTriggerTime = 0;    // Tracks time for each trigger
unsigned long previousMicros = 0;     // Tracks time for Digipins bitstream
const unsigned int polygonPulse_us = 20; // Polygon trigger length

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
int randVectorSize = 0;               // Number of integers in rand_vector (input vector)

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
    Serial.print("Sequence finished; period = "); // Send completion message to Python
    Serial.println(period); // output the period for debugging

    sequenceComplete = false;            // Reset for the next cycle
  }

  // Run the stimulation until currentRandIndex = randVectorSize 
  if (period > 0 && micros() - lastTriggerTime >= interPeriod && currentRandIndex < randVectorSize) {
    lastTriggerTime = micros(); // micros can count up to 71 minutes
    startTrigger();                      // Trigger the Light sequence
    startDigipinsBitstream();            // Start sending the bitstream to Digipins - the digipin starts after the light
    //Serial.println(lastTriggerTime);   // Timing of each trigger send to terminal display
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
    //   Serial.read  (); // Clear any leftover characters from the buffer
  }
}

// Parses the incoming serial message
void parseInput(String input) {
  // input example - "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],1000,200\n"
  // message = f"{arduino_display_indices},{self.stages[stage_index].groups_period},{self.stages[stage_index].on_time}\n"
  // self.arduino_comm.send_message(arduino_display_indices, stage.groups_period, stage.on_time) # 
  // sent from runProtocol ~L214 
  //Serial.println("Start parsing");

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

    period = periodStr.toInt()*1000; // period = periodStr.toInt() * 1000; // Received in ms, stored in µs
    ledOnTime = onTimeStr.toInt(); // ms

    //Print updated values
    // Serial.print("rand vector: ");
    // Serial.println(indicesStr); // Display in ms
    // Serial.print("peroid (ms):");
    // Serial.println(period); // Display in ms
    // Serial.print("LED On Time (ms): ");
    // Serial.println(ledOnTime); // Display in ms

    parseRandVector(indicesStr);

    // Reset trigger index and completion flag
    currentRandIndex = 0;
    sequenceComplete = false;
  } else {
    Serial.println("Error: Invalid message format");
  }
}

// Parses the list of integers
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
  interPeriod = period; // in microseconds

  // Debugging output - print the parsed randomized vector
  Serial.print("Parsed Vector: ");
  for (int i = 0; i < randVectorSize; i++) {
    Serial.print(randVector[i]);
    if (i < randVectorSize - 1) Serial.print("_");
  }
  Serial.print(" interPeriod us: ");
  Serial.println(interPeriod);

}

// polygon image and light timing
void startTrigger() {
  // Critical microsecond section: keep it short to minimize jitter
  noInterrupts();
  digitalWrite(polygonPin, HIGH);                 // 1) trigger polygon
  delayMicroseconds(polygonPulse_us);             //    short pulse only 20microseconds
  digitalWrite(polygonPin, LOW);                  //    return LOW for a clean next edge

  // delayMicroseconds(polygonToLightDelay_us);      // 2) allow polygon/image to settle

  digitalWrite(lightPin, HIGH);                   // 3) turn light ON
  interrupts();

  delay(ledOnTime);                               // ms
  digitalWrite(lightPin, LOW);                    // light OFF
}

// Initiates the Light pulse sequence
// void startTrigger() {
//   digitalWrite(polygonPin, HIGH);
//   delayMicroseconds(polygonDelay_us); // turn the light and wait to stabilize
//   digitalWrite(lightPin, HIGH);
  
//   delay(ledOnTime); // in ms -  delayMicroseconds can only be used for short periods <65ms (16bit int) 

//   digitalWrite(lightPin, LOW);         // Deactivate Light
//   digitalWrite(polygonPin, LOW); 
//   //digitalWrite(digipinsPin, LOW);
//   //Serial.println("out");
// }

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
          //Serial.println("New num2:");
          sequenceComplete = true;                            // Set sequence complete flag if all indices are processed
          
        }
      }
    }
  }
}
