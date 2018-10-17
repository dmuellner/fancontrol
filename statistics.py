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
from lxml import etree
import os
import shutil
import subprocess
import tempfile
import time
import datetime
import numpy as np
import calendar

config = RawConfigParser()
config.read('fancontrol.cfg')

w, h = 1440, 600 # graph size
wplus = w + 85   # image size
hplus = h + 75

intervals = [5,10,15,20,25,30,40,50,60,75,100,200,300,600] # divisors of h

today = datetime.date.today()

def nextOffTime(date, starttimestamp):
    date = date + datetime.timedelta(days=1)
    logfile = config.get('logging', 'logfile')
    if date != today:
        logfile = logfile + date.strftime('.%Y-%m-%d')

    if os.path.isfile(logfile):
        for line in open(logfile, 'r'):
            entries = [entry.strip() for entry in line.split(',')]
            t = time.strptime(entries[0], '%Y-%m-%d %H:%M:%S')
            timestamp = calendar.timegm(t)
            minute = int(np.floor((timestamp - starttimestamp) / 60))
            assert minute >= w, (minute, w)
            if entries[4] == 'fan.py' and entries[5] == 'fan':
                if entries[6] == 'True':
                    return
                elif entries[6] == 'False':
                    return timestamp
            elif entries[4] == 'menu.py' and entries[5] == 'user':
                if entries[6] == 'FanOn':
                    return
                if entries[6] == 'FanOff':
                    return timestamp
            elif entries[4] == 'control.py' and entries[5] in ('Startup', 'Shutdown'):
                return timestamp
    return time.time()

def lastOnTime(date, starttimestamp):
    date = date + datetime.timedelta(days=-1)
    logfile = config.get('logging', 'logfile')
    if date != today:
        logfile = logfile + date.strftime('.%Y-%m-%d')

    lastOnTimestamp = None

    if os.path.isfile(logfile):
        for line in open(logfile, 'r'):
            entries = [entry.strip() for entry in line.split(',')]
            t = time.strptime(entries[0], '%Y-%m-%d %H:%M:%S')
            timestamp = calendar.timegm(t)
            minute = int(np.floor((timestamp - starttimestamp) / 60))
            assert minute < 0
            if entries[4] == 'fan.py' and entries[5] == 'fan':
                if entries[6] == 'True':
                    lastOnTimestamp = timestamp
                elif entries[6] == 'False':
                    lastOnTimestamp = None
            elif entries[4] == 'menu.py' and entries[5] == 'user':
                if entries[6] == 'FanOn':
                    lastOnTimestamp = timestamp
                elif entries[6] == 'FanOff':
                    lastOnTimestamp = None
            elif entries[4] == 'control.py' and entries[5] in ('Startup', 'Shutdown'):
                lastOnTimestamp = None
    return lastOnTimestamp

