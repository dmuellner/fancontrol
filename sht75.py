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


    This file is derived from the package “sht_sensor” by Mike Kazantsev:

    https://github.com/mk-fg/sht-sensor
'''
from __future__ import print_function
import logging
import math
import sys
import time
import RPi.GPIO as GPIO
from numpy import interp

from uptime import Uptime

logger = logging.getLogger('fancontrol')

DEBUG = False

class ShtFailure(Exception):
    def __init__(self, value):
        self.value = value
        sys.stderr.write('Sensor: ' + value + '\n')

    def __str__(self):
        return repr(self.value)
class ShtCommFailure(ShtFailure): pass
class ShtCRCCheckError(ShtFailure): pass

wait_short = 0.0000001 # 100ns, not sure if actually makes a difference

class ShtComms(object):
    def _crc8(self, cmd, v0, v1, _crc_table=[
            0x00, 0x31, 0x62, 0x53, 0xc4, 0xf5, 0xa6, 0x97, 0xb9, 0x88, 0xdb, 0xea,
            0x7d, 0x4c, 0x1f, 0x2e, 0x43, 0x72, 0x21, 0x10, 0x87, 0xb6, 0xe5, 0xd4,
            0xfa, 0xcb, 0x98, 0xa9, 0x3e, 0x0f, 0x5c, 0x6d, 0x86, 0xb7, 0xe4, 0xd5,
            0x42, 0x73, 0x20, 0x11, 0x3f, 0x0e, 0x5d, 0x6c, 0xfb, 0xca, 0x99, 0xa8,
            0xc5, 0xf4, 0xa7, 0x96, 0x01, 0x30, 0x63, 0x52, 0x7c, 0x4d, 0x1e, 0x2f,
            0xb8, 0x89, 0xda, 0xeb, 0x3d, 0x0c, 0x5f, 0x6e, 0xf9, 0xc8, 0x9b, 0xaa,
            0x84, 0xb5, 0xe6, 0xd7, 0x40, 0x71, 0x22, 0x13, 0x7e, 0x4f, 0x1c, 0x2d,
            0xba, 0x8b, 0xd8, 0xe9, 0xc7, 0xf6, 0xa5, 0x94, 0x03, 0x32, 0x61, 0x50,
            0xbb, 0x8a, 0xd9, 0xe8, 0x7f, 0x4e, 0x1d, 0x2c, 0x02, 0x33, 0x60, 0x51,
            0xc6, 0xf7, 0xa4, 0x95, 0xf8, 0xc9, 0x9a, 0xab, 0x3c, 0x0d, 0x5e, 0x6f,
            0x41, 0x70, 0x23, 0x12, 0x85, 0xb4, 0xe7, 0xd6, 0x7a, 0x4b, 0x18, 0x29,
            0xbe, 0x8f, 0xdc, 0xed, 0xc3, 0xf2, 0xa1, 0x90, 0x07, 0x36, 0x65, 0x54,
            0x39, 0x08, 0x5b, 0x6a, 0xfd, 0xcc, 0x9f, 0xae, 0x80, 0xb1, 0xe2, 0xd3,
            0x44, 0x75, 0x26, 0x17, 0xfc, 0xcd, 0x9e, 0xaf, 0x38, 0x09, 0x5a, 0x6b,
            0x45, 0x74, 0x27, 0x16, 0x81, 0xb0, 0xe3, 0xd2, 0xbf, 0x8e, 0xdd, 0xec,
            0x7b, 0x4a, 0x19, 0x28, 0x06, 0x37, 0x64, 0x55, 0xc2, 0xf3, 0xa0, 0x91,
            0x47, 0x76, 0x25, 0x14, 0x83, 0xb2, 0xe1, 0xd0, 0xfe, 0xcf, 0x9c, 0xad,
            0x3a, 0x0b, 0x58, 0x69, 0x04, 0x35, 0x66, 0x57, 0xc0, 0xf1, 0xa2, 0x93,
            0xbd, 0x8c, 0xdf, 0xee, 0x79, 0x48, 0x1b, 0x2a, 0xc1, 0xf0, 0xa3, 0x92,
            0x05, 0x34, 0x67, 0x56, 0x78, 0x49, 0x1a, 0x2b, 0xbc, 0x8d, 0xde, 0xef,
            0x82, 0xb3, 0xe0, 0xd1, 0x46, 0x77, 0x24, 0x15, 0x3b, 0x0a, 0x59, 0x68,
            0xff, 0xce, 0x9d, 0xac ]):
        # See: http://www.sensirion.com/nc/en/products/\
        #  humidity-temperature/download-center/?cid=884&did=124&sechash=5c5f91f6
        crc = _crc_table[cmd]
        crc = _crc_table[crc ^ v0]
        crc = _crc_table[crc ^ v1]
        # Reverse bit order
        # See: http://graphics.stanford.edu/~seander/bithacks.html#ReverseByteWith64BitsDiv
        return (crc * 0x0202020202 & 0x010884422010) % 1023

    def __init__(self, pin_sck, pin_data):
        self.pin_sck, self.pin_data = pin_sck, pin_data
        GPIO.setup((self.pin_sck, self.pin_data), GPIO.OUT)
        self.reset_connection()

    def __del__(self):
        GPIO.cleanup([self.pin_sck, self.pin_data])

    def _data_set(self, v):
        GPIO.setup(self.pin_data, GPIO.OUT)
        GPIO.output(self.pin_data, v)
        time.sleep(wait_short)

    def _data_get(self):
        return GPIO.input(self.pin_data)

    def _sck_tick(self, v):
        GPIO.output(self.pin_sck, v)
        time.sleep(wait_short)

    def reset_connection(self):
        tick, data = self._sck_tick, self._data_set
        data(1)
        for ii in xrange(9):
            tick(0)
            tick(1)
        try:
            self._send(0b00011100)
            self._wait()
            time.sleep(0.012)
        except ShtCommFailure as e:
            logger.error('Error, Connection reset failed, {}'.format(e))

    def _transmission_start(self):
        tick, data = self._sck_tick, self._data_set
        tick(0)
        data(1)
        tick(1)
        data(0)
        tick(0)
        tick(1)
        data(1)

    def _send(self, cmd):
        tick, data = self._sck_tick, self._data_set
        self._transmission_start()
        tick(0)
        for n in xrange(8):
            data(cmd & (1 << 7 - n))
            tick(1)
            tick(0)

        GPIO.setup(self.pin_data, GPIO.IN, GPIO.PUD_UP)
        tick(1)
        if self._data_get():
            raise ShtCommFailure('Command ACK failed on step 1.')
        tick(0)
        if not self._data_get():
            raise ShtCommFailure('Command ACK failed on step 2.')

    def _wait(self):
        GPIO.setup(self.pin_data, GPIO.IN, GPIO.PUD_UP)
        #try:
        #    channel = GPIO.wait_for_edge(self.pin_data, GPIO.FALLING, timeout=1000)
        #except RuntimeError as error:
        #    raise ShtCommFailure(*error.args)
        #if channel is None:
        #    raise ShtCommFailure('Wait timeout')

        # Busy wait... more reliable
        t0 = Uptime()
        while self._data_get():
            if Uptime() - t0 > 1:
                raise ShtCommFailure('Wait timeout')

    def _read_bits(self, bits, v=0):
        tick = self._sck_tick
        GPIO.setup(self.pin_data, GPIO.IN, GPIO.PUD_UP)
        for n in xrange(bits):
            tick(1)
            v = (v << 1) + self._data_get()
            tick(0)
        return v

    def _read_meas_16bit(self):
        # Most significant bits (upper nibble is always zeroes)
        v0 = self._read_bits(8)
        # Send ack
        tick, data = self._sck_tick, self._data_set
        data(1)
        data(0)
        tick(1)
        tick(0)
        # Least significant bits
        v1 = self._read_bits(8)
        return v0, v1

    def _get_meas_result(self, cmd):
        self._send(cmd)
        self._wait()
        v0, v1 = self._read_meas_16bit()
        # self._skip_crc()
        crc0, crc1 = self._crc8(cmd, v0, v1), self._read_crc()
        if crc0 != crc1:
            raise ShtCRCCheckError('Checksum error: {} != {}.'.
                                   format(crc0, crc1))
        return v0 * 256 | v1

    def _read_crc(self):
        self._data_set(1)
        self._data_set(0)
        self._sck_tick(1)
        self._sck_tick(0)
        return self._read_bits(8)

    def _skip_crc(self):
        self._data_set(1)
        self._sck_tick(1)
        self._sck_tick(0)

class Sht(ShtComms):
    # All table/chapter refs here point to:
    #  Sensirion_Humidity_SHT7x_Datasheet_V5.pdf

    voltage_default = 3.5

    class c:
        @staticmethod
        def compute_d1(voltage):
            # Table 8, C
            V = (2.5, 3.0, 3.5, 4.0, 5.0)
            d1_ = (-39.4, -39.6, -39.7, -39.8, -40.1)
            assert voltage >= V[0]
            assert voltage <= V[-1]
            return interp(voltage, V, d1_)
        d2 = 0.01 # Table 8, C/14b
        c1, c2, c3 = -2.0468, 0.0367, -1.5955e-6 # Table 6, 12b
        t1, t2 = 0.01, 0.00008 # Table 7, 12b
        tn = dict(water=243.12, ice=272.62) # Table 9
        m = dict(water=17.62, ice=22.46) # Table 9

    class cmd:
        t = 0b00000011
        rh = 0b00000101
        soft_reset = 0b00011110

    def __init__(self, pin_sck, pin_data, voltage=None, **sht_comms_kws):
        '''"voltage" setting is important,
           as it influences temperature conversion coefficients!!!
           Unless you're using SHT1x/SHT7x, please make
           sure all coefficients match your sensor's datasheet.'''
        self.voltage = voltage or self.voltage_default
        self.d1 = self.c.compute_d1(self.voltage)
        super(Sht, self).__init__(pin_sck, pin_data, **sht_comms_kws)

    def read_t(self):
        t_raw = self._get_meas_result(self.cmd.t)
        return t_raw * self.c.d2 + self.d1

    def read_rh(self, t=None):
        if t is None: t = self.read_t()
        return self._read_rh(t)

    def _read_rh(self, t):
        rh_raw = self._get_meas_result(self.cmd.rh)
        rh_linear = self.c.c1 + self.c.c2 * rh_raw + self.c.c3 * rh_raw**2 # ch 4.1
        return (t - 25.0) * (self.c.t1 + self.c.t2 * rh_raw) + rh_linear # ch 4.2

    def read_dew_point(self, t=None, rh=None):
        'With t and rh provided, does not access the hardware.'
        if t is None: t, rh = self.read_t(), None
        if rh is None: rh = self.read_rh(t)
        t_range = 'water' if t >= 0 else 'ice'
        tn, m = self.c.tn[t_range], self.c.m[t_range]
        return ( # ch 4.4
            tn * (math.log(rh / 100.0) + (m * t) / (tn + t))
            / (m - math.log(rh / 100.0) - m * t / (tn + t)) )

# Wrapper for the sensor functions

NaN = float('NaN')

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def __str__(self):
        return str(self.__dict__)

class Sensor:
    def __init__(self, clock, data):
        self.sht = Sht(clock, data, voltage = 3.3)
        self.rH = NaN
        self.T = NaN
        self.tau = NaN

    def read(self):
        try:
            self.T = self.sht.read_t();
            self.rH = self.sht.read_rh(self.T);
            self.tau = self.sht.read_dew_point(self.T, self.rH)
            self.Error = False
        except (ShtCommFailure, ShtCRCCheckError) as e:
            logger.warning('Error, {}'.format(e))
            self.sht.reset_connection()
            self.T, self.rH, self.tau = NaN, NaN, NaN
            self.Error = True

        return Bunch(rH = self.rH, T = self.T, tau = self.tau, Error = self.Error)
