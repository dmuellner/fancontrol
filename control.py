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
import logging.handlers
import os
import time

from average import Average
from component import allThreadsAlive
from dcf77_thread import DCF77
from devices import Devices
from display import Display
from fan import Fan
from htmlwriter import HtmlWriter
from menu import Menu
from messageboard import messageboard
from sensor import Sensor
from signals_handler import signals_handler
from status import Status
from uptime import Uptime, UptimeAsString
from wlan import RestartWLAN, CheckNetwork

config = RawConfigParser()
config.read('fancontrol.cfg')
logfile = config.get('logging', 'logfile')

logdir = os.path.dirname(os.path.abspath(logfile))
if not os.path.isdir(logdir):
    os.makedirs(logdir)

logger = logging.getLogger('fancontrol')
logger.setLevel(logging.INFO)
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.uptime = UptimeAsString()
        return True
logger.addFilter(ContextFilter())
# File handler: rotate logs daily, keep logs > 2 years
fh = logging.handlers.TimedRotatingFileHandler(logfile, when='midnight', backupCount=750)
class UTCFormatter(logging.Formatter):
    converter = time.gmtime
fh.setFormatter(UTCFormatter('%(asctime)s,%(uptime)s,%(levelno)s,%(filename)s,%(message)s'))
logger.addHandler(fh)
# Console handler: for warnings and errors
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
ch.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))
logger.addHandler(ch)

logger.info('Startup')

signals_handler = signals_handler(messageboard)

with Display(), \
     Sensor(), \
     Status(), \
     HtmlWriter(), \
     Fan(), \
     Menu(), \
     Devices(), \
     DCF77(), \
     Average(), \
     RestartWLAN(), \
     CheckNetwork():
    time0 = Uptime()
    while messageboard.query('ExitThread') is None:
        exception = messageboard.query('Exception')
        if exception is not None:
            raise exception
        messageboard.post('Time', (Uptime(), time.localtime()))
        time1 = Uptime()
        if not time1 >= time0:
            logger.warning('Error in uptime: {} < {}.'.format(time1, time0))
            time0 = time1
        sleeptime = 1 - time1 + time0
        if sleeptime <= 0:
            logger.warning(u'Zero sleep time: {} < {}, Δ={:.1f}s.'.
                           format(time0, time1, time1-time0))
        while sleeptime > 0:
            time.sleep(sleeptime)
            time1 = Uptime()
            sleeptime = 1 - time1 + time0
        if sleeptime > -.1:
            time0 += 1
        else:
            logger.warning('Sleep longer than expected: {} < {}, Δ={:.1f}s.'.
                           format(time0, time1, time1-time0))
            time0 = time1
        if not allThreadsAlive():
            messageboard.post('ExitThread', True)

logger.info('Shutdown')
