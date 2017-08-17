# WiLL-i-ROMS-Controller
#
# raspPi -> mcp23008 -> CD4066B -> Soundboards
# using python -V 2.7.3
#
# NOTES:
# -sequencer file format different from blocks
# -sound card(s) enumeration
# -Card1 CC is now timer CLK
# -sped up seq loading into tracker to near instant
# -card / seq type selector now to dialog from util menu
# -adding bit player and code clean up
# -added card 4
# -change block format into seq format
# -moved bitPlayer, cardSelect to main screen, removed 2 dialogs
#
# TODO
# - rewrite in C (wiringPi) and GTK+3 (Glade)
# - sort out the old block Play code, replace with seq format
# - separate this file into multiple class files
# - CARD_ENUM at init to populate, account for a CARD to be missing
# - blockPlay and midiToPins require CARD_ENUM, card switches popup
# - reload button to reload current file (when writing via geany)
# - possible auto load sequential seqs (numbered) as load is instant
# - pause seq button, then it resumes..
# - user write/edit/save file sequence
# - CC messages - all midi CCs trig pin 1 every data send tick
# - rom12.716 organ trigger ?
# - pinX[1] as volume pot via pwm, or ROM id num ?
#
from Tkinter import *
import tkSimpleDialog
from tkFileDialog import askopenfilename
from tkFileDialog import asksaveasfilename
import tkFont
import tkMessageBox
import smbus
import time
from rtmidi.midiutil import open_midiport
import threading
from os import path

#GLOBALS
VERSION = "1.4.3"
CARD_1_ADDR = 0x20
CARD_2_ADDR = 0x21
CARD_3_ADDR = 0x22
CARD_4_ADDR = 0x23
CARD_ENUM = [CARD_1_ADDR, CARD_2_ADDR, CARD_3_ADDR, CARD_4_ADDR]

TEST_TIMER = 0.2
RUN_LOOP = False
MAIN_TIMER = 0.8
MIDI_LISTEN = False

#combine CARD_LIST with CARD_ADDR so enum has both name and address
CARD_LIST = ["CARD_1", "CARD_2", "CARD_3", "CARD_4"]
SEQ_TYPE_LIST = ["patt1Test", "blockSeqPlay", "seqFilePlay"]
USER_SEQ_TYPE = ""
USER_CARD = "CARD_1"
BIT_LIST = ["19"]
BLOCK_LIST = []
SEQ_FILE_CONTENT = []
SEQ_FILE_NAME = ""
SEQ_FILE_SIZE = 0
BLOCK_LINE_COUNTER = 0


#multi pins in order
pinsArray = {
	0:0x00, 1:0x01, 2:0x02, 3:0x03, 4:0x04, 5:0x05,
	6:0x06, 7:0x07, 8:0x08, 9:0x09, 10:0x0A, 
	11:0x0B, 12:0x0C, 13:0x0D, 14:0x0E, 15:0x0F,
	16:0x20, 17:0x21, 18:0x22, 19:0x23, 20:0x24,
	21:0x25, 22:0x26, 23:0x27, 24:0x28, 25:0x29,
	26:0x2A, 27:0x2B, 28:0x2C, 29:0x2D, 30:0x2E,
	31:0x2F
	}
#blocks for patt1Test()	
block1Array = {
	0:0x01, 1:0x03, 2:0x02, 3:0x00, 
	4:0x08, 5:0x0B, 6:0x00, 7:0x08
	}
	
block2Array = {	
	0:0x0B, 1:0x0B, 2:0x0B, 3:0x0B, 
	4:0x01, 5:0x0B, 6:0x0B, 7:0x0B
	}
	
block3Array = {
	0:0x0C, 1:0x0D, 2:0x20, 3:0x3A, 
	4:0x0C, 5:0x0D, 6:0x20, 7:0x3A
	}

########### INIT ###########
bus = smbus.SMBus(1)
iodir_register = 0x00
gpio_register = 0x09
#enable as output
for card in CARD_ENUM:
	print("Card: " + str("0x%x" % card))
	bus.write_byte_data(card, iodir_register, 0x00)

