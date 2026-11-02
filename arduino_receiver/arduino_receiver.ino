
#include <RCSwitch.h>

RCSwitch mySwitch = RCSwitch();
unsigned long lastCode = 0;
unsigned long lastCodeTime = 0;
const unsigned long DEBOUNCE_MILLISECONDS = 1000;

void setup() {
  Serial.begin(9600);
  mySwitch.enableReceive(digitalPinToInterrupt(2));
}

void loop() {
  if (mySwitch.available()) {
    unsigned long code = mySwitch.getReceivedValue();
    unsigned long now = millis();

    if (code != lastCode || now - lastCodeTime >= DEBOUNCE_MILLISECONDS) {
      Serial.println(code);
      lastCode = code;
      lastCodeTime = now;
    }

    mySwitch.resetAvailable();
  }
}