def read_log(*date):
    date = datetime.date(*date)
    logfile = config.get('logging', 'logfile')
    if date != today:
        logfile = logfile + date.strftime('.%Y-%m-%d')

    t = date.timetuple()
    starttimestamp = time.mktime(t)

    onTimes = []
    offTimes = []
    extraOffTimes = [time.time()]
    data1 = np.zeros((w, 2))
    data2 = np.zeros((w, 2))
    num1 = np.zeros((w, 1), dtype=int)
    num2 = np.zeros((w, 1), dtype=int)

    minT = np.infty
    maxT = -minT

    for line in open(logfile, 'r'):
        entries = [entry.strip() for entry in line.split(',')]
        t = time.strptime(entries[0], '%Y-%m-%d %H:%M:%S')
        timestamp = calendar.timegm(t)
        minute = int(np.floor((timestamp - starttimestamp) / 60))
        assert minute >= 0
        assert minute < w + 60
        if minute >= w:
            continue
        if entries[4] == 'fan.py' and entries[5] == 'fan':
            if entries[6] == 'True':
                onTimes.append(timestamp)
            elif entries[6] == 'False':
                offTimes.append(timestamp)
        elif entries[4] == 'control.py' and entries[5] in ('Startup', 'Shutdown'):
            extraOffTimes.append(timestamp)
        elif entries[4] == 'menu.py' and entries[5] == 'user':
            if entries[6] == 'FanOn':
                onTimes.append(timestamp)
            elif entries[6] == 'FanOff':
                offTimes.append(timestamp)
        elif entries[4] == 'sensor.py' and entries[5] == 'measurement':
            if minute >= 0 and minute<= w:
                rH1, T1, tau1, Error1, rH2, T2, tau2, Error2 = entries[6:]
                if Error1 == 'False':
                    T1 = float(T1)
                    tau1 = float(tau1)
                    data1[minute] += (T1, tau1)
                    num1[minute] += 1
                if Error2 == 'False':
                    T2 = float(T2)
                    tau2 = float(tau2)
                    data2[minute] += (T2, tau2)
                    num2[minute] += 1
    # Prevent "RuntimeWarning: invalid value encountered in true_divide"
    data1 = np.where(num1>0, data1, np.nan) / num1
    data2 = np.where(num2>0, data2, np.nan) / num2

    minT = np.nanmin([np.nanmin(data1), np.nanmin(data2)])
    maxT = np.nanmax([np.nanmax(data1), np.nanmax(data2)])

    extraOnTime = lastOnTime(date, starttimestamp)
    if extraOnTime is not None:
        onTimes.append(extraOnTime)
    extraOffTime = nextOffTime(date, starttimestamp)
    if extraOffTime is not None:
        offTimes.append(extraOffTime)
    onTimes.sort()
    offTimes.sort()

    fanIntervals = []
    for onTime in onTimes:
        offIndex = np.searchsorted(offTimes, onTime)
        if offIndex < len(offTimes):
            offTime = offTimes[offIndex]
            assert onTime <= offTime, (onTime, offTime)

            x1 = int(np.floor((onTime - starttimestamp) / 60.0))
            if x1 >= w: continue
            x1 = max(0, x1)
            x2 = int(np.ceil((offTime - starttimestamp) / 60.0))
            if x2 < 0: continue
            x2 = min(x2, w-1)

            fanIntervals.append((x1, x2))
    return data1, data2, minT, maxT, fanIntervals

def plotcurve(SE, elem, points, maxT, minT, color):
    if points:
        s = ''
        for x, y in points:
            assert x >= 0 and x < w
            s += ' {x},{y:.1f}'.format(x=x, y=y).rstrip('0').rstrip('.')
        SE(elem, 'polyline', points=s[1:], style="stroke:" + color)


def plot(SE, elem, data, maxT, minT, color):
    points = []
    for x, T in enumerate(data):
        assert x >= 0 and x < w
        if T != T:
            plotcurve(SE, elem, points, maxT, minT, color)
            points = []
        else:
            y = (maxT - T) / float(maxT - minT) * h
            points.append((x,y))
    plotcurve(SE, elem, points, maxT, minT, color)


