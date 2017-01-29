# WiLL-i-ROMS-Controller
# version 1.0
#
# raspPi -> mcp23008 -> CD4066B -> Soundboard
# using python -V 2.7.3
#
# NOTES:
# -must use 0x00 and 0x23 as note off or next note can fail to trigger
# -included 0x00 in playPin() prior to pinHex trigger
# -use None as a sustain in blocks, playPin() will skip it
# -midi listener is on separate thread
# -midi switchable to single card or all cards
# -new sequencer file format for multiple cards
# -tracker canvas enabled with playhead
#
# TODO
# - user write/edit/save file sequence
# - userBlock card switcher
# - CC messages - all CCs trig pin 1 every data send tick
# - rom12.716 organ trigger ?
# - pinX[1] as CC or volume pot per card via pwm
# - single,universal pwm addressed to MCP23008->CD4066->card
#
from Tkinter import *
import tkSimpleDialog
from tkFileDialog import askopenfilename
import tkFont
import smbus
import time
from rtmidi.midiutil import open_midiport
import threading

#GLOBALS
CARD_1_ADDR = 0x20
CARD_2_ADDR = 0x21

TEST_TIMER = 0.2
RUN_LOOP = False
MAIN_TIMER = 0.2
MIDI_LISTEN = False

CARD_LIST = ["CARD_ALL", "CARD_1", "CARD_2"]
SEQ_LIST = ["patt1Test", "blockPlay", "seqFilePlay"]
USER_SEQ = ""
USER_CARD = ""
BLOCK_LIST = []
SEQ_FILE_CONTENT = []


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
bus.write_byte_data(CARD_1_ADDR, iodir_register, 0x00)
bus.write_byte_data(CARD_2_ADDR, iodir_register, 0x00)
midiPort = 1 # set for MK-425C midi controller
	
	
###### CONTROL FUNCTIONS #####	
def stopAll():
	#zero
	bus.write_byte_data(CARD_1_ADDR, gpio_register, 0x00)
	bus.write_byte_data(CARD_2_ADDR, gpio_register, 0x00)
	#play pin 19 as a resetter, no sound
	bus.write_byte_data(CARD_1_ADDR, gpio_register, 0x23)
	bus.write_byte_data(CARD_2_ADDR, gpio_register, 0x23)
	status.set("%s", "stop all")
	
def kybdHalt():
	status.set("%s", "kybd halt")
	loopCheckControl(0)
	stopAll()

def playPin(pinHex):
	if pinHex is None:
		return
	else:
		#stop all first
		bus.write_byte_data(CARD_1_ADDR, gpio_register, 0x00)
		bus.write_byte_data(CARD_2_ADDR, gpio_register, 0x00)
		#then play pinHex
		bus.write_byte_data(CARD_1_ADDR, gpio_register, pinHex)
		bus.write_byte_data(CARD_2_ADDR, gpio_register, pinHex)
		#status.set("%s %d", "play pinHex: ", pinHex)
		
def playCardPin(cardHex, pinHex):
	if pinHex is None:
		return
	else:
		#stop all first
		bus.write_byte_data(cardHex, gpio_register, 0x00)
		#play pin
		bus.write_byte_data(cardHex, gpio_register, pinHex)
		#status.set("%s %d %d", "play card,pinHex: ", cardHex, pinHex)
		
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

############## FILE PLAY ################
def trackerSeqFileFormat(lineNum, line):
	carded = line.split("|")
	card1 = carded[0].split(",")
	card2 = carded[1].split(",")
	printLine = (str(lineNum) + "\t" + card1[0] + "\t" + card1[1] +
		"\t" + card2[0] + "\t" + card2[1])
	
	tracker.set(printLine)

def trackerSeqFile():
	global SEQ_FILE_CONTENT
	lineNum = 1
	tracker.clear()
	tracker.set("NUM\tCARD1\tCC\tCARD2\tCC")
	for line in SEQ_FILE_CONTENT:		
		trackerSeqFileFormat(lineNum, line)
		lineNum += 1
		
	tracker.scrollbarSet(lineNum)
	tracker.highlight(1)
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
	#have list of seq lines "11,0|1,0" etc
	global SEQ_FILE_CONTENT
	global CARD_1_ADDR
	global CARD_2_ADDR
	
	if not SEQ_FILE_CONTENT:
		status.set("%s", "seq file content empty")
		loopCheckControl(0)
		return
	else:	
		status.set("%s", "seq file play")
		lineCounter = 1
		for line in SEQ_FILE_CONTENT:
			carded = line.split("|")
			#print carded			
			pin1 = carded[0].split(",")
			pin1[0] = checkValidSeqPin(pin1[0])
			pin2 = carded[1].split(",")
			pin2[0] = checkValidSeqPin(pin2[0])
			#disregard pinX[1] as reserved for CC, not used yet			
			playCardPin(CARD_1_ADDR, pinsArray.get(pin1[0], None))
			playCardPin(CARD_2_ADDR, pinsArray.get(pin2[0], None))
			tracker.highlight(lineCounter)
			lineCounter += 1
			time.sleep(MAIN_TIMER)

		status.set("%s", "seq file end")

