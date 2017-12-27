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
import logging
import os
import signal
import sys
from threading import currentThread

logger = logging.getLogger('fancontrol')

class signals_handler:
    def __init__(self, messageboard):
        self.messageboard = messageboard
        signal.signal(signal.SIGINT, self.generate_sigint_handler())
        signal.signal(signal.SIGTERM, self.generate_sigterm_handler())
        signal.signal(signal.SIGUSR1, self.generate_sigusr1_handler())
        signal.signal(signal.SIGUSR2, self.generate_sigusr2_handler())
        signal.signal(signal.SIGHUP, self.generate_sighup_handler())

    def generate_sigint_handler(self):
        def sigint_handler(signal, frame):
            print('Process {}, thread {}: SIGINT received.'.format(os.getpid(), currentThread().name))
            self.messageboard.post('ExitThread', True)
            logger.info('SIGINT received: exit.')
            sys.exit()
        return sigint_handler

    def generate_sigterm_handler(self):
        def sigterm_handler(signal, frame):
            print('Process {}, thread {}: SIGTERM received.'.format(os.getpid(), currentThread().name))
            self.messageboard.post('ExitThread', True)
            logger.info('SIGTERM received: exit.')
            sys.exit()
        return sigterm_handler

    def generate_sigusr1_handler(self):
        def sigusr1_handler(signal, frame):
            print('Process {}, thread {}: SIGUSR1 received.'.format(os.getpid(), currentThread().name))
            logger.info('SIGUSR1 received: ignore.')
        return sigusr1_handler

    def generate_sigusr2_handler(self):
        def sigusr2_handler(signal, frame):
            print('Process {}, thread {}: SIGUSR2 received.'.format(os.getpid(), currentThread().name))
            logger.info('SIGUSR2 received: ignore.')
        return sigusr2_handler

    def generate_sighup_handler(self):
        def sighup_handler(signal, frame):
            print('Process {}, thread {}: SIGHUP received.'.format(os.getpid(), currentThread().name))
            logger.info('SIGHUP received: ignore.')
        return sighup_handler
