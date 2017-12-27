#!/usr/bin/env python2
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
import sys
if sys.hexversion < 0x03000000:
    from ConfigParser import RawConfigParser
else:
    from configparser import RawConfigParser
from datetime import datetime
import logging
from threading import Event
import time

from component import ComponentWithThread
import sht75
from uptime import Uptime

logger = logging.getLogger('fancontrol')

config = RawConfigParser()
config.read('fancontrol.cfg')
clock1 = config.getint('pins', 'sensor1_clock')
data1 = config.getint('pins', 'sensor1_data')
clock2 = config.getint('pins', 'sensor2_clock')
data2 = config.getint('pins', 'sensor2_data')

measure_interval = config.getint('measure', 'interval')
assert measure_interval >= 1

class csv:
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return ','.join(map(str, self.args))

def delay(seconds):
    time0 = Uptime()
    sleeptime = seconds
    while sleeptime > 0:
        time.sleep(sleeptime)
        time1 = Uptime()
        sleeptime = seconds - time1 + time0

class Sensor(ComponentWithThread):
    def __init__(self):
        ComponentWithThread.__init__(self, 'sensor')
        self.S1 = sht75.Sensor(clock1, data1)
        self.S2 = sht75.Sensor(clock2, data2)
        self.event = Event()
        self.lastmeasurement = Uptime()

    def __enter__(self):
        self.messageboard.subscribe('Time', self, Sensor.onTime)
        return ComponentWithThread.__enter__(self)

    def onTime(self, message):
        self.uptime, localtime = message
        if self.uptime > self.lastmeasurement + 10.5:
            logger.warning('Interval between measurements > 10.5s: {}, {}.'.
                           format(self.lastmeasurement, self.uptime))
        if int(self.uptime) % measure_interval == 0 \
           or self.uptime > self.lastmeasurement + 10.5:
            self.lastmeasurement = self.uptime
            self.event.set()

    def run(self):
        while self.messageboard.query('ExitThread') is None:
            if self.event.wait(1):
                self.event.clear()
                # Start measurement approx. 250 ms after the full second.
                # This lowers interference with the DCF77 receiver.
                microsecond = datetime.now().microsecond
                wait = ((1250000 - microsecond) % 1000000) / 1000000.0
                assert wait >= 0
                assert wait < 1
                delay(wait)
                S1Data = self.S1.read()
                S2Data = self.S2.read()
                self.messageboard.post('Measurement', (self.uptime, S1Data, S2Data))
                logger.info(csv('measurement',
                                S1Data.rH, S1Data.T, S1Data.tau, S1Data.Error,
                                S2Data.rH, S2Data.T, S2Data.tau, S2Data.Error))
