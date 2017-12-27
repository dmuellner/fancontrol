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
    import Queue
else:
    from configparser import RawConfigParser
    import queue
import codecs
import datetime
import os
import shutil
import time

from ip import get_ip_address, get_wan_ip
from uptime import Uptime
from component import Component

progstart = Uptime()

DEBUG = False

config = RawConfigParser()
config.read('fancontrol.cfg')
pagefilename = config.get('webserver', 'page')
pagetempfilename = config.get('webserver', 'temppage')
datafilename = config.get('webserver', 'data')
datatempfilename = config.get('webserver', 'tempdata')

indexsource = config.get('webserver', 'indexsource')
indextarget = config.get('webserver', 'indextarget')
shutil.copyfile(indexsource, indextarget)

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def CSSstyle(x):
    c = Bunch()
    c.rH = '' if x.rH==x.rH else 'color:red'
    c.T = '' if x.T==x.T else 'color:red'
    c.tau = '' if x.tau==x.tau else 'color:red'
    return c

def prettyPrint(number):
    return '{:2.1f}'.format(number).replace('-', u'−')

class PageGenerator:
    def __init__(self):
        self.statustxt = 'Status: Not set.'
        self.statusstyle = 'color:red'
        self.set_mode(None)
        self.set_fanstate(None)
        self.last_sync = None
        self.S1 = Bunch(T=float('nan'), tau=float('nan'), rH=float('nan'))
        self.S2 = Bunch(T=float('nan'), tau=float('nan'), rH=float('nan'))

    def set_measurements(self, S1, S2):
        self.S1 = S1
        self.S2 = S2

    def set_status(self, status):
        self.statustxt = status[0]
        self.statusstyle = status[1]
        self.last_sync = status[2]

    def set_fanstate(self, state):
        if state == 'FanOn':
            self.fanstatetxt = 'Fan: On.'
            self.fanstatestyle = 'color:#FF8C00'
        elif state == 'FanOff':
            self.fanstatetxt = 'Fan: Off.'
            self.fanstatestyle = ''
        elif state == 'OpenWindow':
            self.fanstatetxt = 'Window is being opened.'
            self.fanstatestyle = 'color:#FF8C00'
        elif state == 'CloseWindow':
            self.fanstatetxt = 'Window is being closed.'
            self.fanstatestyle = 'color:#FF8C00'
        else:
            self.fanstatetxt = 'Fan state: unknown.'
            self.fanstatestyle = 'color:red'

    def set_mode(self, mode):
        if mode == 'manual':
            self.modetxt = 'Mode: manual. '
        else:
            self.modetxt = ''

    def write(self):
        localtime = time.localtime()
        with codecs.open(pagetempfilename, 'w', encoding='utf8') as f:
            f.write(u'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fan control</title>
<meta name="author" content="Daniel Müllner">
<script type="text/JavaScript">
function timedRefresh(timeoutPeriod) {{ setTimeout("location.reload(true);",timeoutPeriod); }}
window.onload = timedRefresh(10000);
</script>
</head>
<style>
body {{font-family: sans-serif;}}
h1 {{font-size: 125%;}}
table {{border:1px solid grey;
border-collapse:collapse;}}
            td{{padding:4px 8px}}
tr.bg {{background-color:#ffb;}}
tr.hr {{border-bottom:1px solid black}}
td.l {{text-align:left;}}
td.c {{text-align:center;}}
td.r {{text-align:right;}}
</style>
<body>
<h1>Fan control</h1>
<table>
  <tr>
    <td colspan="3">
      {date}<span style="float:right">{time}</span>
    </td>
  </tr>
  <tr class="hr">
    <td>
    </td>
    <td class="c">
      Indoors
    </td>
    <td class="c">
      Outdoors
    </td>
  </tr>
  <tr class="bg">
    <td>
      Relative humidity in %
    </td>
    <td class="c" style="{S1Color.rH}">
      {S1rH}
    </td>
    <td class="c" style="{S2Color.rH}">
      {S2rH}
    </td>
  </tr>
  <tr>
    <td>
      Temperature in °C
    </td>
    <td class="c" style="{S1Color.T}">
      {S1T}
    </td>
    <td class="c" style="{S2Color.T}">
      {S2T}
    </td>
  </tr>
  <tr class="bg">
    <td>
      Dew point in °C
    </td>
    <td class="c" style="{S1Color.tau}">
      {S1tau}
    </td>
    <td class="c" style="{S2Color.tau}">
      {S2tau}
    </td>
  </tr>
  <tr>
    <td colspan="3" style="{fanstatestyle}">
      {modetxt}{fanstatetxt}
    </td>
  </tr>
  <tr class="bg hr">
    <td colspan="3" style="{statusstyle}">
      {statustxt}
    </td>
  </tr>
  <tr>
    <td colspan="3">
      IP Ethernet:&nbsp;<span style="float:right">{IPeth0}</span>
    </td>
  </tr>
  <tr class="bg">
    <td colspan="3">
      IP WLAN:&nbsp;<span style="float:right">{IPwlan0}</span>
    </td>
  </tr>
  <tr>
    <td colspan="3">
      IP WAN:&nbsp;<span style="float:right">{IPwan}</span>
    </td>
  </tr>
  <tr class="bg">
    <td colspan="3">
      OS uptime:&nbsp;<span style="float:right">{uptime}</span>
    </td>
  </tr>
  <tr>
    <td colspan="3">
      Controller uptime:&nbsp;<span style="float:right">{progtime}</span>
    </td>
  </tr>
  <tr class="bg">
    <td colspan="3">
      Last DCF77 signal:&nbsp;<span style="float:right">{lastsync}</span>
    </td>
  </tr>
</table>
</body>
</html>
'''.
                    format(date=time.strftime("%d.%m.%Y", localtime),
                           time=time.strftime("%H:%M:%S", localtime),
                           S1rH=prettyPrint(self.S1.rH),
                           S2rH=prettyPrint(self.S2.rH),
                           S1T=prettyPrint(self.S1.T),
                           S2T=prettyPrint(self.S2.T),
                           S1tau=prettyPrint(self.S1.tau),
                           S2tau=prettyPrint(self.S2.tau),
                           S1Color=CSSstyle(self.S1), S2Color=CSSstyle(self.S2),
                           statustxt = self.statustxt,
                           statusstyle = self.statusstyle,
                           modetxt = self.modetxt,
                           fanstatetxt = self.fanstatetxt,
                           fanstatestyle = self.fanstatestyle,
                           IPeth0=get_ip_address('eth0'),
                           IPwlan0=get_ip_address('wlan0'),
                           IPwan=get_wan_ip(),
                           uptime=str(datetime.timedelta(seconds=int(Uptime()))),
                           progtime=str(datetime.timedelta(seconds=int(Uptime() - progstart))),
                           lastsync=self.last_sync if self.last_sync else 'None')
            )
        os.rename(pagetempfilename, pagefilename)

    def writedata(self):
        localtime = time.localtime()
        with codecs.open(datatempfilename, 'w', encoding='utf8') as f:
            f.write(u'''\
{date}
{time}
{S1Color.rH}
{S1rH}
{S2Color.rH}
{S2rH}
{S1Color.T}
{S1T}
{S2Color.T}
{S2T}
{S1Color.tau}
{S1tau}
{S2Color.tau}
{S2tau}
{fanstatestyle}
{modetxt}{fanstatetxt}
{statusstyle}
{statustxt}
{IPeth0}
{IPwlan0}
{IPwan}
{uptime}
{progtime}
{lastsync}'''.
                    format(date=time.strftime("%d.%m.%Y", localtime),
                           time=time.strftime("%H:%M:%S", localtime),
                           S1rH=prettyPrint(self.S1.rH),
                           S2rH=prettyPrint(self.S2.rH),
                           S1T=prettyPrint(self.S1.T),
                           S2T=prettyPrint(self.S2.T),
                           S1tau=prettyPrint(self.S1.tau),
                           S2tau=prettyPrint(self.S2.tau),
                           S1Color=CSSstyle(self.S1), S2Color=CSSstyle(self.S2),
                           statustxt = self.statustxt,
                           statusstyle = self.statusstyle,
                           modetxt = self.modetxt,
                           fanstatetxt = self.fanstatetxt,
                           fanstatestyle = self.fanstatestyle,
                           IPeth0=get_ip_address('eth0'),
                           IPwlan0=get_ip_address('wlan0'),
                           IPwan=get_wan_ip(),
                           uptime=str(datetime.timedelta(seconds=int(Uptime()))),
                           progtime=str(datetime.timedelta(seconds=int(Uptime() - progstart))),
                           lastsync=self.last_sync if self.last_sync else 'None')
            )
        os.rename(datatempfilename, datafilename)

    def writeEndPage(self):
        localtime = time.localtime()
        with open(pagetempfilename, 'w') as f:
            f.write('''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fan control</title>
<meta name="author" content="Daniel Müllner">
<script type="text/JavaScript">
function timedRefresh(timeoutPeriod) {{ setTimeout("location.reload(true);",timeoutPeriod); }}
window.onload = timedRefresh(10000);
</script>
</head>
<style>
body {{font-family: sans-serif;}}
</style>
<body>
{date}, {time}: Program exited.
</body>
</html>
'''.
                    format(date=time.strftime("%d.%m.%Y", localtime),
                           time=time.strftime("%H:%M:%S", localtime))
            )
        os.rename(pagetempfilename, pagefilename)

class HtmlWriter(Component):
    def __init__(self):
        Component.__init__(self, 'HTML writer')
        self.pageGenerator = PageGenerator()
        self.oldstatus = (None, None)

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Measurement', self, HtmlWriter.onMeasurement)
            self.messageboard.subscribe('HTMLStatus', self, HtmlWriter.onHTMLStatus)
            self.messageboard.subscribe('FanState', self, HtmlWriter.onFanState)
            self.messageboard.subscribe('Mode', self, HtmlWriter.onMode)
        return Component.__enter__(self)

    def __exit__(self, exc_type, exc_value, traceback):
        Component.__exit__(self, exc_type, exc_value, traceback)
        with self.lock:
            self.pageGenerator.writeEndPage()

    def onMeasurement(self, message):
        with self.lock:
            self.pageGenerator.set_measurements(*message[1:])
            #self.pageGenerator.write() # ???
            self.pageGenerator.writedata()

    def onHTMLStatus(self, message):
        with self.lock:
            self.pageGenerator.set_status(message)
            #self.pageGenerator.write()
            self.pageGenerator.writedata()

    def onFanState(self, message):
        with self.lock:
            self.pageGenerator.set_fanstate(message)
            #self.pageGenerator.write()
            self.pageGenerator.writedata()

    def onMode(self, message):
        with self.lock:
            self.pageGenerator.set_mode(message)
            #self.pageGenerator.write()
            self.pageGenerator.writedata()
