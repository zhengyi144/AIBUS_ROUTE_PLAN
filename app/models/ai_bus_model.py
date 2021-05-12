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
    
    def selectStationNameByText(self,queryText,citycode):
        """
        模糊查询stationName
        """
        selectStr="select id,siteName,siteProperty,province,city,region,road from tbl_station where siteName like %s and userCitycode=%s"
        row=self.mysqlPool.fetchAll(selectStr,(('%'+queryText+'%'),citycode))
        return row
    
    def selectStationList(self,province,city,siteName,road,siteStatus,citycode,pageSize,pageNum):
        """
        查询站点列表
        """
        args=[]
        selectStr="select id,siteName,siteProperty,province,city,region,road,direction,longitude,latitude,siteStatus,updateTime,updateUser from tbl_station where userCitycode=%s"
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


        