midiPort = 1 # set for MK-425C midi controller
	
	
###### CONTROL FUNCTIONS #####	
def stopAll():
	#must zero the pins first, pin 19 (0x23) as RESET
	# this pin is not used in some ROMs, instead: 21,22 (0x25, 0x26)
	# ensure cards 1,2,3 are type 1 with 0x23 reset roms.
	#need to figure out rom use in card4 
	global CARD_ENUM
	for card in CARD_ENUM:
		bus.write_byte_data(card, gpio_register, 0x00)
		if card == CARD_4_ADDR:
			bus.write_byte_data(card, gpio_register, 0x25)
		else:
			bus.write_byte_data(card, gpio_register, 0x23)

	status.set("%s", "stop all")
	
def kybdHalt():
	status.set("%s", "kybd halt")
	loopCheckControl(0)
	stopAll()

def playPin(pinHex):
	if pinHex is None:
		return
	else:
		#must zero the pins first
		global CARD_ENUM
		for card in CARD_ENUM:
			bus.write_byte_data(card, gpio_register, 0x00)
			bus.write_byte_data(card, gpio_register, pinHex)
		
def playCardPin(cardHex, pinHex):
	if pinHex is None:
		return
	else:
		#must zero the pins first
		bus.write_byte_data(cardHex, gpio_register, 0x00)
		bus.write_byte_data(cardHex, gpio_register, pinHex)
		
def updateTimer(userTime):
	status.set("%s %s", "timer update: ", userTime)
	if not userTime:
		return
	elif (userTime < 0.1):
		return
	elif (userTime > 1.0):
		return
	else:
		global MAIN_TIMER
		MAIN_TIMER = userTime

def updateSeqType(userSeqType):
	status.set("%s %s", "seq type select: ", userSeqType)
	if not userSeqType:
		return
	else:
		global USER_SEQ_TYPE
		USER_SEQ_TYPE = userSeqType	

def updateUserCard(userCard):
	status.set("%s %s", "card select: ", userCard)
	if not userCard:
		return
	else:
		global USER_CARD
		USER_CARD = userCard

############## FILE PLAY ################
def trackerSeqFileFormat(lineNum, line):
	#needs to account for no card values
	carded = line.split("|")
	numCards = len(carded)
	if (numCards <= 0):
		return
	
	printLine = (str(lineNum))
	for i in range(0, numCards):
		card = carded[i].split(",")
		printLine += "\t" + card[0] + "\t" + card[1]
		
	printLine += "\n"
	return printLine


def trackerSeqFile():
	global SEQ_FILE_CONTENT
	global SEQ_FILE_SIZE
	lineNum = 1
	formattedLines = ""
	tracker.clear()
	header.playheadClear()
	header.playheadLine("\t\tLOADING SEQUENCE...")
	for line in SEQ_FILE_CONTENT:		
		formattedLines += trackerSeqFileFormat(lineNum, line)
		lineNum += 1
	header.playheadLine("\t\t\tREADY"	)
	SEQ_FILE_SIZE = lineNum - 1
	controls.updateCurrentSeq()
	tracker.set(formattedLines)
	tracker.scrollbarSet(lineNum)
#end func

def checkValidSeqPin(temp):
	if temp == "n":
		temp = None
	elif temp == "":
		temp = None
	else:
		temp = int(temp)
	return temp
	
def seqFilePlay():
	#have list of seq lines "11,0.8|1,0" etc
	global SEQ_FILE_CONTENT
	global CARD_ENUM
	
	if not SEQ_FILE_CONTENT:
		status.set("%s", "seq file content empty")
		loopCheckControl(0)
		return
	else:	
		status.set("%s", "seq file play")
		lineCounter = 1
		for line in SEQ_FILE_CONTENT:
			carded = line.split("|")
			numCards = len(carded)
			playheadString = str(lineCounter)
			for i in range(0, numCards):
				pin = carded[i].split(",")
				pin[0] = checkValidSeqPin(pin[0])
				#pin[1] testing for timer
				if pin[1] != "0":
					#has a useable string value				
					#convert and update timer
					updateTimer(float(pin[1]))
					
				playCardPin(CARD_ENUM[i], pinsArray.get(pin[0], None))
				playheadString += "\t" + str(pin[0]) + "\t0"
			
			header.playheadLine(playheadString)
			lineCounter += 1
			time.sleep(MAIN_TIMER)

		status.set("%s", "seq file end")

