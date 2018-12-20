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
getDateStr = lambda : datetime.datetime.now().strftime(timeStrFormate)
getDateFromStr = lambda a :  datetime.datetime.strptime(a, "%Y-%m-%d %H:%M:%S")
getTimeSpanS = lambda a,b : (a-b).seconds
getStrTsS = lambda a,b : getTimeSpanS(getDateFromStr(a),getDateFromStr(b))

Attribute_initialization = {
    "mac_list": ['59:88:88:88:' + re.sub(r'^(?P<xx>\d\d)', "\g<xx>:", str(i)) for i in range(1000, 4000)],
    "DeviceFacturer": 1008,
    "DeviceType": 2025,
    #额定电压2200代表220V
    "RatedV":2200,
    #电压波动范围，正负15%，超过或者不足会触发过压/欠压保护和相应事件上报
    "RatedFloatV":0.15,
    #当前最大的电流数，和插入的插孔相关，需要和插孔设置联动
    "SwitchMaxI":0,
    #最小功率充电时候的电流单位:毫安
    "SwitchMinI":6000,
    #3孔最大电流，超过会触发过流保护，自动断电,标准电流为16A
    "Switch3MaxI":18000,
    #7孔最大电流，超过会触发过流保护，自动断电，标准电流为32A
    "Switch7MaxI":32000 * 1.1,
    "comPowerCtlResult": 0,
    "comSetLockResult":0,
    #"subDeviceType": 3010,
    "_RegisterType": 1,
    "_name": 'CDZCZ',
    "_manufacturer": 'HD',
    "_ip": "192.168.0.235",
    "_mask": '255.255.255.0',
    "_version": '1.0.01',
    "_algVersionInfo":"8.8.8",

    "_type":10000,
    "_isCharging":0,
    #充电开始时间
    "_startTime": getDateStr(),
    #当前时间
    "_currentTime":getDateStr(),
    #用于周期性上报的时候获取上次时间段时间，计算本时间段电量
    "_lastReportTime":getDateStr(),
    #充电时间，一般采用当前-开始时间进行计算
    "_duarationTime":0,
    #开始充电电量，感觉类似于里程表的东西，模拟器中暂不实现，暂定恒定为0，若要实现，需要增加并保存
    "_startQuantity":0,
    #本次充电已经使用的充电电量2代表0.02kwh
    "_usedQuantity":0,
    #跟_usedQuantity一样，不过不四舍五入，防止出现电流过小导致10秒内上报0+0=0的问题
    "_usedQuantity2":0,
    #记录当前输出电压，2200=220V
    "_voltageOut":2200,
    #记录当前电流，单位mA
    "_currentI":0,
    #记录当前功率，目前采用电压*电流计算
    "_power":0.0,
    "_switch3Status":0,
    "_switch7Status":0,
    "_lock3Status":0,
    "_lock7Status":0,
    "_urgentStatus":0,
    "_devStatus":0,

    "_result":0,
    "_switchStatus":2,
    "_orderNumber":"",
    "_reason":1,

    "_icType":1,
    "_accountBalance":0.00,
    "_usedBalance":0.00,

    "_endTime":getDateStr(),

    "_FileURL":"",
    "_FtpAddr":"",

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
    #region 8.1 系统命令
    "COM_DEV_REGISTER": {"msg": "设备注册"},
    "COM_DEV_RESET": {"msg": "恢复出厂设置"},
    "COM_READ_TIME": {"msg": "读取时间"},
    "COM_SET_TIME": {"msg": "设置时间"},
    "COM_READ_SYSTEM_VERSION": {"msg": "读取系统版本信息"},
    "COM_NOTIFY_UPDATE": {"msg": "通知设备升级"},
    #endregion
    #region 8.2 设备参数
    "COM_DEV_STATUS": {"msg": "查询设备状态"},
    "COM_REQ_REAL_DATA": {"msg": "请求实时数据"},
    "COM_SETTING_PARAMETERS": {"msg": "设置参数"},
    "COM_SET_QR_CODE": {"msg": "设置序列号"},
    #endregion
    #region 8.3 设备操控
    "COM_START_CHARGE": {"msg": "开始充电"},
    "COM_STOP_CHARGE": {"msg": "停止充电"},
    "COM_POWER_CONTROL": {"msg": "功率控制"},
    "COM_SET_LOCK": {"msg": "电子锁开关"},
    #endregion
    #region 8.4 事件上传
    "COM_HEARTBEAT": {"msg": "设备心跳"},
    "COM_UPLOAD_EVENT": {"msg": "事件上报"},
    "COM_UPLOAD_START_RESULT": {"msg": "开始充电结果上报"},
    "COM_UPLOAD_STOP_RESULT": {"msg": "停止充电结果上报"},
    "COM_UPLOAD_STOP_EVENT": {"msg": "停止充电事件上报"},
    "COM_IC_CARD_REQ_CHARGE": {"msg": "IC卡启动/停止充电"},
    #endregion
    #region 8.x 文档中没有，但网关会发来的命令
    "COM_QUERY_DIR": {"msg": "设备目录查询"}
    #endregion
}