############## TEST BLOCKS ################
def oneTest():
	status.set("%s", "test pin")
	bus.write_byte_data(CARD_1_ADDR, gpio_register, 0x03)
	bus.write_byte_data(CARD_2_ADDR, gpio_register, 0x03)
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
def createBlock(result):
	status.set("%s %s", "create block: ", result)
	if not result:
		return
	else:	
		#make into list
		global BLOCK_LIST
		BLOCK_LIST = result.split(',')
		print BLOCK_LIST	
	
def blockPlay():
	# check if have a list or suffer
	global BLOCK_LIST
	global MAIN_TIMER
	if not BLOCK_LIST:
		status.set("%s", "block list empty")
		loopCheckControl(0)
		return
	else:	
		status.set("%s", "block list play")
		#checks and converts
		for entry in BLOCK_LIST:
			entry = checkValidSeqPin(entry)
			#play it
			playPin(pinsArray.get(entry, None))
			time.sleep(MAIN_TIMER)
#end func
	
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
	fileName = askopenfilename()
	with open(fileName) as file:
		fileContents = file.read()
		BLOCK_LIST = fileContents.split(',')
		#file.close()
	tracker.set(BLOCK_LIST)
	status.set("%s", "file read into block list")

def loadSeqFile():
	global SEQ_FILE_CONTENT
	fileName = askopenfilename()
	with open(fileName) as file:
		SEQ_FILE_CONTENT = file.readlines()
	
	#remove whitespace chars
	SEQ_FILE_CONTENT = [line.strip() for line in SEQ_FILE_CONTENT]
	status.set("%s", "seq file read")
	trackerSeqFile()	
		
def saveBlock():
	global BLOCK_LIST
	if not BLOCK_LIST:
		status.set("%s", "no block data to save")
		return
	else:
		file_ = open('BlockSave.txt', 'w')		
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
	status.set("%s", "new not implemented")

def callback():
	status.set("%s", "empty callback")
#end func
def callExit():
	status.set("%s", "exit not implemented")
#end func
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
		global USER_SEQ
		if not USER_SEQ:
			USER_SEQ = globals()["patt1Test"()]()
		
	def run(self):
		status.set("%s", "seq thread start")
		global USER_SEQ
		while RUN_LOOP:
			globals()[USER_SEQ]()
		
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
		
		# bit clunky
		global USER_CARD	
		pinAdjust = noteIn - 35
		if USER_CARD == "CARD_1":
			playCardPin(CARD_1_ADDR, pinsArray[pinAdjust])
		elif USER_CARD == "CARD_2":
			playCardPin(CARD_2_ADDR, pinsArray[pinAdjust])
		else:
			playPin(pinsArray[pinAdjust])
		
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
		Label(master, text="WiLL-i-ROMS Controller").grid(row=0,sticky=W)
		Label(master, text="Hex Sequencer version 1").grid(row=1,sticky=W)
		Label(master, text="(two board testing)").grid(row=2,sticky=W)
		Label(master, text="(tracker type testing)").grid(row=3,sticky=W)
		Label(master, text="---------------------").grid(row=4,sticky=W)
		Label(master, text="KaputnikGo, 2017").grid(row=5,sticky=W)
	
	
class CreateDialog(tkSimpleDialog.Dialog):	
	def body(self, master):
		Label(master, text="card 1:").grid(row=0, sticky=W)
		self.entry1 = Entry(master)
		
		global BLOCK_LIST
		if BLOCK_LIST:
			counter = 0
			entryString = ""
			for entry in BLOCK_LIST:
				if (counter < len(BLOCK_LIST) - 1):
					entryString += (entry + ",")
					counter += 1
				else:
					entryString += entry
				
			self.entry1.insert(END, entryString)
			
		self.entry1.grid(row=0, column=1)
		return self.entry1 #focus
		
	def apply(self):
		self.result = self.entry1.get()
#end class

class TimerDialog(tkSimpleDialog.Dialog):
	def body(self, master):
		Label(master, text="range:1.0 - 0.1").grid(row=0,sticky=W)
		self.entryTimer = Entry(master)
		
		global MAIN_TIMER
		self.entryTimer.insert(END, MAIN_TIMER)
		self.entryTimer.grid(row=0, column=1)
		return self.entryTimer #focus
		
	def apply(self):
		self.userTime = float(self.entryTimer.get())
		

