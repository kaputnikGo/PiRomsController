/*****************************************
  Test:
     in Serial Monitor type these commands followed by return:
      add 5, 10
      subtract 10, 5

  ** this could be simplified

/*********/

#include <string.h>
#include <stdlib.h>

#define CR '\r'
#define LF '\n'
#define BS '\\b'
#define NULLCHAR '\0'
#define SPACE ' '
#define COMMAND_BUFFER_LENGTH 25 

char CommandLine[COMMAND_BUFFER_LENGTH];  // buffer +1 for a termination char
const char *delimiters = ", \ ";                    
const char *addCommandToken = "add";
const char *subCommandToken = "sub";
const char *sendCommandToken = "send";      // send an int to be index in pinHex array
const char *cardCommandToken = "card";      // send a pin to specific card: card 5, 31

// temp var for the card number selected (1-5)
int userCard = 0;


/*****************************************
      Return the string of the next command.  
      Commands are delimited by return
      Handle BackSpace character
      Make  all chars lowercase
*****************************************/
 // COMAND_BUFFER_LENGTH must be less than 255 chars long
bool getCommand(char  * commandLine) {
  static uint8_t charsRead = 0;
  //read asynchronously until full command input
  while (Serial.available()) {
    char c = Serial.read();
    switch (c) {
      case CR:      //termination chars
      case LF:
        commandLine[charsRead] = NULLCHAR;        // null terminate our command char array
        if (charsRead  > 0)  {
          charsRead = 0;                          // charsRead is static,  so have to reset
          //Serial.println(commandLine);
          return true;
        }
        break;
      case BS:                                    // handle backspace in input: put a space in last char
        if (charsRead > 0)  {                     // and adjust commandLine and charsRead
          commandLine[--charsRead] = NULLCHAR;
          Serial << byte(BS) << byte(SPACE) << byte(BS);
        }
        break;
      default:
        // c = tolower(c);
        if (charsRead < COMMAND_BUFFER_LENGTH) {
          commandLine[charsRead++] = c;
        }
        commandLine[charsRead] = NULLCHAR;        // fallback to a null char
        break;
    }
  }
  return false;
}

/*  ****************************
   readNumber: return a 16bit signed integer from the command line
   readWord: get a text word from the command line
*/
int readNumber () {
  char * numTextPtr = strtok(NULL, delimiters);
  return atoi(numTextPtr); 
}
char * readWord() {
  char * word = strtok(NULL,  delimiters);
  return word;
}
void errorCommand(char  * ptrToCommandName) {
  Serial.print("Command not found: ");
  Serial.println(ptrToCommandName);
}

/****************************************************
   commands
*/
// need a card and pin command
// int + int
int cardCommand() {
  int cardNum = readNumber();
  // will be vars for changing number of cards available after i2c bus poll
  if (cardNum >= 1 && cardNum <= 5) {
    userCard = cardNum;
  }
  int pinInt = readNumber();
  return pinInt;
}

int sendCommand() {
  // send this over i2c
  return readNumber();
}

int addCommand() {
  int firstOperand = readNumber();
  int secondOperand = readNumber();
  return firstOperand + secondOperand;
}

int subCommand() {
  int firstOperand = readNumber();
  int secondOperand = readNumber();
  return firstOperand - secondOperand;
}

/****************************************************
   called by main .ino file, debugs are rem'd
*/
int processCommand(char * commandLine) {
  /*
  Serial.print("Command: ");
  Serial.println(commandLine);
  */
  int result = 0;
  char * ptrToCommandName = strtok(commandLine,  delimiters);
  /*
  Serial.print("commandName: ");
  Serial.println(ptrToCommandName);
  */
  // process the example commands here, change for diff commands
  if (strcmp(ptrToCommandName, cardCommandToken) == 0) {
    result = cardCommand();
    //Serial.print("send: ");
    //Serial.println(result);
  }
  else if (strcmp(ptrToCommandName, sendCommandToken) == 0) {
    result = sendCommand();
    //Serial.print("send: ");
    //Serial.println(result);
  }
  else if (strcmp(ptrToCommandName, addCommandToken) == 0) {
    result = addCommand();
    //Serial.print("add: ");
    //Serial.println(result);    
  } 
  else if (strcmp(ptrToCommandName, subCommandToken) == 0) {
    result = subCommand();
    //Serial.print("subtract: ");
    //Serial.println(result);
  } 
  else {
    errorCommand(ptrToCommandName);
  }
  return result;
}