# -*- coding: utf-8 -*
import socket
from phe import paillier
from socketserver import BaseRequestHandler,ThreadingTCPServer
import threading
import ssl
import os
import sys
n=103137711908459749008675703156179202060099188611451698862152164174844363177189949791581867550510388530433164216568426387085788768470603452552962425567820801742849040774249157410525589084301274421232038511153980146434027940463640040114127907511805959733540235860629883526963367149745347782236948461470070100951
p=8726010827357079941107610436467323503356946523965064153944786898883814121376375728527494740233734076731079985180105983616610200372166012498010156701860799
q=11819571846634750570171644836163270600188214561347496429590863593080262562280670170203921505171717382856979361538822794275464530041627426769623542283638249

public_key=paillier.PaillierPublicKey(n)
private_key=paillier.PaillierPrivateKey(public_key,p,q)
W=[0.0 for i in range(9)]
lr=0.01

devicenum=4
flag=0  #用于标记有没有从云得到grad
s=threading.Semaphore(1)

currentdir='Believable/'
cafile=currentdir+'server1.crt'
keyfile=currentdir+'server1.key'
bindip=('0.0.0.0',9990)

class Handler(BaseRequestHandler):  
    def handle(self):
        global W,flag,lr
        data=''
        while True:
            tmp = self.request.recv(1024).decode('utf-8')
            if tmp=='Getkey' or tmp=='Getw':
                data=tmp
                break
            elif not tmp:
                break
            else:
                data+=tmp

        #下发公钥
        if data=='Getkey':
            self.request.sendall(str(public_key.n).encode('utf-8'))
            print('Sendkey to device/server')

        #下发W权值
        elif data=='Getw':
            if flag and W[0]!=0.0:
                msg='Sendw'+'\t'.join([str(x) for x in W])
                self.request.sendall(msg.encode('utf-8'))

                s.acquire()     #多个线程可能修改flag
                flag-=1
                s.release()

                print('Sendw to device')

        #得到了grad，进行解密
        elif data[0:8]=='sendgrad':
            #print(data)
            tmp=[int(x) for x in data[8:].split('\t')]
            grad=[]
            for i in range(0,18,2):
                grad.append(private_key.decrypt(paillier.EncryptedNumber(public_key,tmp[i],tmp[i+1])))
            for i in range(9):
                W[i]=W[i]-lr*grad[i]
            print('Getgrad from Cloud')

            flag=devicenum
        else:
            print(f'error:{data}')
 
if __name__ == '__main__':
    if len(sys.argv)<=2:
        if len(sys.argv)==2:
            devicenum=int(sys.argv[1])
        try:
            server = ThreadingTCPServer(bindip,Handler) #参数为监听地址和已建立连接的处理类
            server.socket=ssl.wrap_socket(server.socket,keyfile=keyfile,certfile=cafile,server_side=True,ssl_version=ssl.PROTOCOL_SSLv23)
            print('listening-----------believable_server')
            server.serve_forever() #监听，建立好TCP连接后，为该连接创建新的socket和线程，并由处理类中的handle方法处理
        except:
            os.system('pause')
    else:
        print('error arg')