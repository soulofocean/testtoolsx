代码说明：
建议结合《设备模拟器介绍.pptx》一起看

1. APIs
APIs\common_APIs.py：一些有用的独立的基本的公用函数，被所有代码共享；用做一个基本函数库
APIs\security.：加解密相关模块，对外提供实现加解密算法的API

2. basic
basic\cprint.py:  带颜色的print,便于调试
basic\log_tool.py：log模块，记录有用的事件
basic\task.py：实现了基本的任务队列功能

3. connection
connections\my_socket.py：TCP通讯模块,处理底层的消息交互，对标准socket库做了一层封装， 更加方便使用


4. protocol:
protocol\protocol_process.py：通过class communication_base实现模拟器通讯框架抽象层，定义了模拟器内部的数据处理流程
protocol\light_protocol.py：通过class SDK(communication_base)实现模拟器的私有协议层，同时也实现了communication_base定义的数据通讯方式（TCP、UDP or 串口）
protocol\light_devices.py：通过class Dev(BaseSim)实现了模拟器的应用协议层，通过加载具体设备的配置文件，实现了具体设备的接口交互消息
protocol\config: 具体设备消息配置文件，具体可参考《轻量级设备-说明文档.docx》

5.
dev_sim.py：当作为独立的工具使用时（Dev类可以直接被其它自动化工具导入并实例化）， 本模块提供实例化Dev，为用户提供CLI操作
