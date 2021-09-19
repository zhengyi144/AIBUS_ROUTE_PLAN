import xlrd
import yaml
import xlwt
import json
import os
import hashlib
from xlutils.copy import copy

def readExcel(file,sheetIndex,mappingItem):
    """
    file: 上传文件
    sheetIndex: sheet系列
    mappingItem:excel表头对应数据库字段
    """
    #打开文件file
    f=file.read()
    wb=xlrd.open_workbook(file_contents=f)
    #wb=xlrd.open_workbook(filename=r"C:\Users\ZY\Desktop\康驰路线规划\网点导入模板.xlsx")
    sheet=wb.sheet_by_index(sheetIndex)
    with open("config/excelMap.yaml", 'r', encoding='utf-8') as f:
        excelMap = yaml.safe_load(f.read())
    mapItems=excelMap[mappingItem]
    #读取表头
    nrows=sheet.nrows
    header=[]
    data=[]
    for head in  sheet.row_values(0):
        head=head.strip("*").strip(" ")
        if head in mapItems.keys():
            header.append(mapItems[head])
        else:
            header.append(head)
    #读取数据
    for i in range(1, nrows):
        rowValues=sheet.row_values(i)
        rowDict={}
        others={}
        for n,head in enumerate(header):
            if head in mapItems.values():
                rowDict[head]=rowValues[n]
            else:
                others[head]=rowValues[n]
        rowDict["others"]=json.dumps(others)
        data.append(rowDict)
    return data

#设置表格样式
# 颜色索引  #######################################################
"""
aqua 0x31
black 0x08
blue 0x0C
blue_gray 0x36
bright_green 0x0B
brown 0x3C
coral 0x1D
cyan_ega 0x0F
dark_blue 0x12
dark_blue_ega 0x12
dark_green 0x3A
dark_green_ega 0x11
dark_purple 0x1C
dark_red 0x10
dark_red_ega 0x10
dark_teal 0x38
dark_yellow 0x13
gold 0x33
gray_ega 0x17
gray25 0x16
gray40 0x37
gray50 0x17
gray80 0x3F
green 0x11
ice_blue 0x1F
indigo 0x3E
ivory 0x1A
lavender 0x2E
light_blue 0x30
light_green 0x2A
light_orange 0x34
light_turquoise 0x29
light_yellow 0x2B
lime 0x32
magenta_ega 0x0E
ocean_blue 0x1E
olive_ega 0x13
olive_green 0x3B
orange 0x35
pale_blue 0x2C
periwinkle 0x18
pink 0x0E
plum 0x3D
purple_ega 0x14
red 0x0A
rose 0x2D
sea_green 0x39
silver_ega 0x16
sky_blue 0x28
tan 0x2F
teal 0x15
teal_ega 0x15
turquoise 0x0F
violet 0x14
white 0x09
yellow 0x0D
"""
def set_style(name,size,color,bold=False):
    """
    name: 字体类型
    size: 字体大小
    color:字体颜色
    """
    #初始化样式
    style = xlwt.XFStyle()
    # 为样式创建字体
    font = xlwt.Font()
    # 字体类型：比如宋体、仿宋也可以是汉仪瘦金书繁
    font.name = name
    # 字体大小
    font.height = 20 * size  # 如10号字体，size=10
    # 设置字体颜色、蓝色
    font.colour_index = color #0x0C 
    # 设置加粗
    font.bold = bold
    style.font = font
    return style

def writeExcel(filename,fields,resultdata,sheetName,removeLabel=True):
    """
    filename: 保存文件名称省市
    fields: 字段名称
    resultdata: 数据结果
    """
    # 定义输出excel文件名
    fileName=str(filename) + '.xls'
    filePath='./report/'+ fileName
    #先删除已经存在的文件
    if os.path.exists(filePath) and removeLabel:
        os.remove(filePath)

    if not os.path.exists(filePath):
        workbook=xlwt.Workbook(fileName)
        sheet=workbook.add_sheet(sheetName,cell_overwrite_ok=True)
    else:
        rb =xlrd.open_workbook(filePath)
        workbook = copy(rb)
        sheet=workbook.add_sheet(sheetName,cell_overwrite_ok=True)
    
    for field in range(0,len(fields)):
        sheet.write(0,field,fields[field],set_style('Times New Roman',11,0x0C,True))
    for row in range(1,len(resultdata)+1):
        for col in range(0,len(fields)):
            sheet.write(row,col,u'%s' % resultdata[row-1][col],set_style('Times New Roman',11,0x0C,True))
    workbook.save(filePath)
    return filePath

def generate_md5_key(item):
    """
    生成md5
    """
    md5_machine=hashlib.md5()
    md5_machine.update(item.encode('utf-8'))
    return md5_machine.hexdigest()



"""
if __name__ == '__main__':
    # data=readExcel("",0,"site")
    # print(data)
    #fields =["省份","城市","区域"]
    #resultdata =[["福建省","福州市","鼓楼区"],["福建省","福州市","仓山区"]]
    #filename = "福州"
    #writeExcel(filename,fields,resultdata)
"""






