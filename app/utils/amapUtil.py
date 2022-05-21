import requests,json,time
from concurrent import futures
#from logger import get_logger
from app.utils.logger import get_logger
from app.utils.util import route

logger=get_logger(name="amapUtil",log_file="logs/logger.log")

key = "36fdeffd608643f8dec6d43b2d9b8ec8" 
#mykey="c499537db92f1234f8390eeec13cfbe5"
# 驾车路径规划 36fdeffd608643f8dec6d43b2d9b8ec8 
def get_route(origin,destination,routeType=0):
    if routeType==0:
        api=f'http://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&output=JSON&key={key}'
    elif routeType==1:
        api=f'http://restapi.amap.com/v4/direction/truck?origin={origin}&destination={destination}&size=3&nosteps=1&key={key}'
    elif routeType==2:
        api=f'http://restapi.amap.com/v3/direction/walking?origin={origin}&destination={destination}&key={key}'
    r=requests.get(api,verify=False)
    r=r.text
    jsonData=json.loads(r)
    return jsonData

def get_route_distance_time(origin,destination,routeType=0): 
    """
    # 该函数是调用高德API获取起始点到终点两个经纬度之间的距离以及时间（以米为单位）
    origin: 起始点经纬度
    destination: 终点经纬度
    #输出
    distance：距离，单位为米
    duration：时长，单位为秒
    """ 
    distance = 0
    duration = 0  
    if origin==destination:
        return {"dist":distance,"time":duration}
    #路线规划
    info=get_route(origin,destination,routeType=routeType)
    if "status" in info.keys() and info["status"]=='1': 
        #路线时间
        duration=int(info['route']['paths'][0]['duration'])
        
        #路线距离
        distance=int(info['route']['paths'][0]['distance'])
        
        logger.info("get amap dist:{},time:{}".format(distance,duration))
        return {"dist":distance,"time":duration}
    elif "errcode" in info.keys() and info["errcode"]==0:
        duration=int(info['data']['route']['paths'][0]['duration'])
        
        #路线距离
        distance=int(info['data']['route']['paths'][0]['distance'])
        
        logger.info("get amap dist:{},time:{}".format(distance,duration))
        return {"dist":distance,"time":duration}
    else:
        logger.info("get amap fail!")
        return None
    
def get_thread_info(routeNode):
    """
    routeNode={"key","origin","destination","routeType"}
    return: {"key","dist","time"}
    """
    res=get_route_distance_time(routeNode["origin"],routeNode["destination"],routeNode["routeType"])
    if routeNode["routeType"]==1:
        time.sleep(1)
    #再循环一次
    if res is None:
        logger.info("retry get_route_distance_time!")
        res=get_route_distance_time(routeNode["origin"],routeNode["destination"],routeNode["routeType"])
    return {"key":routeNode["key"],"dist":res["dist"],"time":res["time"]}

def build_process(routeNodeList):
    """
    input:
        routeNodeList=[{"key","origin","destination","routeType"}]
    output:
        result={"key1":{"dist","time"},"key2":{"dist","time"},...}
    """
    result={}
    routeType=routeNodeList[0]["routeType"]
    max_workers=5
    if routeType==1:
        max_workers=1
    logger.info("routeType:{},thread num:{}".format(routeType,max_workers))
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for item in executor.map(get_thread_info,routeNodeList):
            result[item["key"]]={"dist":item["dist"],"time":item["time"]}
    return result

def search_around_place(location,kwargs):
    api=f'http://restapi.amap.com/v3/place/around?location={location}&key={key}'
    for k,v in kwargs.items():
        api=api+f"&{k}={v}"
    #print(api)
    r=requests.get(api,verify=False)
    r=r.text
    jsonData=json.loads(r)
    return jsonData

def get_driving_polyline(origin,destination,routeType=0):
    """
    获取起止点的道路坐标
    """
    info=get_route(origin,destination,routeType=routeType)
    polylines=[]
    if "status" in info.keys() and info["status"]=='1': 
        #路线
        steps=info['route']['paths'][0]['steps']
        #print(steps)
        for step in steps:
            polyline=step["polyline"]
            #将'polyline': '119.32447,26.119731;119.324284,26.119809;119.323802,26.120017;119.323607,26.1201;119.323216,26.12026'
            points=polyline.split(";")
            for point in points:
                coord=point.split(",")
                polylines.append({"lng":float(coord[0]),"lat":float(coord[1])})
    return polylines

def convert_coord_to_GCJ02(origin,coordSys="baidu"):
    url=f'http://restapi.amap.com/v3/assistant/coordinate/convert?locations={origin}&coordsys={coordSys}&key={key}'
    r=requests.get(url,verify=False)
    r=r.text
    jsonData=json.loads(r)
    coords=[]
    if "locations" in jsonData.keys() and jsonData["locations"]:
        locations=jsonData["locations"].split(";")
        for location in locations:
            coord=location.split(",")
            coords.append([float(coord[0]),float(coord[1])])
    return coords

if __name__ == '__main__':
    city = "福州市"    # 你的城市
    origin ='116.481499,39.990475'
    destination ='119.26216500,26.088172'
    """
    waypoints="119.290322,26.106594;119.281202,26.102822"
    api=f'http://restapi.amap.com/v4/direction/truck?origin={origin}&destination={destination}&size=3&nosteps=1&waypoints={waypoints}&key={key}'
    print(api)
    r=requests.get(api,verify=False)
    r=r.text
    jsonData=json.loads(r)
    print(jsonData)
    """
    #print(get_driving_polyline(origin,destination,routeType=0))
    #print(get_route_distance_time(origin,destination,routeType=1))
    print(convert_coord_to_GCJ02(origin))


    



    
    