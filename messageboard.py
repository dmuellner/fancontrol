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
from collections import OrderedDict
import weakref

from rwlock import RWLock, RWLockReaderPriority

class MessageBoard:
    def __init__(self):
        self.messages = {}
        self.messageLock = RWLock()
        self.subscriptions = {}
        self.subscriptionLock = RWLockReaderPriority()

    def post(self, heading, message):
        with self.messageLock.write_access:
            self.messages[heading] = message
        with self.subscriptionLock.read_access:
            if heading in self.subscriptions:
                for wr, callback in self.subscriptions[heading].iteritems():
                    instance = wr()
                    if instance is not None:
                        callback(instance, message)

    def query(self, heading):
        with self.messageLock.read_access:
            if heading in self.messages:
                return self.messages[heading]

    def subscribe(self, heading, instance, callback):
        with self.subscriptionLock.write_access:
            if not heading in self.subscriptions:
                self.subscriptions[heading] = OrderedDict()
            wr = weakref.ref(instance)
            assert wr not in self.subscriptions[heading]
            self.subscriptions[heading][wr] = callback

    def unsubscribe(self, heading, instance):
        with self.subscriptionLock.write_access:
            wr = weakref.ref(instance)
            if heading in self.subscriptions and wr in self.subscriptions[heading]:
                del self.subscriptions[heading][wr]
            if not self.subscriptions[heading]:
                del self.subscriptions[heading]

    def unsubscribeAll(self, instance):
        with self.subscriptionLock.write_access:
            wr = weakref.ref(instance)
            for heading in list(self.subscriptions):
                if wr in self.subscriptions[heading]:
                    del self.subscriptions[heading][wr]
                if not self.subscriptions[heading]:
                    del self.subscriptions[heading]

    def ask(self, heading, message):
        with self.subscriptionLock.read_access:
            if heading in self.subscriptions:
                for wr, callback in self.subscriptions[heading].iteritems():
                    instance = wr()
                    if instance is not None:
                        return callback(instance, message)

messageboard = MessageBoard()
