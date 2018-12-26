#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'ZengXu'
__mtime__ = '2018-10-9'
"""
import threading
import random
import time
import json
import copy
import re
import datetime
import os
import APIs.common_APIs as common_APIs
from collections import defaultdict
from importlib import import_module
from protocol.basic_devices import BaseSim
from basic.task import Task
from protocol.light_protocol import SDK


class ReportType:
    '''上报状态'''
    PERIOD_PERIOD = 10000
    SWITCH3_CHANGE = 10001
    SWITCH7_CHANGE = 10002
    LOCK3_CHANGE = 10003
    LOCK7_CHANGE = 10004
    URGENT_CHANGE = 10005
    STATUS_CHANGE = 10006
    CHARGE_RECORD_UPLOAD = 10007

class SwitchStatus:
    '''开始充电结果上报中的开关状态'''
    Both3And7 = 1
    # 37都没插
    Neither3Nor7 = 2
    # 只有7插但是没插稳
    Only7_Unstable = 3
    # 只有3插着
    Only3 = 4
    # 只有7插着
    Only7 = 5
    # 对于7来说，车没有响应
    Only7_CarNoResponse = 6

class DeviceStatus:
    '''设备状态'''
    OVER_VOLTAGE = 0x01
    UNDER_VOLTAGE = 0x02
    OVER_CURRENT = 0x04
    UNDER_TEMP = 0x08
    ELECTRIC_LEAKAGE = 0x10

class ReasonType:
    UrgentStop = 1
    DevFault = 2
    GunStatusChange = 3

class CDZ_Dev(BaseSim):
    type_lock = threading.Lock()
    charging_lock = threading.Lock()

    def __init__(self, logger, config_file, server_addr, N=0, tt=None, encrypt_flag=0, self_addr=None):
        super(CDZ_Dev, self).__init__(logger)
        module_name = "protocol.config.%s" % config_file
        mod = import_module(module_name)
        self.sim_config = mod
        self.LOG = logger
        self.N = N
        self.tt = tt
        self.encrypt_flag = encrypt_flag
        self.iniFile = "CDZ.ini"
        self.attribute_initialization()
        self.sdk_obj = SDK(logger=logger, addr=server_addr, self_addr=self_addr)
        if self_addr!=None:
            self._ip = self_addr
        self.sdk_obj.sim_obj = self
        self.sdk_obj.device_id = self._deviceID
        self.need_stop = False

        # state data:
        # self.task_obj = Task('Washer-task', self.LOG)
        self.dev_register = False
        self.command_list = getattr(self.sim_config, "Command_list")
        # self.create_tasks()

        # 心跳为30秒发送一次
        self.heartbeat_interval_s = 30
        # 延迟1秒注册
        self.reg_dev_relay_s = 1
        # 充电中10秒上报一次状态
        self.report_status_s = 10
        self.report_thread = None

        self.maintain_inv_s = 1
        self.report_inv_s = 0.01

    def run_forever(self):
        thread_list = []
        thread_list.append([self.sdk_obj.recv_data_loop])
        thread_list.append([self.sdk_obj.schedule_loop])
        thread_list.append([self.sdk_obj.send_data_loop])
        # thread_list.append([self.sdk_obj.heartbeat_loop])
        thread_list.append([self.to_send_heartbeat])
        # thread_list.append([self.task_obj.task_proc])
        # thread_list.append([self.status_maintain])
        # thread_list.append([self.status_report_monitor])
        # thread_list.append([self.msg_dispatch])
        thread_list.append([self.to_register_dev])
        thread_ids = []
        for th in thread_list:
            thread_ids.append(threading.Thread(target=th[0], args=th[1:]))

        for th in thread_ids:
            th.setDaemon(True)
            th.start()
        #self.to_register_dev()

    def to_register_dev(self):
        time.sleep(self.reg_dev_relay_s)
        if self.dev_register:
            self.LOG.warn(common_APIs.chinese_show("设备已经注册[{}]".format(self._deviceID)))
        else:
            time.sleep(self.reg_dev_relay_s)  # wait the send_data_loop thread to start
            self.LOG.info(common_APIs.chinese_show("发送设备注册[{}]".format(self._deviceID)))
            self.send_msg(json.dumps(
                self.get_send_msg('COM_DEV_REGISTER')), ack=b'\x00')

    def to_send_heartbeat(self):
        while self.need_stop == False:
            self.LOG.info("8.4.1 heartbeat")
            if self.dev_register:
                self.send_msg(json.dumps(
                    self.get_send_msg('COM_HEARTBEAT')), ack=b'\x00')
            time.sleep(self.heartbeat_interval_s)

    def send_charging_report_by_thread(self):
        if (self.report_thread == None or not self.report_thread.isAlive()):
            self.report_thread = threading.Thread(target=self.send_charging_report_period)
            print(self.report_thread.__dict__)
            self.report_thread.setDaemon(True)
            self.report_thread.start()

    def handle_var_before_report(self, isEndReport = False):
        '''用于处理上报之前的一些变量变化逻辑，主要是用电量的计算与刷新和时间的保存和其他一些变量联动逻辑
        isEndReport为TRUE意为此次上报为停止充电后的最后一次上报，电流和功率字段需要特殊处理'''
        realTimeStr = self.sim_config.getDateStr()
        realTime = self.sim_config.getDateFromStr(realTimeStr)
        self.LOG.warn("realTime {}".format(realTime))
        # 此处为了防止在统计过程中由于currentTime被SETTIME或者别的原因干扰，新建立一个字段保存上次计算的间隔
        lastCalTime = self.sim_config.getDateFromStr(self.get_item("_lastReportTime"))
        self.LOG.warn("lastCalTime {}".format(lastCalTime))
        ts = self.sim_config.getTimeSpanS(realTime, lastCalTime)
        self.LOG.warn("ts {}".format(ts))
        currentP = self.get_item("_voltageOut") * self.get_item("_currentI") / 1000
        # 单位是0.1瓦特
        self.set_item("_power", round(currentP))
        # 单位是0.01千瓦时（KWH）
        usedQ = ts * currentP / 360000
        self.set_item("_usedQuantity2", self.get_item("_usedQuantity2") + usedQ)
        #self.set_item("_usedQuantity", self.get_item("_usedQuantity") + round(usedQ))
        #上报的时候将真实的取整即可
        self.set_item("_usedQuantity", round(self.get_item("_usedQuantity2")))
        self.set_item("_currentTime", realTime.strftime(self.sim_config.timeStrFormate))
        # 此处保存上一次上报的时间，作为下一次上报计算新增变量的依据
        self.set_item("_lastReportTime", realTime.strftime(self.sim_config.timeStrFormate))
        self.set_item("_duarationTime",
                      self.sim_config.getStrTsS(self.get_item("_currentTime"), self.get_item("_startTime")))
        if isEndReport:
            self.set_item("_currentI", 0)
            self.set_item("_power", 0)

    def send_charging_report_period(self):
        while self.need_stop == False and self.is_in_charging():
            # self.LOG.info("send_charging_report_period")
            self.send_charging_report_onetime(ReportType.PERIOD_PERIOD)
            time.sleep(self.report_status_s)

    def send_charging_report_onetime(self, reportType, isEndReport=False):
        self.LOG.info("send_charging_report_onetime,type:{0}".format(reportType))
        if self.dev_register:
            self.handle_var_before_report(isEndReport)
            self.send_msg(self.get_upload_event(reportType), ack=b'\x00')

    #reason取值含义：1表示急停事件，2表示设备发生故障，3表示枪连接状态发生变化
    def send_charging_stop_event(self, reason):
        self.LOG.info("send_charging_stop_event,reason:{0}".format(reason))
        if self.dev_register:
            self.set_item("_reason",int(reason))
            self.send_msg(self.get_upload_stop_event(), ack=b'\x00')

    @common_APIs.need_add_lock(type_lock)
    def get_upload_event(self, reportType):
        self.LOG.warn(common_APIs.chinese_show("8.4.2 事件上报"))
        self._type = reportType
        report_msg = self.get_send_msg('COM_UPLOAD_EVENT')
        return json.dumps(report_msg)

    def get_upload_start_result(self):
        self.LOG.warn(common_APIs.chinese_show("8.4.3 开始充电结果上报"))
        report_msg = self.get_send_msg('COM_UPLOAD_START_RESULT')
        return json.dumps(report_msg)

    def get_upload_stop_result(self):
        self.LOG.warn(common_APIs.chinese_show("8.4.4 停止充电结果上报"))
        report_msg = self.get_send_msg('COM_UPLOAD_STOP_RESULT')
        return json.dumps(report_msg)

    def get_upload_stop_event(self):
        self.LOG.warn(common_APIs.chinese_show("8.4.5 停止充电事件上报"))
        report_msg = self.get_send_msg('COM_UPLOAD_STOP_EVENT')
        return json.dumps(report_msg)

    # reqType=0表示停止充电，需要orderNumber
    # reqType=1表示开始充电，不需要orderNumber
    def get_upload_IC_req(self, reqType=1):
        self.LOG.warn(common_APIs.chinese_show("8.4.6 IC卡充电申请"))
        self._icType = reqType
        report_msg = self.get_send_msg('COM_IC_CARD_REQ_CHARGE')
        report_msg["Data"][0] = report_msg["Data"][int(reqType)]
        return json.dumps(report_msg)

    def send_ic_charging_req(self,regType):
        if self.dev_register:
            self.set_item("_icType",regType)
            self.send_msg(self.get_upload_IC_req(regType), ack=b'\x00')

    #region 收到消息后的联动逻辑和相关逻辑处理函数
    def maintain_max_switch_i(self):
        u'''维护开关最大电流，以计算充电最大功率'''
        if self.get_item("_switch3Status") > 0:
            self.set_item("SwitchMaxI", self.get_item("Switch3MaxI"))
        elif self.get_item("_switch7Status") > 0:
            self.set_item("SwitchMaxI", self.get_item("Switch7MaxI"))
        else:
            self.set_item("SwitchMaxI", 0)

    def is_in_charging(self):
        '''获取充电状态，TRUE：正在充电，FALSE：未在充电'''
        return self.get_item("_isCharging") == 1

    @common_APIs.need_add_lock(charging_lock)
    def set_charging_status(self,status:int):
        """设置充电状态，0：停止充电 1：开始充电"""
        self.set_item("_isCharging",int(status))

    def set_endTime_to_currentTime(self):
        realTimeStr = self.sim_config.getDateStr()
        self.set_item("_endTime", realTimeStr)

    def switch_connect(self, switchNum, switchOption):
        """将switchNum孔插座的status 设置为 switchOption"""
        itemKey = "_switch3Status"
        keyReport = ReportType.SWITCH3_CHANGE
        otherKey = "_switch7Status"
        otherKeyReport = ReportType.SWITCH7_CHANGE
        if (switchNum == 7):
            itemKey, otherKey = otherKey, itemKey
            keyReport, otherKeyReport = otherKeyReport, keyReport
        isEndReport:bool = False
        # 必须将3设置为非0才会将7设置为0，反之亦然
        if switchOption > 0 and self.try_set_item(otherKey, 0):
            if self.is_in_charging():
                #充电中暴力拔枪 停止充电，上报充电停止事件
                isEndReport = True
                self.set_charging_status(0)
                self.set_endTime_to_currentTime()
                self.send_charging_stop_event(ReasonType.GunStatusChange)
            self.send_charging_report_onetime(otherKeyReport,isEndReport)
        if self.try_set_item(itemKey, switchOption):
            if self.is_in_charging() and switchOption==0:
                # 充电中暴力拔枪 停止充电，上报充电停止事件
                isEndReport = True
                self.set_charging_status(0)
                self.set_endTime_to_currentTime()
                self.send_charging_stop_event(ReasonType.GunStatusChange)
            self.send_charging_report_onetime(keyReport,isEndReport)
        self.maintain_max_switch_i()

    def handle_start_charge(self):
        '''开始充电的联动逻辑，函数会发送ACK'''
        msg_cmd = "COM_START_CHARGE"
        rsp_msg = json.dumps(self.get_rsp_msg(msg_cmd))
        tp = int(self.get_item("_targetPower"))
        # sw3status = self.get_item("_switch3Status")
        # sw7status = self.get_item("_switch7Status")
        swStatus = self.getSwitchStatus()
        self.LOG.debug("switch_status:{}".format(swStatus))
        tI = 0
        # 预约充电需要加电子锁并上报,目前逻辑为预约前必须先插上插座
        if tp == 0:
            if swStatus == SwitchStatus.Only3 and self.try_set_item("_lock3Status", 1):
                self.send_charging_report_onetime(ReportType.LOCK3_CHANGE)
            if swStatus == SwitchStatus.Only7 and self.try_set_item("_lock7Status", 1):
                self.send_charging_report_onetime(ReportType.LOCK7_CHANGE)
        elif tp == -1:
            # 为-1时意思以6A电流充电
            tI = self.get_item("SwitchMinI")
            self.set_item("_currentI", tI)
        elif tp == -2:
            # 为-2时意思用最大电流充电,如果都不插枪此处为0，因为SwitchMaxI为0
            tI = self.get_item("SwitchMaxI")
            self.set_item("_currentI", tI)
        else:
            tI = tp * 1000 / self.get_item("_voltageOut")
            self.set_item("_currentI", round(tI))
        realTimeStr = self.sim_config.getDateStr()
        self.set_item("_usedQuantity",0)
        self.set_item("_usedQuantity2",0)
        self.set_item("_startTime", realTimeStr)
        self.set_item("_currentTime", realTimeStr)
        self.set_item("_lastReportTime", realTimeStr)
        # 先把此消息的回复发出去
        self.sdk_obj.add_send_data(self.sdk_obj.msg_build(rsp_msg))
        self.update_msgst(msg_cmd, 'rsp')
        # 开始处理开始充电结果消息的发送
        if swStatus not in {SwitchStatus.Only3, SwitchStatus.Only7} \
                or tI > self.get_item("SwitchMaxI"):
            self.set_item("_result", 1)
        else:
            if swStatus == SwitchStatus.Only3:
                if self.try_set_item("_switch3Status", 2):
                    self.send_charging_report_onetime(ReportType.SWITCH3_CHANGE)
            elif swStatus == SwitchStatus.Only7:
                if self.try_set_item("_switch7Status", 4):
                    self.send_charging_report_onetime(ReportType.SWITCH7_CHANGE)
            realPower = tI * self.get_item("_voltageOut") / 1000
            self.set_item("_power", round(realPower))
        self.send_msg(self.get_upload_start_result(), ack=b'\x00')
        if self.get_item("_result")==0:
            self.set_charging_status(1)
            self.send_charging_report_by_thread()

    def handle_stop_charge(self):
        '''停止充电的联动逻辑,函数会发送ACK'''
        msg_cmd = "COM_STOP_CHARGE"
        rsp_msg = json.dumps(self.get_rsp_msg(msg_cmd))
        swStatus = self.getSwitchStatus()
        self.set_endTime_to_currentTime()
        # 先把此消息的回复发出去
        self.set_charging_status(0)
        self.sdk_obj.add_send_data(self.sdk_obj.msg_build(rsp_msg))
        self.update_msgst(msg_cmd, 'rsp')
        #self.set_item("_isCharging", 0)
        self.set_item("_result", 0)
        self.send_msg(self.get_upload_stop_result(), ack=b'\x00')
        self.send_charging_report_onetime(ReportType.CHARGE_RECORD_UPLOAD,isEndReport=True)
        if int(self.get_item("_unlock")) == 1:
            if swStatus == SwitchStatus.Only3 and self.try_set_item("_lock3Status", 0):
                self.send_charging_report_onetime(ReportType.LOCK3_CHANGE)
            if swStatus == SwitchStatus.Only7 and self.try_set_item("_lock7Status", 0):
                self.send_charging_report_onetime(ReportType.LOCK7_CHANGE)

    def handle_power_control(self):
        '''功率控制联动逻辑，函数不会发送ACK'''
        tI = 0
        result = 0
        tp = self.get_item("_targetPower")
        v = self.get_item("_voltageOut")
        if v == 0:
            result = 1
        elif tp > 0:
            tI = tp / v
            if tI > self.get_item("SwitchMaxI"):
                result = 1
        elif tp == -1:
            tI = self.get_item("SwitchMinI")
        elif tp == -2:
            tI = self.get_item("SwitchMaxI")
        if result == 0:
            self.set_item("_currentI", tI)
        self.set_item("comPowerCtlResult", result)

    def handle_set_lock(self):
        '''电子锁处理逻辑函数，会发送电子锁状态上报，但是不会发送ACK，ACK由框架统一发送'''
        msg_cmd = "COM_SET_LOCK"
        rsp_msg = self.get_rsp_msg(msg_cmd)
        #0表示设置成功，-1表示设置失败
        result = 0
        #0- 关闭，1- 打开
        operate = int(self.get_item("_unlock"))
        #通道号，Bit0表示3孔插座，Bit1表示7孔插座
        op_ch = int(self.get_item("_channel"))
        if operate not in (0,1) or op_ch not in (0,1,2,3):
            result = -1
        #0表示未上锁，1表示已上锁,因此需要对operate进行异或操作
        lock_status = operate^1
        if op_ch & 0b01:
            if self.try_set_item("_lock3Status",lock_status):
                self.send_charging_report_onetime(ReportType.LOCK3_CHANGE)
        if op_ch & 0b10:
            if self.try_set_item("_lock7Status",lock_status):
                self.send_charging_report_onetime(ReportType.LOCK7_CHANGE)
        self.set_item("comSetLockResult",result)
        #self.sdk_obj.add_send_data(self.sdk_obj.msg_build(rsp_msg))
        #self.update_msgst(msg_cmd, 'rsp')

    def getSwitchStatus(self):
        sw3status = self.get_item("_switch3Status")
        sw7status = self.get_item("_switch7Status")
        status = SwitchStatus.Neither3Nor7
        if sw3status > 0:
            if sw7status > 0:
                # 3 7 都插抢
                status = SwitchStatus.Both3And7
            else:
                # 仅3插抢
                status = SwitchStatus.Only3
        elif sw7status > 0:
            # only 7
            if (sw7status == 1):
                # 1表示没连接车，假设这时候就是所谓的7没插好
                status = SwitchStatus.Only7_Unstable
            else:
                status = SwitchStatus.Only7
        else:
            # no one
            status = SwitchStatus.Neither3Nor7
        self.set_item("_switchStatus",status)
        return status

    #endregion

    def protocol_handler(self, msg, ack=False):
        if ack:
            self.update_msgst(msg['Command'], 'rsp')
            if msg['Command'] == 'COM_DEV_REGISTER':
                if msg['Result'] == 0:
                    self.dev_register = True
                    # decrypt
                    if self.encrypt_flag:
                        self.add_item('_encrypt_key', msg['Data'][0]['aeskey'])
                    self.LOG.warn(common_APIs.chinese_show("设备注册成功[{}]\n".format(self._deviceID)))
                    return None
                else:
                    self.dev_register = False
                    self.LOG.error(common_APIs.chinese_show("设备注册失败[{}]".format(self._deviceID)))
                    return None
            elif msg['Command'] == 'COM_IC_CARD_REQ_CHARGE':
                if msg['Result'] == 0:
                    self.set_items(msg['Command'], msg)
                    if self.get_item("_icType"==1):
                        #region 处理IC卡开始充电
                        tI = self.get_item("SwitchMinI")
                        self.set_item("_currentI", tI)
                        realTimeStr = self.sim_config.getDateStr()
                        self.set_item("_startTime", realTimeStr)
                        self.set_item("_currentTime", realTimeStr)
                        self.set_item("_lastReportTime", realTimeStr)
                        swStatus = self.getSwitchStatus()
                        if swStatus == SwitchStatus.Only3:
                            if self.try_set_item("_switch3Status", 2):
                                self.send_charging_report_onetime(ReportType.SWITCH3_CHANGE)
                        elif swStatus == SwitchStatus.Only7:
                            if self.try_set_item("_switch7Status", 4):
                                self.send_charging_report_onetime(ReportType.SWITCH7_CHANGE)
                        realPower = tI * self.get_item("_voltageOut") / 1000
                        self.set_item("_power", round(realPower))
                        self.send_msg(self.get_upload_start_result(), ack=b'\x00')
                        self.set_item("_isCharging", 1)
                        self.send_charging_report_by_thread()
                        #endregion
                    else:
                        #region 处理IC卡停止充电
                        self.set_endTime_to_currentTime()
                        self.set_charging_status(0)
                        self.set_item("_result", 0)
                        self.send_msg(self.get_upload_stop_result(), ack=b'\x00')
                        self.send_charging_report_onetime(ReportType.CHARGE_RECORD_UPLOAD, isEndReport=True)
                        #endregion
                else:
                    self.LOG.error("COM_IC_CARD_REQ_CHARGE 返回失败")
                return None
            else:
                return None
        else:
            self.update_msgst(msg['Command'], 'req')
        if msg['Command'] == 'COM_HEARTBEAT'or msg['Command'] == 'COM_IC_CARD_REQ_CHARGE':
            pass
        elif msg['Command'] in self.command_list:
            self.set_items(msg['Command'], msg)
            if msg['Command'] == 'COM_SET_QR_CODE':
                # 如果当前有打开图片，先关掉
                # os.system("taskkill /f /t /im dllhost.exe")
                common_APIs.save_ini_file(self.iniFile, self._deviceID,
                                          url=self.get_item("_url"), sn=self.get_item("_sn"))
                common_APIs.GetQrCodeByUrlAndSn(self.get_item("_url"),
                                                self.get_item("_sn"), imgFile=self.get_item("_qcodeFile"))
            elif msg['Command'] == 'COM_START_CHARGE':
                self.handle_start_charge()
                # handle_start_charge已经发过了ACK，这里不需要返回再发了，所以返回None
                return None
            elif msg['Command'] == 'COM_STOP_CHARGE':
                self.handle_stop_charge()
                return None
            elif msg['Command'] == 'COM_POWER_CONTROL':
                self.handle_power_control()
            elif msg['Command'] == 'COM_SET_LOCK':
                self.handle_set_lock()
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
                needSet = True
                for i in msg_param_list[1:]:
                    if re.match(r'\d+', i):
                        i = int(i)
                    else:
                        pass
                    if isinstance(tmp_msg,list) and i>=len(tmp_msg):
                        needSet = False
                        self.LOG.error("tmp_msg[{0}] out of range:i={1}".format(tmp_msg,i))
                        break
                    if isinstance(tmp_msg,dict) and i not in tmp_msg:
                        needSet = False
                        self.LOG.info("key:[{0}] not in tmp_msg".format(i))
                        break
                    tmp_msg = tmp_msg[i]
                if needSet:
                    self.set_item(item, tmp_msg)

    def attribute_initialization(self):
        attribute_params_dict = getattr(
            self.sim_config, "Attribute_initialization")
        for attribute_params, attribute_params_value in attribute_params_dict.items():
            self.add_item(attribute_params, attribute_params_value)

        self._mac = self.mac_list[self.N]
        # "_deviceID": "1005200958FCDBDA5380",
        # "_subDeviceID": "301058FCDBDA53800001",
        self._deviceID = str(self.DeviceFacturer) + \
                         str(self.DeviceType) + self._mac.replace(":", '')
        self._encrypt_key = self._deviceID[-16:].encode('utf-8')
        self._qcodeFile = self._mac.replace(":", '') + ".png"
        # self._decrypt_key = self._deviceID[-16:].encode('utf-8')
        # self._subDeviceID = str(self.subDeviceType) + \
        # self._mac.replace(":", '') + "%04d" % (self.N + 1)
        qcodeDict = common_APIs.read_ini_file(self.iniFile, self._deviceID, "url", "sn")
        if "url" in qcodeDict and "sn" in qcodeDict:
            self.set_item("_sn", qcodeDict["sn"])
            self.set_item("_url", qcodeDict["url"])
            common_APIs.ShowQrCodeImage(self.get_item("_url"), self.get_item("_sn"), self._qcodeFile,showImg=False)

    def set_abnormal_status(self,reason:int, status:int = 1):
        #急停状态无改变则不触发任何事情
        status_key = "_urgentStatus"
        report_type = ReportType.URGENT_CHANGE
        inCharging = self.is_in_charging()
        if reason == ReasonType.UrgentStop:
            #默认值中就是按此情况设置的，所以这个分支不需要做啥了，加入只是为了不进入else分支
            pass
        elif reason == ReasonType.DevFault:
            status_key = "_devStatus"
            report_type = ReportType.STATUS_CHANGE
        else:
            self.LOG.error("Reason:{} not supported!".format(reason))
            raise Exception("Reason:{} not supported!".format(reason))
        if self.try_set_item(status_key, int(status)):
            # 正在充电时候按下急停/设备错误才会设置endTime和上报异常停止充电事件，否则只上报
            if inCharging:
                self.set_charging_status(0)
                self.set_endTime_to_currentTime()
                self.send_charging_stop_event(reason)
            #无论是否在充电都要上报，在充电时isEndReport为TRUE，重置电流和功率为0
            #不在充电时电流和功率本就为0，重置也不影响，但是为了防止重置逻辑更改，此处不充电时设置为FALSE
            self.send_charging_report_onetime(report_type, isEndReport=inCharging)


    # region 暂时不用的功能
    def create_tasks(self):
        pass
        # self.task_obj.add_task(
        # 'status maintain', self.status_maintain, 10000000, 10)

        # self.task_obj.add_task('monitor status report',
        # self.status_report_monitor, 10000000, 1)

        # self.task_obj.add_task(
        # 'dev register', self.to_register_dev, 1, 10)

        # self.task_obj.add_task(
        # 'heartbeat', self.to_send_heartbeat, 1000000, 300)

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


if __name__ == '__main__':
    # os.system("taskkill /f /t /im dllhost.exe")
    # x = b'\x01'
    # y = b'\x10'
    # print(type(x))
    a =(0,1,2,3)
    for i in a:
        print(i^1)
    pass
