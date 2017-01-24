# Will-i-ROMS-Controller
# version 1.0
#
# raspPi -> mcp23008 -> CD4066B -> Soundboard
# Tkinter gui
from Tkinter import *
import smbus
import time
# MIDI input
# https://spotlightkid.github.io/python-rtmidi/
from rtmidi.midiutil import open_midiport

#vars
bus = smbus.SMBus(1)
address = 0x20
iodir_register = 0x00
gpio_register = 0x09
TIMER_SLEEP = 0.2
midiPort = 1 # set for MK-425C midi controller
MIDI_LISTEN = False
#dictionary for multi pins
pinsArray = {
	0:0x00, 1:0x01, 2:0x02, 3:0x03, 4:0x04, 5:0x05,
	6:0x06, 7:0x07, 8:0x08, 9:0x09, 10:0x0A, 
	11:0x0B, 12:0x0C, 13:0x0D, 14:0x0E, 15:0x0F,
	16:0x20, 17:0x21, 18:0x22, 19:0x23, 20:0x24,
	21:0x25, 22:0x26, 23:0x27, 24:0x28, 25:0x29,
	26:0x2A, 27:0x2B, 28:0x2C, 29:0x2D, 30:0x2E,
	31:0x2F
	}
#INIT
#enable as output
bus.write_byte_data(address, iodir_register, 0x00)
	
	
###### CONTROL FUNCTIONS #####	
def stopAll():
	bus.write_byte_data(address, gpio_register, 0x00)

def playPin(pinHex):
	bus.write_byte_data(address, gpio_register, pinHex)
	status.set("%s %d", "play pin: ", pinHex)

def oneTest():
	status.set("%s", "test pin")
	#playPin(0x03)
	bus.write_byte_data(address, gpio_register, 0x03)
	time.sleep(TIMER_SLEEP)
	stopAll()


def seqRun():
	#run through all 15
	status.set("%s", "seq start")
	for key in pinsArray:
		playPin(pinsArray[key])
		time.sleep(TIMER_SLEEP)
		# need to stop all after each trigger
		stopAll()
	status.set("%s", "seq end")

def callback():
	print "function callback!"
#end func

def callExit():
	print "Exit called"
#end func

########### MIDI INPUT ###########

# needs to be on separate thread, is consuming GUI

def midiToPins(noteIn):
	# c=36, c#=37, etc
	# subtract 35 to get pinsArray[key]
	# assume has a note on velocity here
	# todo account for octave, etc
	
	# boundary check, for now
	if (noteIn <= 35):
		noteIn = 36
	elif (noteIn >= 68):
		noteIn = 67
		
	pinAdjust = noteIn - 35
	playPin(pinsArray[pinAdjust])
	

def midiToPinsOff():
	#serves as note off/vel=0
	stopAll()
	
def midiListen(message):
	# from list [0,1,2]
	# [1] = note number :: map to pins
	# [2] = vel (0-127)
	if (message[2] >= 1):
		midiToPins(message[1])
	else:
		midiToPinsOff()

def midiError():
	status.set("%s %d", "Midi error for port: ", midiPort)
		
def midiTest():
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
		print('')
	finally:
		print('Stop midi listener')
		midiin.close_port()
		del midiin	



###### INTERFACE #######
# http://effbot.org/tkinterbook/

class Controls:
	def __init__(self, master):
		frame = Frame(master)
		frame.pack()
		
		quitButton = Button(
			frame, text="QUIT", fg="red", command=frame.quit
			)
		quitButton.pack(side=LEFT, padx=5, pady=3)
		
		testButton = Button(
			frame, text="Test", command=self.goTest
			)
		testButton.pack(side=LEFT, padx=5, pady=3)
		
		seqButton = Button(
			frame, text="Seq", command=self.goSeqRun
			)
		seqButton.pack(side=LEFT, padx=5, pady=3)
		
		resetButton = Button(
			frame, text="Reset", command=self.goReset
			)
		resetButton.pack(side=LEFT, padx=5, pady=3)
		
		self.midiButton = Button(
			frame, text="midi", command=self.goMidi
			)
		self.midiButton.pack(side=LEFT, padx=2, pady=3)
		
	#control functions
	
	def goTest(self):
		print "test"
		oneTest()
	#end func
	
	def goSeqRun(self):
		print "seq"
		seqRun()
	#end func
	
	def goReset(self):
		print "reset"
		stopAll()
	#end func
	
	def goMidi(self, tog=[0]):
		global MIDI_LISTEN	
		tog[0] = not tog[0]
		if tog[0]:
			self.midiButton.config(text='midi ON')
			MIDI_LISTEN = True
			midiTest()
		else:
			self.midiButton.config(text='midi OFF')
			MIDI_LISTEN = False
		

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
root.title("WiLL-i-ROMS Sound Controller");
controls = Controls(root)
#add menu
menu = Menu(root)
root.config(menu=menu)
filemenu = Menu(menu)
menu.add_cascade(label="File", menu=filemenu)
filemenu.add_command(label="New", command=callback)
filemenu.add_command(label="Open", command=callback)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=callExit)
helpmenu = Menu(menu)
menu.add_cascade(label="Help", menu=helpmenu)
helpmenu.add_command(label="About", command=callback)

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
stopAll()
