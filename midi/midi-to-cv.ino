#define PULSE_PIN 3

void setup() {
  pinMode(PULSE_PIN, OUTPUT);
  Serial.begin(31250);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  initTimer1_31250Hz();
}

void clock_pulse() {
  noInterrupts();

  TCCR2A = 0;
  TCCR2B = 0;
  TCNT2 = 0;

  // 50 * 1024 clock divider / 16000000 Hz = 3.2 ms
  OCR2B = 50;

  // set on compare match
  TCCR2A = (1 << COM2B1) | (1 << COM2B0);
  // force compare match
  TCCR2B = (1 << FOC2B);

  // clear on compare match
  TCCR2A = (1 << COM2B1);
  // start timer with prescaler = 1024
  TCCR2B |= (1 << CS22) | (1 << CS21) | (1 << CS20);

  interrupts();
}

void initTimer1_31250Hz() {
  // Configure Pin 9 as an output
  pinMode(9, OUTPUT); // cv pin
  pinMode(8, OUTPUT); // gate pin
  digitalWrite(8, LOW);

  // Disable interrupts globally while configuring registers
  noInterrupts();

  // Reset Timer 1 Control Registers
  TCCR1A = 0;
  TCCR1B = 0;
  
  // Set Fast PWM Mode 14 (WGM13=1, WGM12=1, WGM11=1, WGM10=0)
  // This mode uses ICR1 as the TOP value to define the frequency
  TCCR1A |= (1 << WGM11);
  TCCR1B |= (1 << WGM12) | (1 << WGM13);

  // Enable non-inverting PWM on Channel A (Pin 9)
  // This clears OC1A on Compare Match, sets OC1A at BOTTOM
  TCCR1A |= (1 << COM1A1);

  // Set Prescaler to 1 (No prescaling) -> CS10=1
  TCCR1B |= (1 << CS10);

  // Set the TOP value for 31250 Hz
  // 16MHz / (1 * 31250Hz) - 1 = 511
  ICR1 = 511;

  // Initialize the output compare register to a 0% duty cycle
  OCR1A = 0;

  // Re-enable interrupts
  interrupts();
}

int playing_note = -1;

void note_on( uint8_t channel, uint8_t note ) {

  if( channel != 0x00 ) {
    return;
  }

  if( playing_note >= 0 ) {
    return;
  }

  // pwm on pin 9
  OCR1A = note << 2;
  digitalWrite( 8, HIGH );
  playing_note = note;

  digitalWrite(LED_BUILTIN, HIGH);
}

void note_off( uint8_t channel, uint8_t note ) {

  if( channel != 0x00 ) {
    return;
  }

  if( playing_note != note ) {
    return;
  }

  digitalWrite( 8, LOW );
  playing_note = -1;

  digitalWrite(LED_BUILTIN, LOW);
}

uint8_t command_bytes[4]= { 0, 0, 0, 0 };

void clear_command() {
  command_bytes[0] = 0;
  command_bytes[1] = 0;
  command_bytes[2] = 0;
  command_bytes[3] = 0;
}

void push_command_byte( uint8_t b ) {
  command_bytes[3] = command_bytes[2];
  command_bytes[2] = command_bytes[1];
  command_bytes[1] = command_bytes[0];
  command_bytes[0] = b;
}

void loop() {
  // put your main code here, to run repeatedly:
  int b = Serial.read();
  if( b == -1 ) {
    return;
  }

  if( b == 0xF8 ) {
    clock_pulse();
    clear_command();
    return;
  }

  push_command_byte( b );

  if( ( command_bytes[2] & 0xF0 ) == 0x80 ) {
    note_off( command_bytes[2] & 0x0F, command_bytes[1] );
    clear_command();
    return;
  }

  if( ( command_bytes[2] & 0xF0 ) == 0x90 ) {
    if( command_bytes[0] == 0x00 ) {
      note_off( command_bytes[2] & 0x0F, command_bytes[1] );
    } else {
      note_on( command_bytes[2] & 0x0F, command_bytes[1] );
    }
    clear_command();
    return;
  }

}
