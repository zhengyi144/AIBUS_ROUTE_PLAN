from sklearn.cluster import DBSCAN
from numpy import *
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from math import *

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



def clusteringByDbscan(latList,lngList,epsRadius,minSamples):
    """
    # DBSCAN算法：将簇定义为密度相连的点最大集合，能够把具有足够高密度的区域划分为簇，并且可在噪声的空间数据集中发现任意形状的簇。
    # 密度：空间中任意一点的密度是以该点为圆心，以EPS为半径的圆区域内包含的点数目
    # 边界点：空间中某一点的密度，如果小于某一点给定的阈值min_samples,则称为边界点
    # 噪声点：不属于核心点，也不属于边界点的点，也就是密度为1的点
    #DBSCAN的算法，聚类结果不错，因为是按照设定的人的活动半径的密度可达来聚合的，但其结果是将数据集合分类，并不求出中心点。
    latList: 纬度数据
    lngList: 经度数据
    epsRadius: 聚内直线距离
    minSamples：最少点数目
    """
    if epsRadius and latList and lngList:
        X = pd.DataFrame({"lat":latList,"lng":lngList})
        distance_matrix = squareform(pdist(X, (lambda u, v: haversine(u, v))))
        #选取0.5公里（500m）作为密度聚合半径参数，在此使用球面距离来衡量地理位置的距离，来作为聚合的半径参数。
        # 聚合所需指定的min_samples数目为3个（一个聚合点至少是三个人）
        # db = DBSCAN(eps=0.5, min_samples=3, metric='precomputed')
        #如果你将metric设置成了precomputed的话,那么传入的X参数应该为各个向量之间的相似度矩阵,
        # 然后fit函数会直接用你这个矩阵来进行计算.否则的话,你还是要乖乖地传入(n_samples, n_features)形式的向量.
        db = DBSCAN(epsRadius,minSamples, metric='precomputed') #通过metric='precomputed'计算稀疏的半径临近图，这会节省内存使用
        db.fit(distance_matrix)#模型的训练
        y_db = db.fit_predict(distance_matrix)#模型的预测方法
        #标记聚类点对应下标为True
        coreSamplesMask = zeros_like(db.labels_,dtype=bool)
        coreSamplesMask[db.core_sample_indices_] = True
        #聚类标签（数组，表示每个样本所属聚类）和所有聚类的数量，标签-1对应的样本表示异常点
        clusterLabels = db.labels_
        uniqueClusterLabels = set(clusterLabels)
        nClusters = len(uniqueClusterLabels) - (-1 in clusterLabels)
        print(nClusters)
        # X['cluster'] = y_db
        # print(X['lat'], X['lng'], X['cluster'])
        # print(X)
        # print(X.values)
        # 异常点
        offset_mask = (clusterLabels == -1)
        
        noiseSamples=X[offset_mask].values
        # #聚类点
        # coreSamples= X[coreSamplesMask].values
        # #边界点
        # p_mask = ~(coreSamplesMask | offset_mask)
        # aroundSamples= X[p_mask].values#X['lat'], X['lng'], X['cluster']

        clusterSet =[]
        # aroundSet ={}
        for i,cluster in enumerate(uniqueClusterLabels):
            # offset_mask = (cluster == -1)
            # noiseSamples1= X[offset_mask]
            #clusterIndex是个True/Fasle数组，其中True表示对应样本为聚类点
            if cluster!=-1:
                clusterIndex =(clusterLabels==cluster)
                #聚类点
                coreSamples= X[clusterIndex&coreSamplesMask].values
                #聚类网点id
                clusterInfo ={}
                clusterInfo['siteSet'] = i
                clusterInfo['locationset'] = coreSamples
                clusterSet.append(clusterInfo)
                #边界点
                aroundSamples= X[(clusterIndex&~coreSamplesMask)].values
            # noiseSamples= X[cluster== -1]


    return clusterSet,noiseSamples,aroundSamples


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

    latList = [119.27469246249998,119.274748,119.274848,119.32690238333333,119.32710,118.27469246249998,118.32690238333333,117.927469246249998,116.32690238333333]#假设有两个候选点
    lngList = [26.026210115,26.02631,26.02731,26.140896100000003,26.140906,25.026210115,25.140896100000003,24.026210115,20.140896100000003]
    # canCent=[]#默认为空
    coreSamples,nosieSamples,aroundSamples =clusteringByDbscan(latList,lngList,eps,min_samples)
    print(coreSamples)
    print(nosieSamples)
    print(aroundSamples)
