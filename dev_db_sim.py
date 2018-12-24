#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = '电表模拟器'
__author__ = '123124100'
__mtime__ = '2018/12/17 15:03'
"""
import argparse
import logging
import os
import re
import subprocess
import sys
from cmd import Cmd

import APIs.common_APIs as common_APIs
from basic.log_tool import MyLogger
from protocol.db_devices import DB_Dev
from basic.cprint import cprint


class ArgHandle():
    def __init__(self):
        self.parser = self.build_option_parser("-" * 50)

    def build_option_parser(self, description):
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument(
            '-t', '--time-delay',
            dest='tt',
            action='store',
            default=0,
            type=int,
            help='time delay(ms) for msg send to server, default time is 500(ms)',
        )
        parser.add_argument(
            '-x', '--xx',
            dest='xx',
            action='store',
            default=0,
            type=int,
            help='special device ids',
        )
        parser.add_argument(
            '-p', '--server-port',
            dest='server_port',
            action='store',
            default=2012,
            type=int,
            help='Specify TCP server port, default is 2012',
        )
        parser.add_argument(
            '-i', '--server-IP',
            dest='server_IP',
            action='store',
            default='10.101.72.29',
            help='Specify TCP server IP address',
        )
        parser.add_argument(
            '--config',
            dest='config_file',
            action='store',
            default="cdz_db_conf",
            help='Specify device type',
        )
        parser.add_argument(
            '-c', '--count',
            dest='device_count',
            action='store',
            default=1,
            type=int,
            help='Specify how many devices to start, default is only 1',
        )
        parser.add_argument(
            '--self_IP',
            dest='self_IP',
            action='store',
            default='',
            help='Specify TCP client IP address',
        )
        return parser

    def get_args(self, attrname):
        return getattr(self.args, attrname)

    def check_args(self):
        global ipv4_list
        ipv4_list = []

        if arg_handle.get_args('self_IP'):
            ipv4s = common_APIs.get_local_ipv4()
            ip_prefix = '.'.join(arg_handle.get_args(
                'self_IP').split('.')[0:-1])
            ip_start = int(arg_handle.get_args('self_IP').split('.')[-1])
            ipv4_list = [ip for ip in ipv4s if re.search(
                r'%s' % (ip_prefix), ip) and int(ip.split('.')[-1]) >= ip_start]

            ipv4_list.sort()
            for ipv4 in ipv4_list:
                cprint.notice_p("find ip: " + ipv4)

    def run(self):
        self.args = self.parser.parse_args()
        cprint.notice_p("CMD line: " + str(self.args))
        self.check_args()


class MyCmd(Cmd):
    def __init__(self, logger, sim_objs=None):
        Cmd.__init__(self)
        self.prompt = "DB>>>"
        self.sim_objs = sim_objs
        self.LOG = logger
        self.ControlIndex = -1

    def help_log(self):
        cprint.notice_p(
            "change logger level: log {0:critical, 1:error, 2:warning, 3:info, 4:debug}")

    def do_log(self, arg, opts=None):
        level = {
            '0': logging.CRITICAL,
            '1': logging.ERROR,
            '2': logging.WARNING,
            '3': logging.INFO,
            '4': logging.DEBUG,
        }
        if int(arg) in range(5):
            for i in self.sim_objs:
                cprint.notice_p("=" * 40)
                self.sim_objs[i].LOG.set_level(level[arg])
        else:
            cprint.warn_p("unknow log level: %s!" % (arg))

    def help_st(self):
        cprint.notice_p("show state")

    def do_st(self, arg, opts=None):
        for i in range(len(self.sim_objs)):
            cprint.notice_p("-" * 20)
            self.sim_objs[i].status_show()

    def help_record(self):
        cprint.notice_p("send record:")

    def do_record(self, arg, opts=None):
        for i in self.sim_objs:
            i.send_msg(
                i.get_upload_record(int(arg)))

    def help_event(self):
        cprint.notice_p("send event")

    def do_event(self, arg, opts=None):
        for i in self.sim_objs:
            i.send_msg(
                i.get_upload_event(int(arg)))

    def help_set(self):
        cprint.notice_p("set state")

    def do_set(self, arg, opts=None):
        args = arg.split()
        for i in self.sim_objs:
            i.set_item(args[0], args[1])

    def default(self, arg, opts=None):
        try:
            subprocess.call(arg, shell=True)
        except:
            pass

    def emptyline(self):
        pass

    def help_exit(self):
        print("Will exit")

    def do_exit(self, arg, opts=None):
        cprint.notice_p("Exit CLI, good luck!")
        sys_cleanup()
        sys.exit()

    def help_ctl(self):
        cprint.notice_p("设置要操作的设备序列号")
        cprint.notice_p("ctl [index]")
        cprint.notice_p("index默认为-1，意为对所有设备执行同一操作")
        cprint.notice_p("使用show命令查看当前有的设备序列号和DEV ID以及当前操控的设备序列号")

    def do_ctl(self, arg, opt=None):
        args = arg.split()
        if len(args) != 1 and not args[0].isdigit():
            return self.help_ctl()
        val = int(args[0])
        if(val > len(sims)-1):
            return self.do_show()
        devid = "ALL"
        if(val != -1):
            devid = sims[val].get_item("_deviceID")
        self.ControlIndex = val
        cprint.notice_p("set ctl index to {0} (devid:{1})".format(self.ControlIndex,devid))

    def help_show(self):
        cprint.notice_p("获取当前所有ID和序列号")

    def do_show(self):
        if not sims:
            return cprint.notice_p("Not any devices")
        cprint.notice_p("Dev List")
        for index in range(len(sims)):
            cprint.notice_p("[index:{0}] [devid:{1}]".format(self.ControlIndex, sims[index].get_item("_deviceID")))


def sys_init():
    # sys log init
    global LOG
    LOG = MyLogger(os.path.abspath(sys.argv[0]).replace(
        'py', 'log'), clevel=logging.DEBUG, renable=False)
    global cprint
    cprint = cprint(os.path.abspath(sys.argv[0]).replace('py', 'log'))

    # cmd arg init
    global arg_handle
    arg_handle = ArgHandle()
    arg_handle.run()
    LOG.info("Let's go!!!")

def sys_cleanup():
    LOG.info("Goodbye!!!")

def delallLog(doit = True):
    if doit:
        files = os.listdir(os.getcwd())
        print(files)
        for file in files:
            if file.find(".log") != -1 and file.find("dev_db_sim") !=-1 :
                os.remove(file)
                print("file:%s is removed" % (file,))


import time
if __name__ == '__main__':
    delallLog()
    sys_init()
    global ipv4_list
    if arg_handle.get_args('device_count') > 1:
        log_level = logging.WARN
    else:
        log_level = logging.DEBUG

    sims = []
    for i in range(arg_handle.get_args('device_count')):
        dev_LOG = MyLogger('dev_db_sim_%d.log' % (
            i), clevel=log_level, flevel=log_level, fenable=True)

        if ipv4_list:
            id = i % len(ipv4_list)
            #self_addr = (ipv4_list[id], random.randint(
                #arg_handle.get_args('server_port'), 65535))
            self_addr = (ipv4_list[id], 0)
            dev_LOG.warn('self addr is: %s' % (str(self_addr)))
        else:
            self_addr = None

        sim = DB_Dev(logger=dev_LOG, config_file=arg_handle.get_args('config_file'),
                  server_addr=(arg_handle.get_args('server_IP'), arg_handle.get_args('server_port')),
                  N=arg_handle.get_args('xx') + i,tt=arg_handle.get_args('tt'), self_addr=self_addr)
        if self_addr:
            sim.set_item('_ip', self_addr[0])
        sim.run_forever()
        sims.append(sim)

    if True:
        # signal.signal(signal.SIGINT, lambda signal,
        #              frame: cprint.notice_p('Exit SYSTEM: exit'))
        my_cmd = MyCmd(logger=LOG, sim_objs=sims)
        my_cmd.cmdloop()

    else:
        sys_join()
        sys_cleanup()
        sys.exit()