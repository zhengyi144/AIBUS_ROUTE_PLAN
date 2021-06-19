import numpy as np
import math
from app.utils.GPSConvertUtil import getGPSDistance
'''
模拟退火算法
'''
class SAOptimizer:
    def optimize(self,fun,yBound=(-np.inf,np.inf),initFun=np.random.random,\
                randFun=np.random.random,t=10000,alpha=0.98,stop=1e-1,iterPerT=1,l=1):
        '''
        fun:目标函数，接受np.array作为参数
        yBound:y的值范围
        initFun:目标函数的初始化权值函数取
        randFun:对参数的随机扰动函数，接受现有权值，返回扰动后的新权值np.array
        t:初始温度
        alpha:退火速率
        stop:停止退火温度
        iterPerT：每个温度下迭代次数
        l：新旧值相减后的乘数，越大，越不容易接受更差值
        '''
        yOld=None
        while yOld==None or yOld<yBound[0] or yOld>yBound[1]:
            xOld=initFun()
            yOld=fun(xOld)
        yBest=yOld
        xBest=np.copy(xOld)
        #降温过程
        count=0
        while(t>stop):
            downT=False
            for i in range(iterPerT):
                xNew=randFun(xOld)
                yNew=fun(xNew)
                if yNew>yBound[1] or yNew<yBound[0]:
                    continue
                #dE
                dE=-(yOld-yNew)*l
                if dE<0:
                    downT=True
                    count=0
                else:
                    count+=1
                if self.judge(dE,t):
                    xOld=xNew
                    yOld=yNew
                    if yOld<yBest:
                        yBest=yOld
                        xBest=xOld
            if downT:
                t=t*alpha
            #长时间不降温
            if count>1000:break
        
        return xBest,yBest
    
    def judge(self,dE,t):
        '''
        根据退火概率exp(-dE/kT)来决定是否决定新状态
        '''
        if dE<0:
            return 1
        else:
            p=np.exp(-dE/t)
            if p>np.random.random(size=1):
                return 1
            else: return 0


def tspSolution(destination,wayPoints):
    """
    利用模拟退火算法解决tsp问题
    params:
       destination:{lng,lat}
       wayPoints:[{id,lng,lat},{id,lng,lat}]
    """
    wayPoints.append(destination)
    wayPoints=np.array(wayPoints)
    #print(wayPoints)
    init = lambda :wayPoints #参数为城市序列
    #这里需要自定义扰动函数
    def randf(now):
        new = np.copy(now)
        size = new.shape[0]-1
        while 1:
            index1 = np.random.randint(size)
            index2 = np.random.randint(size)
            if index2 != index1: break
        temp = new[index1]
        new[index1] = new[index2]
        new[index2] = temp
        return new

    def f(weight):
        size = weight.shape[0]
        dist = 0
        for i in range(size - 1):
            dist+=getGPSDistance(weight[i]["lng"],weight[i]["lat"],weight[i+1]["lng"],weight[i+1]["lat"])#math.sqrt(pow(weight[i]["lng"]-weight[i+1]["lng"],2)+pow(weight[i]["lat"]-weight[i+1]["lat"],2))
        return dist

    sa = SAOptimizer()
    xbest,ybest = sa.optimize(f, initFun=init, randFun=randf, stop=1e-3, t=1e3, alpha=0.98, l=10, iterPerT=1)
    return xbest,ybest

"""
if __name__=="__main__":
    destination={"lng":7,"lat":1}
    wayPoints=[{"id":0,"lng":1,"lat":1},{"id":1,"lng":3,"lat":3},{"id":3,"lng":6,"lat":2},{"id":2,"lng":5,"lat":4}]
    tspSolution(destination,wayPoints)
"""
