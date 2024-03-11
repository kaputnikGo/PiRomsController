/*
  Card05-test
  access onboard LED as status light
  test i2c connection to card05
  includes i2cScanner function to get addresses
  debug to Serial Monitor

  -- WORKING:
  - loop of pinArray, captured by Logic Analyser
  - play specfic card with pinHex array
  - timer library for tempo control
  - GPIO_REG read and write
  - LCD output
  - MCP and NAND outputs
  - serial monitor command send pin int
  - serial monitor send pin to specific card (1-5)

  -- TODO
  - wire up soundboard !!

*/

/*
INIT
*/
#include <Wire.h>
#include <arduino-timer.h>
#include <LiquidCrystal_I2C.h>
#include "CommandLine.h"

// debugPrint("myVar= ", myVar);
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
const int PIN_NUMS = 32;
#define MAIN_TIMER      800     // 800 ms
#define TEST_TIMER      250     // 250 ms

int pinCounter = 0;       //test counter for pins, 0-31
char buffer[16];
char bufferHex[4];

/*
need to setup the MCP23008 pin input/ouput etc
iodir_register = 0x00
gpio_register = 0x09
enable as output:
bus.write_byte_data(card, iodir_register, 0x00)
*/

/*
example seq txt file with | as sentinel between CARDs, pin number is decimal
"0.7"=tempo, "n"=ignore, "-,0"=unused control 
19,0.7|10,0|19,0|n,0
n,0|n,0|n,0|n,0
n,0|n,0|n,0|n,0
n,0|n,0|n,0|n,0
n,0|n,0|n,0|n,0
n,0|n,0|n,0|n,0
n,0|n,0|n,0|n,0
14,0|n,0|31,0|n,0
19,0|10,0|19,0|n,0
py seq sends pinArray[num] as hex to gpio, ie:
bus.write_byte_data(card, gpio_register, 0x23)
tempo 0.7 = 700 ms
*/

// hex array for sending to Controller card, all pins
// note the sequence is for the Soundboard sound select IOJ3
const byte pinsArray[32] = {
	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 
	0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
	0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 
	0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F  
};

const int cardCol[6] = {0, 1, 4, 7, 10, 13};    // account for unused zero 

auto timer = timer_create_default(); // create a timer with default settings

LiquidCrystal_I2C lcd(0x27, 16, 2);   // lcd addr 0x27 (dec 39), col, row

/*
FUNCTIONS
*/

/*
void i2cScanner() {
  byte error, address;
  int nDevices;
  Serial.println("Scanning...");
  nDevices = 0;
  for (address = 1; address < 127; address++) {
    //check return value
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("i2c device found at address 0x");
      if (address < 16)
        Serial.print("0");
      Serial.print(address, HEX);
      Serial.println(" !");
      nDevices++;
    }
    else if (error == 4) {
      Serial.print("Unknown error at address 0x");
      if (address < 16)
        Serial.print("0");
      Serial.print(address, HEX);
    }
  }
  if (nDevices == 0)
    Serial.println("No i2c devices found\n");
  else
    Serial.println("done\n");
}
*/

void setupLCD() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiLL-i-ROMS test");
  lcd.setCursor(0, 1);
  lcd.print("|__|__|__|__|__|");
  Serial.println("WiLL-i-ROMS test");
}

void updateLCD(int row, char* name, char* value) {
  // no flickering,
  lcd.setCursor(0, row);
  lcd.print(name);
  lcd.setCursor(6, row);
  lcd.print(value);
}

void playheadLCD(int cardNum, char* value) {
  // 16 cols, /5 = cols={1,4,7,10,13}
  // hardcoded for the cols
  lcd.setCursor(cardNum, 1);
  lcd.print(value);
}

void clearPrintLCD(char* printOut) {
  // can flicker
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(printOut);
}

void cardSetup() {
  Wire.beginTransmission(CARD_5_ADDR);
  Wire.write(IODIR_REGISTER);
  Wire.write(0x00);
  Wire.endTransmission();
}
// test read from card
void readCard() {
  Wire.beginTransmission(CARD_5_ADDR);
  Wire.write(GPIO_REGISTER);
  Wire.endTransmission();
  Wire.requestFrom(CARD_5_ADDR, 1); // one byte read
  uint8_t val = Wire.read();
  Serial.print("read from GPIO: ");
  Serial.print(val, HEX);
  Serial.println("");
}

byte getPinHex(int candy) {
  // assuming a decimal number
  // candy = [0, ..., 31]
  return pinsArray[candy];
}

void playPin(byte pinHex) {
  // play single pin on any card running
}

void playCardPin(int cardNum, byte pinHex) {
  // play single pin on specific card num
}

void debugLCD(int cardNum, int pinInt) {
  // convert to pinHex char, send to playheadLCD(1, pinHex)
  // requires char
  sprintf(bufferHex, "%02x", pinsArray[pinInt]);
  playheadLCD(cardNum, bufferHex);
}

void testCardTrigger(int cardNum, byte pinHex) {
  //must zero the pins first
  // Card05, decimal 36 (0x24)(bin 100100)
  digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  Wire.beginTransmission(cardNum);
  Wire.write(GPIO_REGISTER);
  Wire.write(pinHex);
  Wire.endTransmission();
  digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
}

void getNextPin(int count) {
  testCardTrigger(CARD_5_ADDR, pinsArray[count]);
}

void testController() {
  if (pinCounter <= 31) {
    sprintf(bufferHex, "%02x", pinsArray[pinCounter]); 
    //output to lcd
    playheadLCD(7, bufferHex);
    getNextPin(pinCounter);
    pinCounter++;
  }
  else {
    pinCounter = 0;
    //readCard();
  }
}

void listenJava() {
  if (Serial.available() > 0) {    
    byte incomingByte = 0;
    incomingByte = Serial.read(); // read the incoming byte:
    if (incomingByte != -1) { // -1 means no data is available
      //debugPrint("received: ", incomingByte);
      debugLCD(cardCol[1], incomingByte);
      //lcd.setCursor(0, 1); // set cursor to secon row
      //lcd.print(incomingByte); // print out the retrieved value to the 
    }
  }
}

/*
SETUP
*/
// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  //
  Wire.begin();     // join i2c bus
  cardSetup();      // test setting iodir reg on card5
  Serial.begin(9600);
  //Serial.println("\ni2c Scanner");
  // call function every nnn milliseconds
  timer.every(TEST_TIMER, testController);
  //timer.every(5000, i2cScanner)
  setupLCD();
}

/*
MAIN LOOP
*/
// the loop function runs over and over again forever
void loop() {
  timer.tick(); // tick the timer
  // test comms from java app
  listenJava();
  // test receive commands with a constant poll, move to a timer?
  if (getCommand(CommandLine)) {
    // does not check for bad nums
    uint8_t result = processCommand(CommandLine);
    if (result > 0 && result <= PIN_NUMS) {
      // send it to i2c
      // check for userCard
      if (userCard >= 1 && userCard <= 5) {
        debugLCD(cardCol[userCard], result);
      }
      else {
        // fallback to safe, or use zero null position?
        debugLCD(1, result);
      }
      debugPrint("userCard: ", userCard);
    }
    else {
      // bad number !(1-32)
      // does not clear the last good num sent to LCD
      int read = COMMAND_BUFFER_LENGTH;
      debugPrint("ERROR bad num: ", result);
    }
  }
}
