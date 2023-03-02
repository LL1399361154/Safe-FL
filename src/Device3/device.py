import random
import math
import socket
import paillier #修改后的paillier
import time
import os
import ssl
import sys

currentdir='./'               
cafile1=currentdir+'server1.crt'    #可信服务器的证书
cafile2=currentdir+'server3.crt'    #边服务器的证书
Rfile=currentdir+'R-14-7.txt'       #随机数的预计算文件
trainfile=currentdir+'train.txt'   #训练集
testfile=currentdir+'test.txt'      #测试集
log=currentdir+"log3.txt"
ip_believable=('127.0.0.1',9990)    #可信服务器ip
ip_edge=('127.0.0.1',9995)         #边服务器ip


class client_class:
    def __init__(self,filefd):
        self.data4train = [] 	#训练集, 假设每个样本的特征数量都一样
        self.data4test = [] 	#测试集, 假设每个样本的特征数量都一样
        self.lm = 0.0001 		#对权值做正则化限制的权重
        self.W = [0.0 for v in range(10)] #当前模型
        self.iterations = 1	#迭代次数
        self.dim=9 #数据的维度
        self.test_start=0 #用于时间的测试
        self.test_end=0 #用于时间的测试
        self.file=filefd
        #将预计算的随机数读取到内存
        f=open(Rfile,'rb')
        self.Rs=f.read()
        f.close()
        #通过Getkey向可信服务器获取公钥
        context=ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sslsocket = ssl.wrap_socket(client_socket,ca_certs=cafile1,cert_reqs=ssl.CERT_REQUIRED)
        while 1:
            try:
                sslsocket.connect(ip_believable)
                msg = 'Getkey'.encode('utf-8')
                sslsocket.sendall(msg)
                msg = sslsocket.recv(1024).decode('utf-8')
                self.public_key=paillier.PaillierPublicKey(int(msg))
                sslsocket.close()
                break
            except ConnectionRefusedError:
                self.file.write('Believable服务器没开启，稍后重连\n')
                time.sleep(2)
        self.nsquare=self.public_key.n*self.public_key.n
        self.num=7
        self.total=16384
    #加载数据，格式为:   (lable,[,,...,,])    
    def load_data(self,filename,data):
        for line in open(filename, 'rt'):
            sample=[]
            line = line.rstrip("\r\n\t ")
            fields = line.split("\t")
            label = int(fields[9]) # LABEL取值: 1 or -1
            for x in fields[:9]:
                sample.append(float(x))
            data.append((label, sample))
    #训练数据
    def getr(self):
        sel=[random.randrange(self.total) for i in range(self.num)]
        res=[0 for i in range(self.num)]
        for i in range(self.num):
            res[i]=int().from_bytes(self.Rs[sel[i]*256:sel[i]*256+256],byteorder='big',signed='False')
        r=1
        for x in res:
            r*=x
        return r%self.nsquare

    def svm_train(self):
        grad = [0.0 for v in range(self.dim)]               #梯度

        #批量梯度下降
        for index in range(len(self.data4train)):
            y = self.data4train[index][0]                       #y是label
            X = self.data4train[index][1][:]                    #存储sample
            WX = 0.0
            for j in range(0, self.dim):
                WX += self.W[j] * X[j]
            if 1 - WX *y > 0:
                for j in range(0, self.dim):
                    grad[j] += self.lm * self.W[j] - X[j] * y   #求各个维度的grad，并求和
            else:                                               # 1-WX *y <= 0的时候，目标函数的前半部分恒等于0, 梯度也是0
                for j in range(0, self.dim):
                    grad[j] += self.lm * self.W[j] - 0
        self.file.write(str(grad)+'\n')
        #加密grad
        self.test_start=time.process_time() 
        return [self.public_key.encrypt(x,obfuscator=self.getr()) for x in grad]
    def svm_predict(self, data, W):
        num_correct = 0
        for i in range(len(data)):
            target = data[i][0] #即label
            X = data[i][1] # 即sample
            sum = 0.0
            for j in range(0, 9):
                sum += X[j] * W[j]
            predict = -1
            if sum > 0:  #权值>0，认为目标值为1
                predict = 1
            if predict*target>0: #预测值和目标值符号相同
                num_correct += 1
        return num_correct * 1.0 / len(data) #返回正确率
    def send_grad(self):
        #加载数据集
        self.load_data(trainfile,self.data4train)
        self.load_data(testfile,self.data4test)
        for i in range(self.iterations):
            ciphergrad=self.svm_train()#得到梯度
            #给边服务器梯度
            tmp=[]
            for x in ciphergrad:
                tmp.extend([x.ciphertext(),x.exponent])
            context=ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sslsocket = ssl.wrap_socket(client_socket,ca_certs=cafile2,cert_reqs=ssl.CERT_REQUIRED)
            #尝试连接边服务器，并发送grad
            while 1:
                try:
                    sslsocket.connect(ip_edge)
                    msg=sslsocket.recv(1024).decode('utf-8')
                    self.file.write(msg+'\n')

                    ciphergrad=[str(x) for x in tmp]
                    msg = ('sendgrad'+'\t'.join(ciphergrad)).encode("utf-8")
                    sslsocket.sendall(msg)              #发送grad

                    sslsocket.close()
                    break
                except ConnectionRefusedError:
                    self.file.write('edge服务器没开启，稍后重连\n')
                    time.sleep(2)
            #请求更新后的W，如果连接失败，则退出程序
            #服务解密需要时间，不断的申请W
            while True:
                try:
                    context=ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                    client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    sslsocket = ssl.wrap_socket(client_socket,ca_certs=cafile1,cert_reqs=ssl.CERT_REQUIRED)
                    sslsocket.connect(ip_believable)
                    msg='Getw'.encode('utf-8')
                    sslsocket.sendall(msg)#发送请求
                    msg=sslsocket.recv(1024).decode('utf-8')#接受W
                    sslsocket.close()
                    if msg and msg[:5]=='Sendw':
                        break
                except:
                    self.file.write('Believable服务器掉线了，稍后重连\n')
                    exit(-1)
            #更新W
            self.test_end=time.process_time() 
            self.file.write('从加密grad到得到新模型的耗时：'+str(self.test_end-self.test_start)+'\n')
            self.W=[float(x) for x in msg[5:].split('\t')]
            self.file.write(str(self.W)+'\n')
        acc=self.svm_predict(self.data4test,self.W)
        self.file.write(f'accurracy: {acc}'+'\n')
        return acc 
