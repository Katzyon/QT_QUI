// Arduino serial buffer is 64 bytes (~19 integers)
// Arduino Uno-COM13
//
// Serial command modes:
// 1. 3-field mode: "[randVector],period,on_time"
//    Normal vector playback. Each value in randVector is presented once,
//    spaced by period.
// 2. 4-field mode: "[img1,img2],period,on_time,ISI"
//    Repeated two-image pair mode. The vector must contain exactly two image
//    indices. The sketch presents image 1, waits ISI, presents image 2, then
//    waits until period has elapsed from the start of the pair before
//    repeating the same pair again.

// Pin assignments
const int lightPin = 3;          // Light pin 3
const int digipinsPin = 4;       // Digipins pin 4
const int polygonPin = 5;        // Polygon pin

// Configuration parameters
unsigned long period = 0;             // Stored in microseconds, received in milliseconds
unsigned long ledOnTime = 0;          // Light ON time in milliseconds
unsigned long pairISI = 0;            // 4-field mode only: gap between image 1 and image 2, in microseconds
const unsigned int polygonPulse_us = 20;  // Polygon trigger length

// Timing variables
unsigned long lastTriggerTime = 0;         // 3-field mode pacing
unsigned long pairSequenceStartTime = 0;   // 4-field mode: start of current two-image sequence
unsigned long pairGapStartTime = 0;        // 4-field mode: end of image 1 presentation

// State variables
int currentRandIndex = 0;                  // 3-field mode: current index in randVector
bool sequenceComplete = false;             // 3-field mode completion flag
bool sending = false;                      // Digipins bitstream state
bool pairSequenceActive = false;           // 4-field mode: pair currently in progress
bool pairWaitingForSecondImage = false;    // 4-field mode: waiting ISI before image 2
bool pairPendingImmediateStart = false;    // 4-field mode starts immediately after a valid parse

// Variables for Digipins encoding
const unsigned long dt = 200;         // Interval for each bit (200 microseconds ~=4 frames at 20KHz)
bool phase = true;                    // Bit transmission phase
int bitIndex = -1;                    // Bit index for Digipins

const int MAX_VECTOR_SIZE = 18;       // Maximum size due to Arduino serial buffer limitations - can be 19 but keep it pair
int randVector[MAX_VECTOR_SIZE];      // Fixed-size array for randVector
int randVectorSize = 0;               // Number of integers in randVector

enum PlaybackMode {
  PLAYBACK_VECTOR = 0,
  PLAYBACK_PAIR = 1 // paired ISI stimulation 
};

PlaybackMode playbackMode = PLAYBACK_VECTOR;

void setup() {
  pinMode(lightPin, OUTPUT);
  pinMode(digipinsPin, OUTPUT);
  pinMode(polygonPin, OUTPUT);
  Serial.begin(19200);
}

void loop() {
  readSerialInput();

  if (sequenceComplete && playbackMode == PLAYBACK_VECTOR) {
    Serial.print("Sequence finished; period = ");
    Serial.println(period);
    sequenceComplete = false;
  }

  if (playbackMode == PLAYBACK_PAIR) {
    runPairPlayback();
  } else {
    runVectorPlayback();
  }
}

void runVectorPlayback() {
  // 3-field mode: normal vector playback. Each randVector entry is presented
  // once, spaced by period, exactly as in the original sketch.
  if (period == 0 || currentRandIndex >= randVectorSize) {
    return;
  }

  if (micros() - lastTriggerTime >= period) {
    lastTriggerTime = micros();
    triggerImage(randVector[currentRandIndex]);
    currentRandIndex++;

    if (currentRandIndex >= randVectorSize) {
      sequenceComplete = true;
    }
  }
}

