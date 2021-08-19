# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 11:01:35 2020

@author: Ming-Yi Hsu
"""

from matplotlib import pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import numpy as np
import netCDF4 as nc
import seaborn as sns
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from cartopy.util import add_cyclic_point
sns.set_context('talk', font_scale=1.2) 


#讀取檔案位置
ncf_data = 'D:/nc/GRCTellus.JPL.200204_201911.GLO.RL06M.MSCNv02CRI.nc'
data_JPL = nc.Dataset(ncf_data)
print(data_JPL)
#確認nc檔案內容



#取得變數名稱及數量
all_vars = data_JPL.variables.keys()
print(all_vars)
print(len(all_vars))


#取得變數資訊
all_vars_info = data_JPL.variables.items() 
type(all_vars_info)
all_vars_info = list(all_vars_info)
print(all_vars_info)




#將nc檔案變數讀取
lat = data_JPL.variables['lat'][:].data
lon = data_JPL.variables['lon'][:].data
uncert  = data_JPL.variables['uncertainty'][:].data
thickness = data_JPL.variables['lwe_thickness'][:].data
lat_bound = data_JPL.variables['lat_bounds'][:].data
lon_bound = data_JPL.variables['lon_bounds'][:].data
time = lon_bound = data_JPL.variables['time'][:].data
length = len(time)
#'uncertainty' 及 'lwe_thickness' 為包含經緯度的3維資料，資料內容為(time,lat,lon)



cycle_think, cycle_lon = add_cyclic_point(thickness, coord=lon)
cycle_LON, cycle_LAT = np.meshgrid(cycle_lon, lat)

#設定投影
projection = ccrs.PlateCarree()

#資料輸出成png檔案
ims=[]    

for i in range(0,length):
    think=cycle_think[i,:,:]
    fig, ax = plt.subplots(figsize=(12, 5), subplot_kw=dict(projection=projection))
    con = ax.contourf(cycle_LON, cycle_LAT,think)

    #設定坐標軸
    ax.set_xticks(np.arange(-180, 181, 60), crs = projection)
    ax.set_yticks(np.arange(-90, 91, 30), crs = projection)
    lon_formatter = LongitudeFormatter(number_format='.0f',degree_symbol='', dateline_direction_label=True)
    lat_formatter = LatitudeFormatter(number_format='.0f', degree_symbol='')
    ax.xaxis.set_major_formatter(lon_formatter)
    ax.yaxis.set_major_formatter(lat_formatter)
    #設定海岸線
    ax.coastlines() 
    plt.grid(True)
    #設定colorbar
    cb = fig.colorbar(con)
    #cb.set_ticks(np.arange(-500,600, 100))
    #cb.set_ticklabels(np.arange(-500,600, 100))
    ims.append(con)
    #輸出成png檔案
    fig.savefig('D:/nc/'+str(i)+'.png', dpi=300, bbox_inches='tight')
    plt.show()
