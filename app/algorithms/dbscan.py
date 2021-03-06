import os
import sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parentdir)
import itertools
from sklearn.cluster import DBSCAN
from numpy import *
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from math import *
#from utils.GPSConvertUtil import getGPSDistance
from app.utils.GPSConvertUtil import getGPSDistance
from app.utils.amapUtil import *
from app.utils.logger import get_logger

logger=get_logger(name="dbscan",log_file="logs/logger.log")

def haversine(lonlat1, lonlat2):
    """
    # 该函数是为了通过经纬度计算两点之间的距离（以公里为单位）
    lonlat1: 经纬度1
    lonlat2: 经纬度2
    """
    lat1, lon1 = lonlat1
    lat2, lon2 = lonlat2
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def calcClusterCenter(clusterDataFrame):
    """
    DBSCAN算法只能获取簇集合，因此还需确定簇中心点：
    #通过计算簇中心点，然后计算各点与中心点最小距离则为中心点
    clusterDataFrame:"id","lat","lng"  calcDistance(x["lng"],x["lat"],meanLng,meanLat)
    return:centerId
    """
    clusterDataFrame=clusterDataFrame.reset_index()
    meanLat=clusterDataFrame["lat"].mean()
    meanLng=clusterDataFrame["lng"].mean()
    clusterDataFrame["dist"]=clusterDataFrame.apply(lambda x:getGPSDistance(x["lng"],x["lat"],meanLng,meanLat),axis=1)
    minIndex=clusterDataFrame["dist"].idxmin()
    return clusterDataFrame.loc[minIndex,["id"]].values
    
def clusterByDbscan(dataList,epsRadius,minSamples):
    """
    # DBSCAN算法：将簇定义为密度相连的点最大集合，能够把具有足够高密度的区域划分为簇，并且可在噪声的空间数据集中发现任意形状的簇。
    # 密度：空间中任意一点的密度是以该点为圆心，以EPS为半径的圆区域内包含的点数目
    # 边界点：空间中某一点的密度，如果小于某一点给定的阈值min_samples,则称为边界点
    # 噪声点：不属于核心点，也不属于边界点的点，也就是密度为1的点
    #DBSCAN的算法，聚类结果不错，因为是按照设定的人的活动半径的密度可达来聚合的，但其结果是将数据集合分类，并不求出中心点。
    dataList:[{"id","lat","lng",""},{"id","lat","lng",""}],必需包括id,lat,lng字段
    epsRadius: 聚内直线距离(km)
    minSamples：最少点数目
    return：
    {'noiseIds': [24, 25], 'clusterSet': [{'clusterCoreIds': [20, 21, 26], 'clusterCenterId': 26.0, 'clusterAroundIds': []}, {'clusterCoreIds': [22, 23], 'clusterCenterId': 22.0, 'clusterAroundIds': []}]}
    """
    if epsRadius and dataList:
        df = pd.DataFrame(dataList)
        df["lat"]=df["lat"].astype(float)
        df["lng"]=df["lng"].astype(float)
        X=df[["lat","lng"]]
        distance_matrix = squareform(pdist(X, (lambda u, v: haversine(u, v))))
        #选取0.5公里（500m）作为密度聚合半径参数，在此使用球面距离来衡量地理位置的距离，来作为聚合的半径参数。
        # 聚合所需指定的min_samples数目为3个（一个聚合点至少是三个人）
        # db = DBSCAN(eps=0.5, min_samples=3, metric='precomputed')
        #如果你将metric设置成了precomputed的话,那么传入的X参数应该为各个向量之间的相似度矩阵,
        # 然后fit函数会直接用你这个矩阵来进行计算.否则的话,你还是要乖乖地传入(n_samples, n_features)形式的向量.
        db = DBSCAN(epsRadius,minSamples, metric='precomputed') #通过metric='precomputed'计算稀疏的半径临近图，这会节省内存使用
        db.fit(distance_matrix)#模型的训练
        y = db.fit_predict(distance_matrix)#模型的预测方法
        #标记聚类点对应下标为True
        coreSamplesMask = zeros_like(db.labels_,dtype=bool)
        coreSamplesMask[db.core_sample_indices_] = True
        #print(db.core_sample_indices_)
        #聚类标签（数组，表示每个样本所属聚类）和所有聚类的数量，标签-1对应的样本表示异常点
        clusterLabels = db.labels_
        uniqueClusterLabels = set(clusterLabels)
        nClusters = len(uniqueClusterLabels) - (-1 in clusterLabels)
        #print(nClusters)
        # 异常点
        clusterInfo ={}
        offset_mask = (clusterLabels == -1)
        noiseIds=df.loc[offset_mask,["id"]].values
        clusterInfo["noiseIds"]=noiseIds.flatten().tolist()
        
        clusterSet =[]
        for i,clusterLabel in enumerate(uniqueClusterLabels):
            #clusterIndex是个True/Fasle数组，其中True表示对应样本为聚类点
            clusterData={}
            if clusterLabel!=-1:
                clusterIndex =(clusterLabels==clusterLabel)
                #计算聚类点集的中心点
                clusterDf= df.loc[clusterIndex&coreSamplesMask,["id","lat","lng"]]
                clusterCorePoints=df.loc[clusterIndex&coreSamplesMask,["id"]].values
                clusterData["clusterCoreIds"]=clusterCorePoints.flatten().tolist()
                clusterData["clusterCenterId"]=calcClusterCenter(clusterDf)[0]
                #边界点
                aroundPoints= df.loc[(clusterIndex&~coreSamplesMask),["id"]].values
                clusterData["clusterAroundIds"]=aroundPoints.flatten().tolist()
                clusterSet.append(clusterData)
        clusterInfo["clusterSet"]=clusterSet

    return clusterInfo

