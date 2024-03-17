/*
  Card05-test

  -- WORKING:
  - can read full 5 card line from USB serial

  -- TODO
  - wire up soundboard(s) !!

*/

/*
INIT
*/
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define  debugPrint(x,y) (Serial.print(x), Serial.println(y))
// found card05 at addr 0x24
// Wire.h requires int not uint8_t for transmission
// piRoms controller enum:
const int CARD_1_ADDR = 32;      // 0x20
const int CARD_2_ADDR = 33;      // 0x21
const int CARD_3_ADDR = 34;      // 0x22
const int CARD_4_ADDR = 35;      // 0x23
const int CARD_5_ADDR = 36;      // 0x24
const byte IODIR_REGISTER = 0x00;
const byte GPIO_REGISTER = 0x09;
//const int PIN_NUMS = 32;
// hex array for sending to Controller card, all pins
// note the sequence is for the Soundboard sound select IOJ3
const byte pinsArray[32] = {
	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 
	0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
	0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 
	0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F  
};

const int cardCol[6] = {0, 1, 4, 7, 10, 13};    // account for unused zero 
LiquidCrystal_I2C lcd(0x27, 16, 2);   // lcd addr 0x27 (dec 39), col, row

const char STOP_BIT = 99; // 0x63, should never get this value in normal pin ops
const int LINE_SIZE = 11; // 2 per card plus stop_bit
byte buf[LINE_SIZE];
char bufferHex[4];
int readLength = 0;

/*
FUNCTIONS
*/
void playheadLCD(int cardNum, char value) {
  lcd.setCursor(cardCol[cardNum], 1);
  sprintf(bufferHex, "%02x", pinsArray[(int)value]);
  lcd.print(bufferHex);
}
void playCardPinHex(int cardNum, byte pinHex) {
  //must zero the pin first <- still necessary?
  // Card05, decimal 36 (0x24)
  digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  Wire.beginTransmission(cardNum);
  Wire.write(GPIO_REGISTER);
  //Wire.write(0);
  Wire.write(pinHex);
  Wire.endTransmission();
  // update LCD after i2c write
  playheadLCD(cardNum, pinHex);
  digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
}
//called in main loop
void listenSerial() {
  if (Serial.available() > 0) {    
    // reads up to STOP_BIT, does not include in buf
    readLength = Serial.readBytesUntil(STOP_BIT, buf, LINE_SIZE);
    for(int i = 0; i < readLength; i += 2) {
      //read 2 bytes, 1st is card, 2nd is pin
      playCardPinHex(int(buf[i]), buf[i+1]);
    }
  }
}
/*
SETUP
*/
// setup sub functions
void setupLCD() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiLL-i-ROMS test");
  lcd.setCursor(0, 1);
  lcd.print("|__|__|__|__|__|");
  //debug print
  Serial.println("WiLL-i-ROMS tester");
}
void cardSetup() {
  // set the IO reg to enable output from MCP23008
  // need to loop thru all cards
  Wire.beginTransmission(CARD_5_ADDR);
  Wire.write(IODIR_REGISTER);
  Wire.write(0x00);
  Wire.endTransmission();
}

// proper setup function runs once on reset or power on
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  Wire.begin();     // join i2c bus
  cardSetup();      // test setting iodir reg on card5
  Serial.begin(9600);
  setupLCD();
}

/*
MAIN LOOP
*/
// the loop function runs over and over again forever
void loop() {
  listenSerial();
}
