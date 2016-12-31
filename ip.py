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
import fcntl
import requests
import socket
import struct

def get_ip_address(ifname='wlan0'):
    'Source: http://code.activestate.com/recipes/439094/'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        return 'None'

def get_wan_ip():
    try:
        r = requests.get('http://whatismyip.akamai.com', timeout=1, stream=True)
        # Validate the result: a plain text ip address.
        ip = r.raw.read(15)
        for c in ip:
            if not c in '0123456789.':
                return 'Error'
        return ip
    except:
        return 'Error'

if __name__=='__main__':
    print(get_ip_address())
