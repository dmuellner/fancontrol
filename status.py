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
from component import Component

C_ERROR = (255,0,0)
C_OK = (0,127,0)
C_ALERT = (0,159,255)
C_MEASURE = (0,159,255)

C_HTML_ERROR = 'color:red'
C_HTML_OK = 'color:#007f00'
C_HTML_ALERT = 'color:#009fff'


class Status(Component):
    def __init__(self):
        Component.__init__(self, 'status')
        self.new_measurement = False
        self.measurement_error = False
        self.ip_address = None
        self.lasthtmlstatus = None

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Measurement', self, Status.onMeasurement)
            self.messageboard.subscribe('StatusProcessed', self, Status.onStatusProcessed)
            self.messageboard.subscribe('Mode', self, Status.onMode)
        return Component.__enter__(self)

    def onMeasurement(self, message):
        with self.lock:
            self.new_measurement = True
            uptime, S1Data, S2Data = message
            self.measurement_error = S1Data.Error or S2Data.Error

            self.__generateDisplayStatus()
            self.__generateHTMLStatus()

    def onStatusProcessed(self, message):
        with self.lock:
            if self.new_measurement:
                self.new_measurement = False
                self.__generateDisplayStatus()

    def onMode(self, message):
        with self.lock:
            self.__generateDisplayStatus()

    def __generateHTMLStatus(self):
        last_sync = self.messageboard.query('DCF77TimeSync')
        if self.measurement_error:
            status = ('Sensor error.', C_HTML_ERROR, last_sync)
        elif last_sync is None:
            status = ('Wait for radio clock signal.', C_HTML_ALERT, last_sync)
        else:
            fanComment = self.messageboard.query('FanComment')
            if fanComment is None:
                fanComment = 'N/A'
            error = 'error' in fanComment or 'Error' in fanComment
            color = C_HTML_ERROR if error else C_HTML_OK
            statustxt = 'Error' if error else 'OK'
            status = ('Status: ' + statustxt + '. ' + fanComment, color, last_sync)
        if status != self.lasthtmlstatus:
            self.lasthtmlstatus = status
            self.messageboard.post('HTMLStatus', status)

    def __generateDisplayStatus(self):
        if self.new_measurement:
            status = ('Messung.', C_MEASURE)
        elif self.measurement_error:
            status = ('Sensorfehler.', C_ERROR)
        elif self.messageboard.query('DCF77TimeSync') is None:
            status = ('Warte auf Funksignal.', C_ALERT)
        else:
            mode = self.messageboard.query('Mode')
            if mode == 'manual':
                status = ('Status: OK (manuell).', C_OK)
            else:
                status = ('Status: OK (Automatik).', C_OK)
        self.messageboard.post('Status', status)
