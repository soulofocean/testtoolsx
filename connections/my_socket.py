#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ATS socket
   by Kobe Gong. 2017-9-29
"""

import datetime
import os
import random
import re
import select
import socket
import sys
import threading
import time

import APIs.common_APIs as common_APIs
from APIs.common_APIs import protocol_data_printB
from basic.log_tool import MyLogger

try:
    import queue as Queue
except:
    import Queue


BUFF_SIZE = 512


class MyServer:
    def __init__(self, logger, addr):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(False)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(addr)
        server.listen(10000)
        self.server = server

        self.LOG = logger

        # comm data
        self.clients = {}
        self.inputs = [server]
        self.conn_to_addr = {}

    def get_client_count(self):
        return len(self.clients)

    def run_forever(self, *arg):
        BUFF_SIZE = 1024
        timeout = 1

        try:
            while True:
                self.LOG.debug(
                    "Waiting for next event, now has active clients: %d" % (len(self.clients)))
                readable, writable, exceptional = select.select(
                    self.inputs, [], [], timeout)
                for conn in readable:
                    if conn == self.server:
                        try:
                            connection, client_address = self.server.accept()
                            connection.setblocking(0)
                            self.LOG.info(
                                "Get connection from: " + client_address[0])
                            self.clients[client_address] = {
                                'conn': connection,
                                'queue_in': Queue.Queue(),
                                'queue_out': Queue.Queue(),
                            }
                            self.inputs.append(connection)
                            self.conn_to_addr[connection] = client_address

                        except Exception as e:
                            self.LOG.error("Get connection %s falied![%s]" % (
                                client_address[0], e))
                            pass

                    else:
                        try:
                            data = conn.recv(BUFF_SIZE)
                            if data:
                                self.clients[self.conn_to_addr[conn]
                                             ]['queue_in'].put(data)

                                dmsg = b'\x48\x44\x58\x4d\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x30\x01\x00\x00\x00\x01\x00\x00\x00\x29\x00\x00\x8f\x20\x7b\x22\x52\x65\x73\x75\x6c\x74\x22\x3a\x30\x2c\x22\x43\x6f\x6d\x6d\x61\x6e\x64\x22\x3a\x22\x43\x4f\x4d\x5f\x44\x45\x56\x5f\x52\x45\x47\x49\x53\x54\x45\x52\x22\x7d'

                                self.clients[self.conn_to_addr[conn]
                                             ]['queue_out'].put(dmsg)

                                if isinstance(data, type(b'')):
                                    tmp_data = data
                                else:
                                    tmp_data = data.encode('utf-8')
                                    self.LOG.info(protocol_data_printB(
                                        tmp_data, title="Get data from " + self.conn_to_addr[conn][0] + ":"))
                            else:
                                # Interpret empty result as closed connection
                                self.LOG.error(
                                    self.conn_to_addr[conn][0] + ' closed!')
                                self.clients[self.conn_to_addr[conn]
                                             ]['conn'].close()
                                self.inputs.remove(conn)
                                del self.clients[self.conn_to_addr[conn]]
                                del self.conn_to_addr[conn]

                        except socket.error:
                            self.LOG.error("Get data from %s falied!" %
                                           (self.conn_to_addr[conn][0]))
                            self.clients[self.conn_to_addr[conn]
                                         ]['conn'].close()
                            self.inputs.remove(conn)
                            del self.clients[self.conn_to_addr[conn]]
                            del self.conn_to_addr[conn]

                if self.singlethread:
                    self.send_once()

        except KeyboardInterrupt:
            self.LOG.info(
                'KeyboardInterrupt, now to close all clinets and server!')
            for client in self.clients:
                self.clients[client]['conn'].close()
            self.server.close()

        except Exception as e:
            self.LOG.error(str(e))
            for client in self.clients:
                self.clients[client]['conn'].close()
            self.server.close()

        finally:
            self.LOG.info("socket server end!")
            sys.exit(0)

    def sendloop(self, *arg):
        while True:
            self.send_once()

    def send_once(self):
        try:
            for client in self.conn_to_addr:
                if self.clients[self.conn_to_addr[client]]['queue_out'].empty():
                    pass
                else:
                    data = self.clients[self.conn_to_addr[client]
                                        ]['queue_out'].get()
                    if isinstance(data, type(b'')):
                        tmp_data = data
                    else:
                        tmp_data = data.encode('utf-8')

                        self.LOG.yinfo(protocol_data_printB(
                            tmp_data, title="Send data to " + self.conn_to_addr[client][0] + ":"))
                    client.send(tmp_data)

        except Exception as e:
            self.LOG.error(
                self.conn_to_addr[client][0] + ' closed! [%s]' % (str(e)))
            self.clients[self.conn_to_addr[client]]['conn'].close()
            self.inputs.remove(client)
            del self.clients[self.conn_to_addr[client]]
            del self.conn_to_addr[client]


class MyClient:
    state_lock = threading.Lock()
    conn_lock = threading.Lock()
    bind_lock = threading.Lock()

    def __init__(self, logger, addr, self_addr=None):
        self.client = ''
        self.addr = addr
        self.LOG = logger
        self.self_addr = self_addr
        self.connected = False
        self.binded = False
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @common_APIs.need_add_lock(state_lock)
    def get_connected(self):
        return self.connected

    @common_APIs.need_add_lock(state_lock)
    def set_connected(self, value):
        self.connected = value

    @common_APIs.need_add_lock(bind_lock)
    def get_binded(self):
        return self.binded

    @common_APIs.need_add_lock(bind_lock)
    def set_binded(self, value):
        self.binded = value

    @common_APIs.need_add_lock(conn_lock)
    def connect(self):
        if self.self_addr and self.binded == False:
            # self.client.setblocking(False)
            #self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.client.bind(self.self_addr)
            self.set_binded(True)
            self.LOG.warn("Client bind self_addr %s" % (self.self_addr,))

        self.inputs = [self.client]
        try:
            code = self.client.connect_ex(self.addr)
            if code == 0:
                self.LOG.info("Connection setup suceess!")
                self.set_connected(True)
                return True
            elif code == 10065:#一般是由于绑定的网卡不可用或者木有连接WIFI
                self.LOG.error("Connect to server failed [code:%s] wait 10s..." % (code))
                if self.get_binded() and self.self_addr:
                    self.LOG.error("May be client bind interface is down binded addr:%s" % str(self.self_addr))
                time.sleep(10)
                return False
            elif code == 10038: #for shequ server disconnect socket 30s while not data transfer
                self.LOG.error("Connect to server failed [code:%s] reset socket after 1s..." % (code))
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if (self.get_binded()):  # 保证Socket绑定的网卡不变
                    self.set_binded(False)
                # sys.exit()
                return False
            else:#不知道神马情况，遇到再说，先睡一秒
                self.LOG.warn("Connect to server failed other code[code:%s]" % (code))
                time.sleep(1)
                return False
        except Exception as e:
            self.LOG.warn("Connect to server failed[%s], wait 1s..." % (e))
            # TODO, these case should handle the socket.error 9 only, add more code here later...
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # add by zx for add->del->add WIFI sim
            if (self.get_binded()):  # 保证Socket绑定的网卡不变
                self.set_binded(False)
            # sys.exit()
            return False

    def close(self):
        return self.client.close()

    def recv_once(self, timeout=None):
        try:
            if not self.get_connected():
                return
            data = ''
            readable, writable, exceptional = select.select(
                self.inputs, [], [], timeout)

            # When timeout reached , select return three empty lists
            if not (readable):
                pass
            else:
                data = self.client.recv(BUFF_SIZE)
                if data:
                    if isinstance(data, type(b'')):
                        tmp_data = data
                    else:
                        tmp_data = data.encode('utf-8')
                    self.LOG.debug(protocol_data_printB(
                        tmp_data, title="client get data:"))

                else:
                    self.LOG.error("Server maybe has closed!")
                    self.client.close()
                    self.inputs.remove(self.client)
                    self.set_connected(False)
            return data

        except socket.error:
            self.LOG.error("socket error, don't know why.")
            self.client.close()
            self.inputs.remove(self.client)
            self.set_connected(False)

    def send_once(self, data=None):
        try:
            if not self.get_connected():
                return
            if isinstance(data, type(b'')):
                tmp_data = data
            else:
                tmp_data = data.encode('utf-8')
            self.LOG.debug(protocol_data_printB(
                tmp_data, title="client send date:"))

            self.client.send(tmp_data)

        except Exception as e:
            self.LOG.error(
                "send data fail, Server maybe has closed![%s]" % (str(e)))
            self.client.close()
            if self.client in self.inputs:
                self.inputs.remove(self.client)
            self.set_connected(False)

if __name__ == "__main__":
    a="0123456789"
    print(a)
    pass
