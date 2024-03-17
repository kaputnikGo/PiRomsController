/*
    archive for functions
    that may be useful. 
    And notes.
*/


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

if (incomingByte != -1) { // -1 means no data is available
  //debugPrint("received: ", incomingByte);
  debugLCD(cardCol[1], incomingByte);
  //lcd.setCursor(0, 1); // set cursor to secon row
  //lcd.print(incomingByte); // print out the retrieved value to the 
}

void getNextPin(int count) {
  testCardTrigger(CARD_5_ADDR, pinsArray[count]);
}

void updateLCD(int row, char* name, char* value) {
  // no flickering,
  lcd.setCursor(0, row);
  lcd.print(name);
  lcd.setCursor(6, row);
  lcd.print(value);
}

void clearPrintLCD(char* printOut) {
  // can flicker
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(printOut);
}

void testController() {
  if (pinCounter <= 31) {
    sprintf(bufferHex, "%02x", pinsArray[pinCounter]); 
    //output to lcd
    //playheadLCD(7, bufferHex);
    getNextPin(pinCounter);
    pinCounter++;
  }
  else {
    pinCounter = 0;
    readCard();
  }
}

byte getPinHex(int candy) {
  // assuming a decimal number
  // candy = [0, ..., 31]
  return pinsArray[candy];
}

void printLCD(int cardNum, int pinInt) {
  // convert to pinHex char, send to playheadLCD(1, pinHex)
  // requires char
  sprintf(bufferHex, "%02x", pinsArray[pinInt]);
  playheadLCD(cardNum, bufferHex);
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

void loop() {
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