def clusterByAdaptiveDbscan(siteList,epsRadius,minSamples,distType=1):
    """
    DBSCAN算法是将密度相连点的最大集合作为簇，但是由于簇内点会辐射出去的原因会使簇内一些点距离聚类中心点超过实际限定距离epsRadius，
    因此对DBSCAN算法进行改造，只取满足限定距离的最大集合，满足条件的集合但中心点已经被纳入其他集合，被抛弃的点作为边界点，
    不满足minSamples作为异常点
    siteList:[{"id","lat","lng","number",""},{"id","lat","lng","number",""}],必需包括id,lat,lng,number字段
    epsRadius: 聚内直线距离(km)
    minSamples：最少点数目
    """
    NOISE = "N"
    UNASSIGNED = "U"
    if epsRadius and minSamples and siteList:
        #1)先构造集合对，计算两两之间的距离
        sitePairInfo={}
        sitePairs=list(itertools.permutations(siteList, 2))
        routeNodeList=[]
        for sitePair in sitePairs:
            key=str(sitePair[0]["id"])+"-"+str(sitePair[1]["id"])
            dist=getGPSDistance(float(sitePair[0]["lng"]),float(sitePair[0]["lat"]),float(sitePair[1]["lng"]),float(sitePair[1]["lat"]))
            if dist<=epsRadius:
                fromNode=str(round(sitePair[0]["lng"],6))+","+str(round(sitePair[0]["lat"],6))
                toNode=str(round(sitePair[1]["lng"],6))+","+str(round(sitePair[1]["lat"],6))
                routeNodeList.append({"key":key,"origin":fromNode,"destination":toNode,"routeType":2})
            else:
                sitePairInfo[key]=dist
        
        #获取高德数据
        if len(routeNodeList)>0:
            nodeInfo=build_process(routeNodeList)
            logger.info("nodeInfo result:%s",nodeInfo)
            for key, value in nodeInfo.items():
                sitePairInfo[key]=value["dist"]
         
        #2)以每个点为中心找出限定范围内的点集
        neighborPointsList=[]
        clusterResult={}
        for site in siteList:
            neighborPoints=[]
            neighborNumber=site["number"] 
            neighborPoints.append(site["id"])
            clusterResult[site["id"]]=UNASSIGNED
            for point in siteList:
                if site["id"]!=point["id"]:
                    key=str(site["id"])+"-"+str(point["id"])
                    if sitePairInfo[key]<=epsRadius:
                        neighborPoints.append(point["id"])
            if len(neighborPoints)<minSamples:
                clusterResult[site["id"]]=NOISE
            else:
                neighborPointsList.append({"id":site["id"],"neighborPoints":neighborPoints,"size":len(neighborPoints),"number":neighborNumber})
        
        #3)对上面点集进行按照点集大小排序，然后筛选出聚类集合
        neighborPointsList.sort(key=lambda x: (x["size"],x["number"],x["id"]),reverse=True)
        logger.info("neightbor point sort result:%s",neighborPointsList)
        clusterDict={}
        for item in neighborPointsList:
            #先判断id是否已经被划分
            if clusterResult[item["id"]]==UNASSIGNED:
                clusterResult[item["id"]]=item["id"]
                clusterDict[item["id"]]=set()
                clusterDict[item["id"]].add(item["id"])

                for idx in item["neighborPoints"]:
                    #只标注未被聚类的点
                    if clusterResult[idx]==UNASSIGNED or clusterResult[idx]==NOISE:
                        clusterResult[idx]=item["id"]
                        clusterDict[item["id"]].add(idx)
                clusterDict[item["id"]]=list(clusterDict[item["id"]])
                #重新判断聚类集合是否满足要求
                if len(clusterDict[item["id"]])<minSamples:
                    for idx in clusterDict[item["id"]]:
                        clusterResult[idx]=UNASSIGNED
                    del clusterDict[item["id"]]

        #4)返回聚类核心点、边界点点集、异常点集
        noiseList=[]
        aroundList=[]
        for key in clusterResult.keys():
            if clusterResult[key]==UNASSIGNED:
                aroundList.append(key)
            elif clusterResult[key]==NOISE:
                noiseList.append(key)
        return {"noiseList":noiseList,"aroundList":aroundList,"clusterDict":clusterDict}

