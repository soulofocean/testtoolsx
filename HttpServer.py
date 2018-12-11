#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = '123124100'
__mtime__ = '2018/10/18 16:35'
"""
#!/usr/bin/python

#encoding=utf-8

from BaseHTTPServer import HTTPServer,BaseHTTPRequestHandler
import io,shutil
import urllib,urlparse
import os, sys
import time

port =8765#端口号

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):#GET请求
        mpath, margs = urllib.splitquery(self.path) # ?分割
        # self.do_action(mpath, margs)#转发

def do_POST(self):

    length=int(self.headers['Content-Length'])

    post_data = urlparse.parse_qs(self.rfile.read(int(self.headers['content-length'])))#获取内容

    print(str(post_data['op'])[2:-2]) #获取name为op的值

    log(post_data,self.client_address[0]) #收集日志

    self.send_response(200)

    self.send_header("Content-type","text/html")

    self.end_headers()

def do_action(self, path, args):

    self.outputtxt(path + args)

def outputtxt(self, content):

    #指定返回编码

    enc ="UTF-8"

    content = content.encode(enc)

    f = io.BytesIO()

    f.write(content)

    f.seek(0)

    self.send_response(200)

    self.send_header("Content-type","text/html; charset=%s"% enc)

    self.send_header("Content-Length",str(len(content)))

    self.end_headers()

    shutil.copyfileobj(f,self.wfile)

def log(data,ip):

    path_temp = os.path.split(os.path.realpath(__file__))[0];

    current_path = path_temp.replace("\\","/");

    filename = current_path +"/shubohui.log";

    f =open(filename,'a');

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()));

    f.write(timestamp +" IP : "+ip+":"+str(8765)+" | Parameter Body :"+str(data) +"\r\n");

    f.close();

    addr = ('',port)#随时接收任何端口的请求

    server = HTTPServer(addr,RequestHandler)

    server.serve_forever()