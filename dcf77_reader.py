#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
    Copyright © 2016 Daniel Müllner <http://danifold.net>
    All changes from 2017-12-27 on: Copyright © Google Inc. <http://google.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
'''
import atexit
import sys
if sys.hexversion < 0x03000000:
    from ConfigParser import RawConfigParser
else:
    from configparser import RawConfigParser
from datetime import datetime, timedelta, tzinfo
from timeit import default_timer as timer
import RPi.GPIO as GPIO
import threading
import time

DEBUG = False

config = RawConfigParser()
config.read('fancontrol.cfg')
dataPin = config.getint('pins', 'dcf77')

def cleanup():
    print('Start GPIO cleanup for DCF77 reader.')
    GPIO.cleanup(dataPin)
    print('GPIO cleaned up for DCF77 reader.')

atexit.register(cleanup)

GPIO.setmode(GPIO.BOARD)
GPIO.setup(dataPin, GPIO.IN, GPIO.PUD_UP)

# Todo: replace by datetime.timezone for Python3
STDOFFSET = timedelta(hours = 1)
DSTOFFSET = timedelta(hours = 2)
ZERO = timedelta(0)
HOUR = timedelta(hours = 1)
class DCF77Timezone(tzinfo):
    def __init__(self, isdst):
        self._isdst = isdst

    def utcoffset(self, dt):
        # 'dt' argument is ignored!
        if self._isdst:
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        # 'dt' argument is ignored!
        if self._isdst:
            return HOUR
        else:
            return ZERO

    def tzname(self, dt):
        # 'dt' argument is ignored!
        return 'CEST' if self._isdst else 'CET'

# Convert BCD to decimal
def bcdToDec(b0, b1, b2=0, b3=0):
    result = b0 + b1 * 2 + b2 * 4 + b3 * 8
    assert result < 10, ('BCD', result)
    return result

# Parity check (even parity)
# The parity bit must be contained in the array.
def check_parity(bit_arr):
    assert sum(bit_arr) & 1 == 0, ('Parity', bit_arr)

def decodeDCF77(bit_seq):
    try:
        assert bit_seq[0] == 0 and bit_seq[20] == 1, ('0, 20', bit_seq[0], bit_seq[20])
        assert bit_seq[17] != bit_seq[18], ('17, 18', bit_seq[17:19])
        check_parity(bit_seq[21:29])
        check_parity(bit_seq[29:36])
        check_parity(bit_seq[36:59])

        # Daylight saving time?
        isdst = bit_seq[17]
        tzinfo = DCF77Timezone(isdst)

        # Minute (BCD)
        minute1 = bcdToDec(*bit_seq[21:25])
        minute10 = bcdToDec(*bit_seq[25:28])
        assert minute10 < 6, ('Minute10', minute10)
        minute = minute1 + 10 * minute10

        # Hour (BCD)
        hour1 = bcdToDec(*bit_seq[29:33])
        hour10 = bcdToDec(*bit_seq[33:35])
        assert hour10 < 3, ('Hour10', hour10)
        hour = hour1 + 10 * hour10
        assert hour < 24, ('Hour', hour)

        # Year (BCD)
        year1 = bcdToDec(*bit_seq[50:54])
        year = year1 + 10 * bcdToDec(*bit_seq[54:58]) + 2000
        assert year >= 2015, ('Year', year)

        # Month (BCD)
        month = bcdToDec(*bit_seq[45:49]) + bit_seq[49] * 10
        assert month >= 1, ('Month', month)
        assert month <= 12, ('Month', month)
        # Day (BCD)
        day1 = bcdToDec(*bit_seq[36:40])
        day = day1 + 10 * bcdToDec(*bit_seq[40:42])
        assert day >= 1, ('Day', day)
        assert day <= 31, ('Day', day)

        # Convert to 'datetime' format
        second = 0
        microsecond = 0
        dcf77_time = datetime(year, month, day, hour, minute, second, microsecond, tzinfo)
        return dcf77_time
    except AssertionError as e:
        if DEBUG:
            print(e)
        return None

def dummyBreakEvent():
    return False

class Receiver:
    def __init__(self, callback=None, breakEvent=dummyBreakEvent):
        self.callback = callback
        self.breakEvent = breakEvent
        self.lock = threading.Lock()

    def run(self):
        self.bit_seq = [0] * 59
        self.sec = 61
        self.dcf77_time = None
        self.exception = None
        self.state = None
        self.t0 = self.t1 = timer()
        GPIO.add_event_detect(dataPin, GPIO.BOTH, bouncetime=50, callback=self.onData)
        while not self.breakEvent() and not self.exception:
            time.sleep(1)
        GPIO.remove_event_detect(dataPin)
        if self.exception:
            raise self.exception

    def onData(self, channel):
        with self.lock:
            try:
                if GPIO.input(dataPin) == GPIO.LOW:
                    self.t0 = timer()
                    if self.state == 0:
                        if DEBUG:
                            print('Callback called twice on falling edge.')
                        self.sec = 60
                    self.state = 0
                    time_up = self.t0 - self.t1
                    if DEBUG:
                        print(time_up)
                    if time_up > 1.7 and time_up < 2.0:
                        if self.dcf77_time and self.callback:
                            self.callback(self.dcf77_time)
                            self.dcf77_time = None
                        if DEBUG:
                            print('Start new bit sequence.')
                        self.sec = 0
                    elif (time_up > 1.0 or time_up < .7) and self.sec < 61:
                        if DEBUG:
                            print('Unusual pause length: {}s.'.format(time_up))
                    if DEBUG:
                        print('Seconds: {}'.format(self.sec))
                else:
                    self.t1 = timer()
                    if self.state == 1:
                        if DEBUG:
                            print('Callback called twice on rising edge.')
                        self.sec = 60
                    self.state = 1
                    time_down = self.t1 - self.t0
                    zero_bit = time_down > 0.08 and time_down < 0.13
                    one_bit = time_down > 0.17 and time_down < 0.24
                    self.dcf77_time = None
                    if zero_bit == one_bit:
                        if DEBUG:
                            print('Unusual pulse length: {}s.'.format(time_down))
                        self.sec = 60
                    elif self.sec < 59:
                        self.bit_seq[self.sec] = one_bit
                        self.sec += 1
                        if self.sec==59:
                            self.dcf77_time = decodeDCF77(self.bit_seq)
                            if not self.dcf77_time:
                                print('DCF77: Decode error.')
            except Exception as e:
                self.exception = e

# Main function to receive the DCF77 signal
def receiveTime(callback=None):
    R = Receiver(callback)
    R.run()

if __name__=='__main__':
    def compareToSystemTime(dcf77_time):
        now = datetime.now()
        print('System time: {}'.format(now))
        print('DCF77 time:  {}'.format(dcf77_time))
        print('Difference: {}'.format(abs(dcf77_time - now)))
    dcf77_time = receiveTime(compareToSystemTime)