############## TEST BLOCKS ################
def oneTest():
	status.set("%s", "test pin")
	global CARD_ENUM
	for card in CARD_ENUM:
		bus.write_byte_data(card, gpio_register, 0x00)
		bus.write_byte_data(card, gpio_register, 0x03)

	time.sleep(TEST_TIMER)
	stopAll()


def allTest():
	#run through all 31
	status.set("%s", "test all")
	for key in pinsArray:
		playPin(pinsArray[key])
		time.sleep(TEST_TIMER)
	stopAll()
	
def block1():
	for key in block1Array:
		playPin(block1Array[key])
		time.sleep(MAIN_TIMER)
#end block1

def block2():
	for key in block2Array:
		playPin(block2Array[key])
		time.sleep(MAIN_TIMER)	
#end block2

def block3():
	for key in block3Array:
		playPin(block3Array[key])
		time.sleep(MAIN_TIMER)	
#end block3

############ USER BLOCK ###############
def getCardAddr(cardName):
	global CARD_ENUM
	if not cardName:
		cardName = "CARD_1"

	if cardName == "CARD_1":
		return CARD_ENUM[0]
	elif cardName == "CARD_2":
		return CARD_ENUM[1]
	elif cardName == "CARD_3":
		return CARD_ENUM[2]
	elif cardName == "CARD_4":
		return CARD_ENUM[3]
	else:
		return CARD_ENUM[0]
	
	
def createBlock(result):
	#change to seq format
	if not result:
		return
	else:	
		#make into list
		#global BLOCK_LINE_COUNTER
		status.set("%s %s", "create block: ", result)
		global BLOCK_LIST
		BLOCK_LIST = result
		tracker.set(BLOCK_LIST)
		#BLOCK_LINE_COUNTER += 1
		#tracker.scrollbarSet(BLOCK_LINE_COUNTER)
		
def blockSeqPlay():
	global BLOCK_LIST
	global MAIN_TIMER
	global CARD_ENUM
	
	if not BLOCK_LIST:
		status.set("%s", "block seq empty")
		loopCheckControl(0)
		return
	else:	
		status.set("%s", "block seq play")
		#checks and converts
		#for line in BLOCK_LIST:
		lineCounter = 1
		line = BLOCK_LIST
		carded = line.split("|")
		numCards = len(carded)
		playheadString = str(lineCounter)
		for i in range(0, numCards):
			pin = carded[i].split(",")
			pin[0] = checkValidSeqPin(pin[0])
			#pin[1] testing for timer
			if pin[1] != "0":
				#has a useable string value				
				#convert and update timer
				updateTimer(float(pin[1]))
					
			playCardPin(CARD_ENUM[i], pinsArray.get(pin[0], None))			
			playheadString += "\t" + str(pin[0]) + "\t0"
								
		header.playheadLine(playheadString)
		lineCounter+=1
		time.sleep(MAIN_TIMER)
	
def patt1Test():
	status.set("%s", "patt1 test")
	for i in range(0, 1):
		for x in range(0, 2):
			block1()		
			block3()			
		block2()			
#end patt1Test	

def loopCheckControl(value):
	#0=off/unselected,1=on/selected
	global RUN_LOOP
	if (value == 0):
		RUN_LOOP = False
		status.set("%s", "RUN_LOOP off")
	else:
		RUN_LOOP = True
		status.set("%s", "RUN_LOOP on")

########### FILE UTIL INFO ###########
# TODO
def newSeq():
	status.set("%s", "new not implemented")
	
