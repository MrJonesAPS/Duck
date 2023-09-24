import adafruit_thermal_printer
import serial
import os
from escpos.printer import Serial
import socketio
from datetime import date, datetime, timedelta

#Get the system IP address.
#this doesn't matter for this program, 
# but it's convenient because I have this setup headless
SERVER_IP_ADDRESS = os.environ.get("IP", None).strip()

#Initialize Socket
sio = socketio.Client()

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=0)
    printer = ThermalPrinter(uart, 
                            auto_warm_up=False, 
                            dot_print_s = 0.01, 
                            byte_delay_s = 0)
    printer.warm_up()
    printer.print("Here is my IP address:")
    printer.print(SERVER_IP_ADDRESS)
    printer.feed(2)
    return printer

def initializePrinter_escpos():
    p = Serial(devfile='/dev/serial0',
           baudrate=19200,
           bytesize=8,
           parity='N',
           stopbits=1,
           timeout=0.01,
           dsrdtr=True)
    return p
'''
#Commenting out checkPaper()
#might be nice to eventually 
#send this info back over the socket
def checkPaper():
    try:
        if printer.has_paper():
            pass
        else:
            flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")
    except:
        flash("Unable to check paper status","error")
'''

'''
def PrintWPPass(name, date):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("__(.)<   WARRIOR")
    printer.print("\___)    PASS")
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.feed(3)
    printer.print(name)
    printer.print("is invited")
    printer.print("to room C116")
    printer.print("on")
    printer.print(custom_strftime('%a, %B {S}', date))
    printer.feed(3)
    printer.print("Questions?") 
    printer.print("See Mr. Jones")
    printer.print("in room C116")
    printer.feed(2)


def PrintInvitation(name, date, period, reason):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("__(.)<INVITATION")
    printer.print("\___)")
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.feed(2)
    printer.print(name)
    printer.print("you are invited")
    printer.print("to room C116")
    printer.print("during " + period)
    printer.print("on")
    printer.print(custom_strftime('%a, %B {S}', date))
    printer.print("reason:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.print(reason)
    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.feed(2)
    printer.print("Questions?") 
    printer.print("See Mr. Jones")
    printer.print("in room C116")
    printer.feed(2)
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("****")
    printer.print("This invitation only signifies")
    printer.print("that you are welcome to be in")
    printer.print("C116 during this period.")
    printer.print("Your teacher must give")
    printer.print("permission to leave their")
    printer.print("classroom.")
    printer.feed(2)
'''


###
#Initialize Printer
###
printer = initializePrinter()
printer_escpos = initializePrinter_escpos()


@sio.event
def connect():
    printer.print("I'm connected!")
    printer.feed(2)
    #sio.emit('login', {'userKey': 'streaming_api_key'})

@sio.event
def connect_error():
    printer.print("The connection failed!")
    printer.feed(2)

@sio.event
def message(data):
    printer.print('I received a message!')
    printer.feed(2)

@sio.on('Pass')
def PrintHallPass(data):
    print("Received a hall pass. Will print now.")
    print(data)
    name = data.get("name")
    destination = data.get("destination")
    passID = data.get("passID")
    nowTime = datetime.now().strftime("%I:%M %p")
    nowDate = date.today().strftime("%B %d, %Y")
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("__(.)<   THIS IS A   <(.)__")
    printer.print("\___)    HALL PASS    (___/")
    printer.feed(1)
    printer.print(name)
    printer.print("is going to " + destination)
    printer.print("at " + nowTime)
    printer.print("on " + nowDate)
    printer.feed(1)
    printer.print("Questions? See Mr. Jones")
    printer.print("in room C116")
    printer.feed(1)
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.print("(scan to validate)")
    printer_escpos.qr("https://www.duck.whscs.net/view_pass/" + str(passID),native=False ,size=8)
    printer_escpos.text("\n\n\n")



sio.connect('https://www.duck.whscs.net')
sio.wait()