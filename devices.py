#!/usr/bin/env python2
# -*- coding: utf-8 -*-
'''
    Copyright © 2016 Daniel Müllner <http://danifold.net>

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
    from Queue import Queue, Empty
else:
    from configparser import RawConfigParser
    from queue import Queue, Empty
import time

import RPi.GPIO as GPIO

from uptime import Uptime
from component import ComponentWithThread

DEBUG = False
CLOSE_WINDOW = True

config = RawConfigParser()
config.read('fancontrol.cfg')
relays = [
    config.getint('pins', 'relay1'),
    config.getint('pins', 'relay2'),
    config.getint('pins', 'relay3'),
    config.getint('pins', 'relay4')]

def cleanup():
    print('Start GPIO cleanup for devices.')
    GPIO.output(relays, GPIO.HIGH)
    GPIO.cleanup(relays)
    print('GPIO cleaned up for devices.')

atexit.register(cleanup)

GPIO.setmode(GPIO.BOARD)
for relay in relays:
    print('Set up relay on port {}.'.format(relay))
    GPIO.setup(relay, GPIO.OUT, initial=GPIO.HIGH)

def delay(seconds):
    time0 = Uptime()
    sleeptime = seconds
    while sleeptime > 0:
        time.sleep(sleeptime)
        time1 = Uptime()
        sleeptime = seconds - time1 + time0

class Devices(ComponentWithThread):
    def __init__(self):
        ComponentWithThread.__init__(self, 'devices')
        self.isFanOn = False
        self.isWindowMotorOn = False
        self.queue = Queue()
        if CLOSE_WINDOW:
            self.onDevices('VentilationOff')

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Devices', self, Devices.onDevices)
        return ComponentWithThread.__enter__(self)

    def stop(self):
        ComponentWithThread.stop(self)
        if CLOSE_WINDOW:
            self.__closeWindow()

    def onDevices(self, message):
        with self.lock:
            self.queue.put(message)

    def run(self):
        while self.messageboard.query('ExitThread') is None:
            try:
                if DEBUG:
                    print('Devices: queue length is {}'.format(self.queue.qsize()))
                message = self.queue.get(True, 1)
                self.queue.task_done()
                if DEBUG:
                    print('Devices message: {}'.format(message))
                if message=='StartOpenWindow':
                    self.__startOpenWindow()
                elif message=='StartCloseWindow':
                    self.__startCloseWindow()
                elif message=='StopWindowMotor':
                    self.__stopWindowMotor()
                elif message=='OpenWindow':
                    self.__openWindow()
                elif message=='CloseWindow':
                    self.__closeWindow()
                elif message=='FanOn':
                    self.__fanOn()
                elif message=='FanOff':
                    self.__fanOff()
                elif message=='VentilationOn':
                    self.__openWindow()
                    self.__fanOn()
                elif message=='VentilationOff':
                    self.__fanOff()
                    self.__closeWindow()
                else:
                    raise ValueError(message)
            except Empty:
                pass

    def __startOpenWindow(self):
        if self.isWindowMotorOn:
            self.__stopWindowMotor()
        self.messageboard.post('FanState', 'OpenWindow')
        self.isWindowMotorOn = True
        GPIO.output(relays[1], GPIO.LOW)
        delay(.5)
        GPIO.output([relays[0], relays[3]], GPIO.LOW)
        delay(.5)

    def __startCloseWindow(self):
        if self.isWindowMotorOn:
            self.__stopWindowMotor()
        self.messageboard.post('FanState', 'CloseWindow')
        self.isWindowMotorOn = True
        GPIO.output(relays[1], GPIO.HIGH)
        delay(.5)
        GPIO.output([relays[0], relays[3]], GPIO.LOW)
        delay(.5)

    def __stopWindowMotor(self):
        if self.isFanOn:
            self.messageboard.post('FanState', 'FanOn')
        else:
            self.messageboard.post('FanState', 'FanOff')
        GPIO.output(relays[0], GPIO.HIGH)
        delay(.5)
        GPIO.output(relays[1], GPIO.HIGH)
        self.isWindowMotorOn = False
        if not self.isFanOn:
            GPIO.output(relays[3], GPIO.HIGH)
        delay(.5)

    def __openWindow(self):
        self.__startOpenWindow()
        delay(10)
        self.__stopWindowMotor()

    def __closeWindow(self):
        self.__startCloseWindow()
        delay(10)
        self.__stopWindowMotor()

    def __fanOn(self):
        self.messageboard.post('FanState', 'FanOn')
        GPIO.output(relays[2:4], GPIO.LOW)
        self.isFanOn = True
        delay(.5)

    def __fanOff(self):
        GPIO.output(relays[2], GPIO.HIGH)
        self.isFanOn = False
        if not self.isWindowMotorOn:
            GPIO.output(relays[3], GPIO.HIGH)
            self.messageboard.post('FanState', 'FanOff')
        delay(.5)
