const int DRIVE  = 8;
const int MID    = 7;   // between X and second 10k
const int RET_Y  = 6;   // Y return (GND)
const int RET_X2 = 5;   // X2 return (GND)
const int SENSE1 = A0;  // between first 10k and X
const int SENSE2 = A1;  // between second 10k and Y
const int SENSE3 = A2;  // between third 10k and X2
const float VCC     = 5.0;
const float R_KNOWN = 10000.0;

void setup() {
  Serial.begin(115200);
  pinMode(DRIVE,  OUTPUT); digitalWrite(DRIVE,  LOW);
  pinMode(MID,    OUTPUT); digitalWrite(MID,    LOW);
  pinMode(RET_Y,  OUTPUT); digitalWrite(RET_Y,  LOW);
  pinMode(RET_X2, OUTPUT); digitalWrite(RET_X2, LOW);
}

bool bleed(int sensePin, int returnPin, int nodeNum) {
  digitalWrite(returnPin, LOW);
  unsigned long t0 = millis();
  while (true) {
    delay(200);
    float v = analogRead(sensePin) * (VCC / 1023.0);
    if (v <= 0.2) return true;
    if (millis() - t0 > 6000) {
      Serial.print("BLEED_TIMEOUT:"); Serial.println(nodeNum);
      return false;
    }
  }
}

void measureNode(int drivePin, int sensePin, int returnPin, int nodeNum) {
  digitalWrite(drivePin,  LOW);
  digitalWrite(returnPin, LOW);
  if (!bleed(sensePin, returnPin, nodeNum)) return;

  Serial.print("CHARGE:"); Serial.print(nodeNum); Serial.print(":");
  digitalWrite(returnPin, LOW);
  digitalWrite(drivePin, HIGH);
  unsigned long t0 = millis();
  for (int i = 0; i < 100; i++) {
    float v = analogRead(sensePin) * (VCC / 1023.0);
    unsigned long t = millis() - t0;
    Serial.print(t); Serial.print(",");
    Serial.print(v, 3); Serial.print(";");
    delay(20);
  }
  Serial.println();

  delay(200);
  float V_fwd = analogRead(sensePin) * (VCC / 1023.0);

  digitalWrite(drivePin, LOW);
  digitalWrite(returnPin, HIGH);
  delay(200);
  float V_rev = analogRead(sensePin) * (VCC / 1023.0);
  digitalWrite(returnPin, LOW);

  Serial.print("FWD:"); Serial.print(nodeNum); Serial.print(":");
  Serial.print(V_fwd, 4); Serial.print("|REV:");
  Serial.println(V_rev, 4);

  digitalWrite(drivePin,  LOW);
  digitalWrite(returnPin, LOW);
  delay(2000);
}

void loop() {
  Serial.println("PROBING:1:X-alone D8-D7");
  pinMode(MID, OUTPUT); digitalWrite(MID, LOW);
  pinMode(RET_Y, INPUT); pinMode(RET_X2, INPUT);
  measureNode(DRIVE, SENSE1, MID, 1);
  pinMode(RET_Y, OUTPUT); pinMode(RET_X2, OUTPUT);

  Serial.println("PROBING:2:Y-alone D7-D6");
  pinMode(DRIVE, OUTPUT); digitalWrite(DRIVE, LOW);
  pinMode(RET_X2, INPUT);
  measureNode(MID, SENSE2, RET_Y, 2);
  pinMode(RET_X2, OUTPUT);

  Serial.println("PROBING:3:XY-verify D8-D6");
  pinMode(MID, INPUT); pinMode(RET_X2, INPUT);
  measureNode(DRIVE, SENSE1, RET_Y, 3);
  pinMode(MID, OUTPUT); digitalWrite(MID, LOW);
  pinMode(RET_X2, OUTPUT);

  Serial.println("PROBING:4:X2-alone D8-D5");
  pinMode(MID, INPUT); pinMode(RET_Y, INPUT);
  measureNode(DRIVE, SENSE3, RET_X2, 4);
  pinMode(MID, OUTPUT); digitalWrite(MID, LOW);
  pinMode(RET_Y, OUTPUT);
}
