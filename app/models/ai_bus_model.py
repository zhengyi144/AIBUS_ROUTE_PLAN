import logging
from re import S
from flask import current_app
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
        selectStr="select id,siteName,siteProperty,province,city,region,road,longitude,latitude \
                   from tbl_station where siteName like %s and userCitycode=%s "
        authStr="and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        row=self.mysqlPool.fetchAll(selectStr+authStr,(('%'+queryText+'%'),citycode))
        return row
    
    def selectStationList(self,province,city,siteName,road,siteStatus,citycode,pageSize,pageNum,userNames):
        """
        查询站点列表
        """
        args=[]
        selectStr="select id,siteName,siteProperty,province,city,region,road,direction,longitude,latitude,\
                   siteStatus,updateTime,updateUser from tbl_station where userCitycode=%s"
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
        selectStr+=" order by id limit %s ,%s"
        args.append(pageNum*pageSize)
        args.append(pageSize)
        return self.mysqlPool.fetchAll(selectStr,args)
    
    def insertSiteFile(self,row):
        """
        插入网点文件信息
        """
        insertStr="insert into tbl_site_files(fileName,fileProperty,fileStatus,destination,mapType,longitude,latitude,userCitycode,createUser,updateUser)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.insert(insertStr,row)
    
    def selectSiteFileIdByFileName(self,row):
        """
        根据文件名查找
        """
        selectStr="select max(id) as id from tbl_site_files where fileName=%s"
        row=self.mysqlPool.fetchOne(selectStr,row)
        return row

    def selectSiteFileList(self,citycode,userNames):
        """
        查询网点文件列表
        """
        selectStr="select id as fileId, fileName,siteCount from tbl_site_files t where t.userCitycode=%s and t.fileStatus=1 "
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        selectStr=selectStr+authStr
        return self.mysqlPool.fetchAll(selectStr,(citycode))

    def fuzzyQuerySiteFileList(self,queryText,citycode,userNames):
        """
        查询网点文件列表
        """
        selectStr="select id as fileId, fileName,siteCount from tbl_site_files t where t.userCitycode=%s and t.fileStatus=1 and fileName like %s"
        authStr=" and createUser in (%s)"% ','.join("'%s'" % item for item in userNames) 
        selectStr=selectStr+authStr
        return self.mysqlPool.fetchAll(selectStr,(citycode,('%'+queryText+'%')))

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
        updateStr="update tbl_site_files set fileStatus=%s,siteCount=%s where id=%s"
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
    
    def selectTempSiteInfo(self,fileId,kwargs,pageSize,pageNum):
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
        selectStr+=" order by id limit %s ,%s"
        args.append(pageNum*pageSize)
        args.append(pageSize)
        return self.mysqlPool.fetchAll(selectStr,args)
    
    def invalidSiteBySiteName(self,row):
        """
        根据siteName、经纬度、fileId失效对应网点
        """
        updateStr="update tbl_site set siteStatus=%s,updateUser=%s WHERE siteName =%s and fileId=%s and longitude=%s and latitude=%s "
        return self.mysqlPool.update(updateStr,row)
    
    def selectSiteFileStatus(self,fileId):
        """
        查询网点文件状态
        """
        selectStr="SELECT fileProperty,fileStatus from tbl_site_files where id=%s"
        return self.mysqlPool.fetchOne(selectStr,(fileId))
    
    def selectSiteGeoListByFileId(self,fileId):
        """
        根据文件id查询SiteGeoList
        """
        selectStr="SELECT id, latitude,longitude,clusterName,number \
                   FROM tbl_site WHERE fileId = %s AND siteStatus = 1"
        return self.mysqlPool.fetchAll(selectStr,(fileId))

    def batchClusterSites(self,rows):
        """
        tbl_cluster_result
        """
        batchStr="insert into tbl_cluster_result(fileId,siteId,clusterName,clusterProperty,clusterStatus,\
                                                 longitude,latitude,number,siteSet)  \
                   values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        row=self.mysqlPool.batch(batchStr,rows)
        return row