import requests,json
from app.utils.logger import get_logger

logger=get_logger(name="amapUtil",log_file="logs/logger.log")

key = "36fdeffd608643f8dec6d43b2d9b8ec8" 
#mykey="c499537db92f1234f8390eeec13cfbe5"
# 驾车路径规划 36fdeffd608643f8dec6d43b2d9b8ec8 
def get_route(origin,destination,routeType=1):
    if routeType==1:
        api=f'http://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&output=JSON&key={key}'
    elif routeType==0:
        api=f'http://restapi.amap.com/v3/direction/walking?origin={origin}&destination={destination}&key={key}'
    r=requests.get(api)
    r=r.text
    jsonData=json.loads(r)
    return jsonData

def get_route_distance_time(origin,destination,routeType=1): 
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
    #路线规划
    info=get_route(origin,destination,routeType=routeType)
    if info["status"]=='1': 
        #路线时间
        duration=int(info['route']['paths'][0]['duration'])
        
        #路线距离
        distance=int(info['route']['paths'][0]['distance'])
        
        logger.info("get amap dist:{},time:{}".format(distance,duration))
    else:
        logger.info("get amap fail!")
    return {"dist":distance,"time":duration}

"""
if __name__ == '__main__':
    city = "北京市"    # 你的城市
    origin ='116.481028,39.989643'
    destination ='116.434446,39.90816'
    print(get_route_distance_time(origin,destination))
"""

    



    
    