"""
if __name__=="__main__":

    #eps:DBSCAN算法参数，即我们的ϵ-邻域的距离阈值，和样本距离超过ϵ的样本点不在ϵ-邻域内。默认值是0.5.
    # 一般需要通过在多组值里面选择一个合适的阈值。eps过大，则更多的点会落在核心对象的ϵ-邻域，
    # 此时我们的类别数可能会减少， 本来不应该是一类的样本也会被划为一类。反之则类别数可能会增大，本来是一类的样本却被划分开
    eps=1.5 #选取0.5公里（500m）作为密度聚合半径参数，在此使用球面距离来衡量地理位置的距离，来作为聚合的半径参数。

    #min_samples： DBSCAN算法参数，即样本点要成为核心对象所需要的ϵ-邻域的样本数阈值。默认值是5.
    #  一般需要通过在多组值里面选择一个合适的阈值。通常和eps一起调参。在eps一定的情况下，min_samples过大，
    # 则核心对象会过少，此时簇内部分本来是一类的样本可能会被标为噪音点，类别数也会变多。
    # 反之min_samples过小的话，则会产生大量的核心对象，可能会导致类别数过少。
    min_samples=2#聚合所需指定的min_samples数目为3个（一个聚合点至少是三个人）

    latList = [119.27469246249998,119.274848,119.32690238333333,119.32710,118.27469246249998,118.32690238333333,117.927469246249998,116.32690238333333,119.274748]#假设有两个候选点
    lngList = [26.026210115,26.02731,26.140896100000003,26.140906,25.026210115,25.140896100000003,24.026210115,20.140896100000003,26.02631]
    data=[{"id":20,"lng":119.27469246249998,"lat":26.026210115},{"id":21,"lng":119.274848,"lat":26.02731},{"id":22,"lng":119.32690238333333,"lat":26.140896100},\
          {"id":23,"lng":119.32710,"lat":26.140906},{"id":24,"lng":118.274692462,"lat":25.026210115},{"id":25,"lng":118.326902,"lat":25.1408961},{"id":26,"lng":119.274748,"lat":26.02631}]
    # canCent=[]#默认为空
    clusterInfo=clusterByDbscan(data,eps,min_samples)
    print(clusterInfo)
"""
"""
if __name__=="__main__":
    data=[{"id":0,"lng":119.310162,"lat":26.098756},{"id":1,"lng":119.311964,"lat":26.100529},{"id":2,"lng":119.309303,"lat":26.100529},{"id":3,"lng":119.306986,"lat":26.09945},\
        {"id":4,"lng":119.33501,"lat":26.100182},{"id":5,"lng":119.335525,"lat":26.096944},{"id":6,"lng":119.332349,"lat":26.100953},\
        {"id":7,"lng":119.327328,"lat":26.097638},{"id":8,"lng":119.315097,"lat":26.086307},{"id":9,"lng":119.335267,"lat":26.100684},
        {"id":10,"lng":119.311428,"lat":26.098006},{"id":23,"lng":119.32710,"lat":26.140906},{"id":24,"lng":118.274692462,"lat":25.026210115},{"id":25,"lng":118.326902,"lat":25.1408961},{"id":26,"lng":119.274748,"lat":26.02631}]
    print(clusterByAdaptiveDbscan(data,1000,5))
"""

    

