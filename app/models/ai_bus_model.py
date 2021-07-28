import logging
from re import S
from threading import Condition
from flask import current_app
from numpy import insert, select
from werkzeug.wrappers import CommonRequestDescriptorsMixin
from app.utils.mysql import MysqlPool


class AiBusModel:
    def __init__(self):
        host=current_app.config["MYSQL_ADDRESS"]
        port=current_app.config["MYSQL_PORT"]
        user=current_app.config["MYSQL_USERNAME"]
        passwd=current_app.config["MYSQL_PASSWORD"]
        db=current_app.config["MYSQL_DB"]
        self.mysqlPool=MysqlPool(host,port,user,passwd,db)
    
    def selectUserByUserInfo(self,userName,password):
        """
        查询tbl_user表中是否存在username
        """
        queryStr="select userName from tbl_user where userName=%s and password=%s"
        row=self.mysqlPool.fetchOne(queryStr,(userName,password))
        return row
    
    def selectSubUserByUserName(self,userName,citycode):
        """
        根据userName查找下级userName
        """
        queryStr="SELECT r.userName FROM tbl_user t LEFT JOIN tbl_user r ON r.pid=t.id WHERE t.userName =%s and t.cityCode=%s"
        return self.mysqlPool.fetchAll(queryStr,(userName,citycode))
        
    
    def insertStation(self,row,geojson):
        """
        插入tbl_station
        """

        insertStr="insert into tbl_station(province,city,region,siteName,siteProperty,siteStatus,direction,longitude,latitude,road,unilateral,userCitycode,createUser,updateUser,location)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromGeoJSON( '"+geojson +"',2,0))"
        row=self.mysqlPool.insert(insertStr,row)
        return row
    
    def updateStation(self,row,geojson):
        """
        更新tbl_station
        """
        updateStr="update tbl_station \
                  set province=%s,city=%s,region=%s,siteName=%s,siteProperty=%s,\
                  siteStatus=%s,direction=%s,longitude=%s,latitude=%s,location=ST_GeomFromGeoJSON( '"+geojson +"',2,0),\
                  road=%s,unilateral=%s,userCitycode=%s,updateUser=%s  \
                  where id=%s "
        row=self.mysqlPool.insert(updateStr,row)
        return row
    
    def batchStation(self,rows):
        """
        插入tbl_station
        """
        batchStr="insert into tbl_station(province,city,region,siteName,siteProperty,direction,longitude,latitude,road,userCitycode,createUser,updateUser,location)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromGeoJSON(%s,2,0))"
        row=self.mysqlPool.batch(batchStr,rows)
        return row
    
    def selectStationNameByText(self,queryText,citycode,userNames):
        """
        模糊查询stationName
        """
        selectStr="select id,siteName,if(siteProperty=1,'固定','临时') as siteProperty,province,city,region,road,longitude,latitude \
                   from tbl_station where siteName like %s "
        authStr="and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        row=self.mysqlPool.fetchAll(selectStr+authStr,(('%'+queryText+'%')))
        return row
    
    def selectRoadByText(self,queryText,userNames):
        """
        模糊查询stationName
        """
        selectStr="select province,city,region,road from tbl_station where road like %s "
        authStr="and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        row=self.mysqlPool.fetchAll(selectStr+authStr,(('%'+queryText+'%')))
        return row

    def selectStationList(self,province,city,siteName,road,siteStatus,pageSize,pageNum,citycode,userNames):
        """
        查询站点列表
        """
        args=[]
        
        selectStr="select id,siteName,if(siteProperty=1,'固定','临时') as siteProperty,province,city,region,road,direction,longitude,latitude,\
                   (case when siteStatus=1 then '有效' when siteStatus=2 then '无效' when siteStatus=3 then '停用' end) as siteStatus,\
                   if(unilateral=0,'否','是') as unilateral,\
                   updateTime,updateUser from tbl_station where userCitycode=%s"
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        selectStr=selectStr+authStr
        
        args.append(citycode)
        if province is not None and province !="":
            selectStr+=" and province=%s"
            args.append(province)
        if city is not None and city !="":
            selectStr+=" and city=%s"
            args.append(city)
        if siteName is not None and siteName !="":
            selectStr+=" and siteName=%s"
            args.append(siteName)
        if road is not None and road !="":
            selectStr+=" and road=%s"
            args.append(road)
        if siteStatus is not None and siteStatus !="":
            if siteStatus=="有效":
                siteStatus=1
            elif siteStatus=="无效":
                siteStatus=2
            else:
                siteStatus=3
            selectStr+=" and siteStatus=%s"
            args.append(siteStatus)
        #计算总数
        countStr="select count(1) as num from ( " +selectStr+") a"
        res=self.mysqlPool.fetchOne(countStr,args)
        selectStr+=" order by updateTime desc,id desc limit %s ,%s"
        args.append(pageNum*pageSize)
        args.append(pageSize)
        return res["num"],self.mysqlPool.fetchAll(selectStr,args)
    
    def insertSiteFile(self,row):
        """
        插入网点文件信息
        """
        insertStr="insert into tbl_site_files(fileName,fileProperty,fileStatus,siteCount,destination,mapType,longitude,latitude,userCitycode,createUser,updateUser)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
    
    def selectSiteFileIdByFileName(self,row):
        """
        根据文件名查找
        """
        selectStr="select max(id) as id from tbl_site_files where fileName=%s"
        row=self.mysqlPool.fetchOne(selectStr,row)
        return row

    def selectFileList(self,citycode,userNames):
        """
        查询网点文件和聚类文件列表
        """
        selectStr="select id as fileId, fileName,siteCount,null as clusterFileName,null as clusterFileId,clusterMinSamples,clusterRadius,\
                   destination,longitude,latitude from tbl_site_files t where t.userCitycode=%s and t.fileStatus=1 "
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        orderStr=" order by id desc "
        selectStr=selectStr+authStr+orderStr
        return self.mysqlPool.fetchAll(selectStr,(citycode))
    
    def selectSiteFileList(self,citycode,userNames):
        """
        查询网点文件列表
        """
        selectStr="select id as fileId, fileName,siteCount,destination,longitude,latitude from tbl_site_files t where t.userCitycode=%s and t.fileStatus=1 and clusterStatus=0 "
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        selectStr="select tt.*,c.fileName as clusterFileName,c.id as clusterFileId,c.clusterMinSamples,c.clusterRadius from ("\
                  +selectStr+authStr+") tt LEFT JOIN tbl_site_files c on c.siteFileId=tt.fileId order by tt.fileId desc"
        return self.mysqlPool.fetchAll(selectStr,(citycode))

    def fuzzyQuerySiteFileList(self,queryText,citycode,userNames):
        """
        查询网点文件列表
        """
        selectStr="select id as fileId, fileName,siteCount from tbl_site_files t where t.userCitycode=%s and t.fileStatus=1 and fileName like %s"
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        selectStr=selectStr+authStr
        return self.mysqlPool.fetchAll(selectStr,(citycode,('%'+queryText+'%')))

    def selectSiteNameByText(self,queryText,fileId,siteStatus):
        """"
        根据文件id+站点名称模糊查询，clientName,clientProperty,age,clientAddress,number,grade  
        """
        selectStr="select id,siteName,if(siteProperty=1,'固定','临时') as siteProperty,longitude,latitude \
                  from tbl_site where fileId=%s and siteName like %s AND siteStatus = %s"
        return self.mysqlPool.fetchAll(selectStr,(fileId,('%'+queryText+'%'),siteStatus))
        

    def batchSites(self,rows):
        """
        插入tbl_site
        """
        batchStr="insert into tbl_site(fileId,region,siteName,siteProperty,siteStatus,longitude,latitude,clientName,\
                 clientProperty,clientAddress,age,grade,number,others,createUser,updateUser,location)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromGeoJSON(%s,2,0))"
        row=self.mysqlPool.batch(batchStr,rows)
        return row
    
    def updateSiteFile(self,row):
        """
        更新tbl_site_files.fileStatus=1
        """
        updateStr="update tbl_site_files set fileStatus=%s,siteCount=%s,updateUser=%s where id=%s"
        row=self.mysqlPool.update(updateStr,row)
        return row
    
    def updateSiteStatusByfieldId(self,row):
        """
        更新tbl_site.siteStatus，失效临时网点
        """
        updateStr="update tbl_site set siteStatus=%s,updateUser=%s where fileId=%s and siteStatus=%s"
        return self.mysqlPool.update(updateStr,row)

    def updateSiteStatusByIds(self,fileId,siteStatus,siteIds,userName):
        """
        将临时网点更新为有效网点
        """
        updateStr="update tbl_site set siteStatus=%s,updateUser=%s where fileId=%s"
        condition=" and id in (%s)"% ','.join("%s" % item for item in siteIds)
        return self.mysqlPool.update(updateStr+condition,(siteStatus,userName,fileId))
    
    def selectSiteInfoByFileId(self,row):
        """
        根据文件id查找siteInfo,GROUP BY siteName, latitude,longitude
        """
        selectStr="SELECT siteName, latitude,longitude,SUM(number) AS clientNumber \
                   FROM tbl_site WHERE fileId = %s AND siteStatus = 1 GROUP BY siteName, latitude,longitude"
        return self.mysqlPool.fetchAll(selectStr,row)
    
    def selectClientNameByIds(self,siteIds):
        selectStr="select clientName from tbl_site where "+" id in (%s)"% ','.join("%s" % item for item in siteIds)
        return self.mysqlPool.fetchAll(selectStr,())
    
    def selectSiteClientNumberByFileId(self,fileId):
        """
        根据文件id查询总人数
        """
        selectStr="SELECT SUM(number) AS clientNumber FROM tbl_site WHERE fileId = %s AND siteStatus = 1"
        return self.mysqlPool.fetchOne(selectStr,(fileId))

    def selectCustomSiteInfo(self,fileId):
        """
        根据文件id查询自定义字段内容
        """
        selectStr="select if(siteProperty=1,'固定','临时') as siteProperty ,region, clientName,clientProperty,age,clientAddress,number,grade  \
                  from tbl_site where fileId=%s AND siteStatus = 2"
        return self.mysqlPool.fetchAll(selectStr,(fileId))

    
    def selectTempSiteInfo(self,fileId,kwargs):
        """
        根据文件id查找临时siteInfo
        """
        args=[]
        selectStr="select id,siteName,if(siteProperty=1,'固定','临时') as siteProperty,longitude,latitude,\
                  clientName,clientProperty,age,clientAddress,number,grade  \
                  from tbl_site where fileId=%s AND siteStatus = 2"
        args.append(fileId)
        for key,value in kwargs.items():
            selectStr=selectStr+" and "+key+"=%s"
            args.append(value)
        #selectStr+=" order by id limit %s ,%s"
        #args.append(pageNum*pageSize)
        #args.append(pageSize)
        return self.mysqlPool.fetchAll(selectStr,args)
    
    def invalidSiteBySiteName(self,row):
        """
        根据siteName、经纬度、fileId失效对应网点
        """
        updateStr="update tbl_site set siteStatus=%s,updateUser=%s WHERE siteName =%s and fileId=%s and longitude=%s and latitude=%s "
        return self.mysqlPool.update(updateStr,row)

    def selectInvalidClientNumber(self,row):
        """
        根据
        """
        selectStr="select sum(number) as clientNumber from tbl_site where siteName =%s and fileId=%s and longitude=%s and latitude=%s "
        return self.mysqlPool.fetchOne(selectStr,row)

    def selectSiteFileStatus(self,fileId):
        """
        查询网点文件状态
        """
        selectStr="SELECT fileName,fileProperty,fileStatus,siteFileId,clusterStatus,clusterRadius,clusterMinSamples,destination,mapType,longitude,latitude,siteCount from tbl_site_files where id=%s"
        return self.mysqlPool.fetchOne(selectStr,(fileId))
    
    def searchSiteListByFileId(self,fileId):
        """
        根据文件id导出网点文件
        """
        selectStr="SELECT region,if(siteProperty=1,'固定','临时') as siteProperty, latitude,longitude,siteName,clientName,clientProperty,clientAddress,age,grade,number \
                   FROM tbl_site WHERE fileId = %s AND siteStatus = 1"
        return self.mysqlPool.fetchAll(selectStr,(fileId))

    def selectSiteGeoListByFileId(self,fileId):
        """
        根据文件id查询SiteGeoList
        """
        selectStr="SELECT id,siteProperty, latitude as lat,longitude as lng,siteName,number \
                   FROM tbl_site WHERE fileId = %s AND siteStatus = 1"
        return self.mysqlPool.fetchAll(selectStr,(fileId))
    
    def insertClusterFile(self,row):
        """
        插入网点文件信息
        """
        insertStr="insert into tbl_site_files(fileName,fileProperty,fileStatus,siteFileId,clusterStatus,clusterRadius,clusterMinSamples,destination,mapType,longitude,latitude,userCitycode,createUser,updateUser)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        return self.mysqlPool.insert(insertStr,row)
    
    def selectClusterFileId(self,row):
        """
        查找聚类文件id
        """
        selectStr="select id from tbl_site_files where fileName=%s and fileStatus=%s and siteFileId=%s"
        return self.mysqlPool.fetchOne(selectStr,row)

    def batchClusterSites(self,rows):
        """
        tbl_cluster_result
        """
        batchStr="insert into tbl_cluster_result(fileId,relativeId,clusterName,relativeProperty,clusterProperty,clusterStatus,\
                                                 longitude,latitude,number,siteSet,createUser,updateUser)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.batch(batchStr,rows)
        return row
    
    def updateClusterResultByFileId(self,row,statusArr):
        """
        更新tbl_cluster_result
        """
        updateStr="update tbl_cluster_result set clusterStatus=%s,updateUser=%s where fileId=%s"
        condition=" and clusterStatus in (%s)"% ','.join("%s" % item for item in statusArr)
        row=self.mysqlPool.update(updateStr+condition,row)
        return row
    
    def updateClusterResultByClusterFileId(self,row):
        updateStr="update tbl_cluster_result set fileId=%s,clusterStatus=%s,updateUser=%s where fileId=%s and clusterStatus=2"
        row=self.mysqlPool.update(updateStr,row)
        return row
    
    def invalidClusterSitesById(self,row,idArr):
        updateStr="update tbl_cluster_result set clusterStatus=0,updateUser=%s"
        condition="where id in(%s)"% ','.join("%s" % item for item in idArr)
        row=self.mysqlPool.update(updateStr+condition,row)
        return row
    
    def insertClusterPoint(self,row):
        insertStr="insert into tbl_cluster_result(fileId,relativeId,relativeProperty,clusterName,clusterProperty,clusterStatus,\
                                                 longitude,latitude,number,siteSet,createUser,updateUser)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
        return row
    
    def selectClusterPointId(self,row):
        selectStr="select id from tbl_cluster_result where fileId=%s and clusterName=%s and longitude=%s and latitude=%s"
        return self.mysqlPool.fetchOne(selectStr,row)

    
    def selectClusterResult(self,row):
        selectStr="select id,relativeId,clusterName,relativeProperty,clusterProperty,longitude,\
                  latitude,number,siteSet from tbl_cluster_result where clusterStatus=%s and fileId=%s"
        row=self.mysqlPool.fetchAll(selectStr,row)
        return row

    def searchClusterResult(self,fileId):
        selectStr="select region,clusterName,longitude,\
        (case when clusterProperty=1 then '聚类点' when clusterProperty=2 then '边界点' else '异常点' end) as clusterProperty,\
                  latitude,number,if(relativeProperty=1,'固定','临时') as siteProperty from tbl_cluster_result where  fileId=%s and clusterStatus = 1"
        return self.mysqlPool.fetchAll(selectStr,(fileId))
    
    def selectClusterNumberById(self,fileId,id,label):
        selectStr="SELECT id, number,siteSet FROM tbl_cluster_result t \
                         WHERE t.fileId = %s"
        if label=="U":
            condition=" and relativeId=%s"
            id="station_"+str(id)
        else:
            condition=" and id=%s"
        row=self.mysqlPool.fetchOne(selectStr+condition,(fileId,id))
        return row
    
    def updateClusterPointById(self,row):
        updateStr="update tbl_cluster_result set clusterName=%s,fileId=%s,clusterProperty=%s,clusterStatus=%s,relativeProperty=%s,longitude=%s,latitude=%s, number=%s,siteSet=%s,updateUser=%s where  id=%s"
        row=self.mysqlPool.update(updateStr,row)
        return row

    def selectClusterParams(self,row):
        selectStr="select clusterRadius,clusterMinSamples from tbl_site_files  where id=%s and clusterStatus=1 and fileStatus=1"
        row=self.mysqlPool.fetchOne(selectStr,row)
        return row

    def selectClusterParamsBySiteFileId(self,row):
        selectStr="select id, clusterRadius,clusterMinSamples from tbl_site_files  where siteFileId=%s and clusterStatus=1 and fileStatus=1"
        row=self.mysqlPool.fetchOne(selectStr,row)
        return row
    
    def updateClusterParams(self,row):
        updateStr="update tbl_site_files set clusterRadius=%s,clusterMinSamples=%s,updateUser=%s where id=%s"
        row=self.mysqlPool.update(updateStr,row)
        return row

    def inserRouteParams(self,row):
        insertStr="insert into tbl_route_node(startLng,startLat,startNode,endLng,endLat,\
                                                endNode,minDist,minTime,directDist)  \
                values(%s,%s,ST_GeomFromGeoJSON(%s,2,0),%s,%s,ST_GeomFromGeoJSON(%s,2,0),%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
        return row
    
    def selectRouteParams(self,row):
        selectStr="select minDist as dist,minTime as time from tbl_route_node where ABS(startlng-%s)<=0.000001 and ABS(startlat-%s)<=0.000001 \
                   and ABS(endLng-%s)<=0.000001 and ABS(endLat-%s)<=0.000001"
        row=self.mysqlPool.fetchOne(selectStr,row)
        return row
    
    def insertRouteInfo(self,row):
        insertStr="insert into tbl_route_info(fileId,routeUuid,destName,destLng,destLat,passengers,occupancyRate,odometerFactor,routeFactor,roundTrip)\
            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
        return row
    
    def insertRouteDetail(self,row):
        insertStr="insert into tbl_route_detail(routeUuid,nodeIndex,nodeName,nodeStatus,nodeLng,nodeLat,number,nextDist,nextTime,nodeProperty)\
            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
        return row
    
    def updateRouteDetail(self,row):
        updateStr="update tbl_route_detail set nodeIndex=%s,nodeProperty=%s,nextDist=%s,nextTime=%s where routeUuid=%s and id=%s"
        return self.mysqlPool.update(updateStr,row)
    
    def selectRouteDetail(self,row):
        selectStr="select id,nodeIndex,nodeName,nodeLng as lng,nodeLat as lat,number,nextDist,nextTime from tbl_route_detail where routeUuid=%s and nodeStatus=%s order by nodeIndex"
        return self.mysqlPool.fetchAll(selectStr,row)

    def deleteNodesByRouteId(self,row):
        deleteStr="delete from tbl_route_detail where routeUuid=%s"
        return self.mysqlPool.delete(deleteStr,row)
    

    def selectFileListByClusterStatus(self,clusterStatus,citycode,userNames):
        """
        查询网点文件和聚类文件列表
        """
        selectStr="select id as fileId, fileName,destination,longitude,latitude from tbl_site_files t \
            where t.userCitycode=%s and t.fileStatus=1 and clusterStatus=%s"
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        orderStr=" order by id desc "
        selectStr=selectStr+authStr+orderStr
        return self.mysqlPool.fetchAll(selectStr,(citycode,clusterStatus))
    
    def updateFileRoutePlanParams(self,row):
        """
        更新路径规划参数
        """
        updateStr="update tbl_site_files set passengers=%s,occupancyRate=%s,odometerFactor=%s,\
                  roundTrip=%s,routeFactor=%s,waypoints=%s where fileId=%s"
        return self.mysqlPool.update(updateStr,row)
    
    def selectRouteInfo(self,row):
        """
        根据fileid查询路线规划参数
        """
        selectStr="select routeUuid,destName,destLng,destLat,passengers,occupancyRate,odometerFactor,routeFactor,roundTrip \
                from tbl_route_info where fileId=%s group by routeUuid,destName,destLng,destLat,passengers,occupancyRate,odometerFactor,routeFactor,roundTrip"
        return self.mysqlPool.fetchAll(select,row)
    