#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'ZengXu'
__mtime__ = '2018-10-9'
"""
from abc import ABCMeta, abstractmethod
from collections import defaultdict
import threading
import json
import copy

class BaseSim():
    __metaclass__ = ABCMeta

    def __init__(self, logger):
        self.LOG = logger
        self.sdk_obj = None

        # state data:
        self.msgst = defaultdict(lambda: {})
        self.task_obj = None

    def update_msgst(self, command, direct):
        if command in self.msgst:
            pass
        else:
            self.msgst[command] = {
                'req': 0,
                'rsp': 0,
            }

        self.msgst[command][direct] += 1

    def set_item(self, item, value):
        if item in self.__dict__:
            self.__dict__[item] = value
        else:
            self.LOG.error("Unknow item: %s" % (item))

    def try_set_item(self, item, value):
        '''尝试设置item为value,如果item不存在或者value无变化不会设置并返回FALSE，否则进行设置并返回TRUE'''
        if item in self.__dict__:
            if(self.__dict__[item]!=value):
                self.__dict__[item] = value
                return True
            return False
        else:
            self.LOG.error("Unknow item: %s" % (item))
            return False

    def get_item(self, item):
        if item in self.__dict__:
            return self.__dict__[item]
        else:
            self.LOG.error("Unknow item: %s" % (item))

    def add_item(self, item, value):
        try:
            setattr(self, item, value)
        except:
            self.LOG.error("add item fail: %s" % (item))

    def status_show(self):
        for item in sorted(self.__dict__):
            if item.startswith('_'):
                self.LOG.warn("%s: %s" % (item, str(self.__dict__[item])))

        self.LOG.warn('~' * 10)
        for msg_code in self.msgst:
            self.LOG.warn("%s:" % (msg_code))
            self.LOG.warn("\t\t\treq: %d" % (self.msgst[msg_code]['req']))
            self.LOG.warn("\t\t\trsp: %d" % (self.msgst[msg_code]['rsp']))
            self.LOG.warn("-" * 30)

    def send_msg(self, msg, ack=b'\x01'):
        self.update_msgst(json.loads(msg)['Command'], 'req')
        return self.sdk_obj.add_send_data(self.sdk_obj.msg_build(msg, ack))

    @abstractmethod
    def protocol_handler(self, msg, ack=False):
        pass

    def stop(self):
        self.need_stop = True
        self.sdk_obj.stop()
        if self.task_obj:
            self.task_obj.stop()
        self.LOG.warn('Thread %s stoped!' % (__name__))

    def run_forever(self):
        thread_list = []
        thread_list.append([self.sdk_obj.schedule_loop])
        thread_list.append([self.sdk_obj.send_data_loop])
        thread_list.append([self.sdk_obj.recv_data_loop])
        thread_list.append([self.sdk_obj.heartbeat_loop])
        thread_list.append([self.task_obj.task_proc])
        thread_ids = []
        for th in thread_list:
            thread_ids.append(threading.Thread(target=th[0], args=th[1:]))

        for th in thread_ids:
            th.setDaemon(True)
            th.start()

    def status_maintain(self):
        pass

    def status_report_monitor(self):
        need_send_report = False
        if not hasattr(self, 'old_status'):
            self.old_status = defaultdict(lambda: {})
            for item in self.__dict__:
                if item.startswith('_'):
                    self.LOG.yinfo("need check item: %s" % (item))
                    self.old_status[item] = copy.deepcopy(self.__dict__[item])

        for item in self.old_status:
            if self.old_status[item] != self.__dict__[item]:
                need_send_report = True
                self.old_status[item] = copy.deepcopy(self.__dict__[item])

        if need_send_report:
            self.send_msg(self.get_event_report(), ack=b'\x00')