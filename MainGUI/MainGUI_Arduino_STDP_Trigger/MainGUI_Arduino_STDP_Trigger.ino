// Arduino Uno - STDP paired-trigger protocol
//
// Serial input format:
//   dt,IPI,Tmin,on_time
//
// Units:
//   dt   = milliseconds between event 1 and event 2 within one STDP pair.
//   IPI  = milliseconds from the start of one pair to the start of the next pair.
//   Tmin    = total protocol duration in minutes. Fractional minutes are allowed.
//   on_time = light pulse width in milliseconds for each event.
//
// Important system assumption:
//   This sketch only generates the trigger timing. Python must preload the
//   two-frame polygon/DMD sequence and place the device in external-trigger
//   mode before sending dt,IPI,Tmin,on_time.
//
// Digital-pin encoding:
//   The digipins output preserves the original encoding style:
//   one HIGH start bit, then 7 data bits LSB-first, each separated by a LOW
//   phase. Event code 1 marks the first event in the pair. Event code 2 marks
//   the second event in the pair.

// Pin assignments copied from the source sketch.
const int lightPin = 3;
const int digipinsPin = 4;
const int polygonPin = 5;

// Trigger pulse configuration.
const unsigned int polygonPulse_us = 20;       // Polygon trigger width.
const unsigned long digipinsBit_us = 200;      // Bit timing for digipins encoding.
unsigned long lightPulse_ms = 0;               // Light pulse width in milliseconds, received from Python.
const unsigned long minimumEventSpacing_us = (8UL * 2UL * digipinsBit_us) + polygonPulse_us;

// Event codes sent to the digipins line.
const byte event1Code = 1;
const byte event2Code = 2;

// Pair scheduler state.
enum PairState {
  PAIR_IDLE = 0,
  PAIR_WAIT_SECOND = 1,
  PAIR_WAIT_NEXT = 2
};

bool protocolRunning = false;
PairState pairState = PAIR_IDLE;

unsigned long pairStartMicros = 0;
unsigned long protocolStartMillis = 0;
unsigned long dt_us = 0;
unsigned long ipi_us = 0;
unsigned long protocolDuration_ms = 0;

// Non-blocking light timing.
bool lightActive = false;
unsigned long lightStartMillis = 0;

void setup() {
  pinMode(lightPin, OUTPUT);
  pinMode(digipinsPin, OUTPUT);
  pinMode(polygonPin, OUTPUT);

  digitalWrite(lightPin, LOW);
  digitalWrite(digipinsPin, LOW);
  digitalWrite(polygonPin, LOW);

  Serial.begin(19200);
}

void loop() {
  readSerialInput();
  updateLightOutput();
  runStdpProtocol();
}

void readSerialInput() {
  if (Serial.available() <= 0) {
    return;
  }

  String input = Serial.readStringUntil('\n');
  input.trim();

  if (input.length() == 0) {
    Serial.println("Error: empty input");
    return;
  }

  if (parseAndStartProtocol(input)) {
    Serial.println("Message received");
  }
}

bool parseAndStartProtocol(String input) {
  int firstComma = input.indexOf(',');
  int secondComma = input.indexOf(',', firstComma + 1);
  int thirdComma = (secondComma == -1) ? -1 : input.indexOf(',', secondComma + 1);
  int fourthComma = (thirdComma == -1) ? -1 : input.indexOf(',', thirdComma + 1);

  if (firstComma == -1 || secondComma == -1 || thirdComma == -1 || fourthComma != -1) {
    Serial.println("Error: expected exactly 4 fields: dt,IPI,Tmin,on_time");
    return false;
  }

  String dtStr = input.substring(0, firstComma);
  String ipiStr = input.substring(firstComma + 1, secondComma);
  String tminStr = input.substring(secondComma + 1, thirdComma);
  String onTimeStr = input.substring(thirdComma + 1);

  float parsedDtMs = 0.0f;
  float parsedIpiMs = 0.0f;
  float parsedTmin = 0.0f;
  float parsedOnTimeMs = 0.0f;

  if (!parseNonNegativeFloat(dtStr, parsedDtMs)) {
    Serial.println("Error: dt must be a valid non-negative number in ms");
    return false;
  }

  if (!parseNonNegativeFloat(ipiStr, parsedIpiMs)) {
    Serial.println("Error: IPI must be a valid non-negative number in ms");
    return false;
  }

  if (!parsePositiveFloat(tminStr, parsedTmin)) {
    Serial.println("Error: Tmin must be a valid positive number in minutes");
    return false;
  }

  if (!parsePositiveFloat(onTimeStr, parsedOnTimeMs)) {
    Serial.println("Error: on_time must be a valid positive number in ms");
    return false;
  }

  unsigned long parsedDtUs = msToUs(parsedDtMs);
  unsigned long parsedIpiUs = msToUs(parsedIpiMs);
  unsigned long parsedDurationMs = minutesToMs(parsedTmin);
  unsigned long parsedOnTimeMsInt = msToMs(parsedOnTimeMs);

  if (parsedIpiUs <= parsedDtUs) {
    Serial.println("Error: IPI must be greater than dt to avoid overlap");
    return false;
  }

  if (parsedDtUs < minimumEventSpacing_us) {
    Serial.print("Error: dt is shorter than the minimum supported interval of ");
    Serial.print(minimumEventSpacing_us);
    Serial.println(" us with the current digipins encoding");
    return false;
  }

  if (parsedDurationMs == 0) {
    Serial.println("Error: Tmin is too small after conversion to milliseconds");
    return false;
  }

  if (parsedOnTimeMsInt == 0) {
    Serial.println("Error: on_time is too small after conversion to milliseconds");
    return false;
  }

  dt_us = parsedDtUs;
  ipi_us = parsedIpiUs;
  protocolDuration_ms = parsedDurationMs;
  lightPulse_ms = parsedOnTimeMsInt;
  protocolStartMillis = millis();
  pairState = PAIR_IDLE;
  protocolRunning = true;

  lightActive = false;
  digitalWrite(lightPin, LOW);
  digitalWrite(digipinsPin, LOW);
  digitalWrite(polygonPin, LOW);

  Serial.print("STDP start dt_us=");
  Serial.print(dt_us);
  Serial.print(" IPI_us=");
  Serial.print(ipi_us);
  Serial.print(" Tmin_ms=");
  Serial.print(protocolDuration_ms);
  Serial.print(" on_time_ms=");
  Serial.println(lightPulse_ms);

  return true;
}