#region 8.1 系统命令
u'''系统命令：8.1.1 设备注册'''
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
                "version": "##self._version##"
                #"macNO":"机号"
                #"gateWay":"网关"
            }
        ]
    }
}

u'''系统命令：8.1.2 恢复出厂设置'''
COM_DEV_RESET = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_DEV_RESET",
        "Result": 0,
    }
}

u'''系统命令：8.1.3 读取时间'''
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

u'''系统命令：8.1.4 设置时间'''
COM_SET_TIME = {
    'set_item': {'_currentTime': 'Data.0.time'},
    "rsp_msg": {
        "Command": "COM_SET_TIME",
        "Result": 0,
    }
}

u'''系统命令：8.1.5 读取系统版本信息'''
COM_READ_SYSTEM_VERSION = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_READ_SYSTEM_VERSION",
        "Result": 0,
        "Data": [
            {
                "appVersionInfo": "##self._version##",
                "algVersionInfo": "##self._algVersionInfo##"
            }
        ]
    }

}

u'''系统命令：通知设备升级'''
COM_NOTIFY_UPDATE = {
    'set_item': {
        "_version":"DARA.0.FirmwareVersion",
        "_FileURL":"DARA.0.FileURL",
        "_FtpAddr":"DARA.0.FtpAddr",
    },
    "rsp_msg": {
        "Command": "COM_NOTIFY_UPDATE",
        "Result": 0
    }
}
#endregion

#region 8.2 设备参数
u'''设备参数：8.2.1 查询设备状态'''
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

