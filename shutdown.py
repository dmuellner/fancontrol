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
import dbus

def shutdown():
    # http://stackoverflow.com/a/41644926
    sys_bus = dbus.SystemBus()
    lg = sys_bus.get_object('org.freedesktop.login1','/org/freedesktop/login1')
    pwr_mgmt =  dbus.Interface(lg,'org.freedesktop.login1.Manager')
    shutdown_method = pwr_mgmt.get_dbus_method("PowerOff")
    shutdown_method(True)