def start(config:dict,path):
    '''
    config sample:
    config={  # Global Var
    "believable_ip":"127.0.0.1",
    "believable_port":9990,
    "edge_ip":"127.0.0.1",
    "edge_port":9995
    }
    or Default Settings
    '''
    global currentdir,cafile1,cafile2,Rfile,trainfile,testfile,log
    global ip_believable
    global ip_edge
    ip_believable=(config["believable_ip"],int(config["believable_port"]))
    ip_edge=(config["edge_ip"],int(config["edge_port"]))
    currentdir=path
    cafile1=currentdir+'server1.crt'    #可信服务器的证书
    cafile2=currentdir+'server3.crt'    #边服务器的证书
    Rfile=currentdir+'R-14-7.txt'       #随机数的预计算文件
    trainfile=currentdir+'train.txt'   #训练集
    testfile=currentdir+'test.txt'      #测试集
    log=currentdir+"log3.txt"


    file=open(log,'a')
    start=time.time()
    client = client_class(file)
    file.write('device1')
    acc=client.send_grad()
    end=time.time()
    file.write('Time span={0}'.format(end-start))
    file.close()
    return (end-start,acc)          


'''
if __name__ == "__main__":
    if len(sys.argv)==7:
        file=open('log.txt','a')

        ip_believable=(sys.argv[1],int(sys.argv[2]))    #可信服务器ip
        ip_edge=(sys.argv[3],int(sys.argv[4]))          #边服务器ip
        trainfile=currentdir+sys.argv[5]   #训练集
        testfile=currentdir+sys.argv[6]      #测试集
        try:
            client = client_class()
            #self.file.write('device1\n')
            client.send_grad()

            self.file.close()

            os.system('pause')
        except:
            os.system('pause')
    else:
        self.file.write('error arg\n')
'''
