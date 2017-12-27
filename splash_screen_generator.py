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

import os
import pygame

os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ['SDL_VIDEODRIVER']="fbcon"

fontname = 'Droid Sans'

fontsize = 17

pygame.display.init()
pygame.font.init()
pygame.mouse.set_visible(0)
sizes = pygame.display.list_modes()
print("Sizes available:", sizes)
size = width, height = sizes[0]
print('Initialize display...')
screen = pygame.display.set_mode(size)
print('Done.')
screen.fill((255,255,255))
font = pygame.font.SysFont(fontname, fontsize)

text = font.render(u'Taupunkt-', True, (0,0,0))
textpos = text.get_rect()
textpos.top = 4
textpos.left = 2
screen.blit(text, textpos)

text = font.render(u'Lüftungssteuerung', True, (0,0,0))
textpos = text.get_rect()
textpos.top = 4 + 20
textpos.left = 2
screen.blit(text, textpos)

text = font.render(u'© Daniel Müllner', True, (0,0,0))
textpos = text.get_rect()
textpos.top = 4 + 2 * 20 + 10
textpos.left = 2
screen.blit(text, textpos)

font = pygame.font.SysFont(fontname, fontsize)
text = font.render(u'Steuerung wurde', True, (255, 127, 0))
textpos = text.get_rect()
textpos.top = 4 + 4 * 20
textpos.left = 2
screen.blit(text, textpos)

font = pygame.font.SysFont(fontname, fontsize)
text = font.render(u'beendet.', True, (255, 127, 0))
textpos = text.get_rect()
textpos.top = 4 + 5 * 20
textpos.left = 2
screen.blit(text, textpos)

pygame.display.flip()

pygame.image.save(screen, 'endscreen.png')
