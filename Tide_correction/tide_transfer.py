# -*- coding: utf-8 -*-
"""
author: Ming-Yi Hsu

"""

import os
import numpy as np
import pandas as pd
from scipy.spatial import distance
from multiprocessing import cpu_count, Pool




def Read_data(filename):
    lon=[]
    lat=[]
    value=[]
    with open(filename,'r') as f:
        data=f.readlines()

    for i in range(len(data)):
        if data[i] == '\n':
            continue

        info=data[i].split()
        lon.append(float(info[0]))
        lat.append(float(info[1]))
        value.append(float(info[2]))
    return(lon,lat,value)
    
    
def Write_data(filename,lon,lat,value1,value2):
    with open(filename, 'w') as g:
        for i in range (len(lon)):

            g.write('%11.7f  %10.7f' % (lon[i],lat[i]))
            g.write('%8.4f  %8.4f\n' % (value1[i],value2[i]))


def FindNearest(lon_want,lat_want,lon_model,lat_model,value1_model,value2_model):           
    
    loc_model = list(zip(lon_model,lat_model))
    loc_want = list(zip(lon_want,lat_want))
    
    tmp = distance.cdist(loc_want,loc_model)
    tmp_ind = distance.cdist(loc_want,loc_model).argmin(axis=1)

    get_lon = [ lon_model[i] for i in tmp_ind ]
    get_lat = [ lat_model[i] for i in tmp_ind ]
    get_value1 = [ value1_model[i] for i in tmp_ind ]
    get_value2 = [ value2_model[i] for i in tmp_ind ]

    return(get_lon,get_lat,get_value1,get_value2)




[lon,lat,depth]=Read_data('.../test.xyz')
[lon_tide1,lat_tide1,mss]=Read_data('.../mss.xyz')
[lon_tide2,lat_tide2,islw]=Read_data('.../ISLW.xyz')

#tide1_dict={"lon":lon_tide1, "lat":lat_tide1, "tide":mss}
#tide2_dict={"lon":lon_tide2, "lat":lat_tide2, "tide":mss}
#tide1_df = pd.DataFrame(tide1_dict)
#tide2_df = pd.DataFrame(tide2_dict)
initial_depth= np.zeros(len(lon))
final_depth= np.zeros(len(lon))


pool=Pool(processes=cpu_count())
[lon_i,lat_i,initial_depth,final_depth]=pool.map(FindNearest2,[lon,lat,lon_tide1,lat_tide1,mss,islw])
pool.close()
#[lon_i,lat_i,initial_depth,final_depth]=FindNearest(lon,lat,lon_tide1,lat_tide1,mss,islw)
new_depth=np.array(depth)+np.array(final_depth)-np.array(initial_depth)

Write_data[lon,lat,depth,new_depth]



