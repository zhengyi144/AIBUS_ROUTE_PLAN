from app.api.common_api import common 
from app.api.basic_data_api import basicdata
from app.api.site_data_api import sitedata

router = [
    common,  # 接口测试
    basicdata,  # 自定义MethodView
    sitedata
]
