from machine import Pin, enable_irq, disable_irq, ADC, UART, RTC
import time
import ure
import BlynkLib
import untplib
# import gc

# reading temperature with DHT11 and sending the data to a (local) blynk server
# using a SIM800 GSM board to send a warning when temperature drops below zero degrees
# or when a button gets pushed on the blynk

# blynk by blynk (http://www.blynk.cc)
# blynklib by danicampora ( https://github.com/wipy/wipy/blob/master/lib/blynk/BlynkLib.py )
# untplib by andrewmk ( https://github.com/andrewmk/untplib )
# DHT decoder by RinusW (http://forum.micropython.org/viewtopic.php?t=1392)
# (inexpensive) SIM800L GPRS GSM Module SIM Board QUAD BAND Antenna for MCU Arduino (and wipy, ...)
# mashup by me andre@andrehtemac.be
# todo sim800 communication needs more work
# 2016/03/12 : version 0.1

# some defaults
# my blynk key
BLYNK_AUTH = '6beed7fd945e4277b23eb33d5fa1dd85'
BLYNK_SERVER = '192.168.128.35'

# where to send the sms to
DESTINATIONPHONENUMBER = '+32499135393'

# pins to uart on sim800 board
TX_PIN = 'GP16'
RX_PIN = 'GP17'

# pin to battery sensor on expansion board
# see http://forum.micropython.org/viewtopic.php?f=11&t=1343 for more info
BAT_PIN = 'GP3'

# pin to connect the dht11 (of dht22) to
DHT_PIN = 'GP4'

# where to finde the time
NTPPOOLSERVER = '0.be.pool.ntp.org'


def decode(inp):
    """
    convert the data from the sensor to 4 values
    :param inp: the bits read from the sensor
    :return: 4 values containing the temp and humidity
    """
    res = [0] * 5
    bits = []
    ix = 0
    try:
        if inp[0] == 1: ix = inp.index(0, ix)  # skip to first 0
        ix = inp.index(1, ix)  # skip first 0's to next 1
        ix = inp.index(0, ix)  # skip first 1's to next 0
        while len(bits) < len(res) * 8:  # need 5 * 8 bits :
            ix = inp.index(1, ix)  # index of next 1
            ie = inp.index(0, ix)  # nr of 1's = ie-ix
            bits.append(ie - ix)
            ix = ie
    except:
        return ([0xff, 0xff, 0xff, 0xff])
    for i in range(len(res)):
        for v in bits[i * 8: (i + 1) * 8]:  # process next 8 bit
            res[i] <<= 1  # shift byte one place to left
            if v > 2:
                res[i] += 1  # and add 1 if lsb is 1
    if (res[0] + res[1] + res[2] + res[3]) & 0xff != res[4]:  # parity error!
        print("Checksum Error")
        res = [0xff, 0xff, 0xff, 0xff]
    return (res[0:4])


def getval(pin):
    """readout a dht11/22 sensor"""
    ms = [1] * 300
    pin(0)
    time.sleep_us(20000)
    pin(1)
    irqf = disable_irq()
    for i in range(len(ms)):
        ms[i] = pin()  # sample input and store value
    enable_irq(irqf)
    return ms


def DHT11(pin):
    """
    decode the data from the sensor if sensor is DHT11
    :param pin: the where the sensor is attached
    :return: tuple with temp and humidity or false on error
    """
    res = decode(getval(pin))
    # return ('{},{}'.format(res[2], res[3])), ('{},{}'.format(res[0], res[1]))
    if res == [0xff, 0xff, 0xff, 0xff]:
        return False
    return ('{}'.format(res[2])), ('{}'.format(res[0]))


