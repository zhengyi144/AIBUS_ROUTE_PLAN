import requests,json
import datetime
from multiprocessing import Pool
from concurrent import futures
# 返回经纬度
def gain_location(adress,key,city):
    api_url=f'https://restapi.amap.com/v3/geocode/geo?city={city}&address={adress}&key={key}&output=json&callback=showLocation'
    r = requests.get(api_url)
    r = r.text
    r = r.strip('showLocation(')#高德
    r = r.strip(')')
    jsonData = json.loads(r)['geocodes'][0]['location'] # 将json字符串转换为字典类型转为字典格式类型
    return jsonData

# 驾车路径规划 36fdeffd608643f8dec6d43b2d9b8ec8 
def get_route(origin,destination,key,city):
    api=f'https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&output=JSON&key={key}&city={city}'
    r=requests.get(api)
    r=r.text
    jsonData=json.loads(r)
    return jsonData

def get_route_info(start,end,key,city):    
    routeplan=[]
    for o in start:
        for d in end:
            route=[]
            #起点
            route.append(o)
            #终点
            route.append(d)
            #起点坐标
            ori=gain_location(o,key,city)
            #终点坐标
            des=gain_location(d,key,city)
            #路线规划
            info=get_route(ori,des,key,city)
            if info["info"]=='OK':
                
                #路线时间
                try:
                    duration=info['route']['transits'][0]['duration']
                except:
                    duration='null'
                route.append(duration)
                
                #路线距离
                try:
                    distance=info['route']['transits'][0]['distance']
                except:
                    distance='null'
                route.append(distance)
                print(o,d,duration,distance)
                routeplan.append(route)
    return routeplan

if __name__ == '__main__':
    KEY = "36fdeffd608643f8dec6d43b2d9b8ec8"  # 你的KEY
    CITY = "北京市"    # 你的城市
    start=['金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代','新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园','金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代','金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代','新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园','金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代']
    end=['新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园','金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代','新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园','新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园','金隅丽景园','苏荷时代','天恒乐活城','明悦湾','gogo新世代','新中关购物中心','五道口购物中心','天作国际大厦','朱辛庄地铁站','朝阳建外soho','海淀文教产业园']
    start_time = datetime.datetime.now()
    listloc = []
    listloc.append(start)
    listloc.append(end)
    routeplan=get_route_info(start,end,KEY,CITY)
    end_time = datetime.datetime.now()
    print(end_time - start_time)
    locs_num = 30*30
    #开启进程池
    p = Pool()
    for listloc in locs_num.index[:6000]:  # 高德api限制每天请求不超过6000个
        p.apply_async(routeplan, (listloc.start,listloc.end,KEY,CITY,))
    p.close()
    p.join()

    
    # 高德开放平台一天只允许免费用户使用API接口6000次......
    # https://www.jianshu.com/p/81edc84def06
    available_loc_list = locs_num.index[:6000]

    with futures.ThreadPoolExecutor(max_workers=20) as excutor:
        excutor.map(listloc)
    # print(routeplan)

    
    