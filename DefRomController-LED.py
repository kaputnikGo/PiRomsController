# Tkinter gui
from Tkinter import *
# LED test from GPIO pins
import time
import RPi.GPIO as GPIO

# set vars
addr0Pin = 3
addr1Pin = 5
addr2Pin = 12
timer = 0.2
seqTimer = 0.5
pOn = GPIO.HIGH
pOff = GPIO.LOW
pCount = 10

# init
# set numbering system as on pi board, not internal
GPIO.setmode(GPIO.BOARD)
# suppress warnings
GPIO.setwarnings(False)
# set pin mode, root
GPIO.setup(addr0Pin, GPIO.OUT)
GPIO.setup(addr1Pin, GPIO.OUT)
GPIO.setup(addr2Pin, GPIO.OUT)
		
# declare functions (first?)
def gpioReset():
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOff)
# end func

def gp0():
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOff)	
	status.set("%s", "gp0")
def gp1():
	GPIO.output(addr0Pin, pOn)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOff)
	status.set("%s", "gp1")
def gp2():
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOn)
	GPIO.output(addr2Pin, pOff)
	status.set("%s", "gp2")
def gp3():
	GPIO.output(addr0Pin, pOn)
	GPIO.output(addr1Pin, pOn)
	GPIO.output(addr2Pin, pOff)
	status.set("%s", "gp3")
def gp4():
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOn)
	status.set("%s", "gp4")
def gp5():
	GPIO.output(addr0Pin, pOn)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOn)
	status.set("%s", "gp5")
def gp6():
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOn)
	GPIO.output(addr2Pin, pOn)
	status.set("%s", "gp6")
def gp7():
	GPIO.output(addr0Pin, pOn)
	GPIO.output(addr1Pin, pOn)
	GPIO.output(addr2Pin, pOn)
	status.set("%s", "gp7")
		
# we only need five gpOuts
def seqLED():
	gp0()
	time.sleep(seqTimer)
	gp1()
	time.sleep(seqTimer)
	gp2()
	time.sleep(seqTimer)
	gp3()
	time.sleep(seqTimer)
	gp4()
	time.sleep(seqTimer)
	gp5()
	time.sleep(seqTimer)
	gp6()
	time.sleep(seqTimer)
	gp7()
	time.sleep(seqTimer)
#end func

def blinkyLED():
	# set output high(3.3v) or low(0v)
	GPIO.output(addr0Pin, pOff)
	GPIO.output(addr1Pin, pOn)
	GPIO.output(addr2Pin, pOn)
	# wait
	time.sleep(timer)
	GPIO.output(addr0Pin, pOn)
	GPIO.output(addr1Pin, pOff)
	GPIO.output(addr2Pin, pOff)
	#wait
	time.sleep(timer)
# end func

def blinkTest():    
	gpioReset()
	# loop it, weird syntax...
	for i in range (pCount):
		blinkyLED()
		status.set("%s %d", "flash: ", i)
	# end loop
	gpioReset()
# end func

def seqRun():
	status.set("%s", "seq start")
	gpioReset()
	seqLED()
	gpioReset()
	

def callback():
	print "function callback!"
#end func

def callExit():
	print "Exit called"
#end func

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
		
		flashButton = Button(
			frame, text="Test", command=self.goTest
			)
		flashButton.pack(side=LEFT, padx=5, pady=3)
		
		seqButton = Button(
			frame, text="SeqRun", command=self.goSeqRun
			)
		seqButton.pack(side=LEFT, padx=5, pady=3)
		
		resetButton = Button(
			frame, text="Reset", command=self.goReset
			)
		resetButton.pack(side=LEFT, padx=5, pady=3)
		
		#direct gp buttons
		gp1Button = Button(
			frame, text="gp1", command=self.goGp1
			)
		gp1Button.pack(side=LEFT, padx=2, pady=3)
		
		gp2Button = Button(
			frame, text="gp2", command=self.goGp2
			)
		gp2Button.pack(side=LEFT, padx=2, pady=3)
		
		gp3Button = Button(
			frame, text="gp3", command=self.goGp3
			)
		gp3Button.pack(side=LEFT, padx=2, pady=3)
		
		gp4Button = Button(
			frame, text="gp4", command=self.goGp4
			)
		gp4Button.pack(side=LEFT, padx=2, pady=3)
		
		gp5Button = Button(
			frame, text="gp5", command=self.goGp5
			)
		gp5Button.pack(side=LEFT, padx=2, pady=3)
	
	def goTest(self):
		print "flash test LEDs...!"
		blinkTest()
	#end func
	
	def goSeqRun(self):
		print "seq run LEDs...!"
		seqRun()
	#end func
	
	def goReset(self):
		print "reset LEDs."
		gpioReset()
	#end func
	
	def goGp1(self):
		gp1()
		
	def goGp2(self):
		gp2()
		
	def goGp3(self):
		gp3()
	
	def goGp4(self):
		gp4()
		
	def goGp5(self):
		gp5()
		
#end class

class StatusBar(Frame):
	def __init__(self, master):
		Frame.__init__(self, master)
		self.label = Label(self, bd=1, relief=SUNKEN, anchor=W)
		self.label.pack(fill=X)
		
	def set(self, format, *args):
		self.label.config(text=format % args)
		self.label.update_idletasks()
		
	def clear(self):
		self.label.config(text="")
		self.label.update_idletasks()
#end class


####### MAIN PROGRAM #######

root = Tk()
root.title("Def Roms Sound Controller");
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
# release GPIO
GPIO.cleanup