def DHT22(pin):
    """
    decode the data from the sensor if sensor is DHT22
    :param pin: the where the sensor is attached
    :return: tuple with temp and humidity or false on error
    """
    res = decode(getval(pin))
    hum = res[0] * 256 + res[1]
    tem = res[2] * 256 + res[3]
    if (tem > 0x7fff):
        # tem = 0x8000 - tem
        return False
    return ('{}.{}'.format(tem // 10, tem % 10)), ('{}.{}'.format(hum // 10, hum % 10))


def getDate():
    """format date"""
    return '{:04}/{:02}/{:02}'.format(rtclock.now()[0], rtclock.now()[1], rtclock.now()[2])


def getTime():
    """format time"""
    return '{:02}:{:02}:{:02}'.format(rtclock.now()[3], rtclock.now()[4], rtclock.now()[5])


def getDateTime():
    """format date time"""
    return '{} {}'.format(getDate(), getTime())


def uartok(uret):
    """
    analyse the return data from the sim800, using regex
    :param uret: the data
    :return: true on OK, false on ERROR
    """
    print(uret)
    if re.search(uret):
        return True
    else:
        if er.search(uret):
            return False
        else:
            uartok(uart.readall())


def sendsms(msg):
    """
    send an sms
    :param msg: the message to send
    :return: true on succes, false on error
    """
    print(uart.readall())
    uart.write('AT+CMGF=1\r\n')
    time.sleep(1)
    if uartok(uart.readall()):
        CMGS = 'AT+CMGS="{}"\r'.format(DESTINATIONPHONENUMBER)
        uart.write(CMGS)
        time.sleep(1)
        uart.write(msg)
        uart.write(chr(26))
        time.sleep(5)
        if uartok(uart.readall()):
            print("sms send")
            return True
        else:
            print("ERROR sending sms")
            return False
    else:
        return False


def sendData():
    """ send the data to the blynk server and (if needed send a sms) """
    print(getDateTime())
    zerodegrees = 0
    r = DHT11(dat)
    global freezing
    if r is not False:
        if int(r[0]) < zerodegrees and freezing is False:
            print('send sms freezing')
            msg = "it is freezing " + str(r[0]) + "C at " + getTime()
            freezing = sendsms(msg)
        if int(r[0]) > zerodegrees and freezing is True:
            print('send sms thawing')
            msg = "it has ended freezing " + str(r[0]) + "C at " + getTime()
            freezing = not(sendsms(msg))

        # virtual pin 0 = temp
        blynk.virtual_write(0, r[0])
        # virtual pin 1 = humidity
        blynk.virtual_write(1, r[1])
        # virtual pin 2 = battery value (raw)
        blynk.virtual_write(2, str(bat()))
        # virtual pin 3 = high when freezing
        if int(r[0]) <= 0:
            blynk.virtual_write(3, 255)
        else:
            blynk.virtual_write(3, 0)


def BLYNK_CONNECTED():
    if(isFirstConnect):
        blynk.syncAll()


def v4_write_handler(value):
    """ send the sms with the temp on push"""
    # virtual Pin 4 is the button
    print("button pushed '{}'".format(value))
    r = DHT11(dat)
    if r is not False and int(value) == 1:
        print('send sms on request')
        msg = "at " + getDateTime() + " it is " + str(r[0]) + "C"
        sendsms(msg)


def clock_adjust():
    """adjust the clock with the ntp data """
    resp = c.request(NTPPOOLSERVER, version=3, port=123)
    print("Offset is ", resp.offset)
    print("Adjusting clock by ", resp.offset, "seconds")
    rtclock.init(time.localtime(time.time() + resp.offset))


# init pin for dht11
dat = Pin(DHT_PIN, Pin.OPEN_DRAIN)
dat(1)

# freezing -> did we already send the sms ? don't send it twice
freezing = False

# set the clock
c = untplib.NTPClient()
rtclock = RTC()
clock_adjust()

# set the regex for the uart answers
re = ure.compile("\r\nOK\r\n")
er = ure.compile("\r\nERROR\r\n")

# config the uart and see if somethings answers
uart = UART(1, baudrate=115200, pins=(TX_PIN, RX_PIN))  # uart #, baudrate, pins tx,rx
uart.write('+++')
uart.write('AT+COPS?\r\n')
time.sleep(1)
while uart.any() != 0:
    print(uart.readall())

# get the battery
adc = ADC()
bat = adc.channel(pin=BAT_PIN)

# initialize Blynk
blynk = BlynkLib.Blynk(BLYNK_AUTH, server=BLYNK_SERVER)

# register virtual pin 4 (the button on the blynk that sends the temp sms right away)
blynk.add_virtual_pin(4, write=v4_write_handler)

# register my task
blynk.set_user_task(sendData, 60000)

# start Blynk (this call should never return)
blynk.run()
