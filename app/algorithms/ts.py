import numpy as np
import math
# from app.algorithms.sa import *
# 
# from app.utils.GPSConvertUtil import getGPSDistance
'''
禁忌算法
'''
class TSOptimizer:
    def optimize(self,dis_mat,time_mat,num_mat,TS_time,TS_dist,Max_number,Min_number,best_initial,num_city):
        '''
        dis_mat:点对点距离矩阵
        time_mat:点对点时间矩阵
        num_mat:各个站点聚类的学生数
        TS_time(界面上设置的驾驶时长)
        TS_dist(界面上设置的驾驶路程)
        Max_number(界面上设置的线路开通有效订单总数上限)
        Min_number(界面上设置的线路开通有效订单总数下限)
        非必选参数：best_initial(目的地和聚类站点，对面站点排列组合后的initial组合列表的生,成并且一一送入TS禁忌算法，找出最优的列表组合)|
        非必选参数：num_city(所有聚类的公交站点数+目的地)
        '''
        route = []
        sub_time = []
        sub_dist = []
        sub_number = []


        path_select = self.TS_algorithm(dis_mat,best_initial,best_initial,num_city)[1]
        #print("path_select=","\n",path_select)

        left_path,route,sub_time,sub_dist,sub_number = self.ind2route(route,sub_time,sub_dist,sub_number,path_select,num_mat,time_mat,dis_mat,TS_time,TS_dist,best_initial,num_city)
        #print("left_path","\n",left_path,"\n","route","\n",route,"\n","sub_time","\n",sub_time,"\n","sub_dist","\n",sub_dist,"\n","sub_number","\n",sub_number)

        while left_path !=[]:
            path_select = self.TS_algorithm(dis_mat,left_path,best_initial,num_city)[1]
            #print("path_select=","\n",path_select)
            left_path,route,sub_time,sub_dist,sub_number = self.ind2route(route,sub_time,sub_dist,sub_number,path_select,num_mat,time_mat,dis_mat,TS_time,TS_dist,best_initial,num_city)
            #print("left_path","\n",left_path,"\n","route","\n",route,"\n","sub_time","\n",sub_time,"\n","sub_dist","\n",sub_dist,"\n","sub_number","\n",sub_number)

            if int(len(left_path)) == 2:
                _,route,sub_time,sub_dist,sub_number= self.ind2route(route,sub_time,sub_dist,sub_number,left_path,num_mat,time_mat,dis_mat,TS_time,TS_dist,best_initial,num_city)
                break

        ###---根据每条线路的最大学生数和最少学生数来选择是否显示该路线---#########
        del_ID = []
        k = 0
        print("len(sub_number)=","\n",len(sub_number))
        for i in range(int(len(sub_number))) :
            if( sub_number[i] < Min_number )or( sub_number[i] > Max_number ):
                del_ID.append(i)
        for j in del_ID:
            j -= k
            del route[j]
            del sub_time[j]
            del sub_dist[j]
            del sub_number[j]
            k += 1
        print("route=","\n",route)
        return route,sub_time,sub_dist,sub_number

        
    #=============禁忌算法=======================
    def TS_algorithm(self,dis_mat,initial,best_initial,num_city):
        #num_city #所有聚类站点总数+学校
        table_len = round((num_city*(num_city-1)/2)**0.5)#---禁忌表长度的设置

        #设置初始解
        path_initial = []
        path_initial.append(initial)
        taboo_table=[] #禁忌表
        #加入禁忌表
        taboo_table.append(initial)

        #求初始解的路径长度
        dis_list = self.cal_newpath(dis_mat,path_initial,best_initial,num_city)
        dis_best = min(dis_list)#最短距离
        path_best = path_initial[dis_list.index(dis_best)]#对应的最短路径方案

        #初始期望
        expect_dis = dis_best
        expect_best = path_best
        for iter in range(50):#迭代
            # 寻找全领域新解
            path_new = self.find_newpath(path_best)

            #求出所有新解的路径长度
            dis_new = self.cal_newpath(dis_mat,path_new,best_initial,num_city)

            #选择路径
            if dis_new == []:
                break
            dis_best=min(dis_new)#最短距离
            path_best=path_new[dis_new.index(dis_best)]#对应的最短路径方案
            if dis_best < expect_dis:#最短的<期望
                expect_dis=dis_best
                expect_best=path_best#更新两个期望
                if path_best in taboo_table:#在禁忌表里
                    taboo_table.remove(path_best)
                    taboo_table.append(path_best)
                else:#不在禁忌表里
                    taboo_table.append(path_best)
            else:#最短的还是不能改善期望
                if path_best in taboo_table:#在禁忌表里
                    dis_new.remove(dis_best)
                    path_new.remove(path_best)
                    if dis_new == []:
                        break
                    dis_best=min(dis_new)#求不在禁忌表中的最短距离
                    path_best=path_new[dis_new.index(dis_best)]#对应的最短路径方案
                    taboo_table.append(path_best)
                else:#不在禁忌表
                    taboo_table.append(path_best)
            if len(taboo_table) >= table_len:
                del taboo_table[0]
        #print(taboo_table)
        #print('最短距离',expect_dis)
        #print('最短路径：',expect_best)
        return expect_dis,expect_best    
    
    #计算所有路径对应的距离--------每条线路按照排序的第一个站点依次串联下一个站点的总路程
    def cal_newpath(self,dis_mat,path_new,initial,num_city):
        dis_list = []
        for each in path_new:#遍历所有领域的列表组合并计算总路程
            dis = 0
            for j in range(int(len(each))-1):
                if str(each[j]) == str(each[j]).split('*')[0]:#为原站点
                    M = int(each[j])
                else: #each[j] == each[j].split('*')+'*':#为对面站点
                    M = int(each[j].split('*')[0])
                if str(each[j+1]) == str(each[j+1]).split('*')[0]:#为原站点
                    N = int(each[j+1])
                else: #each[j+1] == each[j+1].split('*')+'*':#为对面站点
                    N = int(each[j+1].split('*')[0])
                dis = dis_mat[M][N]+dis
            dis_list.append(dis)
        return dis_list
    #寻找上一个最优路径对应的所有邻域解
    def find_newpath(self,path_best):
        path_new=[]
        for i in range(1,int(len(path_best))-1):#range从1开始是因为：0表示目的地，不进行交换
            for j in range(i+1,int(len(path_best))):
                path=path_best.copy()
                path[i],path[j]=path[j],path[i]
                path_new.append(path)
        return path_new

    ########----对TS禁忌算法给出的最短路径，统计在TS_time和TS_dist,vehicle_capacity要求内的子路径的总时间，总路程，总学生数等###########################

    def ind2route(self,route,sub_time,sub_dist,sub_number,path_select,num_mat,time_mat,dis_mat,TS_time,TS_dist,initial,num_city,vehicle_capacity):#,Max_number,Min_number):

        TS_dist0 = TS_dist*1000

        sub_route = []
        left_path = []
        individual = []
        vehicle_load = 0
        elapsed_time = 0
        elapsed_distance = 0
        last_customer_id = 0
        #print(vehicle_capacity,TS_time,TS_dist0)
        #把对面站点的序号变成int型---如8*变成8
        for i in range(len(path_select)):
            if str(path_select[i]) == str(path_select[i]).split('*')[0]:#为原站点
                individual.append(int(path_select[i]))
            elif str(path_select[i]) == str(path_select[i]).split('*')[0]+'*':#为对面站点
                individual.append(int(path_select[i].split('*')[0]))
        #print(individual)
        for customer_id in individual:
            # print(customer_id)
            if customer_id > 0:
                demand = num_mat[customer_id]#the number of student at customer_id station
                updated_vehicle_load = vehicle_load + demand #累计每个站点上车学生数的累计
                service_time = num_mat[customer_id]*0.05#假设每个学生的上车时间为3s
                start_time = time_mat[0][customer_id]
                start_distance = dis_mat[0][customer_id]
                if last_customer_id == 0:
                    updated_elapsed_time = elapsed_time  + service_time + start_time #终点是目的地，单趟
                    updated_elapsed_distance = elapsed_distance + start_distance #终点是目的地，单趟
                else:
                    updated_elapsed_time = elapsed_time + time_mat[last_customer_id][customer_id] + service_time #终点是学校，单趟
                    updated_elapsed_distance = elapsed_distance  + dis_mat[last_customer_id][customer_id] #终点是学校，单趟
                print(updated_vehicle_load,updated_elapsed_time,updated_elapsed_distance)
                if (updated_vehicle_load <= vehicle_capacity) and ((updated_elapsed_time <= TS_time )or(updated_elapsed_distance<=TS_dist0 )):
                #if ( updated_elapsed_time <= TS_time )or( updated_elapsed_distance <= TS_dist0 ):
                    # Add to current sub-route
                    sub_route.append(customer_id)
                    vehicle_load = updated_vehicle_load
                    elapsed_time = updated_elapsed_time
                    elapsed_distance = updated_elapsed_distance
                    if customer_id == individual[int(len(individual))-1]:
                        #global route
                        route.append(sub_route)
                        sub_time0 = elapsed_time
                        sub_dist0 = elapsed_distance
                        sub_number0 = vehicle_load
                        #global sub_time,sub_dist,sub_number
                        sub_time.append(sub_time0)
                        sub_dist.append(sub_dist0)
                        sub_number.append(sub_number0)
                else:
                    route.append(sub_route)
                    sub_time0 = elapsed_time
                    sub_dist0 = elapsed_distance
                    sub_number0 = vehicle_load
                    #global sub_time,sub_dist,sub_number
                    sub_time.append(sub_time0)
                    sub_dist.append(sub_dist0)
                    sub_number.append(sub_number0)
                    for j in sub_route:
                        del individual[individual.index(j)]
                    left_path = individual
                    sub_route = [customer_id]
                    vehicle_load = demand
                    elapsed_time =  service_time + start_time #终点是学校，单趟
                    elapsed_distance = start_distance
                    break
                last_customer_id = customer_id
                print(left_path,route,sub_time,sub_dist,sub_number)
        return left_path,route,sub_time,sub_dist,sub_number

