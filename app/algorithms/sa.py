import numpy as np
import math
from copy import deepcopy
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
        if isinstance(xOld, np.ndarray):
            xBest=np.copy(xOld)
        elif isinstance(xOld,dict):
            xBest=deepcopy(xOld)
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
                        if isinstance(xOld, np.ndarray):
                            xBest=np.copy(xOld)
                        elif isinstance(xOld,dict):
                            xBest=deepcopy(xOld)
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
    xbest,ybest = sa.optimize(f, initFun=init, randFun=randf, stop=1e-3, t=2e4, alpha=0.98, l=10, iterPerT=1)
    return xbest,ybest

def singleRoutePlanSolution(routeInfo):
    """
    单路线规划解决方案
    routeInfo:[{nodePair,routeNode,routeFactor}  
    nodePair:{key:{dist,time},...}  结点对
    routeNode:[{index,nodeName,lng,lat,number},...]  结点信息
    routeFactor: 路线方案，0时间最短，1距离最短
    """
    routeInfo["routeNode"]=np.array(routeInfo["routeNode"])
    init = lambda :routeInfo #参数为城市序列
    #这里需要自定义扰动函数
    def randf(now):
        routeNode=now["routeNode"]
        new = np.copy(routeNode)
        size = new.shape[0]-1
        while 1:
            index1 = np.random.randint(size)
            index2 = np.random.randint(size)
            if index2 != index1: break
        temp = new[index1]
        new[index1] = new[index2]
        new[index2] = temp
        now["routeNode"]=new
        return now

    def f(X):
        routeNode=X["routeNode"]
        nodePair=X["nodePair"]
        routeFactor=X["routeFactor"]
        size = routeNode.shape[0]
        cost = 0
        for i in range(size - 1):
            key=str(routeNode[i]["index"])+"-"+str(routeNode[i+1]["index"])
            if routeFactor==0:
                cost+=nodePair[key]["time"]
            else:
                cost+=nodePair[key]["dist"]
        #print("cost",cost)
        return cost

    sa = SAOptimizer()
    xbest,ybest = sa.optimize(f, initFun=init, randFun=randf, stop=1e-3, t=1e4, alpha=0.98, l=10, iterPerT=1)
    return {"routeNode":xbest["routeNode"].tolist(),"bestRouteCost":ybest}

