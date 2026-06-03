const int sensorPin = A0;
const int pumpPin = 8;

void setup() {
  Serial.begin(9600);
  pinMode(pumpPin, OUTPUT);
  digitalWrite(pumpPin, LOW); // Start with pump OFF
}

void loop() {
  // 1. Send moisture reading to Python
  int sensorValue = analogRead(sensorPin);
  Serial.println(sensorValue);

  // 2. Listen for Pump Commands from Python
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      digitalWrite(pumpPin, HIGH); // Transistor ON
    } else if (command == '0') {
      digitalWrite(pumpPin, LOW);  // Transistor OFF
    }
  }
  
  delay(500); // 0.5 second updates
}