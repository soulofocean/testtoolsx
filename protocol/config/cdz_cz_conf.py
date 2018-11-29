#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = '123124100'
__mtime__ = '2018/11/28 14:27'
"""
import re
import datetime

# 设备初始化参数
# 1005200959FCDBDA1000

timeStrFormate = "%Y-%m-%d %H:%M:%S"
getDateStr = lambda : datetime.datetime.now().strftime(timeStrFormate).encode('utf-8')
getDateFromStr = lambda a :  datetime.datetime.strptime(a.decode('utf-8'), "%Y-%m-%d %H:%M:%S")
getTimeSpanS = lambda a,b : (a-b).seconds
getStrTsS = lambda a,b : getTimeSpanS(getDateFromStr(a),getDateFromStr(b))

Attribute_initialization = {
    "mac_list": ['59:FC:DB:DA:' + re.sub(r'^(?P<xx>\d\d)', "\g<xx>:", str(i)) for i in range(1000, 4000)],
    "DeviceFacturer": 1005,
    "DeviceType": 2009,
    "subDeviceType": 3010,
    "_RegisterType": 1,
    "_name": 'CDZCZ Simulator',
    "_manufacturer": 'HDIOT',
    "_ip": "192.168.0.235",
    "_mask": '255.255.255.0',
    "_version": '1.0.01',

    "_type":10000,
    "_isCharging":0,
    "_startTime": getDateStr(),
    "_currentTime":getDateStr(),
    "_duarationTime":0,
    "_startQuantity":0.00,
    "_usedQuantity":0.00,
    "_voltageOut":0.0,
    "_current":0.000,
    "_power":0.0,
    "_switch3Status":0,
    "_switch7Status":0,
    "_lock3Status":0,
    "_lock7Status":0,
    "_urgentStatus":0,
    "_devStatus":0,

    "_result":0,
    "_switchStatus":2,
    "_orderNumber":"NoOrderNo",

    "_endTime":getDateStr(),

    "_fileServerUrl":"",
    "_ntpServer":"",

    "_url": "http://theMaxLenOfThisUrlis128.com",
    "_sn":"88888888",

    "_targetPower":0.0,

    "_unlock":1,
    "_channel":0,

    "SPECIAL_ITEM": {
        "_State": {
            "init_value": 0,
            "wait_time": 8,
            "use":  ["maintain", "report"],
        }
    },

    "test_msgs": {
        "interval": 10,
        "round": 0,
        "msgs": {
            #"COM_UPLOAD_DEV_STATUS": 0,
            "COM_UPLOAD_RECORD.Data[0].RecordType.30001": 0,
            "COM_UPLOAD_EVENT.Data[0].EventType.30301": 0,
        }
    }
}


# 注册设备支持的消息
Command_list = {
    "COM_DEV_REGISTER": {"msg": "设备注册"},
    "COM_DEV_RESET": {"msg": "恢复出厂设置"},
    "COM_READ_TIME": {"msg": "读取时间"},
    "COM_SET_TIME": {"msg": "设置时间"},
    "COM_READ_SYSTEM_VERSION": {"msg": "读取系统版本信息"},
    "COM_NOTIFY_UPDATE": {"msg": "通知设备升级"},

    "COM_REQ_REAL_DATA": {"msg": "请求实时数据"},
    "COM_SETTING_PARAMETER": {"msg": "设置参数"},
    "COM_SET_QR_CODE": {"msg": "设置序列号"},

    "COM_CHARGE_START": {"msg": "开始充电"},
    "COM_CHARGE_STOP": {"msg": "停止充电"},
    "COM_POWER_CONTROL": {"msg": "功率控制"},
    "COM_SET_LOCK": {"msg": "电子锁开关"},

    "COM_HEARTBEAT": {"msg": "设备心跳"},
    "COM_UPLOAD_EVENT": {"msg": "事件上报"},
    "COM_IC_CARD_REQ_CHARGE": {"msg": "IC卡启动/停止充电"}
}

# 定制设备需要主动发的消息

u'''系统命令：设备注册'''
COM_DEV_REGISTER = {
    "send_msg": {
        "Command": "COM_DEV_REGISTER",
        "Data": [
            {
                "Type": "##self._RegisterType##",
                "deviceID": "##self._deviceID##",
                "manufacturer": "##self._manufacturer##",
                "locationAddr":"28F",
                "name":"##self._name##",
                "ip": "##self._ip##",
                "mac": "##self._mac##",
                "mask": "##self._mask##",
                "version": "##self._version##",
            }
        ]
    }
}

u'''心跳'''
COM_HEARTBEAT = {
    "send_msg": {
        "Command": 'COM_HEARTBEAT',
    }
}

u'''事件上报：事件上报'''
COM_UPLOAD_EVENT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_EVENT',
        "Data": [
            {
                "type":"##self._type##",
                "isCharging": "##self._isCharging##",
                "startTime":"##self._startTime##",
                "currentTime":"##self._currentTime##",
                "duarationTime":"##self._duarationTime##",
                "startQuantity":"##self._startQuantity##",
                "usedQuantity":"##self._usedQuantity##",
                "voltageOut":"##self._voltageOut##",
                "current":"##self._current##",
                "power":"##self._power##",
                "switch3Status":"##self._switch3Status##",
                "switch7Status":"##self._switch7Status##",
                "lock3Status":"##self._lock3Status##",
                "lock7Status":"##self._lock7Status##",
                "urgentStatus":"##self._urgentStatus##",
                "devStatus":"##self._devStatus##",
            }
        ]
    }
}

u'''事件上报：上报开始充电结果'''
COM_UPLOAD_START_RESULT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_START_RESULT',
        "Data": [
                {
                    "result": "##self._result##",
                    "switchStatus":"##_switchStatus##",
                    "startTime":"##_startTime##",
                    "power":"##_power##",
                    "orderNumber":"##_orderNumber##",
                }
        ]
    }
}

u'''事件上报：上报停止充电结果'''
COM_UPLOAD_STOP_RESULT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_STOP_RESULT',
        "Data": [
                {
                    "result": "##self._result##",
                    "switchStatus":"##_switchStatus##",
                    "endTime":"##_endTime##",
                    "orderNumber":"##_orderNumber##",
                }
        ]
    }
}

u'''事件上报：IC卡充电上报'''
COM_IC_CARD_REQ_CHARGE = {
    "send_msg": {
        "Command": 'COM_IC_CARD_REQ_CHARGE',
        "Data": [
                {
                    "deviceID": "##self._deviceID##",
                }
        ]
    }
}




# 定制设备需要应答的消息

u'''系统命令：恢复出厂设置'''
COM_DEV_RESET = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_DEV_RESET",
        "Result": 0,
    }
}

u'''系统命令：读取时间'''
COM_READ_TIME = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_READ_TIME",
        "Result": 0,
        "Data": [
            {
                "time": "##self._currentTime##"
            }
        ]
    }
}


u'''系统命令：设置时间'''
COM_SET_TIME = {
    'set_item': {'_currentTime': 'Data.time'},
    "rsp_msg": {
        "Command": "COM_SET_TIME",
        "Result": 0,
    }
}

u'''系统命令：通知设备升级'''
COM_NOTIFY_UPDATE = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_NOTIFY_UPDATE",
        "Result": 0,
        "Data": [
                {
                    "FirmwareVersion": "##self._version##",
                    "FileURL":"Simu_FileURL",
                    "FtpAddr":"Simu_FtpAddr"
                }
        ]
    }

}


u'''系统命令：读取系统版本信息'''
COM_READ_SYSTEM_VERSION = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_READ_SYSTEM_VERSION",
        "Result": 0,
        "Data": [
            {
                "appVersionInfo": "##self._appVersionInfo##"
            }
        ]
    }

}

u'''设备参数：查询设备状态'''
COM_DEV_STATUS = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_DEV_STATUS",
        "Result": 0,
        "Data": [
            {
                "type": 0,
                "isCharging": "##self._isCharging##",
                "switch3Status":"##self._switch3Status##",
                "switch7Status":"##self._switch7Status##",
                "lock3Status":"##self._lock3Status##",
                "lock7Status":"##self._lock7Status##",
                "urgentStatus":"##self._urgentStatus##",
                "devStatus":"##self._devStatus##",
            }
        ]
    }
}

u'''设备参数：请求实时数据'''
COM_REQ_REAL_DATA = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_REQ_REAL_DATA",
        "Result": 0,
        "Data": [
            {
                "type": 0,
                "isCharging": "##self._isCharging##",
                "orderNumber":"##_orderNumber##",
                "startTime":"##self._startTime##",
                "currentTime":"##self._currentTime##",
                "duarationTime":"##self._duarationTime##",
                "startQuantity":"##self._startQuantity##",
                "usedQuantity":"##self._usedQuantity##",
                "voltageOut":"##self._voltageOut##",
                "current":"##self._current##",
                "power":"##self._power##",
                "switch3Status":"##self._switch3Status##",
                "switch7Status":"##self._switch7Status##",
                "lock3Status":"##self._lock3Status##",
                "lock7Status":"##self._lock7Status##",
                "urgentStatus":"##self._urgentStatus##",
                "devStatus":"##self._devStatus##",
            }
        ]
    }
}



u'''功能命令：读取参数'''
COM_READ_PARAMETER = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_READ_PARAMETER",
        "Result": 0,
        "Data": [
            {
                "deviceID": "##self._deviceID##",
                "fileServerUrl": "##self._fileServerUrl##",
                "ntpServer": "##self._ntpServer##",
                "openDuration": "##self._openDuration##",
                "alarmTimeout": "##self._alarmTimeout##",
            }
        ]
    }

}


u'''设备参数：设置参数'''
COM_SETTING_PARAMETER = {
    "set_item": {
        "_fileServerUrl": "Data.fileServerUrl",
        "_ntpServer": "Data.ntpServer"
    },
    "rsp_msg": {
        "Command": "COM_SETTING_PARAMETER",
        "Result": 0
    }
}

u'''设备参数：设置序列号'''
COM_SET_QR_CODE = {
    "set_item": {
        "_url": "Data.url",
        "_sn": "Data.sn"
    },
    "rsp_msg": {
        "Command": "COM_SET_QR_CODE",
        "Result": 0,
    }
}

u'''设备操控：开始充电'''
COM_START_CHARGE = {
    "set_item": {
        "_targetPower": "Data.targetPower",
        "_orderNumber": "Data.orderNumber"
    },
    "rsp_msg": {
        "Command": "COM_START_CHARGE",
        "Result": 0,
        "Data": [
                {
                    "startTime": "##self._startTime##",
                    "orderNumber": "##self._orderNumber##",
                }
        ]
    }
}

u'''设备操控：停止充电'''
COM_STOP_CHARGE = {
    "set_item": {
        "_unlock": "Data.unlock",
        "_orderNumber": "Data.orderNumber"
    },
    "rsp_msg": {
        "Command": "COM_STOP_CHARGE",
        "Result": 0,
        "Data": [
                {
                    "endTime": "##self._endTime##",
                    "orderNumber": "##self._orderNumber##",
                }
        ]
    }
}

u'''设备操控：功率控制'''
COM_POWER_CONTROL = {
    "set_item": {
        "_targetPower": "Data.targetPower",
        "_orderNumber": "Data.orderNumber"
    },
    "rsp_msg": {
        "Command": "COM_POWER_CONTROL",
        "Result": 0,
        "Data": [
                {
                    "orderNumber": "##self._orderNumber##",
                }
        ]
    }
}

u'''设备操控：电子锁开关'''
COM_SET_LOCK = {
    "set_item": {
        "_unlock": "Data.operateType",
        "_channel": "Data.channel"
    },
    "rsp_msg": {
        "Command": "COM_SET_LOCK",
        "Result": 0,
        "Data": [
                {
                    "result": "##self._result##",
                }
        ]
    }
}



u'''功能命令：下发固定凭证信息'''
COM_LOAD_CERTIFICATE = {
    "set_item": {"_startTime": "Data.0.startTime", "_endTime": "Data.0.endTime", "_subDeviceID": "Data.0.subDeviceID",
                 "_UserType": "Data.0.UserType", "_CredenceType": "Data.0.CredenceType", "_credenceNo": "Data.0.credenceNo",
				 "_userID": "Data.0.userID", },
    "rsp_msg": {
        "Command": "COM_LOAD_CERTIFICATE",
        "Result": 0,
    }
}

u'''功能命令：读取固定凭证信息'''
COM_READ_CERTIFICATE = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_READ_CERTIFICATE",
        "Result": 0,
        "Data": [
            {
                "startTime": "##self._startTime##",
                "endTime": "##self._endTime##",
                "CredenceType": "##self._CredenceType##",
                "credenceNo": "##self._credenceNo##",
            }
        ]
    }
}


u'''功能命令：删除固定凭证信息'''
COM_DELETE_CERTIFICATE = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_DELETE_CERTIFICATE",
        "Result": 0,
    }
}

u'''功能命令：批量下发固定凭证信息'''
COM_LOAD_CERTIFICATE_IN_BATCH = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_LOAD_CERTIFICATE_IN_BATCH",
        "Result": 0,
    }
}