u'''设备参数：8.2.2 请求实时数据'''
COM_REQ_REAL_DATA = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_REQ_REAL_DATA",
        "Result": 0,
        "Data": [
            {
                "type": 0,
                "isCharging": "##self._isCharging##",
                "orderNumber":"##self._orderNumber##",
                "startTime":"##self._startTime##",
                "currentTime":"##self._currentTime##",
                "duarationTime":"##self._duarationTime##",
                "startQuantity":"##self._startQuantity##",
                "usedQuantity":"##self._usedQuantity##",
                "voltageOut":"##self._voltageOut##",
                "current":"##self._currentI##",
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

u'''设备参数：8.2.3设置参数'''
COM_SETTING_PARAMETERS = {
    "set_item": {
        "_fileServerUrl": "Data.0.fileServerUrl",
        "_ntpServer": "Data.0.ntpServer"
    },
    "rsp_msg": {
        "Command": "COM_SETTING_PARAMETERS",
        "Result": 0
    }
}

u'''设备参数：8.2.4 设置序列号'''
COM_SET_QR_CODE = {
    "set_item": {
        "_url": "Data.0.url",
        "_sn": "Data.0.sn"
    },
    "rsp_msg": {
        "Command": "COM_SET_QR_CODE",
        "Result": 0,
    }
}
#endregion

#region 8.3 设备操控
u'''设备操控：8.3.1 开始充电'''
COM_START_CHARGE = {
    "set_item": {
        "_targetPower": "Data.0.targetPower",
        "_orderNumber": "Data.0.orderNumber"
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

u'''设备操控：8.3.2 停止充电'''
COM_STOP_CHARGE = {
    "set_item": {
        "_unlock": "Data.0.unlock",
        "_orderNumber": "Data.0.orderNumber"
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

u'''设备操控：8.3.3 功率控制'''
COM_POWER_CONTROL = {
    "set_item": {
        "_targetPower": "Data.0.targetPower",
        "_orderNumber": "Data.0.orderNumber"
    },
    "rsp_msg": {
        "Command": "COM_POWER_CONTROL",
        "Result": "#self.comPowerCtlResult",
        "Data": [
                {
                    "orderNumber": "##self._orderNumber##",
                }
        ]
    }
}

u'''设备操控：8.3.4 电子锁开关'''
COM_SET_LOCK = {
    "set_item": {
        "_unlock": "Data.operateType",
        "_channel": "Data.channel"
    },
    "rsp_msg": {
        "Command": "COM_SET_LOCK",
        "Result": "##self.comSetLockResult##",
        "Data": [
                {
                    "result": "##self._result##",
                }
        ]
    }
}
#endregion

#region 8.4 事件上传
u'''事件上传：8.4.1 设备心跳'''
COM_HEARTBEAT = {
    "send_msg": {
        "Command": 'COM_HEARTBEAT',
    }
}

u'''事件上传：8.4.2 事件上报'''
COM_UPLOAD_EVENT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_EVENT',
        "Data": [
            {
                "type":"##self._type##",
                "isCharging": "##self._isCharging##",
                "orderNumber":"##self._orderNumber##",
                "startTime":"##self._startTime##",
                "currentTime":"##self._currentTime##",
                "duarationTime":"##self._duarationTime##",
                "startQuantity":"##self._startQuantity##",
                "usedQuantity":"##self._usedQuantity##",
                "voltageOut":"##self._voltageOut##",
                "current":"##self._currentI##",
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

u'''事件上传：8.4.4 开始充电结果上报'''
COM_UPLOAD_START_RESULT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_START_RESULT',
        "Data": [
                {
                    "result": "##self._result##",
                    "reason":"##self._switchStatus##",
                    "startTime":"##self._startTime##",
                    "power":"##self._power##",
                    "orderNumber":"##self._orderNumber##"
                }
        ]
    }
}

u'''事件上传：8.4.5 停止充电结果上报'''
COM_UPLOAD_STOP_RESULT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_STOP_RESULT',
        "Data": [
                {
                    "result": "##self._result##",
                    "endTime":"##self._endTime##",
                    "orderNumber":"##self._orderNumber##",
                }
        ]
    }
}

u'''事件上传：8.4.6 停止充电事件上报'''
COM_UPLOAD_STOP_EVENT = {
    "send_msg": {
        "Command": 'COM_UPLOAD_STOP_EVENT',
        "Data": [
                {
                    "reason": "##self._reason##",
                    "startTime":"##self._startTime##",
                    "endTime":"##self._endTime##",
                    "orderNumber":"##self._orderNumber##"
                }
        ]
    }
}

u'''事件上传：8.4.7 IC卡开始/停止充电'''
COM_IC_CARD_REQ_CHARGE = {
    "send_msg": {
        "Command": 'COM_IC_CARD_REQ_CHARGE',
        "Data": [
                {
                    #_icType=0表示停止充电，需要orderNumber
                    "type": "##self._icType##",
                    "startTime":"##self._startTime##",
                    "endTime":"##self._endTime##",
                    "orderNumber":"##self._orderNumber##"
                },
                {
                    #_icType=1表示开始充电，不需要orderNumber和endTime
                    "type": "##self._icType##",
                    "startTime": "##self._startTime##"
                }
        ]
    },
    "set_item":{
        "_orderNumber":"DATA.0.orderNumber",
        "_accountBalance":"DATA.0.accountBalance",
        "_usedBalance":"DATA.0.usedBalance",
    },
    "rsp_msg":{
        "Command": "COM_IC_CARD_REQ_CHARGE",
        "Result": 0
    }
}
#endregion

# region 8.x 文档中没有，但网关会发来的命令
u'''功能命令：设备目录查询'''
COM_QUERY_DIR = {
    'set_item': {},
    "rsp_msg": {
        "Command": "COM_QUERY_DIR",
        "Result": 0,
        "Data": [
            {
                "deviceID": "##self._deviceID##",
                "name": "##self._name##",
                "manufacturer": "##self._manufacturer##",
                "version": "##self._version##",
                #"subDeviceType": "##self.subDeviceType##"
            }
        ]
    }
}
#endregion

#region 8.y 文档中没有，留着备用的命令

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
#endregion