def singleRoutePlanByGreedyAlgorithm(routeNode,nodePair,nodeCostDF,passengers,occupancyRate,orderNumber,odometerFactor,maxDistance,maxDuration):
    """
    nodePair:{key:{dist,time,directDist},...}  结点对
    routeNode:[{index,nodeName,lng,lat,number},...]  结点信息
    nodeCostDF:时间或者距离dataframe
    passengers:座位上限
    occupancyRate:上座率
    orderNumber:订单数
    odometerFactor:非直线率
    maxDistance:最大行程距离
    maxDuration:最大行程时间

    贪婪算法从目的地开始找距离最近的结点，判断是否满足passengers/occupancyRate/odometerFactor/maxDistance/maxDuration,
    如果超出限制条件后还未查找到符合的路线则返回
    """
    #将routeNode转为dict
    nodeDict={}
    for node in routeNode:
        nodeDict[str(node["index"])]=node

    pointKeys=list(nodeCostDF.columns)
    #print(pointKeys)
    endKey="dest"
    pointKeys.remove(endKey)

    routeList=[]
    #将每个结点作为起始点,找出符合条件的所有路线
    for pointKey in pointKeys:
        startKey=pointKey
        tempKeys=deepcopy(pointKeys)
        tempKeys.remove(startKey)
        startToEnd=startKey+"-"+endKey
        #初始化路线参数
        routeNumber=nodeDict[startKey]["number"]
        routeDist=nodePair[startToEnd]["dist"]
        routeTime=nodePair[startToEnd]["time"]
        routeDirectDist=nodePair[startToEnd]["directDist"]
        routeCost=nodeCostDF.loc[startKey,endKey]
        routeKeys=[]
        routeKeys.append(startKey)
        while len(tempKeys)>0 and routeDist<routeDirectDist*odometerFactor and routeNumber<passengers\
            and routeDist<maxDistance and routeTime<maxDuration:
            #找出startkey距离最近的下一结点
            series=nodeCostDF.loc[startKey,tempKeys]
            minIndex=series.argmin()
            minKey=series.index[int(minIndex)]
            routeKeys.append(minKey)
            #重新计算起始结点至终点的实际距离和路线人数
            routeDist=0
            routeTime=0
            for i in range(0,len(routeKeys)-1):
                nodeKey=routeKeys[i]+"-"+routeKeys[i+1]
                routeDist+=nodePair[nodeKey]["dist"]
                routeTime+=nodePair[nodeKey]["time"]
            nodeKey=routeKeys[len(routeKeys)-1]+"-"+endKey
            routeDist+=nodePair[nodeKey]["dist"]
            routeTime+=nodePair[nodeKey]["time"]
            routeNumber+=nodeDict[minKey]["number"]
            #对比直线系数是否满足要求和人数是否满足要求
            if routeDist<=routeDirectDist*odometerFactor and routeNumber<=passengers\
               and routeDist<maxDistance and routeTime<maxDuration:
                routeCost+=series[minIndex]
                startKey=minKey
            else:
                routeKeys.remove(minKey)
                routeNumber-=nodeDict[minKey]["number"]
            tempKeys.remove(minKey)
            
        #将符合条件的路线都加入routeList
        if len(routeKeys)>1 and routeNumber>orderNumber*occupancyRate/100:
            routeList.append({"startKey":pointKey,"routeNumber":routeNumber,\
                    "routeKeys":routeKeys,"routeCost":routeCost,"routeDist":routeDist,\
                    "routeDirectDist":routeDirectDist})

    #按照结点数量、人数、routeCost进行排序
    routeList.sort(key=lambda x: (len(x["routeKeys"]),x["routeNumber"],x["routeCost"]),reverse=True)

    #取出第一条作为最优路线
    if len(routeList)<=0:
        #未规划点
        invalidRouteNode=[]
        for key in list(nodeCostDF.columns):
            invalidRouteNode.append(nodeDict[key])
        return {"routeNode":None,"invalidRouteNode":invalidRouteNode,\
            "bestRouteCost":0,"routeNumber":0,\
            "routeDist":0,"routeDirectDist":0}
    else:
        #路径点
        bestRouteNode=[]
        bestRouteKeys=routeList[0]["routeKeys"]
        for key in bestRouteKeys:
            bestRouteNode.append(nodeDict[key])
        bestRouteNode.append(nodeDict[endKey])
        
        #未规划点
        invalidRouteNode=[]
        for key in list(nodeCostDF.columns):
            if key not in bestRouteKeys and key !=endKey:
                invalidRouteNode.append(nodeDict[key])
        return {"routeNode":bestRouteNode,"invalidRouteNode":invalidRouteNode,\
            "bestRouteCost":routeList[0]["routeCost"],"routeNumber":routeList[0]["routeNumber"],\
            "routeDist":routeList[0]["routeDist"],"routeDirectDist":routeList[0]["routeDirectDist"]}

    """
    routeKeys=[]
    bestRouteKeys=None
    bestRouteCost=0
    routeKeys.insert(0,startKey)
    routeNumber=0
    routeDist=0
    routeDirectDist=0
    routeCost=0
    while len(pointKeys)>0 and routeNumber<passengers:
        series=nodeCostDF.loc[pointKeys,startKey]
        minIndex=series.argmin()
        #print("minIndex:{}".format(minIndex))
        minKey=series.index[int(minIndex)]
        routeCost+=series[minIndex]
        routeKeys.insert(0,minKey)
        #获取minKey对应结点的信息
        routeNumber+=nodeDict[minKey]["number"]
        nodeKey=minKey+"-"+startKey
        routeDist+=nodePair[nodeKey]["dist"]
        routeDirectDist+=nodePair[nodeKey]["directDist"]
        if routeNumber>orderNumber*occupancyRate/100 and float(routeDist*1.0)/routeDirectDist<=odometerFactor and routeNumber<=passengers:
            bestRouteKeys=np.copy(np.array(routeKeys))
            bestRouteCost=routeCost
        pointKeys.remove(minKey)
        startKey=minKey
    
    if bestRouteKeys is None:
        #未规划点
        invalidRouteNode=[]
        for key in list(nodeCostDF.columns):
            invalidRouteNode.append(nodeDict[key])
        return {"routeNode":None,"invalidRouteNode":invalidRouteNode,"bestRouteCost":bestRouteCost,"routeNumber":routeNumber,"routeDist":routeDist,"routeDirectDist":routeDirectDist}
    else:
        #路径点
        bestRouteNode=[]
        bestRouteKeys=bestRouteKeys.tolist()
        for key in bestRouteKeys:
            bestRouteNode.append(nodeDict[key])
        
        #未规划点
        invalidRouteNode=[]
        for key in list(nodeCostDF.columns):
            if key not in bestRouteKeys:
                invalidRouteNode.append(nodeDict[key])
        return {"routeNode":bestRouteNode,"invalidRouteNode":invalidRouteNode,"bestRouteCost":bestRouteCost,"routeNumber":routeNumber,"routeDist":routeDist,"routeDirectDist":routeDirectDist}
        

    """
    
"""
if __name__=="__main__":
    destination={"lng":7,"lat":1}
    wayPoints=[{"id":0,"lng":1,"lat":1},{"id":1,"lng":3,"lat":3},{"id":3,"lng":6,"lat":2},{"id":2,"lng":5,"lat":4}]
    tspSolution(destination,wayPoints)
"""
