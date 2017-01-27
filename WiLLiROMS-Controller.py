# WiLL-i-ROMS-Controller
# version 1.0
#
# raspPi -> mcp23008 -> CD4066B -> Soundboard
# using python -V 2.7.3
#
# NOTES:
# -must use 0x00 as note off or next note can fail to trigger
# -included 0x00 in playPin() prior to pinHex trigger
# -use None as a sustain in blocks, playPin() will skip it
# -midi listener is on separate thread
# TODO
# - need file append, file view and choose, use a saves folder
# - timer/bpm slider or control
# - open Block shows current blockUserList (if exists)
#
from Tkinter import *
import tkSimpleDialog
import smbus
import time
# MIDI input
# https://spotlightkid.github.io/python-rtmidi/
from rtmidi.midiutil import open_midiport

import threading

#vars
bus = smbus.SMBus(1)
address = 0x20
iodir_register = 0x00
gpio_register = 0x09
TIMER_SLEEP = 0.2
RUN_LOOP = False
# list below is for blocks with stopAll() calls
# 0.15 is very fast, 
# 0.175 is good fast
# 0.2 is fast funky
# 0.3 is funky 
# 0.4 is slow reggae
BLOCK_TIMER = 0.2
TRIAL_TIMER = 0.1

midiPort = 1 # set for MK-425C midi controller
MIDI_LISTEN = False

SEQ_LIST = ["patt1Test", "userBlockPlay"]
USER_SEQ = ""

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
#test triggers for patt1Test()
#8 notes per block	
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
	
#test block used from Trial button
# keyword None as sustain/skip entry
blockTrial = {
	0:0x01, 1:0x00, 2:0x03, 3:0x00,
	4:0x04, 5:None , 6:None , 7:None,
	8:0x08, 9:0x00, 10:0x0B, 11:None,
	12:None, 13:None, 14:0x08, 15:0x00
	}
blockTrial2 = {
	0:0x0E, 1:0x02, 2:0x0E, 3:0x02,
	4:0x20, 5:None, 6:0x02, 7:None,
	}

blockUserList = []

########### INIT ###########
#enable as output
bus.write_byte_data(address, iodir_register, 0x00)

	
	
###### CONTROL FUNCTIONS #####	
def stopAll():
	bus.write_byte_data(address, gpio_register, 0x00)
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
		bus.write_byte_data(address, gpio_register, 0x00)
		#then play pinHex
		bus.write_byte_data(address, gpio_register, pinHex)
		#status.set("%s %d", "play pinHex: ", pinHex)


############## TEST BLOCKS ################
def oneTest():
	status.set("%s", "test pin")
	bus.write_byte_data(address, gpio_register, 0x03)
	time.sleep(TIMER_SLEEP)
	stopAll()


def allTest():
	#run through all 31
	status.set("%s", "test all start")
	for key in pinsArray:
		playPin(pinsArray[key])
		time.sleep(TIMER_SLEEP)
	stopAll()
	
def block1():
	for key in block1Array:
		playPin(block1Array[key])
		time.sleep(BLOCK_TIMER)
#end block1

def block2():
	for key in block2Array:
		playPin(block2Array[key])
		time.sleep(BLOCK_TIMER)	
#end block2

def block3():
	for key in block3Array:
		playPin(block3Array[key])
		time.sleep(BLOCK_TIMER)	
#end block3

############ USER BLOCK ###############
def userBlock(result):
	status.set("%s %s", "user block: ", result)
	#make into list
	global blockUserList
	blockUserList = result.split(',')
	print blockUserList	
	
def userBlockPlay():
	# check if have a userBlock or suffer
	global blockUserList
	if not blockUserList:
		status.set("%s", "user block empty")
		loopCheckControl(0)
		return
	else:	
		status.set("%s", "user block play")
		#checks and converts
		for entry in blockUserList:
			if entry == "n":
				entry = None
			elif entry == "":
				entry = None
			else:
				entry = int(entry)
			#play it
			playPin(pinsArray.get(entry, None))
			time.sleep(TRIAL_TIMER)
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

########### FILE HELP MENU ###########
# TODO
def newSeq():
	status.set("%s", "new not implemented")
	
def loadSeq():
	global blockUserList
	with open('BlockSave.txt') as file:
		fileContents = file.read()
		blockUserList = fileContents.split(',')
		#file.close()
	print blockUserList
	status.set("%s", "file read into user block")
		