def tspSolution(destination,wayPoints,num_city,list_res,TS_time,TS_dist,Max_number,Min_number,dis_mat):
    """
    利用遗传算法解决tsp问题
    params:
       destination:{lng,lat}
       wayPoints:[{id,lng,lat},{id,lng,lat}]
    """
    wayPoints.append(destination)
    wayPoints=np.array(wayPoints)
    ts= TSOptimizer()
    # xbest,ybest = sa.optimize(f, initFun=init, randFun=randf, stop=1e-3, t=1e3, alpha=0.98, l=10, iterPerT=1)

    # num_city = num_city_mat()#num_city是指所有聚类的公交站点数+学校
    # school = get_schoolInfo()#获取学校经纬度信息

    # ####------学校和站点，对面站点排列组合后的initial组合列表的生,成并且一一送入TS禁忌算法，找出最优的列表组合-----#####
    # list_res = Creat_initial_staList()#所有的站点组合，包括对面站点，需要送入TS禁忌算法，找出最优站点列表组合
    # min_dist = 100000
    min_index = 0
    initial = [] #用来遍历每个站点组合的列表
    best_initial = [] #通过TS禁忌算法找到的最优站点列表组合
    for i in range(len(list_res)):
        initial = list_res[i]
        expect_dis = ts.TS_algorithm(dis_mat,initial,initial,num_city)[0]#通过禁忌算法找到这个站点组合的最短路径列表
        if expect_dis < min_dist:
            min_dist = expect_dis
            min_index = i
    #print("min_index:",min_index)
    best_initial = list_res[min_index]#找出最优站点组合
    print("best_initial=:",best_initial)
    print("TS_time=:",TS_time)
    print("TS_dist=:",TS_dist)

    route = []
    #############------路径规划算法模块------#####################
    route,sub_time,sub_dist,sub_number = ts.optimize(TS_time,TS_dist,Max_number,Min_number,best_initial,num_city)
    #############------路径规划算法模块------#####################
    
    return route,sub_time,sub_dist,sub_number

"""
if __name__=="__main__":
    destination={"lng":7,"lat":1}
    wayPoints=[{"id":0,"lng":1,"lat":1},{"id":1,"lng":3,"lat":3},{"id":3,"lng":6,"lat":2},{"id":2,"lng":5,"lat":4}]
    tspSolution(destination,wayPoints)
"""