def loadBlock():
	
	global BLOCK_LIST
	global BLOCK_LINE_COUNTER
	fileName = askopenfilename()
	if not fileName:
		return
	with open(fileName) as file:
		fileContents = file.read()
		BLOCK_LIST = fileContents.split(',')
		#file.close()
	tracker.clear()
	tracker.set(BLOCK_LIST)
	BLOCK_LINE_COUNTER += 1
	tracker.scrollbarSet(BLOCK_LINE_COUNTER)
	status.set("%s", "file read into block list")

def loadSeqFile():
	global SEQ_FILE_CONTENT
	global SEQ_FILE_NAME
	fileName = askopenfilename()
	if not fileName:
		return
	with open(fileName) as file:
		SEQ_FILE_CONTENT = file.readlines()
	
	#remove whitespace chars
	SEQ_FILE_CONTENT = [line.strip() for line in SEQ_FILE_CONTENT]
	SEQ_FILE_NAME = path.basename(fileName)
	status.set("%s", "seq file read: " + SEQ_FILE_NAME)
	trackerSeqFile()	
		
def saveBlock():
	global BLOCK_LIST
	if not BLOCK_LIST:
		status.set("%s", "no block data to save")
		return
	else:
		#file_ = open('BlockSave.txt', 'w')
		filename = asksaveasfilename(
			defaultextension=".txt", 
			initialfile="BlockSave.txt")
			
		if filename is None:
			return
		else:
			file_ = open(filename, 'w')		
		counter = 0			
		for entry in BLOCK_LIST:
			#catch last line here
			if (counter < len(BLOCK_LIST) - 1):
				file_.write("%s" % entry + ",")
				counter += 1
			else:
				file_.write("%s" % entry)
				
		file_.close()
		status.set("%s", "block list saved to file")

def saveSeqFile():
	status.set("%s", "save not implemented")

def callback():
	status.set("%s", "empty callback")
#end func
def callExit():
	if tkMessageBox.askokcancel("Quit", "Oh really?"):
		root.destroy()
#end func
	
def seqTypeSelect():
	seqTypeDialog = SeqTypeDialog(root)

def helpDialog():
	status.set("%s", "help not implemented")
	
def aboutDialog():
	aboutDialog = AboutDialog(root)

