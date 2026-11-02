#include <RCSwitch.h>

RCSwitch mySwitch = RCSwitch();
bool streamEnabled = false;

void setup() {
  Serial.begin(9600);
  mySwitch.enableReceive(digitalPinToInterrupt(2));  // RXB6 DATA -> D2
  Serial.println("READY");
}

void handleHostCommands() {
  while (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "START") {
      streamEnabled = true;
      Serial.println("STREAM:ON");
    } else if (command == "STOP") {
      streamEnabled = false;
      Serial.println("STREAM:OFF");
    } else if (command == "PING") {
      Serial.println("PONG");
    }
  }
}

void loop() {
  handleHostCommands();

  if (mySwitch.available()) {
    unsigned long code = mySwitch.getReceivedValue();

    if (streamEnabled && code != 0) {
      Serial.print("CODE:");
      Serial.println(code);
    } else if (streamEnabled && code == 0) {
      Serial.println("CODE:0");
    }

    mySwitch.resetAvailable();
  }
}
