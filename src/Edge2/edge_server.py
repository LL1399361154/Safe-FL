# -*- coding: utf-8 -*
import socket
from phe import paillier
from socketserver import BaseRequestHandler,ThreadingTCPServer
import threading
import ssl
import os
import time
import sys

devicenum=2                     #该边服务器有两个设备
num=0                           #记录当前收到了几个设备的梯度
lock=threading.Semaphore(1)     #num是临近资源，操作需要互斥
ciphergrad=[]                   #存储收到的梯度

currentdir='Edge2/'
cafile=currentdir+'server3.crt'
cafile1=currentdir+'server1.crt'
cafile2=currentdir+'server4.crt'
keyfile=currentdir+'server3.key'
bindip=('0.0.0.0',9995)
cloudip=('127.0.0.1',9997)
believableip=('127.0.0.1',9990)

#向边服务器获取publickey
client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sslsocket = ssl.wrap_socket(client_socket,ca_certs=cafile1,cert_reqs=ssl.CERT_REQUIRED)
while 1:
    try:
        sslsocket.connect(believableip)
        msg = 'Getkey'.encode('utf-8')
        sslsocket.sendall(msg)
        msg = sslsocket.recv(1024).decode('utf-8')
        public_key=paillier.PaillierPublicKey(int(msg))#拿到公钥
        sslsocket.close()
        break
    except ConnectionRefusedError:
        print('Believable服务器没开启，稍后重连')
        time.sleep(2)

class Handler(BaseRequestHandler):  
    def handle(self):
        global devicenum,num,ciphergrad
                    
        self.request.sendall(('当前剩余的待连接设备个数：{0}'.format(devicenum-num-1)).encode('utf-8'))

        #正常情况下，这里只会收到sendgrad……这样的信息，这个消息过长，可能需要接受多次
        data=''
        while True:
            tmp = self.request.recv(1024).decode('utf-8')
            if not tmp:
                break
            else:
                data+=tmp

        #聚合
        if data[:8]=='sendgrad':
            tmp=[int(x) for x in data[8:].split('\t')]
            grad=[]
            print('梯度列表的长度：',len(tmp))#调试信息
            for i in range(0,18,2):
                grad.append(paillier.EncryptedNumber(public_key,tmp[i],tmp[i+1]))

            #拿到第一个梯度，赋值
            lock.acquire()#P操作
            if num==0:
                ciphergrad=grad[:]
            #拿到第二个梯度，求和
            else:
                for i in range(9):
                    ciphergrad[i]+=grad[i]
            num+=1
            lock.release()#V操作

            print('获得的梯度数：',num)
        #聚合后，送往云处
            if num==devicenum:
                num=0
                tmp=[]
                for x in ciphergrad:
                    tmp.extend([x.ciphertext(),x.exponent])
                client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                sslsocket = ssl.wrap_socket(client_socket,ca_certs=cafile2,cert_reqs=ssl.CERT_REQUIRED)
                #尝试连接cloud服务器，并发送grad
                while 1:
                    try:
                        sslsocket.connect(cloudip)
                        ciphergrad=[str(x) for x in tmp]
                        msg = ('sendgrad'+'\t'.join(ciphergrad)).encode("utf-8")
                        sslsocket.sendall(msg)
                        print('grad消息的长度：',len(msg))
                        sslsocket.close()
                        ciphergrad=[]   #一轮结束，清空
                        break
                    except ConnectionRefusedError:
                        print('Cloud服务器没开启，稍后重连')
                        time.sleep(2)
        else:#接受到违背规则的请求
            print('error')
        print('close connection')
 
if __name__ == '__main__':
    if len(sys.argv)<=2:
        if len(sys.argv)==2:
            devicenum=int(sys.argv[1])
        try:
            server = ThreadingTCPServer(bindip,Handler) #参数为监听地址和已建立连接的处理类
            server.socket=ssl.wrap_socket(server.socket,keyfile=keyfile,certfile=cafile,server_side=True,ssl_version=ssl.PROTOCOL_SSLv23)
            print('listening-----------edge2')
            server.serve_forever() #监听，建立好TCP连接后，为该连接创建新的socket和线程，并由处理类中的handle方法处理
        except:
            os.system('pause')
    else:
        print('error arg')