class Controls:
	def __init__(self, master):
		frame = Frame(master)
		self.varLoop = IntVar()
		
		global seqName
		seqName = StringVar(master)
		seqName.set(SEQ_LIST[0])
		
		global cardName
		cardName = StringVar(master)
		cardName.set(CARD_LIST[0])
		
		quitButton = Button(
			frame, text="QUIT", fg="red", command=frame.quit)
		
		resetButton = Button(
			frame, text="Reset", command=self.goReset)
		
		self.midiButton = Button(
			frame, text="midi OFF", command=self.goMidi)
		
		createButton = Button(
			frame, text="Create", command=self.goCreate)
		
		self.loopCheck = Checkbutton(
			frame, text="loop", variable=self.varLoop,
			command=self.goLoop)			
		frame.bind("<Button-1>", self.goLoop)
		
		playSeqButton = Button(
			frame, text="Play", command=self.goPlaySeq)
		
		timerButton = Button(
			frame, text="Timer", command=self.goTimer)
		
		cardOptions = apply(OptionMenu, (master, cardName) + tuple(CARD_LIST))
		
		seqOptions = apply(OptionMenu, (master, seqName) + tuple(SEQ_LIST))

		print "load interface"
		frame.grid(column=0,row=0)#, columnspan=4, rowspan=4)
		quitButton.grid(row=0, column=0, padx=5, sticky=W)
		resetButton.grid(row=0, column=1, padx=3)
		createButton.grid(row=0, column=2, padx=3)
		self.midiButton.grid(row=0, column=3, padx=3)
		cardOptions.grid(row=0, column=4, padx=1, sticky=NW)
		seqOptions.grid(row=0, column=5, padx=3, sticky=N)
		
		self.loopCheck.grid(row=1, column=0, sticky=W)
		playSeqButton.grid(row=1, column=1)
		timerButton.grid(row=1, column=2)		
			
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
		global USER_CARD	
		tog[0] = not tog[0]
		if tog[0]:
			self.midiButton.config(text='midi ON_')
			MIDI_LISTEN = True
			USER_CARD = cardName.get()
			self.mt = MidiThread()
			self.mt.start()
			self.checkThreadMT()
		else:
			self.midiButton.config(text='midi OFF')
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
			root.after(500, self.checkThreadSQ)
		else:
			print "end SQ thread"
			return
	#end func	
	def goPlaySeq(self):
		print "play seqName:"
		print seqName.get()
		global USER_SEQ
		USER_SEQ = seqName.get()
		self.sq = SeqThread()
		self.sq.start()
		self.checkThreadSQ()
	#end func
	
	def goTimer(self):
		timerDialog = TimerDialog(root)
		updateTimer(timerDialog.userTime)
		
			
#end class	

class Tracker(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.seqLength = 0
		self.canvas = Canvas(self, width=500, height=300,
			bg="black", scrollregion=(0, 0, 0, 400))
			
		#left,top,right,bottom
		self.highlighter = self.canvas.create_rectangle(0,5,500,19, 
			fill="#5c5c5c")
			
		self.yscrollbar = Scrollbar(self, orient=VERTICAL)
		self.yscrollbar.grid(row=0, column=6, sticky=N+S)
		self.canvas.config(yscrollcommand=self.yscrollbar.set)
		self.yscrollbar.config(command=self.canvas.yview)
		
		self.canvas.grid(row=0, column=0, columnspan=6, sticky=NW)	

		self.vFont = tkFont.Font(family="Verdana",size=12,weight="normal")		
		self.canvasTextID = self.canvas.create_text(5, 5, anchor="nw", 
			font=self.vFont, fill="green")			
		self.fontHeight = self.vFont.metrics("linespace")
		
		self.canvas.itemconfig(self.canvasTextID, text="noob tracker")
	
	def __call__(self, format, *args):
		#self.label.config(text=format % args)
		self.canvas.update_idletasks()
		
	def set(self, message):
		self.canvas.insert(self.canvasTextID, INSERT, message)
		self.canvas.insert(self.canvasTextID, INSERT, "\n")
		self.canvas.update_idletasks()
		
	def scrollbarSet(self, lineNum):
		#account for zero not counted
		self.seqLength = lineNum + 1
		self.canvas.config(scrollregion=self.canvas.bbox(ALL))
		bounds = self.canvas.bbox(ALL)
		self.seqHeight = bounds[3] - bounds[1]		
		self.moveFraction = float(1 / float(self.seqHeight / self.fontHeight))
		
	def clear(self):
		self.canvas.dchars(self.canvasTextID, 0, END)
		self.canvas.update_idletasks()
		
	def highlight(self, lineNum):
		# account for font y offset from top
		startY = (lineNum * self.fontHeight) + 5
		endY = startY + self.fontHeight
		self.canvas.coords(self.highlighter, 0, startY, 500, endY)
		# move scrollbar
		self.canvas.yview_moveto(lineNum * self.moveFraction)
		
#end class

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
root.title("WiLL-i-ROMS Controller - Hex Sequencer")
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

infomenu = Menu(menu)
menu.add_cascade(label="Info", menu=infomenu)
infomenu.add_command(label="Help", command=helpDialog)
infomenu.add_command(label="About", command=aboutDialog)

#tracker view
tracker = Tracker(root)
tracker.grid(row=2, column=0, columnspan=6)

#statusbar
status = StatusBar(root)
status.grid(row=3, column=0, columnspan=6, sticky=NW)
status.set("%s", "ready")

root.mainloop()
root.destroy()
