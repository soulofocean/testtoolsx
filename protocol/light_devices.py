#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""devices sim
by Kobe Gong. 2018-1-15
"""

import copy
import datetime
import decimal
import json
import logging
import os
import random
import re
import shutil
import struct
import sys
import threading
import time
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from importlib import import_module

import APIs.common_APIs as common_APIs
from APIs.common_APIs import bit_clear, bit_get, bit_set, protocol_data_printB
from basic.log_tool import MyLogger
from basic.task import Task
from protocol.light_protocol import SDK
from protocol.basic_devices import BaseSim


class Dev(BaseSim):
    def __init__(self, logger, config_file, server_addr, N=0, tt=None, encrypt_flag=0, self_addr=None):
        super(Dev, self).__init__(logger)
        module_name = "protocol.config.%s" % config_file
        mod = import_module(module_name)
        self.sim_config = mod
        self.LOG = logger
        self.N = N
        self.tt = tt
        self.encrypt_flag = encrypt_flag
        self.attribute_initialization()
        self.sdk_obj = SDK(logger=logger, addr=server_addr,
                           encrypt_flag=self.encrypt_flag, self_addr=self_addr)
        self.sdk_obj.sim_obj = self
        self.sdk_obj.device_id = self._deviceID
        self.need_stop = False

        # state data:
        self.task_obj = Task('Washer-task', self.LOG)
        self.dev_register = False
        self.command_list = getattr(self.sim_config, "Command_list")
        #self.create_tasks()

        self.heartbeat_interval_s = 30
        self.reg_dev_relay_s = 1
        self.maintain_inv_s = 1
        self.report_inv_s = 0.01

    def run_forever(self):
        thread_list = []
        thread_list.append([self.sdk_obj.schedule_loop])
        thread_list.append([self.sdk_obj.send_data_loop])
        thread_list.append([self.sdk_obj.recv_data_loop])
        #thread_list.append([self.sdk_obj.heartbeat_loop])
        thread_list.append([self.to_send_heartbeat])
        #thread_list.append([self.task_obj.task_proc])
        thread_list.append([self.status_maintain])
        thread_list.append([self.status_report_monitor])
        thread_list.append([self.msg_dispatch])
        thread_ids = []
        for th in thread_list:
            thread_ids.append(threading.Thread(target=th[0], args=th[1:]))

        for th in thread_ids:
            th.setDaemon(True)
            th.start()
        time.sleep(self.reg_dev_relay_s)#wait the send_data_loop thread to start
        self.to_register_dev()

    def create_tasks(self):
        pass
        #self.task_obj.add_task(
            #'status maintain', self.status_maintain, 10000000, 10)

        #self.task_obj.add_task('monitor status report',
                               #self.status_report_monitor, 10000000, 1)

        #self.task_obj.add_task(
            #'dev register', self.to_register_dev, 1, 10)

        #self.task_obj.add_task(
            #'heartbeat', self.to_send_heartbeat, 1000000, 300)

    def msg_dispatch(self):
        msgs = []

        for msg in self.test_msgs["msgs"]:
            for i in range(self.test_msgs["msgs"][msg]):
                msgs.append(msg)
        random.shuffle(msgs)
        for msg in msgs:
            self.LOG.debug(msg)

        count = 0
        while self.need_stop == False and count < self.test_msgs["round"]:
            if self.dev_register == False:
                time.sleep(0.5)
                continue

            count += 1
            for msg in msgs:
                if self.tt:
                    time.sleep(self.tt / 1000.0)
                else:
                    time.sleep(self.test_msgs["interval"] / 1000.0)
                tmp_msg = msg.split('.')
                if tmp_msg[0] == 'COM_UPLOAD_DEV_STATUS':
                    self.send_msg(self.get_upload_status(), ack=b'\x00')
                elif tmp_msg[0] == 'COM_UPLOAD_RECORD':
                    self.send_msg(self.get_upload_record(
                        tmp_msg[-1]), ack=b'\x00')
                elif tmp_msg[0] == 'COM_UPLOAD_EVENT':
                    self.send_msg(self.get_upload_event(
                        tmp_msg[-1]), ack=b'\x00')
                else:
                    self.LOG.error("Unknow msg to dispatch: %s" % (msg))

    def status_maintain(self):
        while self.need_stop == False:
            for item in self.SPECIAL_ITEM:
                if "maintain" not in self.SPECIAL_ITEM[item]["use"]:
                    continue
                if self.__dict__[item] != self.SPECIAL_ITEM[item]["init_value"]:
                    tmp_item = '_current_time_' + item
                    if '_current_time_' + item in self.__dict__:
                        if self.__dict__[tmp_item] > 0:
                            self.set_item(tmp_item, self.__dict__[tmp_item] - 1)
                            if self.__dict__[tmp_item] <= 0:
                                self.set_item(
                                    tmp_item, self.SPECIAL_ITEM[item]["wait_time"])
                                self.set_item(
                                    item, self.SPECIAL_ITEM[item]["init_value"])
                        else:
                            self.set_item(
                                item, self.SPECIAL_ITEM[item]["init_value"])
                    else:
                        self.add_item('_current_time_' + item,
                                      self.SPECIAL_ITEM[item]["wait_time"])
            time.sleep(self.maintain_inv_s)

    def status_report_monitor(self):
        while self.need_stop == False:
            need_send_report = False
            if not hasattr(self, 'old_status'):
                self.old_status = defaultdict(lambda: {})
                for item in self.__dict__:
                    if item in self.SPECIAL_ITEM and "report" in self.SPECIAL_ITEM[item]["use"]:
                        self.LOG.yinfo("need check item: %s" % (item))
                        self.old_status[item] = copy.deepcopy(self.__dict__[item])

            for item in self.old_status:
                if self.old_status[item] != self.__dict__[item]:
                    need_send_report = True
                    self.old_status[item] = copy.deepcopy(self.__dict__[item])

            if need_send_report:
                self.send_msg(self.get_upload_status(), ack=b'\x00')
        time.sleep(self.report_inv_s)

    def to_register_dev(self):
        if self.dev_register:
            self.LOG.info(common_APIs.chinese_show("设备已经注册"))
        else:
            self.LOG.info(common_APIs.chinese_show("发送设备注册"))
            self.send_msg(json.dumps(
                self.get_send_msg('COM_DEV_REGISTER')), ack=b'\x00')

    def to_send_heartbeat(self):
        while self.need_stop == False:
            self.LOG.info("Thread to_send_heartbeat")
            if self.dev_register:
                self.send_msg(json.dumps(
                    self.get_send_msg('COM_HEARTBEAT')), ack=b'\x00')
            time.sleep(self.heartbeat_interval_s)

    def get_upload_status(self):
        self.LOG.warn(common_APIs.chinese_show("设备状态上报"))
        return json.dumps(self.get_send_msg('COM_UPLOAD_DEV_STATUS'))

    def get_upload_record(self, record_type):
        self.LOG.warn(common_APIs.chinese_show("记录上传"))
        report_msg = self.get_send_msg('COM_UPLOAD_RECORD')
        report_msg["Data"][0]["RecordType"] = record_type
        report_msg["EventCode"] = record_type
        return json.dumps(report_msg)

    def get_upload_event(self, event_type):
        self.LOG.warn(common_APIs.chinese_show("事件上报"))
        report_msg = self.get_send_msg('COM_UPLOAD_EVENT')
        report_msg["Data"][0]["EventType"] = event_type
        report_msg["EventCode"] = event_type
        return json.dumps(report_msg)

    def protocol_handler(self, msg, ack=False):
        if ack:
            self.update_msgst(msg['Command'], 'rsp')
            if msg['Command'] == 'COM_DEV_REGISTER':
                if msg['Result'] == 0:
                    self.dev_register = True
                    # decrypt
                    if self.encrypt_flag:
                        self.add_item('_encrypt_key', msg['Data'][0]['aeskey'])
                    self.LOG.warn(common_APIs.chinese_show("设备已经注册"))
                    return None
                else:
                    self.dev_register = False
                    self.LOG.warn(common_APIs.chinese_show("设备注册失败"))
                    return None
            else:
                return None
        else:
            self.update_msgst(msg['Command'], 'req')

        if msg['Command'] == 'COM_HEARTBEAT':
            pass
        elif msg['Command'] in self.command_list:
            self.set_items(msg['Command'], msg)
            rsp_msg = self.get_rsp_msg(msg['Command'])
            self.update_msgst(msg['Command'], 'rsp')
            return json.dumps(rsp_msg)
        else:
            self.LOG.warn('Unknow msg: %s!' % (msg['Command']))
            return None

    def get_msg_by_command(self, command):
        command = getattr(self.sim_config, command)
        command_str = str(command)
        command_str = re.sub(r'\'TIMENOW\'', '"%s"' % datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'), command_str)
        command_str = re.sub(r'\'randint1\'', '"%s"' %
                             random.randint(0, 1), command_str)
        return eval(command_str.replace("'##", "").replace("##'", ""))

    def get_record_list(self):
        return getattr(self.sim_config, "defined_record")

    def get_event_list(self):
        return getattr(self.sim_config, "defined_event")

    def get_send_msg(self, command):
        return self.get_msg_by_command(command)['send_msg']

    def get_rsp_msg(self, command):
        return self.get_msg_by_command(command)['rsp_msg']

    def set_items(self, command, msg):
        item_dict = self.get_msg_by_command(command)['set_item']
        for item, msg_param in item_dict.items():
            msg_param_list = msg_param.split('.')
            tmp_msg = msg[msg_param_list[0]]
            for i in msg_param_list[1:]:
                if re.match(r'\d+', i):
                    i = int(i)
                else:
                    pass
                tmp_msg = tmp_msg[i]
            self.set_item(item, tmp_msg)

    def attribute_initialization(self):
        attribute_params_dict = getattr(
            self.sim_config, "Attribute_initialization")
        for attribute_params, attribute_params_value in attribute_params_dict.items():
            self.add_item(attribute_params, attribute_params_value)

        self._mac = self.mac_list[self.N]
        #"_deviceID": "1005200958FCDBDA5380",
        #"_subDeviceID": "301058FCDBDA53800001",
        self._deviceID = str(self.DeviceFacturer) + \
            str(self.DeviceType) + self._mac.replace(":", '')
        self._encrypt_key = self._deviceID[-16:].encode('utf-8')
        #self._decrypt_key = self._deviceID[-16:].encode('utf-8')
        self._subDeviceID = str(self.subDeviceType) + \
            self._mac.replace(":", '') + "%04d" % (self.N + 1)


if __name__ == '__main__':

    pass
