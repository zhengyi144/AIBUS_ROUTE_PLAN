import requests,json,time
from concurrent import futures
#from logger import get_logger
from app.utils.logger import get_logger

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
    #time.sleep(0.005)
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
    with futures.ThreadPoolExecutor(max_workers=3) as executor:
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


if __name__ == '__main__':
    city = "北京市"    # 你的城市
    origin ='116.481028,39.989643'
    destination ='116.434446,39.90816'
    print(get_route_distance_time(origin,destination,routeType=1))


    



    
    