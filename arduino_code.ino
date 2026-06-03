const int sensorPin = A0;
const int pumpPin = 8;
bool hardwareActive = false;

void setup() {
  Serial.begin(9600);
  pinMode(pumpPin, OUTPUT);
  digitalWrite(pumpPin, LOW); 
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    if (cmd == 'A') { hardwareActive = true; }   // A = Activate
    if (cmd == 'Q') {                            // Q = Quit/Deactivate
        hardwareActive = false; 
        digitalWrite(pumpPin, LOW); 
    }
    
    // Pump logic (only works if active)
    if (hardwareActive) {
        if (cmd == '1') digitalWrite(pumpPin, HIGH);
        if (cmd == '0') digitalWrite(pumpPin, LOW);
    }
  }

  // Only send data if active
  if (hardwareActive) {
    int sensorValue = analogRead(sensorPin);
    Serial.println(sensorValue);
  }
  
  delay(500);
}