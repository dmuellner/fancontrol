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
import threading

class _Uptimefile:
    def __init__(self):
        self.f = open("/proc/uptime", 'r').__enter__()

    def __del__(self):
        print('Close file /proc/uptime.')
        self.f.__exit__()

    def file(self):
        return self.f

_uptimefile = _Uptimefile()
_f = _uptimefile.file()
_lock = threading.Lock()

def UptimeAsString():
    '''Uptime in Seconds'''
    with _lock:
        _f.seek(0)
        return _f.read().split()[0]

def Uptime():
    '''Uptime in Seconds'''
    return float(UptimeAsString())
