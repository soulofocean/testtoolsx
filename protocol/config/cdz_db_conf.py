#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = '123124100'
__mtime__ = '2018/12/17 15:08'
"""
import re
Attribute_initialization = {
    "mac_list": ['59:99:99:99:' + re.sub(r'^(?P<xx>\d\d)', "\g<xx>:", str(i)) for i in range(1000, 1007)],
    "DeviceFacturer": 1008,
    "DeviceType": 2026,
    #电表报的A相电流，单位为毫安
    "ACurrent" : 1000,
    #电表报的B相电流，单位为毫安
    "BCurrent" : 2000,
    #电表报的C相电流，单位为毫安
    "CCurrent" : 3000,
    # region 暂时不用的配置变量
    "SPECIAL_ITEM": {
        "_State": {
            "init_value": 0,
            "wait_time": 8,
            "use": ["maintain", "report"],
        }
    },
    "test_msgs": {
        'interval': 10,
        'round': 0,
        'msgs': {
        # "COM_UPLOAD_DEV_STATUS": 0,
        "COM_UPLOAD_RECORD.Data[0].RecordType.30001": 0,
        "COM_UPLOAD_EVENT.Data[0].EventType.30301": 0,
        }
    }
    #endregion
}
