import processing.io.*;

// testing RaspPi Processing for WiLL-i-ROMS Hex sequencer

I2C i2cBus;
PFont font;
// "card" refers to the breadboard mcp23008 + cd4066 controllers
byte card_1, card_2, card_3, card_4, card_5;
byte[] cardArray;
// mcp23008 registers:
byte iodir_register;
byte ipol_register;
byte gpintern_register;
byte defval_register;
byte intcon_register;
byte iocon_register;
byte gppu_register;
byte intf_register;
byte intcap_register;
byte gpio_register;
byte olat_register;

String tempText;

void setup() {
  size(600, 400);
  // alt to size(x,y) is fullscreen();
  // only one can be used as first line in setup()
  // or size(displayWidth, displayHeight)
  background(51);
  font = createFont("", 12);
  fill(0, 255, 0); //text fill colour
  textFont(font);
  println("Checking i2c bus...");
  printArray(I2C.list());
  println("Checking attached devices...");
  // cards: 0x20, 0x21, 0x22, 0x23, 0x24
  // NEED SUDO for i2c permissions
  i2cBus = new I2C(I2C.list()[0]);
  //TODO need to poll for enum device addresses, not hard code them
  cardArray = new byte[5];
  cardArray[0] = card_1 = 0x20;
  cardArray[1] = card_2 = 0x21;
  cardArray[2] = card_3 = 0x22;
  cardArray[3] = card_4 = 0x23;
  cardArray[4] = card_5 = 0x24;
  // etc
  // mcp23008 registers:
  iodir_register = 0x00; // def. 1111 1111, 0xff
  ipol_register = 0x01; // all rest are 0000 0000, 0x00
  gpintern_register = 0x02;
  defval_register = 0x03;
  intcon_register = 0x04;
  iocon_register = 0x05; // def. --00 000- 
  gppu_register = 0x06;
  intf_register = 0x07;
  intcap_register = 0x08;
  gpio_register = 0x09;
  olat_register = 0x0a;

  // stop card(s), zero it then call reset hex:
  // i2cBus.write(card, gpio_register, 0x00)
  // i2cBus.write(card, gpio_register, 0x23)
  
  // play card(s), zero call first, then audio hex:
  // i2cBus.write(card, gpio_register, 0x00)
  // i2cBus.write(card, gpio_register, pinHex)
  runTest();
}

void runTest() {
  
  // text(text, x, y);
  text("Start iodir set and poll test...", 10, 20);
  int i = 0;
  int posi = 45;
  while (i < cardArray.length) {
    if (checkCard(cardArray[i])) {
      initCard(cardArray[i]);
      pollCard(cardArray[i]);
      text("init card " + (i + 1), 10, posi + (i * 15));
    }
    else {
      // card not found with an error
      text("error with card " + (i + 1), 10, posi + (i * 15));
    }
    i++;
  }
  // call end
  println("start test loop sound 0x01...");
  playTestLoop(cardArray[0]);
  println("End of test");
  text("End of test.", 10, 130);
}

boolean checkCard(byte cardHex) {
  // return if cardHex is present and connected
  tempText = "check card " + String.format("0x%02X", cardHex);
  println(tempText);
  try {
    i2cBus.beginTransmission(int(cardHex));
  }
  catch (Exception ex) {
    // consume it, hopefully
    println("checkcard error: " + ex);
    return false;
  }
  return true;
}

void initCard(byte cardHex) {
  // cardHex values 0x20 to 0x24
  // init each mcp23008 to IODIR output
  // default value is 0xff (input)
  tempText = "init card " + String.format("0x%02X", cardHex);
  println(tempText);  
  i2cBus.beginTransmission(int(cardHex));
  i2cBus.write(iodir_register);
  i2cBus.write(0x00);
  i2cBus.endTransmission();
}

void pollCard(byte cardHex) {
    // reg call start
  i2cBus.beginTransmission(int(cardHex));
  i2cBus.write(iodir_register);
  byte readAddr = i2cBus.read(1)[0];
  tempText = "IODIR reg state: " + String.format("0x%02X", readAddr);
  println(tempText);
  // call end, when read() do not need i2cBus.endTransmission();
}

void playTestLoop(byte cardHex) {
  // use delay(1000) for one sec delay
  int loopLength = 10;
  for (int i = 0; i <= loopLength; i++) {
    i2cBus.beginTransmission(int(cardHex));
    i2cBus.write(gpio_register);
    i2cBus.write(0x00); // reset first
    i2cBus.write(0x01); // pinball rom 1 : blaster sound
    i2cBus.endTransmission();
    println("Blaster " + i);
    delay(500);
  }
}
