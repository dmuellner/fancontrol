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
from datetime import datetime
import logging
import dbus
from threading import Event
import time

from component import Component, ComponentWithThread
from uptime import Uptime
from ip import get_ip_address

DEBUG = False

logger = logging.getLogger('fancontrol')

config = RawConfigParser()
config.read('fancontrol.cfg')

measure_interval = config.getint('check_network', 'interval')
assert measure_interval >= 1

class RestartWLAN(Component):
    def __init__(self):
        Component.__init__(self, 'restartWLAN')

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('RestartWLAN', self, RestartWLAN.onResetWLAN)
        return Component.__enter__(self)

    def onResetWLAN(self, message):
        assert message == True
        with self.lock:
            sys_bus = dbus.SystemBus()
            systemd1 = sys_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
            manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
            job = manager.RestartUnit('netctl@ts3.service', 'fail')

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

class CheckNetwork(ComponentWithThread):
    def __init__(self):
        ComponentWithThread.__init__(self, 'check_wlan')
        self.event = Event()
        self.lastmeasurement = Uptime()

    def __enter__(self):
        self.messageboard.subscribe('Time', self, CheckNetwork.onTime)
        return ComponentWithThread.__enter__(self)

    def onTime(self, message):
        self.uptime, localtime = message
        if self.uptime > self.lastmeasurement + 10.5:
            logger.warning('Interval between network checks > 10.5s: {}, {}.'.
                           format(self.lastmeasurement, self.uptime))
        if int(self.uptime) % measure_interval == 0 \
           or self.uptime > self.lastmeasurement + 10.5:
            self.lastmeasurement = self.uptime
            self.event.set()

    @staticmethod
    def checkNetwork():
        return get_ip_address('wlan0') != 'None' or \
            get_ip_address('eth0') != 'None'

    def run(self):
        while self.messageboard.query('ExitThread') is None:
            if self.event.wait(1):
                self.event.clear()
                # Start measurement approx. 250 ms after the full second.
                # This lowers interference with the DCF77 receiver.
                microsecond = datetime.now().microsecond
                wait = ((1500000 - microsecond) % 1000000) / 1000000.0
                assert wait >= 0
                assert wait < 1
                delay(wait)
                online = self.checkNetwork()
                self.messageboard.post('Network', online)
                #logger.info(csv('network', online))
