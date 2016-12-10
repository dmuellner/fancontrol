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
        self.fanState = False
        self.mode = None
        self.returnFromManualMode = True

        self.lastOn = -90000
        self.lastOff = None
        self.lastDecision = -90000

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Mode', self, Fan.onMode)
            self.messageboard.subscribe('Time', self, Fan.onTime)
        return Component.__enter__(self)

    def onMode(self, message):
        with self.lock:
            self.mode = message
            if self.mode != 'manual':
                self.returnFromManualMode = True
                self.lastOn = None
                self.lastOff = -90000
                self.lastDecision = -90000

    def decideFan(self, uptime):
        if self.lastOn is not None:
            remainingVentilationPeriod = ventilation_period - uptime + self.lastOn
            if remainingVentilationPeriod > 0:
                self.messageboard.post('FanComment',
                                       'Remaing ventilation period: {} min.'.format(int(remainingVentilationPeriod / 60.0 + .5)))
                return True
            self.lastOn = None
            self.lastOff = uptime
        elif uptime - self.lastDecision < 50:
            return False

        self.lastDecision = uptime

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
            return False

        if S1Data.T < S2Data.T:
            self.messageboard.post('FanComment',
                                   'Permanent ventilation: warm and dry outside.')
            return True

        if S1Data.T < 10:
            self.messageboard.post('FanComment',
                                   'Low room temperature.')
            return False

        offSeconds = expm1((15.0 - S2Data.T) / 6.0) * 20 * 60
        if offSeconds < 60:
            return True
        if not (offSeconds <= 86400):
            offSeconds = 86400
        remainingWaitPeriod = max(0, offSeconds - uptime + self.lastOff)
        self.messageboard.post('FanComment',
                               'Wait period: {} min ({} min remaining).'.
                               format(
                                   int(offSeconds / 60.0 + .5),
                                   int(remainingWaitPeriod / 60.0 + .5)))
        self.messageboard.post('WaitPeriod', offSeconds)
        self.messageboard.post('RemainingWaitPeriod', remainingWaitPeriod)
        return remainingWaitPeriod == 0

    def onTime(self, message):
        with self.lock:
            if self.mode == 'manual':
                return
            uptime, localtime = message
            action = self.decideFan(uptime)

            if self.returnFromManualMode or action != self.fanState:
                self.returnFromManualMode = False
                self.fanState = action
                logger.info('fan, {}'.format(action))
                if action:
                    self.messageboard.post('Devices', 'VentilationOn')
                    self.lastOn = uptime
                    self.lastOff = None
                else:
                    self.messageboard.post('Devices', 'VentilationOff')
                    self.lastOn = None
                    self.lastOff = uptime
