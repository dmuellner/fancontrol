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

import atexit
import sys
if sys.hexversion < 0x03000000:
    from ConfigParser import RawConfigParser
else:
    from configparser import RawConfigParser
import os
import pygame
import shutil
import time
from itertools import count

from component import Component

DEBUG = False

os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ['SDL_VIDEODRIVER']="fbcon"

fontname = 'Droid Sans'

fontsize = 15

config = RawConfigParser()
config.read('fancontrol.cfg')
endscreen_raw = config.get('screenshot', 'endscreen_raw')

def display_endscreen():
    pygame.quit()
    shutil.copyfile(endscreen_raw, '/dev/fb1')

atexit.register(display_endscreen)

WHITE = (255, 255, 255)
YELLOW = (255, 255, 140)
STATUSBG = (230, 230, 230)

icon_offline = pygame.image.load('/usr/share/icons/HighContrast/16x16/status/network-error.png')
icon_online = pygame.image.load('/usr/share/icons/HighContrast/16x16/status/network-idle.png')
icon_unknown = pygame.image.load('/usr/share/icons/HighContrast/16x16/status/network-no-route.png')

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

class Screen:
    def __init__(self, messageboard):
        self.messageboard = messageboard
        pygame.display.init()
        pygame.font.init()
        pygame.mouse.set_visible(0)
        self.line = []
        sizes = pygame.display.list_modes()
        print("Available display sizes:", sizes)
        size = self.width, self.height = sizes[0]
        print('Initialize display...')
        self.screen = pygame.display.set_mode(size)
        print('Done.')
        self.font = pygame.font.SysFont(fontname, fontsize)
        self.clear()
        NaN = float('NaN')
        dummyMeasurement = Bunch(rH = NaN, T = NaN, tau = NaN)
        self.set_measurements(dummyMeasurement, dummyMeasurement)
        self.set_background(WHITE)
        self.in_menu = True # Suppress display update
        self.localtime = time.localtime()
        self.in_menu = False

    def clear(self):
        self.screen.fill((255,255,255))
        self.y = 0
        self.lineheight = 0

    def set_background(self, color):
        self.bgcolor = color

    def displaytext(self, text, align, color):
        text = self.font.render(text, True, color, self.bgcolor)
        textpos = text.get_rect()
        textpos.top = self.y
        if align=='l':
            textpos.left = 2
        elif align=='r':
            textpos.right = self.width - 2
        elif align=='c2':
            textpos.centerx = self.width * .5
        elif align=='c3':
            textpos.centerx = self.width * .82
        else:
            raise ValueError()
        self.line.append((text, textpos))
        self.lineheight = max(self.lineheight, textpos.height)

    def hrule(self):
        pygame.draw.line(self.screen, (0,0,0), (0, self.y), (self.width - 1, self.y))
        self.y += 1

    def linefeed(self):
        self.screen.fill(self.bgcolor, pygame.Rect(0, self.y, self.width, self.lineheight))
        for surface, pos in self.line:
            self.screen.blit(surface, pos)
        self.line = []
        self.y += self.lineheight
        self.lineheight = 0
        self.set_background(WHITE)

    def displaybottom(self, text, color):
        text = self.font.render(text, True, color, self.bgcolor)
        textpos = text.get_rect()
        textpos.bottom = self.height
        textpos.left = 2
        self.screen.fill(self.bgcolor, pygame.Rect(0, textpos.top, self.width, self.height - textpos.top))
        self.screen.blit(text, textpos)

    def showpage(self):
        pygame.display.flip()

    def set_time(self, localtime):
        self.localtime = localtime
        if not self.in_menu:
            self.show_measurements()
        self.messageboard.post('StatusProcessed', True)

    def set_measurements(self, S1, S2):
        self.rH1 = S1.rH
        self.T1 = S1.T
        self.tau1 = S1.tau
        self.rH2 = S2.rH
        self.T2 = S2.T
        self.tau2 = S2.tau

    def get_fanstate(self):
        fanstate = self.messageboard.query('FanState')
        if fanstate == 'FanOn':
            return u'Lüftung ist an.', (255, 127, 0)
        elif fanstate == 'FanOff':
            return u'Lüftung ist aus.', (0, 127, 0)
        elif fanstate == 'OpenWindow':
            return u'Öffne Fenster.', (255, 127, 0)
        elif fanstate == 'CloseWindow':
            return u'Schliesse Fenster.', (255, 127, 0)
        else:
            return u'Lüftung: unbekannt.', (255, 0, 0)

    @staticmethod
    def color(x):
        return (0,0,0) if x==x else (255,0,0)

    def show_measurements(self):
        self.clear()
        self.displaytext(time.strftime("%d.%m.%Y", self.localtime), 'l', (0,0,0))
        self.displaytext(time.strftime("%H:%M:%S", self.localtime), 'r', (0,0,0))
        self.linefeed()
        self.displaytext("Innen", 'c2', (0,0,0))
        self.displaytext("Aussen", 'c3', (0,0,0))
        self.linefeed()
        self.hrule()
        self.set_background(YELLOW)
        self.displaytext("rF in %", 'l', (0,0,0))
        self.displaytext('{:2.1f}'.format(self.rH1), 'c2', self.color(self.rH1))
        self.displaytext('{:2.1f}'.format(self.rH2), 'c3', self.color(self.rH2))
        self.linefeed()
        self.displaytext(u"T in °C", 'l', (0,0,0))
        self.displaytext('{:2.1f}'.format(self.T1), 'c2', self.color(self.T1))
        self.displaytext('{:2.1f}'.format(self.T2), 'c3', self.color(self.T2))
        self.linefeed()
        self.set_background(YELLOW)
        self.displaytext(u"τ in °C", 'l', (0,0,0))
        self.displaytext('{:2.1f}'.format(self.tau1), 'c2', self.color(self.tau1))
        self.displaytext('{:2.1f}'.format(self.tau2), 'c3', self.color(self.tau2))
        self.linefeed()
        fanstatetext, fanstatecolor = self.get_fanstate()
        self.displaytext(fanstatetext, 'l', fanstatecolor)
        online = self.messageboard.query('Network')
        if online is None:
            icon = icon_unknown
        elif online:
            icon = icon_online
        else:
            icon = icon_offline
        iconpos = icon.get_rect()
        iconpos.top = self.y
        iconpos.right = self.width
        self.line.append((icon, iconpos))
        self.linefeed()
        status = self.messageboard.query('Status')
        if status is not None:
            statustxt, statuscolor = status
            self.displaytext(statustxt, 'l', statuscolor)
            self.linefeed()
        self.showpage()

    def show_startscreen(self):
        self.clear()
        self.displaytext('Fan control', 'l', (0,0,0))
        self.linefeed()
        self.displaytext(u'by Daniel Müllner', 'l', (0,0,0))
        self.linefeed()
        self.showpage()

    def leave_menu(self):
        self.in_menu = False
        self.show_measurements()

    def show_menu(self, items, highlight=None, statusline=None):
        self.in_menu = True
        self.clear()
        for index, item in zip(count(), items):
            if index==highlight:
                self.set_background((127,255,127))
            self.displaytext(item, 'l', (0,0,0))
            self.linefeed()
        if statusline:
            self.set_background(STATUSBG)
            self.displaybottom(statusline, (50,50,255))
            self.set_background(WHITE)
        self.showpage()

    def show_info(self, items, highlight=None, statusline=None):
        self.in_menu = True
        self.clear()
        for index, item in zip(count(), items):
            if index==highlight:
                self.set_background((127,255,127))
            self.displaytext(item[0], 'l', (0,0,0))
            if len(item) > 1:
                self.displaytext(item[1], 'r', (0,0,0))
            self.linefeed()
        if statusline:
            self.set_background(STATUSBG)
            self.displaybottom(statusline, (50,50,255))
            self.set_background(WHITE)
        self.showpage()

class Display(Component):
    def __init__(self):
        Component.__init__(self, 'display')
        self.screen = Screen(self.messageboard)
        self.screen.show_startscreen()

    def __enter__(self):
        with self.lock:
            self.messageboard.subscribe('Measurement', self, Display.onMeasurement)
            self.messageboard.subscribe('Time', self, Display.onTime)
            self.messageboard.subscribe('MainScreen', self, Display.onMainScreen)
            self.messageboard.subscribe('Menu', self, Display.onMenu)
            self.messageboard.subscribe('Info', self, Display.onInfo)
        return Component.__enter__(self)

    def onMeasurement(self, message):
        with self.lock:
            self.screen.set_measurements(*message[1:])

    def onTime(self, message):
        uptime, localtime = message
        with self.lock:
            self.screen.set_time(localtime)

    def onMainScreen(self, message):
        with self.lock:
            self.screen.leave_menu()

    def onMenu(self, message):
        with self.lock:
            self.screen.show_menu(*message)

    def onInfo(self, message):
        with self.lock:
            self.screen.show_info(message)
