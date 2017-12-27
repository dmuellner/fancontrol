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
from collections import deque
import logging

from component import Component
from sht75 import Bunch
from uptime import Uptime

logger = logging.getLogger('fancontrol')

NaN = float('NaN')

class Average(Component):
    def __init__(self):
        Component.__init__(self, 'average')
        self.deque = deque(maxlen = 9000) # enough for 24h

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Measurement', self, Average.onMeasurement)
            self.messageboard.subscribe('Average', self, Average.onAverage)
        return Component.__enter__(self)

    def onMeasurement(self, message):
        with self.lock:
            self.deque.appendleft(message)

    def onAverage(self, message):
        with self.lock:
            uptime0 = Uptime()
            timespan = message

            T1 = 0
            rH1 = 0
            tau1 = 0
            count1 = 0
            T2 = 0
            rH2 = 0
            tau2 = 0
            count2 = 0

            for uptime, S1Data, S2Data in self.deque:
                assert uptime <= uptime0
                if uptime0 - uptime > timespan:
                    break
                if not S1Data.Error:
                    T1 += S1Data.T
                    rH1 += S1Data.rH
                    tau1 += S1Data.tau
                    count1 += 1
                if not S2Data.Error:
                    T2 += S2Data.T
                    rH2 += S2Data.rH
                    tau2 += S2Data.tau
                    count2 += 1
            if count1 > 0:
                T1 /= count1
                rH1 /= count1
                tau1 /= count1
            Error1 = count1 < max(1, timespan / 20)
            if count2 > 0:
                T2 /= count2
                rH2 /= count2
                tau2 /= count2
            Error2 = count2 < max(1, timespan / 20)
            return (Bunch(rH = rH1, T = T1, tau = tau1, Error = Error1),
                    Bunch(rH = rH2, T = T2, tau = tau2, Error = Error2))
