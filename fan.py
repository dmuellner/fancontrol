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
import logging
from math import expm1

from component import Component

DEBUG = False

logger = logging.getLogger('fancontrol')

config = RawConfigParser()
config.read('fancontrol.cfg')
ventilation_period = config.getfloat('fan', 'ventilation_period')

class Fan(Component):
    def __init__(self):
        Component.__init__(self, 'fan')
        self.mode = None
        self.fanState = None
        self.lastOff = None
        self.stayOnUntil = 0
        self.stayOffUntil = 0

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Mode', self, Fan.onMode)
            self.messageboard.subscribe('Time', self, Fan.onTime)
        return Component.__enter__(self)

    def onMode(self, message):
        with self.lock:
            self.mode = message
            if self.mode != 'manual':
                self.fanState = None
                self.lastOff = -90000
                self.stayOnUntil = 0
                self.stayOffUntil = 0

    def decideFan(self, uptime):
        if self.stayOffUntil > uptime:
            return False

        average1 = self.messageboard.ask('Average', 60)
        average10 = self.messageboard.ask('Average', 60 * 10)

        if average1 is None or average10 is None:
            logger.error('fan, Average is None.')
            self.messageboard.post('FanComment',
                                   'Error!')
            return False

        S1Data = average1[0]
        S2Data = average10[1]
        if S1Data.Error or S2Data.Error:
            self.messageboard.post('FanComment',
                                   'Not enough samples for average.')
            return False

        if S1Data.tau - S2Data.tau < 1:
            self.messageboard.post('FanComment',
                                   'High outside dew point.')
            self.stayOffUntil = uptime + 20*60
            return False

        if S1Data.T < S2Data.T:
            self.messageboard.post('FanComment',
                                   'Permanent ventilation: warm and dry outside.')
            self.stayOnUntil = uptime + 20*60
            return True

        if S1Data.T < 10:
            self.messageboard.post('FanComment',
                                   'Low room temperature.')
            self.stayOffUntil = uptime + 20*60
            return False

        remainingVentilationPeriod = self.stayOnUntil - uptime
        if remainingVentilationPeriod > 0:
            self.messageboard.post('FanComment',
                                   'Remaing ventilation period: {} min.'.format(int(remainingVentilationPeriod / 60.0 + .5)))
            return True

        #offSeconds = expm1((15.0 - S2Data.T) /  6.0) * 20 * 60
        offSeconds = expm1((15.0 - S2Data.T) / 10.0) * 45 * 60
        #offSeconds = expm1((15.0 - S2Data.T) / 12.0) * 60 * 60

        if offSeconds < 60:
            offSeconds = 0
        if not (offSeconds <= 86400):
            offSeconds = 86400
        if self.lastOff is None:
            remainingWaitPeriod = offSeconds
        else:
            remainingWaitPeriod = max(0, offSeconds - uptime + self.lastOff)
        self.messageboard.post('FanComment',
                               'Wait period: {} min ({} min remaining).'.
                               format(
                                   int(offSeconds / 60.0 + .5),
                                   int(remainingWaitPeriod / 60.0 + .5)))
        self.messageboard.post('WaitPeriod', offSeconds)
        self.messageboard.post('RemainingWaitPeriod', remainingWaitPeriod)
        fanState = remainingWaitPeriod == 0
        if fanState:
            self.stayOnUntil = uptime + 20*60
        return fanState

    def onTime(self, message):
        with self.lock:
            if self.mode == 'manual':
                return
            uptime, localtime = message
            action = self.decideFan(uptime)

            if action != self.fanState:
                self.fanState = action
                logger.info('fan,{}'.format(action))
                if action:
                    self.messageboard.post('Devices', 'VentilationOn')
                    self.lastOff = None
                else:
                    self.messageboard.post('Devices', 'VentilationOff')
                    self.lastOff = uptime