void runStdpProtocol() {
  if (!protocolRunning) {
    return;
  }

  switch (pairState) {
    case PAIR_IDLE:
      if (protocolTimeElapsed()) {
        finishProtocol();
        return;
      }
      startPair();
      break;

    case PAIR_WAIT_SECOND:
      if (micros() - pairStartMicros >= dt_us) {
        triggerEvent(event2Code);
        pairState = PAIR_WAIT_NEXT;
      }
      break;

    case PAIR_WAIT_NEXT:
      // Do not start a new pair once the total duration has elapsed.
      // The current pair is allowed to complete first.
      if (protocolTimeElapsed()) {
        finishProtocol();
        return;
      }

      if (micros() - pairStartMicros >= ipi_us) {
        startPair();
      }
      break;
  }
}

void startPair() {
  pairStartMicros = micros();
  triggerEvent(event1Code);
  pairState = PAIR_WAIT_SECOND;
}

void triggerEvent(byte eventCode) {
  startTrigger();
  startDigipinsBitstream(eventCode);
}

void startTrigger() {
  // Keep the microsecond-critical polygon pulse short.
  noInterrupts();
  digitalWrite(polygonPin, HIGH);
  delayMicroseconds(polygonPulse_us);
  digitalWrite(polygonPin, LOW);
  interrupts();

  // Light timing is handled non-blockingly in updateLightOutput().
  digitalWrite(lightPin, HIGH);
  lightStartMillis = millis();
  lightActive = true;
}

void updateLightOutput() {
  if (!lightActive) {
    return;
  }

  if (millis() - lightStartMillis >= lightPulse_ms) {
    digitalWrite(lightPin, LOW);
    lightActive = false;
  }
}

void startDigipinsBitstream(byte eventCode) {
  int bitIndex = -1;
  bool phaseHigh = true;
  bool sending = true;

  while (sending) {
    if (phaseHigh) {
      if (bitIndex == -1) {
        digitalWrite(digipinsPin, HIGH);
      } else if (bitIndex >= 0 && bitIndex < 7) {
        digitalWrite(digipinsPin, bitRead(eventCode, bitIndex));
      }
      delayMicroseconds(digipinsBit_us);
      phaseHigh = false;
    } else {
      if (bitIndex < 8) {
        digitalWrite(digipinsPin, LOW);
        delayMicroseconds(digipinsBit_us);
      }

      bitIndex++;
      phaseHigh = true;

      if (bitIndex > 7) {
        sending = false;
      }
    }
  }
}

bool protocolTimeElapsed() {
  return millis() - protocolStartMillis >= protocolDuration_ms;
}

void finishProtocol() {
  protocolRunning = false;
  pairState = PAIR_IDLE;
  lightActive = false;

  digitalWrite(lightPin, LOW);
  digitalWrite(digipinsPin, LOW);
  digitalWrite(polygonPin, LOW);

  Serial.println("Sequence finished; STDP protocol complete");
}

bool parseNonNegativeFloat(String field, float &value) {
  field.trim();

  if (field.length() == 0) {
    return false;
  }

  bool seenDigit = false;
  bool seenDecimalPoint = false;

  for (unsigned int i = 0; i < field.length(); i++) {
    char c = field.charAt(i);

    if (c >= '0' && c <= '9') {
      seenDigit = true;
      continue;
    }

    if (c == '.' && !seenDecimalPoint) {
      seenDecimalPoint = true;
      continue;
    }

    return false;
  }

  if (!seenDigit) {
    return false;
  }

  value = field.toFloat();
  return value >= 0.0f;
}

bool parsePositiveFloat(String field, float &value) {
  if (!parseNonNegativeFloat(field, value)) {
    return false;
  }

  return value > 0.0f;
}

unsigned long msToUs(float valueMs) {
  return (unsigned long)(valueMs * 1000.0f + 0.5f);
}

unsigned long msToMs(float valueMs) {
  return (unsigned long)(valueMs + 0.5f);
}

unsigned long minutesToMs(float valueMinutes) {
  return (unsigned long)(valueMinutes * 60000.0f + 0.5f);
}