########### SEQ THREAD CLASS ###########
# this will play out the current function
# kybd interrupt crashes it
class SeqThread(threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		# check or suffer
		global USER_SEQ_TYPE
		if not USER_SEQ_TYPE:
			USER_SEQ_TYPE = globals()["patt1Test"()]()
		
	def run(self):
		status.set("%s", "seq thread start")
		global USER_SEQ_TYPE
		while RUN_LOOP:		
			globals()[USER_SEQ_TYPE]()
					
		status.set("%s", "seq thread end")	
		return
		
#end class

########### MIDI INPUT CLASS ###########
class MidiThread(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self)

	global midiToPins
	def midiToPins(noteIn):
		# c=36, c#=37, etc
		# subtract 35 to get pinsArray[key]
		# assume has a note on velocity here
		# boundary check, for now
		if (noteIn <= 35):
			noteIn = 36
		elif (noteIn >= 67):
			noteIn = 66
		
		# bit clunky, add enum here
		global USER_CARD	
		pinAdjust = noteIn - 35
		playCardPin(getCardAddr(USER_CARD), pinsArray[pinAdjust])
		
	global midiToPinsOff
	def midiToPinsOff():
		#serves as note off/vel=0
		stopAll()
	
	global midiListen	
	def midiListen(message):
		# from list [0,1,2]
		# [1] = note number :: map to pins
		# [2] = vel (0-127)
		if (message[2] >= 1):
			midiToPins(message[1])
		else:
			midiToPinsOff()

	global midiError
	def midiError():
		status.set("%s %d", "Midi error for port: ", midiPort)
	#end funcs
			
	def run(self):
		try:
			midiin, port_name = open_midiport(midiPort)
		except (EOFError, KeyboardInterrupt):
			midiError()
		
		print "start MT thread"
		global USER_CARD
		status.set("%s %s", "Start midi listener on ", USER_CARD)	
		try:
			while MIDI_LISTEN:
				msg = midiin.get_message()
				if msg:
					message, deltatime = msg
					midiListen(message)	
					
				time.sleep(0.01)

		except KeyboardInterrupt:
			kybdHalt()
		finally:
			print('Stop midi listener')
			midiin.close_port()
			del midiin
#end class

###### INTERFACE CLASSES #######
class AboutDialog(tkSimpleDialog.Dialog):
	def body(self, master):
		global VERSION
		Label(master, text="WiLL-i-ROMS Controller").grid(row=0,sticky=W)
		Label(master, text="Hex Sequencer version " + VERSION).grid(row=1,sticky=W)
		Label(master, text="(multi board testing)").grid(row=2,sticky=W)
		Label(master, text="(live version)").grid(row=3,sticky=W)
		Label(master, text="---------------------").grid(row=4,sticky=W)
		Label(master, text="KaputnikGo, 2017").grid(row=5,sticky=W)
	
	
class CreateDialog(tkSimpleDialog.Dialog):	
	def body(self, master):
		Label(master, text="block:").grid(row=0, sticky=W)
		self.entry1 = Entry(master)
		
		global BLOCK_LIST
		if BLOCK_LIST:
			#counter = 0
			entryString = ""
			for entry in BLOCK_LIST:
				entryString += entry
				#if (counter < len(BLOCK_LIST) - 1):
				#	entryString += (entry + ",")
				#	counter += 1
				#else:
				#	entryString += entry
				
			self.entry1.insert(END, entryString)
			
		self.entry1.grid(row=0, column=1)
		return self.entry1 #focus
		
	def apply(self):
		self.result = self.entry1.get()
#end class		
		
class SeqTypeDialog(tkSimpleDialog.Dialog):
	def body(self, master):
		Label(master, text="Seq type selector").grid(row=0,sticky=W)
		self.entrySeq = Entry(master)
		global SEQ_TYPE_LIST
		global USER_SEQ_TYPE
		self.radioSeq = StringVar()
		
		self.entrySeq.insert(END, USER_SEQ_TYPE)
		self.entrySeq.grid(row=0, column=1)
		
		counter = 1
		for seqChoice in SEQ_TYPE_LIST:
			rbname = "rb" + str(counter)
			self.rbname = Radiobutton(master, text=seqChoice,
				variable=self.radioSeq, value=seqChoice,
				command=self.updateType)
			self.rbname.grid(row=counter, column=0)
			if seqChoice == USER_SEQ_TYPE:
				self.rbname.select()
			else:
				self.rbname.deselect()
			counter+=1
			
	def updateType(self):
		self.entrySeq.delete(0,END)
		self.entrySeq.insert(0, self.radioSeq.get())
		
	def apply(self):
		self.userSeqType = self.entrySeq.get()
		if self.userSeqType:
			updateSeqType(self.userSeqType)

class TimerDialog(tkSimpleDialog.Dialog):
	def body(self, master):
		Label(master, text="range:1.0 - 0.1").grid(row=0,sticky=W)
		self.entryTimer = Entry(master)
		self.TIMES = [0.8, 0.7, 0.6, 0.5 ,0.4, 0.3, 0.2, 0.15]
		self.radioTime = DoubleVar()
		
		global MAIN_TIMER
		self.entryTimer.insert(END, MAIN_TIMER)
		self.entryTimer.grid(row=0, column=1)
		
		#radio buttons for mouse only control, bit OTT
		counter = 1
		for timeChoice in self.TIMES:
			rbname = "rb" + str(counter)
			self.rbname = Radiobutton(master, text=str(timeChoice),
				variable=self.radioTime, value=timeChoice,
				command=self.updateTime)
			self.rbname.grid(row=counter, column=0)
			if timeChoice == MAIN_TIMER:
				self.rbname.select()
			else:
				self.rbname.deselect()		
			counter+=1
		
		return self.entryTimer #focus
	
	def updateTime(self):
		self.entryTimer.delete(0,END)
		self.entryTimer.insert(0, self.radioTime.get())
		
	def apply(self):
		self.userTime = float(self.entryTimer.get())
		

class Controls:
	def __init__(self, master):
		frame = Frame(master)
		self.varLoop = IntVar()
		
		global SEQ_FILE_SIZE

		global USER_SEQ_TYPE
		global SEQ_TYPE_LIST
		USER_SEQ_TYPE = SEQ_TYPE_LIST[2]
		
		global USER_CARD
		global CARD_LIST
		USER_CARD = CARD_LIST[0]

		resetButton = Button(
			frame, text="Reset", fg="red", command=self.goReset)
		
		self.midiButton = Button(
			frame, text="midi OFF", fg="black", command=self.goMidi)
		
		createButton = Button(
			frame, text="Create", command=self.goCreate)
		
		self.loopCheck = Checkbutton(
			frame, text="loop", variable=self.varLoop,
			command=self.goLoop)			
		frame.bind("<Button-1>", self.goLoop)
		
		playSeqButton = Button(
			frame, text="Play", command=self.goPlaySeq)
		
		self.pauseSeqButton = Button(
			frame, text="pause", command=self.goPauseSeq)
		
		timerButton = Button(
			frame, text="Timer", command=self.goTimer)
			
		self.currentSeqLabel = Label(
			frame, text="SeqFile : size", fg="blue")
		
		print "load interface"
		frame.grid(column=0,row=0, columnspan=6)
		resetButton.grid(row=0, column=0, sticky=W)
		createButton.grid(row=0, column=1)
		self.midiButton.grid(row=0, column=2)
		timerButton.grid(row=0, column=3)
		self.pauseSeqButton.grid(row=0, column=4)
		self.loopCheck.grid(row=0, column=5, padx=5)#, sticky=E)
		playSeqButton.grid(row=0, column=6)#, sticky=E)	
			
		self.currentSeqLabel.grid(row=1, column=0, columnspan=5, sticky=W)		
			
	def goReset(self):
		print "reset"
		stopAll()
	#end func

#midiListen thread	
	def checkThreadMT(self):
		if self.mt.isAlive():
			root.after(500, self.checkThreadMT)
		else:
			print "end MT thread"
			status.set("%s", "Stop midi listener")
			return
	#end func	
	def goMidi(self, tog=[0]):
		global MIDI_LISTEN
		#global USER_CARD	
		tog[0] = not tog[0]
		if tog[0]:
			self.midiButton.config(text='midi ON_', fg="red")
			MIDI_LISTEN = True
			#USER_CARD = cardName.get()
			#USER_CARD = "CARD_1"
			self.mt = MidiThread()
			self.mt.start()
			self.checkThreadMT()
		else:
			self.midiButton.config(text='midi OFF', fg="black")
			MIDI_LISTEN = False
	#end func
	
	def goCreate(self):
		#dialog box for user input of int keys and Nones
		createDialog = CreateDialog(root)
		createBlock(createDialog.result)
	
	def goLoop(self):
		print "goLoop check"
		loopCheckControl(self.varLoop.get())
		
	def loopBind(event):
		loopCheckControl(self.varLoop.get())
	#end
	
#playSeq thread, SeqThread(sequence)
	def checkThreadSQ(self):
		if self.sq.isAlive():
			root.after(250, self.checkThreadSQ)
		else:
			print "end SQ thread"
			return
	#end func
		
	def goPlaySeq(self):
		self.sq = SeqThread()
		self.sq.start()
		self.checkThreadSQ()
	#end func
	
	def goPauseSeq(self, tog=[0]):
		#global PAUSE_SEQ
		tog[0] = not tog[0]
		if tog[0]:
			self.pauseSeqButton.config(text='PAUSED')
			#PAUSE_SEQ = True
		else:
			self.pauseSeqButton.config(text='pause')
			#PAUSE_SEQ = False
	
	def goTimer(self):
		timerDialog = TimerDialog(root)
		try:
			if timerDialog.userTime:
				updateTimer(timerDialog.userTime)
		except:
			return
				
	def updateCurrentSeq(self):
		global SEQ_FILE_NAME
		global SEQ_FILE_SIZE
		self.currentSeqLabel.config(text=SEQ_FILE_NAME + " : " + str(SEQ_FILE_SIZE))	
#end class	

class Header(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.canvas = Canvas(self, width=500, height=100)
		self.canvas.grid(row=0, column=0, columnspan=6, sticky=NW)
				
		vFont = tkFont.Font(family="Verdana",size=12,weight="normal")
		self.textHead1 = Text(self.canvas, font=vFont, fg="green", bg="black")
		self.textHead2 = Text(self.canvas, font=vFont, fg="green", bg="black")
		self.textHead1.config(height=1, width=67)
		self.textHead2.config(height=1, width=67)
							
		self.textHead1.insert("1.0", "LINE\tCARD1\tCLK\tCARD2\tCC\tCARD3\tCC\tCARD4\tCC\n")
		self.textHead2.insert("1.0", "   \t     \t  \t     \t  \t     \t  \t     \t   ")
		self.textHead1.grid(row=0, column=0, columnspan=6)
		self.textHead2.grid(row=2, column=0, columnspan=6)
		
	def playheadLine(self, message):
		self.textHead2.delete(1.0, END)
		self.textHead2.insert(END, message)
		
	def playheadClear(self):
		self.textHead2.delete(1.0, END)
		self.textHead2.insert("1.0", "   \t     \t  \t     \t  \t     \t  \t     \t   ")
		

class Tracker(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.seqLength = 0		
		#self.moveFraction = 0.017
		
		self.vFont = tkFont.Font(family="Verdana",size=12,weight="normal")
		self.fontHeight = self.vFont.metrics("linespace")	
		self.canvas = Canvas(self, bg="black", scrollregion=(0, 0, 0, 100))
		self.canvas.config(width=540, height=100)
		self.canvas.grid(row=0, column=0, sticky=NW)

		self.canvasTextID = self.canvas.create_text(5, 5, anchor="nw", 
			font=self.vFont, fill="green")			
		self.fontHeight = self.vFont.metrics("linespace")		
		self.canvas.itemconfig(self.canvasTextID, text="non tracker")
		
		self.yscrollbar = Scrollbar(self, orient=VERTICAL)
		self.yscrollbar.grid(row=0, column=6, sticky=N+S)
		self.canvas.config(yscrollcommand=self.yscrollbar.set)
		self.yscrollbar.config(command=self.canvas.yview)		
	
	def __call__(self, format, *args):
		self.canvas.update_idletasks()
	
	def set(self, message):
		self.canvas.insert(self.canvasTextID, INSERT, message)
		self.canvas.insert(self.canvasTextID, INSERT, "\n")
		self.canvas.update_idletasks()
		
	def scrollbarSet(self, lineNum):
		#account for zero not counted
		self.seqLength = lineNum + 1
		self.canvas.config(scrollregion=self.canvas.bbox(ALL))
		
	def clear(self):
		self.canvas.dchars(self.canvasTextID, 0, END)
		self.canvas.update_idletasks()
#end class

class BitPlayer(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.canvas = Canvas(self, width=540, height=200)
		self.canvas.grid(row=0, column=0, columnspan=5, rowspan=2, sticky=NW)
		self.canvas.config(bg="gray44")
		
		#card selector
		self.entryCard = Entry(master)		
		global CARD_LIST
		global USER_CARD
		self.radioCard = StringVar()		
		self.entryCard.insert(END, USER_CARD)
		# end card selector
		
		#for now use pinHex array, not bits,
		self.BITS = [2,3,4,5,6,7]
		self.NUMS = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]
		self.numVar = IntVar(master)
		self.numVar.set(self.NUMS[1])
		self.numOptions = OptionMenu(master, self.numVar, *self.NUMS)
		self.entryBits = Entry(master, width=6)
		self.bitsButton = Button(master, text="Trigger", command=self.trigger)
		self.stopButton = Button(master, text="Stop", command=self.stopBit)
		#self.modifyButton = Button(master, text="Modify", command=self.modifyBit)
		self.numVar.trace('w', self.optionSet)	
		self.entryBits.insert(END, self.numVar.get())
		
		#display card list
		counter = 0
		for cardChoice in CARD_LIST:
			rbname = "rb" + str(counter)
			self.rbname = Radiobutton(master, text=cardChoice,
				variable=self.radioCard, value=cardChoice,
				command=self.updateCard)
			#display radio buttons
			self.rbname.grid(row=4, column=counter)
			if cardChoice == USER_CARD:
				self.rbname.select()
			else:
				self.rbname.deselect()
			counter+=1
		
		self.entryBits.grid(row=5, column=0)
		self.numOptions.grid(row=5, column=1)
		self.bitsButton.grid(row=5, column=2)
		self.stopButton.grid(row=5, column=3)	
		#return self.entryBits #focus
		
	def optionSet(self, *args):
		#get option menu num
		self.entryBits.delete(0,END)
		self.entryBits.insert(END, self.numVar.get())
		
	def trigger(self):		
		self.bitsChecked = checkValidSeqPin(self.entryBits.get())
		self.cardAddr = getCardAddr(self.entryCard.get())
		playCardPin(self.cardAddr, pinsArray.get(self.bitsChecked, None))
		
	def stopBit(self):
		stopAll();
		
	#def modifyBit(self):
		#depends on rom, use #17 for Warlok
		#bus.write_byte_data(CARD_ENUM[3], gpio_register, 0x21)
		
	def apply(self):
		self.result = self.entryBits.get()
	
	def updateCard(self):
		self.entryCard.delete(0,END)
		self.entryCard.insert(0, self.radioCard.get())
	
	def apply(self):
		self.userCard = self.entryCard.get()
		if self.userCard:
			updateUserCard(self.userCard)

class StatusBar(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.label = Label(self, bd=1, relief=SUNKEN, anchor=W)
		self.label.grid(columnspan=6, sticky=NW)
	
	def __call__(self, format, *args):
		self.label.config(text=format % args)
		self.label.update_idletasks()
	
	def set(self, format, *args):
		self.label.config(text=format % args)
		self.label.update_idletasks()
		
	def clear(self):
		self.label.config(text="")
		self.label.update_idletasks()
#end class

####### MAIN PROGRAM #######
root = Tk()
root.title("WiLL-i-ROMS Controller - Hex Sequencer - " + VERSION)
controls = Controls(root)
#add menu
menu = Menu(root)
root.config(menu=menu)

filemenu = Menu(menu)
menu.add_cascade(label="File", menu=filemenu)
filemenu.add_command(label="New", command=newSeq)
filemenu.add_command(label="Load Block", command=loadBlock)
filemenu.add_command(label="Load Sequence", command=loadSeqFile)
filemenu.add_separator()
filemenu.add_command(label="Save Block", command=saveBlock)
filemenu.add_command(label="Save Sequence", command=saveSeqFile)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=callExit)

utilmenu = Menu(menu)
menu.add_cascade(label="Util", menu=utilmenu)
utilmenu.add_command(label="Test one pin", command=oneTest)
utilmenu.add_command(label="Test all pins", command=allTest)
utilmenu.add_separator()
utilmenu.add_command(label="Seq type select", command=seqTypeSelect)

infomenu = Menu(menu)
menu.add_cascade(label="Info", menu=infomenu)
infomenu.add_command(label="Help", command=helpDialog)
infomenu.add_command(label="About", command=aboutDialog)

#tracker view
header = Header(root)
header.grid(row=2, column=0, columnspan=6, sticky=W)
tracker = Tracker(root)
tracker.grid(row=3, column=0, columnspan=6, sticky=W)

#bitPlayer view
bitPlayer = BitPlayer(root)
bitPlayer.grid(row=4, column=0,columnspan=6, rowspan=2, sticky=W)

#statusbar
status = StatusBar(root)
status.grid(row=6, column=0, columnspan=6, sticky=NW)
status.set("%s", "ready")

root.mainloop()
