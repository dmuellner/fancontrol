#!/usr/bin/python
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
import logging
import os
import time

from component import ComponentWithThread
from dcf77_reader import Receiver

logger = logging.getLogger('fancontrol')

class DCF77(ComponentWithThread):
    def __init__(self):
        ComponentWithThread.__init__(self, 'DCF77 receiver')

    def __callback(self, dcf77_time):
        # Format date/time string
        utctime = dcf77_time.utctimetuple()
        time_date_str = time.strftime("\"%Y-%m-%d %H:%M:00\"", utctime)
        # Set system time
        retval = os.system("date -u -s " + time_date_str + " > /dev/null")
        if retval != 0:
            logger.error('"date" command return value is {}.'.format(retval))
        time_date_str = "{:02d}.{:02d}.{:4d}, {:02d}:{:02d} {}".format(
            dcf77_time.day, dcf77_time.month, dcf77_time.year, dcf77_time.hour,
            dcf77_time.minute, dcf77_time.tzinfo.tzname(dcf77_time))
        self.messageboard.post('DCF77TimeSync', time_date_str)
        logger.info('dcf77,{}'.format(time_date_str))

    def run(self):
        def breakEvent():
            return self.messageboard.query('ExitThread') is not None
        R = Receiver(callback=self.__callback, breakEvent=breakEvent)
        R.run()
