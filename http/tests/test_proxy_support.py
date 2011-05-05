# Copyright 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import unittest

import http

# relative import to ease embedding the library
import util


class ProxyHttpTest(util.HttpTestBase, unittest.TestCase):

    def _run_simple_test(self, host, server_data, expected_req, expected_data):
        con = http.HTTPConnection(host)
        con._connect()
        con.sock.data = server_data
        con.request('GET', '/')

        self.assertEqual(expected_req, con.sock.sent)
        self.assertEqual(expected_data, con.getresponse().read())

    def testSimpleRequest(self):
        con = http.HTTPConnection('1.2.3.4:80',
                                  proxy_hostport=('magicproxy', 4242))
        con._connect()
        con.sock.data = ['HTTP/1.1 200 OK\r\n',
                         'Server: BogusServer 1.0\r\n',
                         'MultiHeader: Value\r\n'
                         'MultiHeader: Other Value\r\n'
                         'MultiHeader: One More!\r\n'
                         'Content-Length: 10\r\n',
                         '\r\n'
                         '1234567890'
                         ]
        con.request('GET', '/')

        expected_req = ('GET / HTTP/1.1\r\n'
                        'Host: 1.2.3.4\r\n'
                        'accept-encoding: identity\r\n\r\n')

        self.assertEqual(('127.0.0.42', 4242), con.sock.sa)
        self.assertEqual(expected_req, con.sock.sent)
        resp = con.getresponse()
        self.assertEqual('1234567890', resp.read())
        self.assertEqual(['Value', 'Other Value', 'One More!'],
                         resp.headers.getheaders('multiheader'))
        self.assertEqual(['BogusServer 1.0'],
                         resp.headers.getheaders('server'))

    def testSSLRequest(self):
        con = http.HTTPConnection('1.2.3.4:443',
                                  proxy_hostport=('magicproxy', 4242))
        con._connect()
        con.sock.data = ['HTTP/1.1 100 Continue\r\n\r\n',
                         'HTTP/1.1 200 OK\r\n',
                         'Server: BogusServer 1.0\r\n',
                         'Content-Length: 10\r\n',
                         '\r\n'
                         '1234567890'
                         ]
        con.request('GET', '/')

        expected_req = ('CONNECT 1.2.3.4:443 HTTP/1.0\r\n\r\n'
                        'GET / HTTP/1.1\r\n'
                        'Host: 1.2.3.4\r\n'
                        'accept-encoding: identity\r\n\r\n')

        self.assertEqual(('127.0.0.42', 4242), con.sock.sa)
        self.assertStringEqual(expected_req, con.sock.sent)
        resp = con.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual('1234567890', resp.read())
        self.assertEqual(['BogusServer 1.0'],
                         resp.headers.getheaders('server'))

    def testSSLProxyFailure(self):
        con = http.HTTPConnection('1.2.3.4:443',
                                  proxy_hostport=('magicproxy', 4242))
        con._connect()
        con.sock.data = ['HTTP/1.1 407 Proxy Authentication Required\r\n\r\n',
                         ]
        con.request('GET', '/')

        expected_req = ('CONNECT 1.2.3.4:443 HTTP/1.0\r\n\r\n'
                        'GET / HTTP/1.1\r\n'
                        'Host: 1.2.3.4\r\n'
                        'accept-encoding: identity\r\n\r\n')

        self.assertEqual(('127.0.0.42', 4242), con.sock.sa)
        self.assertStringEqual(expected_req, con.sock.sent)
        resp = con.getresponse()
        self.assertEqual(resp.status, 407)
