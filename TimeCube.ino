// Jacek Fedorynski <jfedor@jfedor.org>
// https://www.jfedor.org/

#include <avr/sleep.h>

#define LED_PIN 0
#define WAKEUP_PIN 3
#define WAKEUP_INT_MASK PCINT3
#define WAKEUP_PIN2 1
#define WAKEUP_INT_MASK2 PCINT1
#define ESP_ENABLE_PIN 4
#define ESP_SIGNAL_PIN 2
#define TIMEOUT 30000L

ISR (PCINT0_vect) {}

bool timed_out;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(WAKEUP_PIN, INPUT_PULLUP);
  pinMode(WAKEUP_PIN2, INPUT_PULLUP);
  pinMode(ESP_ENABLE_PIN, OUTPUT);
  digitalWrite(ESP_ENABLE_PIN, LOW);
  pinMode(ESP_SIGNAL_PIN, INPUT);
  ADCSRA &= ~(1<<ADEN); // disable ADC
  GIMSK |= (1<<PCIE); // enable pin change interrupts
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  timed_out = false;
}

void loop() {
  if (!timed_out) {
    PCMSK |= 1<<WAKEUP_INT_MASK; // set interrupt mask to listen on vibration sensor
  }
  timed_out = false;
  PCMSK |= 1<<WAKEUP_INT_MASK2; // set interrupt mask to wake on button press

  digitalWrite(LED_PIN, LOW);
  // go to sleep
  sleep_mode();
  // ... and we're awake
  digitalWrite(LED_PIN, HIGH);

  PCMSK &= ~(1<<WAKEUP_INT_MASK | 1<<WAKEUP_INT_MASK2); // ignore interrupts for now

  digitalWrite(ESP_ENABLE_PIN, HIGH);

  long start_time = millis();

  delay(2000); // give ESP time to initialize

  while (!digitalRead(ESP_SIGNAL_PIN)) {
    if (millis() - start_time > TIMEOUT) {
      timed_out = true;
      for (int i = 0; i < 10; i++) {
        digitalWrite(LED_PIN, LOW);
        delay(100);
        digitalWrite(LED_PIN, HIGH);
        delay(100);
      }
      break;
    }
  }

  digitalWrite(ESP_ENABLE_PIN, LOW);
}
