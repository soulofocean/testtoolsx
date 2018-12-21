#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'ZengXu'
__mtime__ = '2018-10-9'
"""
import binascii
import datetime
import json
import logging
import os
import random
import re
import struct
import sys
import threading
import time
from abc import ABCMeta, abstractmethod
from collections import defaultdict

import APIs.common_APIs as common_APIs
import connections.my_socket as my_socket
from APIs.common_APIs import crc, crc16, protocol_data_printB
from APIs.security import AES_CBC_decrypt, AES_CBC_encrypt
from protocol.protocol_process import communication_base
import struct
import json
from protocol.protocol_process import communication_base
try:
    import queue as Queue
except:
    import Queue


class MessageType(object):
    '''处理电表协议的信息'''
    def __init__(self,msg:bytes):
        self.addrlen = 6
        self.prefix_head:bytes = msg[0:0+4]
        self.frame_head:bytes = msg[4:4+1]
        self.addr:bytes = msg[5:5+self.addrlen]
        #msg[11] is frame head, skip
        self.cmd:int = msg[12]
        self.data_field_len:int = msg[13]
        self.data = b''
        if self.data_field_len >= 4:
            self.data = msg[14:14+self.data_field_len]
            self.data = self.__process33h('-')
        self.cs:int = msg[-2]
        self.tail:bytes = msg[-1:]
    def __process33h(self, op='+'):
        new_data = bytearray(self.data)
        num = 0x33
        if self.data :
            for i in range(0,len(self.data)):
                if op=='+':
                    new_data[i] = self.data[i] + num
                elif op =='-':
                    new_data[i] = self.data[i] - num
                else:
                    raise "invalid option:{}".format(op)
        return new_data
    def __calcs(self):
        '''计算校验码'''
        msg = bytearray()
        msg.extend(self.frame_head)
        msg.extend(self.addr)
        msg.extend(self.frame_head)
        msg.extend(self.cmd.to_bytes(1,'big'))
        msg.extend(self.data_field_len.to_bytes(1,'big'))
        msg.extend(self.data)
        #msg2 = self.frame_head + self.frame_head +self.addr+self.cmd+self.data_field_len+self.data
        r = 0
        for b in msg:
            r += int(b)
            r &= 0xFF
        return r
    def __processCmd(self):
        return self.cmd^0x80

    def set_addr(self,newaddr:str):
        realaddr = newaddr
        if len(newaddr) > self.addrlen*2:
            realaddr = newaddr[:self.addrlen*2]
        elif len(newaddr)< self.addrlen*2:
            realaddr = "0"*(self.addrlen*2-len(newaddr)) + newaddr
        addr = bytearray()
        for i in range(0, len(realaddr), 2):
            addr.append(int(realaddr[i:i + 2], 16))
        self.addr = bytes(addr)

    def set_datafield(self,dataDict:dict):
        datalen = 3
        if self.data_field_len >=4:
            if self.data[0:4] == b'\x00\x00\x03\x02':
                key = 'tPower'
            elif self.data[0:4] == b'\x00\x01\x02\x02':
                key = 'aI'
            elif self.data[0:4] == b'\x00\x02\x02\x02':
                key = 'bI'
            elif self.data[0:4] == b'\x00\x03\x02\x02':
                key = 'cI'
            else:
                return "Not Suport DataField:{}".format(self.getBinStr(self.data[0:4]))
            if key not in dataDict:
                return "key:{} not in dict".format(key)
            dataFormate = "%0{}d".format(datalen*2)
            dataStr = dataFormate % round(dataDict[key])
            for i in range(len(dataStr)-2,-2, -2):
                self.data.append(int(dataStr[i:i + 2], 16))
            self.data_field_len = datalen  + self.data_field_len
            return None
        return "Field len is {}".format(self.data_field_len)

    def buildRspMessage(self):
        msg = bytearray()
        msg.extend(self.prefix_head)
        msg.extend(self.frame_head)
        msg.extend(self.addr)
        msg.extend(self.frame_head)
        self.cmd = self.__processCmd()
        msg.extend(self.cmd.to_bytes(1,'big'))
        msg.extend(self.data_field_len.to_bytes(1,'big'))
        self.data = self.__process33h('+')
        msg.extend(self.data)
        self.cs = self.__calcs()
        msg.extend(self.cs.to_bytes(1,'big'))
        msg.extend(self.tail)
        #msg2 = self.prefix_head + self.frame_head+ self.addr+self.frame_head+self.cmd+self.data_field_len+self.data+self.cs+self.tail
        return bytes(msg)

    def getBinStr(self, data):
        msg = ''
        if data:
            for d in data:
                msg += "\\x{:02x}".format(d)
        #print(msg)


class DB_Protocol(communication_base):
    def __init__(self, logger, addr, encrypt_flag=0, self_addr=None):
        self.queue_in = Queue.Queue()
        self.queue_out = Queue.Queue()
        super(DB_Protocol, self).__init__(logger, self.queue_in, self.queue_out,
                                  left_data=b'', min_length=16)
        self.addr = addr
        self.encrypt_flag = encrypt_flag
        self.name = 'Device controler'
        self.connection = my_socket.MyClient(logger, addr, self_addr)
        self.state = 'close'
        self.sim_obj = None

        # status data:
        # 4bytes
        self.version = b'HDXM'
        # 20bytes
        self.device_id = b'\x31\x30\x30\x34\x32\x30\x31\x36\x35\x38\x46\x43\x44\x42\x44\x38\x33\x34\x31\x45'
        # 4bytes
        self.pkg_number = b'\x00\x00\x00\x01'

        #region 电表报文头相关变量
        self.prefixHead = b'\xFE\xFE\xFE\xFE'
        #endregion

    def msg_build(self, data, ack=b'\x01'):
        self.LOG.yinfo("send msg: " + self.convert_to_dictstr(data))
        # need encrypt
        if self.encrypt_flag:
            data = AES_CBC_encrypt(self.sim_obj._encrypt_key, data)
        if isinstance(data, type(b'')):
            pass
        else:
            data = data.encode('utf-8')
        if ack == b'\x00':
            src_id = self.device_id
            dst_id = b'\x30' * 20
            self.add_pkg_number()
        else:
            src_id = self.device_id
            dst_id = b'\x30' * 20

        if isinstance(src_id, type(b'')):
            pass
        else:
            src_id = src_id.encode('utf-8')
        msg_head = self.version + src_id + dst_id + ack + self.pkg_number
        msg_length = self.get_msg_length(data)
        msg_crc16 = crc16(data)
        msg = msg_head + msg_length + b'\x00\x00' + msg_crc16 + data
        return msg

    def protocol_data_washer(self, data):
        data_list = []
        left_data = b''

        while data[0:1] != self.prefixHead[0:1] and len(data) >= self.min_length:
            #self.LOG.warn('give up dirty data: %02x' % ord(str(data[0])))
            self.LOG.warn('give up dirty data: 0x%02x' % data[0])
            data = data[1:]

        if len(data) < self.min_length:
            left_data = data
        else:
            if data[0:4] == self.prefixHead:
                data_filed_len = ord(data[13:14])
                length = data_filed_len + self.min_length #struct.unpack('>I', data[49:53])[0]
                if length <= len(data):
                    data_list.append(data[0:length])
                    data = data[length:]
                    if data:
                        data_list_tmp, left_data_tmp = self.protocol_data_washer(
                            data)
                        data_list += data_list_tmp
                        left_data += left_data_tmp
                    else:
                        #self.LOG.error('data field is empty!')
                        pass
                elif length >= 1 and length < 10000:
                    left_data = data
                else:
                    for s in data[:4]:
                        self.LOG.warn('give up dirty data: 0x%02x' % s)
                    left_data = data[4:]
            else:
                pass

        return data_list, left_data

    def add_pkg_number(self):
        pkg_number = struct.unpack('>I', self.pkg_number)[0]
        pkg_number += 1
        self.pkg_number = struct.pack('>I', pkg_number)

    def get_pkg_number(self, data):
        return struct.unpack('>I', data)[0]

    def set_pkg_number(self, data):
        self.pkg_number = data

    def get_msg_length(self, msg):
        return struct.pack('>I', len(msg))

    def protocol_handler(self, msg):
        ack = False
        if msg[0:4] == self.prefixHead:
            #目前貌似木有ACK
            ack = False
            self.LOG.info("recv msg: " + common_APIs.protocol_data_printB(msg))
            rsp_msg:MessageType = self.sim_obj.protocol_handler(msg, ack)
            if rsp_msg:
                #final_rsp_msg = self.msg_build(rsp_msg)
                final_rsp_msg = rsp_msg.buildRspMessage()
            else:
                final_rsp_msg = 'No_need_send'
            return final_rsp_msg
            '''if True or msg[4 + 20:4 + 20 + 20] == self.device_id or msg[4 + 20:4 + 20 + 20] == self.device_id.encode('utf-8'):
                if msg[44:45] != b'\x00':
                    # self.LOG.info("Get ack!")
                    ack = True
                self.set_pkg_number(msg[45:49])
                data_length = struct.unpack('>I', msg[49:53])[0]
                crc16 = struct.unpack('>H', msg[55:57])
                # need decrypt
                if self.encrypt_flag:
                    data = json.loads(AES_CBC_decrypt(self.sim_obj._encrypt_key,
                                                      msg[57:57 + data_length]).decode('utf-8'))
                else:
                    data = json.loads(msg[57:57 + data_length].decode('utf-8'))
                self.LOG.info("recv msg: " + self.convert_to_dictstr(data))
                rsp_msg = self.sim_obj.protocol_handler(data, ack)
                if rsp_msg:
                    final_rsp_msg = self.msg_build(rsp_msg)
                else:
                    final_rsp_msg = 'No_need_send'
                return final_rsp_msg

            else:
                self.LOG.error('Unknow msg: %s' % (msg))
                return "No_need_send"'''
        else:
            self.LOG.warn('Unknow msg: %s!' % (msg))
            return "No_need_send"

    def connection_setup(self):
        self.LOG.warn('Try to connect %s...' % str(self.addr))
        if self.connection.get_connected():
            self.LOG.info('Connection already setup!')
            return True
        elif self.connection.connect():
            self.set_connection_state(True)
            self.LOG.info('Connection setup success!')
            return True
        else:
            self.LOG.warn("Can't connect %s!" % str(self.addr))
            self.LOG.error('Setup connection failed!')
            return False

    def connection_close(self):
        if self.connection.close():
            self.connection.set_connected(False)
            self.set_connection_state(False)
        else:
            self.LOG.error('Close connection failed!')

    def send_data(self, data):
        return self.connection.send_once(data)

    def recv_data(self):
        return self.connection.recv_once()
import time
if __name__ == '__main__':
    start = datetime.datetime.now()
    #data = b'\xfe\xfe\xfe\xfe\x68\xaa\xaa\xaa\xaa\xaa\xaa\x68\x13\x00\xdf\x16'
    data = b'\xfe\xfe\xfe\xfe\x68\xaa\xaa\xaa\xaa\xaa\xaa\x68\x13\x05\x45\x67\x89\xab\xc3\x87\x16'
    m = MessageType(data)
    #testbin = b'\x45\x67\x89\xab\xc3'
    #newdata = m._MessageType__process33h("-")
    m.set_addr("598888881000")
    newdata = m.buildRspMessage()
    m.getBinStr(data)
    m.getBinStr(newdata)
    print(len(newdata))
    time.sleep(0)
    print((datetime.datetime.now()-start).total_seconds())
    #print(common_APIs.protocol_data_printB(bytes(newdata)))