def saveSeq():
	global blockUserList
	if not blockUserList:
		status.set("%s", "no block data to save")
		return
	else:
		file_ = open('BlockSave.txt', 'w')		
		counter = 0			
		for entry in blockUserList:
			#catch last line here
			if (counter < len(blockUserList) - 1):
				file_.write("%s" % entry + ",")
				counter += 1
			else:
				file_.write("%s" % entry)
				
		file_.close()
		status.set("%s", "user block saved to file")

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
		# todo account for octave, etc
		
		# boundary check, for now
		if (noteIn <= 35):
			noteIn = 36
		elif (noteIn >= 67):
			noteIn = 66
			
		pinAdjust = noteIn - 35
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
		
		status.set("%s", "Start midi listener")	
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
# http://effbot.org/tkinterbook/
class AboutDialog(tkSimpleDialog.Dialog):
	def body(self, master):
		Label(master, text="WiLL-i-ROMS Controller").grid(row=0,sticky=W)
		Label(master, text="Hex Sequencer version 1").grid(row=1,sticky=W)
		Label(master, text="(single board testing)").grid(row=2,sticky=W)
		Label(master, text="---------------------").grid(row=3,sticky=W)
		Label(master, text="KaputnikGo, 2017").grid(row=4,sticky=W)
	
	
class BlockDialog(tkSimpleDialog.Dialog):	
	def body(self, master):
		Label(master, text="int or n(none):").grid(row=0, sticky=W)
		self.entry1 = Entry(master)
		self.entry1.grid(row=0, column=1)
		return self.entry1 #focus
		
	def apply(self):
		self.result = self.entry1.get()
#end class

class Controls:
	def __init__(self, master):
		frame = Frame(master)
		frame.pack()
		self.varLoop = IntVar()
		
		global seqName
		seqName = StringVar(master)
		seqName.set(SEQ_LIST[0])
		
		quitButton = Button(
			frame, text="QUIT", fg="red", command=frame.quit
			)
		quitButton.pack(side=LEFT, padx=5, pady=3)
		
		testButton = Button(
			frame, text="Test", command=self.goTest
			)
		testButton.pack(side=LEFT, padx=5, pady=3)
		
		testAllButton = Button(
			frame, text="Test All", command=self.goTestAll
			)
		testAllButton.pack(side=LEFT, padx=5, pady=3)
		
		resetButton = Button(
			frame, text="Reset", command=self.goReset
			)
		resetButton.pack(side=LEFT, padx=5, pady=3)
		
		self.midiButton = Button(
			frame, text="midi OFF", command=self.goMidi
			)
		self.midiButton.pack(side=LEFT, padx=2, pady=3)
		
		blockButton = Button(
			frame, text="Block", command=self.goBlock
			)
		blockButton.pack(side=LEFT, padx=5, pady=3)
		
		self.loopCheck = Checkbutton(
			frame, text="loop", variable=self.varLoop,
			command=self.goLoop
			)
			
		self.loopCheck.pack(side=LEFT, padx=2, pady=3)
		frame.bind("<Button-1>", self.goLoop)
		
		playSeqButton = Button(
			frame, text="Play", command=self.goPlaySeq
			)
		playSeqButton.pack(side=LEFT, padx=5, pady=3)
		
		seqOptions = apply(OptionMenu, (master, seqName) + tuple(SEQ_LIST))
		seqOptions.pack()
		
	#control functions
	
	def goTest(self):
		print "test"
		oneTest()
	#end func
	
	def goTestAll(self):
		print "test all"
		allTest()
	#end func
	
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
		tog[0] = not tog[0]
		if tog[0]:
			self.midiButton.config(text='midi ON_')
			MIDI_LISTEN = True
			self.mt = MidiThread()
			self.mt.start()
			self.checkThreadMT()
		else:
			self.midiButton.config(text='midi OFF')
			MIDI_LISTEN = False
	#end func
	
	def goBlock(self):
		#dialog box for user input of int keys and Nones
		blockDialog = BlockDialog(root)
		userBlock(blockDialog.result)
	
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
			
#end class		

class StatusBar(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.label = Label(self, bd=1, relief=SUNKEN, anchor=W)
		self.label.pack(fill=X)
	
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
filemenu.add_command(label="Load", command=loadSeq)
filemenu.add_separator()
filemenu.add_command(label="Save", command=saveSeq)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=callExit)
infomenu = Menu(menu)
menu.add_cascade(label="Info", menu=infomenu)
infomenu.add_command(label="Help", command=helpDialog)
infomenu.add_command(label="About", command=aboutDialog)

photo = PhotoImage(file="Williams-SndBrd.gif")
label = Label(root, image=photo)
label.image = photo #store it
label.pack()

#statusbar
status = StatusBar(root)
status.pack(side=BOTTOM, fill=X)
status.set("%s", "ready")

root.mainloop()
root.destroy()
