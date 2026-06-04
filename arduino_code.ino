const int sensorPin = A0;
const int pumpPin = 8;
bool hardwareActive = true; 
int lastPumpState = -1; // To track changes

void setup() {
  Serial.begin(9600);
  pinMode(pumpPin, OUTPUT);
  digitalWrite(pumpPin, LOW); 
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    if (cmd == 'A') hardwareActive = true;
    if (cmd == 'Q') { hardwareActive = false; digitalWrite(pumpPin, LOW); }
    
    if (hardwareActive) {
      // Only change the pin if the command is different from current state
      if (cmd == '1' && lastPumpState != 1) {
        digitalWrite(pumpPin, HIGH);
        lastPumpState = 1;
      } 
      else if (cmd == '0' && lastPumpState != 0) {
        digitalWrite(pumpPin, LOW);
        lastPumpState = 0;
      }
    }
  }

  if (hardwareActive) {
    int sensorValue = analogRead(sensorPin);
    // Send with a clear start and end character
    Serial.print("<"); 
    Serial.print(sensorValue);
    Serial.println(">"); 
  }
  
  delay(500); 
}