void runPairPlayback() {
  // 4-field mode: repeated two-image pair with ISI.
  // Sequence timing is:
  //   image 1 -> wait ISI -> image 2 -> wait until full period elapses from
  //   the start of image 1 -> repeat the same pair.
  if (period == 0 || randVectorSize != 2) {
    return;
  }

  if (pairPendingImmediateStart) {
    startPairSequence();
    pairPendingImmediateStart = false;
    return;
  }

  if (!pairSequenceActive) {
    if (micros() - pairSequenceStartTime >= period) {
      startPairSequence();
    }
    return;
  }

  if (pairWaitingForSecondImage) {
    if (micros() - pairGapStartTime >= pairISI) {
      triggerImage(randVector[1]);
      pairWaitingForSecondImage = false;
    }
    return;
  }

  if (micros() - pairSequenceStartTime >= period) {
    pairSequenceActive = false;
  }
}

void startPairSequence() {
  pairSequenceActive = true;
  pairWaitingForSecondImage = true;
  pairSequenceStartTime = micros();

  triggerImage(randVector[0]);
  pairGapStartTime = micros();
}

void triggerImage(int imageIndex) {
  startTrigger();
  startDigipinsBitstream(imageIndex);
}

void readSerialInput() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    if (parseInput(input)) {
      Serial.println("Message received");
    }
  }
}

bool parseInput(String input) {
  input.trim();

  int startBracket = input.indexOf('[');
  int endBracket = input.indexOf(']');

  if (startBracket != 0 || endBracket == -1 || endBracket <= startBracket + 1) {
    Serial.println("Error: Invalid message format");
    return false;
  }

  String indicesStr = input.substring(startBracket + 1, endBracket);
  String scalarFields = input.substring(endBracket + 1);
  scalarFields.trim();

  if (scalarFields.length() == 0 || scalarFields.charAt(0) != ',') {
    Serial.println("Error: Invalid message format");
    return false;
  }

  scalarFields = scalarFields.substring(1);
  scalarFields.trim();

  int firstComma = scalarFields.indexOf(',');
  int secondComma = scalarFields.indexOf(',', firstComma + 1);
  int thirdComma = (secondComma == -1) ? -1 : scalarFields.indexOf(',', secondComma + 1);

  if (firstComma == -1 || thirdComma != -1) {
    Serial.println("Error: Invalid message format");
    return false;
  }

  String periodStr;
  String onTimeStr;
  String isiStr;
  bool isPairMode = (secondComma != -1);

  if (isPairMode) {
    periodStr = scalarFields.substring(0, firstComma);
    onTimeStr = scalarFields.substring(firstComma + 1, secondComma);
    isiStr = scalarFields.substring(secondComma + 1);
  } else {
    periodStr = scalarFields.substring(0, firstComma);
    onTimeStr = scalarFields.substring(firstComma + 1);
  }

  unsigned long parsedPeriodMs = 0;
  unsigned long parsedOnTimeMs = 0;
  unsigned long parsedISIMs = 0;

  if (!parseUnsignedLongField(periodStr, parsedPeriodMs) ||
      !parseUnsignedLongField(onTimeStr, parsedOnTimeMs) ||
      (isPairMode && !parseUnsignedLongField(isiStr, parsedISIMs))) {
    Serial.println("Error: Non-numeric period, on_time, or ISI field");
    return false;
  }

  int parsedVector[MAX_VECTOR_SIZE];
  int parsedVectorSize = 0;

  if (!parseRandVector(indicesStr, parsedVector, parsedVectorSize)) {
    Serial.println("Error: Invalid randVector");
    return false;
  }

  if (isPairMode && parsedVectorSize != 2) {
    Serial.println("Error: 4-field mode requires exactly two image indices");
    return false;
  }

  applyParsedSettings(parsedVector, parsedVectorSize, parsedPeriodMs, parsedOnTimeMs, parsedISIMs, isPairMode);
  return true;
}

bool parseUnsignedLongField(String field, unsigned long &value) {
  field.trim();

  if (field.length() == 0) {
    return false;
  }

  for (unsigned int i = 0; i < field.length(); i++) {
    if (!isDigit(field.charAt(i))) {
      return false;
    }
  }

  value = field.toInt();
  return true;
}

