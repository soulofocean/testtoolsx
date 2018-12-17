#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'ZengXu'
__mtime__ = '2018-10-9'
"""
import connections.my_socket as my_socket
import APIs.common_APIs as common_APIs
import struct
import json
from protocol.protocol_process import communication_base
try:
    import queue as Queue
except:
    import Queue

class DB_Protocol(communication_base):
    def __init__(self, logger, addr, self_addr=None):
        self.queue_in = Queue.Queue()
        self.queue_out = Queue.Queue()
        super(DB_Protocol, self).__init__(logger, self.queue_in, self.queue_out,
                                          left_data=b'', min_length=32)
        self.addr = addr
        self.name = 'Device controler'
        self.connection = my_socket.MyClient(logger, addr, self_addr)
        self.state = 'close'
        self.sim_obj = None
        #PHL = pkt head length for short
        self.PHL = 32
        self.version = b'\x03'
        self.default_ecode_type = b'\x01'
        #First four bytes for short
        # \x01means data is in protobuf type , json type encode is unkown at present, so there is a todo keng
        # may be here should be \x36\x20\x03\x02?
        self.F4B = b'\x36\x20' + self.version + self.default_ecode_type

    def msg_build(self, data, message_type, extern_msg_type=bytes(1), ctrl_addr=bytes(16), encode_type=b'\x01'):
        self.LOG.yinfo("send msg: " + self.convert_to_dictstr(data))
        r1 = b'\x00'
        r2 = b'\x00'
        msgtype = common_APIs.bit_set(message_type,7)
        if 'message_type' in data:
            msgtype = data['message_type']

        ext_msgtype = extern_msg_type
        if 'ext_msgtype' in data:
            ext_msgtype = data['ext_msgtype']

        ctrladdr = ctrl_addr
        if 'ctrladdr' in data:
            ctrladdr = data['ctrladdr']

        if isinstance(data['data'], type(b'')):
            pass
        else:
            data = data['data'].encode('utf-8')
        msg_head = self.F4B[0:3] + encode_type
        msg_data = data
        msg_length = len(msg_data)
        if 'data' in data:
            msg_length = self.get_msg_length(data['data'])
            msg_data = data['data']
        msg = msg_head + msg_length + msgtype + ext_msgtype + r1 + ctrladdr + r2 + msg_data
        return msg

    def protocol_data_washer(self, data):
        data_list = []
        left_data = b''

        while data[0:2] != self.F4B[0:2] and len(data) >= self.min_length:
            self.LOG.warn('give up dirty data: %02x' % ord(str(data[0])))
            data = data[1:]

        if len(data) < self.min_length:
            left_data = data
        else:
            #todo there should be ==Self.F4B[0:3]+\x01 or elf.F4B[0:3]+\x0?
            if data[0:4] == self.F4B[0:3] + self.default_ecode_type:
                length = struct.unpack('>I', data[4:8])[0]
                if length <= len(data[self.PHL:]):
                    data_list.append(data[0:self.PHL + length])
                    data = data[self.PHL + length:]
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
                        self.LOG.warn('give up dirty data: %02x' % ord(chr(s)))
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
        if msg[0:3] == self.F4B[0:3]:
            #todo other condiction may be add here later
            if True :
                #\x01 protobuf \x0? Json
                encode_type = msg[3]
                data_length = struct.unpack('>I', msg[4:4+4])[0]
                message_type = msg[8]
                if message_type >= 128:
                    ack = True
                extern_msg_type = msg[9]
                reserved_1 = msg[10:10+2]
                ctrl_addr = msg[12:12+16]
                reserved_2 = msg[28:28+4]
                ori_data = msg[32:32+data_length]
                # \x01 Protobuf \x0? Json
                if encode_type == b'\x01':
                    #use Protobuf to decode
                    data = ori_data.decode('utf-8')
                else:
                    data = json.loads(ori_data.decode('utf-8'))
                self.LOG.info("recv msg: " + self.convert_to_dictstr(data))
                rsp_msg = self.sim_obj.protocol_handler(data,ack)
                if rsp_msg:
                    final_rsp_msg = self.msg_build(rsp_msg, message_type, extern_msg_type, ctrl_addr)
                else:
                    final_rsp_msg = 'No_need_send'
                return final_rsp_msg

            else:
                self.LOG.error('Unknow msg: %s' % (msg))
                return "No_need_send"

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

    if __name__ == '__main__':
        m = b'\x70'
        m2 = b'\x80'
        if m2 in m :
            print("IN")
        else:
            print("NOT IN")
        #n = bytearray(m)[0]+ bytearray(m2)[0]
        #print(n.to_bytes(1,byteorder="big"))
        pass