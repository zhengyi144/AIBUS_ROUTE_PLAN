import xlrd
import yaml

def readExcel(file,sheetIndex,mapType):
    """
    file: 上传文件
    sheetIndex: sheet系列
    mapName:excel表头对应数据库字段
    """
    #打开文件file
    f=file.read()
    wb=xlrd.open_workbook(file_contens=f)
    #wb=xlrd.open_workbook(filename=r"C:\Users\ZY\Desktop\test.xlsx")
    sheet=wb.sheet_by_index(sheetIndex)
    with open("config/excelMap.yaml", 'r', encoding='utf-8') as f:
        excelMap = yaml.safe_load(f.read())
    mapItems=excelMap[mapType]
    
    #读取表头
    nrows=sheet.nrows
    header=[]
    data=[]
    for head in  sheet.row_values(0):
        header.append(mapItems[head.strip("*")])
    for i in range(1, nrows):
        rowValues=sheet.row_values(i)
        rowDict={}
        for n,head in enumerate(header):
            rowDict[head]=rowValues[n]
        data.append(rowDict)
    return data

"""
if __name__ == '__main__':
    data=readExcel(0,"station")
    print(data)
"""