bool parseSignedIntField(String field, int &value) {
  field.trim();

  if (field.length() == 0) {
    return false;
  }

  int startIndex = 0;
  if (field.charAt(0) == '-' || field.charAt(0) == '+') {
    if (field.length() == 1) {
      return false;
    }
    startIndex = 1;
  }

  for (unsigned int i = startIndex; i < field.length(); i++) {
    if (!isDigit(field.charAt(i))) {
      return false;
    }
  }

  value = field.toInt();
  return true;
}

bool parseRandVector(String indicesStr, int outputVector[], int &outputSize) {
  outputSize = 0;
  indicesStr.trim();

  if (indicesStr.length() == 0) {
    return false;
  }

  while (indicesStr.length() > 0) {
    if (outputSize >= MAX_VECTOR_SIZE) {
      return false;
    }

    int commaPos = indicesStr.indexOf(',');
    String token;

    if (commaPos == -1) {
      token = indicesStr;
      indicesStr = "";
    } else {
      token = indicesStr.substring(0, commaPos);
      indicesStr = indicesStr.substring(commaPos + 1);
    }

    int parsedValue = 0;
    if (!parseSignedIntField(token, parsedValue)) {
      return false;
    }

    outputVector[outputSize++] = parsedValue;
    indicesStr.trim();
  }

  Serial.print("Parsed Vector: ");
  for (int i = 0; i < outputSize; i++) {
    Serial.print(outputVector[i]);
    if (i < outputSize - 1) {
      Serial.print("_");
    }
  }
  Serial.println();

  return true;
}

void applyParsedSettings(int parsedVector[], int parsedVectorSize,
                         unsigned long parsedPeriodMs,
                         unsigned long parsedOnTimeMs,
                         unsigned long parsedISIMs,
                         bool isPairMode) {
  for (int i = 0; i < parsedVectorSize; i++) {
    randVector[i] = parsedVector[i];
  }

  randVectorSize = parsedVectorSize;
  period = parsedPeriodMs * 1000UL;
  ledOnTime = parsedOnTimeMs;
  pairISI = parsedISIMs * 1000UL;
  playbackMode = isPairMode ? PLAYBACK_PAIR : PLAYBACK_VECTOR;

  currentRandIndex = 0;
  sequenceComplete = false;
  sending = false;
  phase = true;
  bitIndex = -1;

  pairSequenceActive = false;
  pairWaitingForSecondImage = false;
  pairPendingImmediateStart = isPairMode;
  pairSequenceStartTime = 0;
  pairGapStartTime = 0;

  Serial.print("Mode: ");
  Serial.println(isPairMode ? "4-field pair repeat" : "3-field vector playback");
  Serial.print("period(us): ");
  Serial.println(period);
  Serial.print("on_time(ms): ");
  Serial.println(ledOnTime);
  if (isPairMode) {
    Serial.print("ISI(us): ");
    Serial.println(pairISI);
  }
}

void startTrigger() {
  noInterrupts();
  digitalWrite(polygonPin, HIGH);
  delayMicroseconds(polygonPulse_us);
  digitalWrite(polygonPin, LOW);

  digitalWrite(lightPin, HIGH);
  interrupts();

  delay(ledOnTime);
  digitalWrite(lightPin, LOW);
}

void startDigipinsBitstream(int imageIndex) {
  bitIndex = -1;
  sending = true;
  phase = true;
  handleDigipinsBits(imageIndex);
}

void handleDigipinsBits(int imageIndex) {
  if (!sending) {
    return;
  }

  while (sending) {
    if (phase) {
      if (bitIndex == -1) {
        digitalWrite(digipinsPin, HIGH);
        delayMicroseconds(dt);
      } else if (bitIndex >= 0 && bitIndex < 7) {
        bool bitValue = bitRead(imageIndex, bitIndex);
        digitalWrite(digipinsPin, bitValue);
        delayMicroseconds(dt);
      }
      phase = false;
    } else {
      if (bitIndex < 8) {
        digitalWrite(digipinsPin, LOW);
        delayMicroseconds(dt);
      }

      bitIndex++;
      phase = true;

      if (bitIndex > 7) {
        sending = false;
      }
    }
  }
}