const int pulsePin = A0;    // Analog pin for pulse sensor
const int buzzerPin = 9;    // Digital pin for buzzer
int threshold = 150;        // Set threshold for abnormal heart rate

unsigned long startTime = 0; // Time at which 1-minute calculation starts
int pulseCount = 0;          // Counter for number of beats in a minute
bool counting = false;       // Flag to indicate counting status

void setup() {
  Serial.begin(9600);        // Start serial communication
  pinMode(buzzerPin, OUTPUT); // Set buzzer as output
}

void loop() {
  // Start counting for 1 minute if not already counting
  if (!counting) {
    startTime = millis();    // Record the start time
    pulseCount = 0;          // Reset pulse counter
    counting = true;
  }

  int pulseValue = analogRead(pulsePin); // Read pulse sensor data
  if (pulseValue > 512) { // Assuming >512 indicates a pulse detected
    pulseCount++;         // Increment pulse count for each beat detected
    delay(50);            // Short delay to debounce sensor reading
  }

  // If 1 minute has passed
  if (millis() - startTime >= 60000) {
    int bpm = int(pulseCount/10);  // The number of pulses counted in 1 minute equals BPM
    Serial.print("BPM: ");
    Serial.println(bpm);   // Output BPM to serial monitor

    // Check if BPM exceeds threshold
    if (bpm > threshold) {
      digitalWrite(buzzerPin, HIGH); // Turn on buzzer if BPM is abnormal
    } else {
      digitalWrite(buzzerPin, LOW);  // Otherwise, turn off buzzer
    }

    // Reset for the next 1-minute period
    counting = false;
    delay(2000);           // 2-second pause before starting the next cycle
  }
}
