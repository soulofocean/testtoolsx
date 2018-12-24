#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = '电表设备'
__author__ = '123124100'
__mtime__ = '2018/12/17 15:07'
"""
import threading
import random
import time
import json
import copy
import re
import datetime
import APIs.common_APIs as common_APIs
from collections import defaultdict
from importlib import import_module
from protocol.basic_devices import BaseSim
from protocol.db_ptotocol import DB_Protocol,MessageType

class CmdType:
    ReadAddr = 0x13
    ReadData = 0x11

class DB_Dev(BaseSim):

    def __init__(self, logger, config_file, server_addr, N=0, tt=None, self_addr=None):
        super(DB_Dev, self).__init__(logger)
        module_name = "protocol.config.%s" % config_file
        mod = import_module(module_name)
        self.sim_config = mod
        self.LOG = logger
        self.N = N
        self.tt = tt
        self.attribute_initialization()
        self.sdk_obj = DB_Protocol(logger=logger, addr=server_addr, self_addr=self_addr)
        self.sdk_obj.sim_obj = self
        self.need_stop = False

        # 心跳为60秒发送一次
        self.heartbeat_interval_s = 60

    def run_forever(self):
        thread_list = []
        thread_list.append([self.sdk_obj.schedule_loop])
        thread_list.append([self.sdk_obj.send_data_loop])
        thread_list.append([self.sdk_obj.recv_data_loop])
        thread_list.append([self.to_send_heartbeat])
        thread_ids = []
        for th in thread_list:
            thread_ids.append(threading.Thread(target=th[0], args=th[1:]))

        for th in thread_ids:
            th.setDaemon(True)
            th.start()

    def to_send_heartbeat(self):
        while self.need_stop == False:
            self.LOG.info("8.4.1 heartbeat")
            self.sdk_obj.add_send_data("H"+self._mac.replace(":",""))
            time.sleep(self.heartbeat_interval_s)

    def protocol_handler(self, msg, ack=False):
        Msg = MessageType(msg)
        self.LOG.debug(str(Msg.__dict__))
        if ack:
            self.update_msgst(Msg.cmd, 'rsp')
            self.LOG.info("Received Ack Msg:{0}".format(Msg.cmd))
            return None
        else:
            self.update_msgst(Msg.cmd, 'req')
        if Msg.cmd == CmdType.ReadAddr:
            Msg.set_addr(self._mac.replace(":",""))
        elif Msg.cmd == CmdType.ReadData:
            logmsg = Msg.set_datafield(self.get_data_dict())
            if logmsg != None:
                self.LOG.error(logmsg)
        else:
            self.LOG.warn('Unknow msg: %d!' % Msg.cmd)
            return None
        return Msg

    def get_data_dict(self):
        datadict = {}
        datadict["aI"] = self.get_item("ACurrent")
        datadict["bI"] = self.get_item("BCurrent")
        datadict["cI"] = self.get_item("CCurrent")
        datadict["tPower"] = round((datadict["aI"]+datadict["bI"]+datadict["cI"])*2200e-3)
        return datadict

    def attribute_initialization(self):
        attribute_params_dict = getattr(
            self.sim_config, "Attribute_initialization")
        for attribute_params, attribute_params_value in attribute_params_dict.items():
            self.add_item(attribute_params, attribute_params_value)

        self._mac = self.mac_list[self.N]
        self._deviceID = str(self.DeviceFacturer) + \
                         str(self.DeviceType) + self._mac.replace(":", '')
        self._encrypt_key = self._deviceID[-16:].encode('utf-8')
        self._qcodeFile = self._mac.replace(":", '') + ".png"

    # region 暂时不用的功能
    def get_msg_by_command(self, command):
        command = getattr(self.sim_config, command)
        command_str = str(command)
        command_str = re.sub(r'\'TIMENOW\'', '"%s"' % datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'), command_str)
        command_str = re.sub(r'\'randint1\'', '"%s"' %
                             random.randint(0, 1), command_str)
        return eval(command_str.replace("'##", "").replace("##'", ""))

    def get_send_msg(self, command):
        return self.get_msg_by_command(command)['send_msg']

    def get_rsp_msg(self, command):
        return self.get_msg_by_command(command)['rsp_msg']

    def set_items(self, command, msg):
        if ('set_item' in self.get_msg_by_command(command)):
            item_dict = self.get_msg_by_command(command)['set_item']
            for item, msg_param in item_dict.items():
                msg_param_list = msg_param.split('.')
                tmp_msg = msg[msg_param_list[0]]
                # if(isinstance(tmp_msg,list)):
                # tmp_msg = tmp_msg[0]
                # 处理Data对应的是List而不是Dictionary，如果返回的就是Dict，set_item配置文件就不需要加.0
                for i in msg_param_list[1:]:
                    if re.match(r'\d+', i):
                        i = int(i)
                    else:
                        pass
                    tmp_msg = tmp_msg[i]
                self.set_item(item, tmp_msg)
    def create_tasks(self):
        pass

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

    def get_upload_status(self):
        self.LOG.warn(common_APIs.chinese_show("设备状态上报"))
        return json.dumps(self.get_send_msg('COM_UPLOAD_DEV_STATUS'))

    def get_upload_record(self, record_type):
        self.LOG.warn(common_APIs.chinese_show("记录上传"))
        report_msg = self.get_send_msg('COM_UPLOAD_RECORD')
        report_msg["Data"][0]["RecordType"] = record_type
        report_msg["EventCode"] = record_type
        return json.dumps(report_msg)
    # endregion