from app.api.common_api import common 
from app.api.basic_data_api import basicdata
from app.api.site_data_api import sitedata
from app.api.route_plan_api import routeplan
from app.api.cluster_api import cluster

router = [
    common,  # 接口测试
    basicdata,  # 自定义MethodView
    sitedata,
    routeplan,
    cluster
]
