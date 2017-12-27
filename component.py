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
from threading import Lock, Thread
import logging

from messageboard import messageboard
from shutdown import shutdown

logger = logging.getLogger('fancontrol')

class ThreadManager:
    def __init__(self, messageboard):
        self.workerThreads = []
        self.messageboard = messageboard
        self.messageboard.subscribe('Shutdown', self, ThreadManager.onShutdown)

    def addThread(self, thread):
        self.workerThreads.append(thread)

    def allThreadsAlive(self):
        for thread in self.workerThreads:
            if not thread.is_alive():
                logger.error('The {} thread died.'.format(thread.name))
                return False
        return True

    def onShutdown(self, message):
        logger.info('Shutdown by user request')
        messageboard.post('ExitThread', True)
        for thread in self.workerThreads:
            thread.stop()
        print('System shutdown')
        shutdown()

threadManager = ThreadManager(messageboard)

allThreadsAlive = threadManager.allThreadsAlive

class Component:
    messageboard = messageboard

    def __init__(self, name):
        self.name = name
        self.lock = Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.messageboard.unsubscribeAll(self)
        self.messageboard.post('ExitThread', True)
        print('Exit {} worker.'.format(self.name))

class ComponentWithThread(Component):
    def __init__(self, name):
        Component.__init__(self, name)
        self.thread = Thread(None, self.__run, self.name)

    def __enter__(self):
        self.thread.start()
        threadManager.addThread(self)
        return Component.__enter__(self)

    def __exit__(self, exc_type, exc_value, traceback):
        Component.__exit__(self, exc_type, exc_value, traceback)
        self.stop()

    def __run(self):
        try:
            self.run()
        except:
            raise
        finally:
            print('Leave {} thread.'.format(self.name))

    def stop(self):
        print('Join {} thread.'.format(self.name))
        self.thread.join()
        print('The {} thread has joined.'.format(self.name))

    def is_alive(self):
        return self.thread.is_alive()