def make_plot(date, upload=False, mark_end=False):
    print("Make plot for {}.".format(date))
    year = date.year
    month = date.month
    day = date.day

    data1, data2, minT, maxT, fanIntervals = read_log(year, month, day)

    minTf = minT
    maxTf = maxT

    minT = int(np.floor(minT))
    maxT = int(np.ceil(maxT))

    spanT = maxT - minT
    for dt in intervals:
        if dt > spanT:
            spanT = dt
            break

    minT = min(minT, int(np.round((minTf + maxTf - spanT) * .5)))
    maxT = minT + spanT

    T1color = np.array([0,0,255], dtype=np.uint8)
    tau1color = np.array([0, 127, 0], dtype=np.uint8)
    T2color = np.array([255,0,0], dtype=np.uint8)
    tau2color = np.array([255, 0, 255], dtype=np.uint8)

    tempdirname = None
    try:
        svg = etree.Element('svg',
                                nsmap={None: 'http://www.w3.org/2000/svg',
                                       'xlink': 'http://www.w3.org/1999/xlink'},
                                width="{}px".format(wplus),
                                height="{}px".format(hplus),
                                viewBox="0 0 {} {}".format(wplus, hplus),
                                version="1.1")

        style = etree.SubElement(svg, 'style', type="text/css")
        style.text=etree.CDATA('''\
*{fill:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:round;}\
line{stroke:black;}\
polyline{stroke-linecap:round;}\
text,tspan{stroke:none;fill:black;font-family:sans-serif;font-size:13px;}\
g.ylabel text{dominant-baseline:mathematical;text-anchor:end;}\
rect{fill:rgb(180,180,180)}\
.thin line{stroke-width:.1px}\
line.thicker{stroke-width:.25px}''')

        defs = etree.SubElement(svg, 'defs')
        SE = etree.SubElement
        SE(defs, 'line', id="htick", x1="0", y1="0", x2="0", y2="10")
        SE(defs, 'line', id="vtick", x1="0", y1="0", x2="10", y2="0")
        SE(svg, 'rect',
           width=str(wplus),
           height=str(hplus),
           style="fill:white")
        text = SE(svg, 'text', y="13")
        text.text = 'Date: {year:04}-{month:02}-{day:02} '.format(year=year, month=month, day=day)
        tspan = SE(text, 'tspan', dx="2em")
        tspan.text = 'Legend:'
        tspan.tail = ' '
        tspan = SE(text, 'tspan', dx=".5em", style="fill:blue")
        tspan.text = u'■'
        tspan.tail = ' Temperature indoors '
        tspan = SE(text, 'tspan', dx="1em", style="fill:green")
        tspan.text = u'■'
        tspan.tail = ' Dew point indoors '
        tspan = SE(text, 'tspan', dx="1em", style="fill:red")
        tspan.text = u'■'
        tspan.tail = ' Temperature outdoors '
        tspan = SE(text, 'tspan', dx="1em", style="fill:magenta")
        tspan.text = u'■'
        tspan.tail = ' Dew point outdoors'
        tspan = SE(text, 'tspan', dx="1em", style="fill:rgb(180,180,180)")
        tspan.text = u'■'
        tspan.tail = ' Fan is on'
        text = SE(svg, 'text', x=str(wplus), y='13', style="text-anchor:end")
        text.text = u'Temperature/dew point in °C'
        text = SE(svg, 'text', x="0", y=str(h + 72))
        text.text = 'Time in hours'

        g1 = SE(svg, 'g', transform="translate(44,30)")

        for x1, x2 in fanIntervals:
            SE(g1, 'rect', x=str(x1), y='.5', width=str(x2-x1+1), height=str(h))

        g2 = SE(g1, 'g', transform="translate(.5,.5)")
        g3 = SE(g2, 'g', transform="translate(0,{})".format(h))
        SE(g3, 'line', x1="0", y1="0", x2=str(w), y2="0")

        for x in range(0, w+1, w//24):
            use = SE(g3, 'use', x=str(x))
            use.set('{http://www.w3.org/1999/xlink}href', "#htick")

        g4 = SE(g3, 'g', transform="translate(0,24)", style="text-anchor:middle")
        for i, x in enumerate(range(0, w+1, w//24)):
            text = SE(g4, 'text', x=str(x))
            text.text = str(i % 24)


        SE(g2, 'line', x1="0", y1="0", x2="0", y2=str(h))
        g9 = SE(g2, 'g', transform="translate(-10,0)")
        for T in range(minT, maxT+1, 1):
            y = '{:.2f}'.format(h - (T - minT) / float(maxT - minT) * h).rstrip('0').rstrip('.')
            use = SE(g9, 'use', y=y)
            use.set('{http://www.w3.org/1999/xlink}href', "#vtick")

        g10 = SE(g9, 'g', transform="translate(-5,0)")
        g10.set('class', "ylabel")
        for T in  range(minT, maxT+1, 1):
            y = '{:.2f}'.format(h - (T - minT) / float(maxT - minT) * h).rstrip('0').rstrip('.')
            text = SE(g10, 'text', y=y)
            text.text = ('' if T>=0 else u'−') + str(abs(T))

        g5 = SE(g2, 'g', transform="translate({},0)".format(w))
        SE(g5, 'line', x1="0", y1="0", x2="0", y2=str(h))

        g6 = SE(g5, 'g', x="0")
        for T in range(minT, maxT+1, 1):
            y = '{:.2f}'.format(h - (T - minT) / float(maxT - minT) * h).rstrip('0').rstrip('.')
            use = SE(g6, 'use', y=y)
            use.set('{http://www.w3.org/1999/xlink}href', "#vtick")

        g7 = SE(g6, 'g', transform="translate(40,0)")
        g7.set('class', "ylabel")
        for T in  range(minT, maxT+1, 1):
            y = '{:.2f}'.format(h - (T - minT) / float(maxT - minT) * h).rstrip('0').rstrip('.')
            text = SE(g7, 'text', y=y)
            text.text = ('' if T>=0 else u'−') + str(abs(T))

        g8 = SE(g2, 'g')
        g8.set('class', "thin")
        for T in range(minT, maxT + 1):
            y = '{:.2f}'.format(h - (T - minT) / float(maxT - minT) * h).rstrip('0').rstrip('.')
            l = SE(g8, 'line', x1="0", y1=y, x2=str(w), y2=y)
            if T % 5 == 0:
                l.attrib['class'] = 'thicker'

        if mark_end:
            l = 0
            for ii in reversed(range(len(data1))):
                if data1[ii,0]==data1[ii,0]:
                    l = ii + 1
                    break
            SE(g2, 'line',
               x1=str(l),
               y1="0",
               x2=str(l),
               y2=str(h - .5),
               style="stroke-dasharray:8; stroke:orange")

        plot(SE, g2, data1[:,0], maxT, minT, 'blue')
        plot(SE, g2, data1[:,1], maxT, minT, 'green')
        plot(SE, g2, data2[:,0], maxT, minT, 'red')
        plot(SE, g2, data2[:,1], maxT, minT, 'magenta')

        ET = etree.ElementTree(svg)
        filename = 'fancontrol_{year:04}-{month:02}-{day:02}.svg'.format(
            year=year, month=month, day=day)
        if upload:
            tempdirname = tempfile.mkdtemp()
            tempfilename = 'fancontrol.svg.tmp'
            tempfilepath = os.path.join(tempdirname, tempfilename)
            ET.write(tempfilepath, pretty_print=False)
            print('Upload')
            retval = subprocess.call(
                '/usr/bin/lftp -c "open ftp.kundencontroller.de; '
                'cd www/data/fangraphs; '
                'put {}; '
                'mv {} {}"'
                .format(tempfilepath, tempfilename, filename), shell=True)
            print('Return value: {}'.format(retval))
            if retval != 0:
                raise RuntimeError('Upload failed')
        else:
            dirname = 'graphs'
            filepath = os.path.join(dirname, filename)
            ET.write(filepath, pretty_print=False)
    except:
        print('Error!')
        raise
    finally:
        if tempdirname is not None:
            shutil.rmtree(tempdirname)
            print('Removed temp dir')

if __name__ == "__main__":
    if len(sys.argv)==2:
        if sys.argv[1]=='all':
            startdate = datetime.date(2016,3,16)
            enddate = today
            dt = datetime.timedelta(days=1)

            date = startdate
            while date < enddate:
                print(date)
                make_plot(date)
                date += dt
        else:
            offset = int(sys.argv[1])
            dt = datetime.timedelta(days=offset)
            make_plot(today - dt,
                      upload=True,
                      mark_end=(offset==0))
