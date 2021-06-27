# -*- coding: utf-8 -*-
"""
Created on Wed Jun 23 13:51:59 2021

@author: mingyihsu
"""
import numpy as np
from osgeo import osr
from osgeo import ogr
from osgeo import gdal
from ipyleaflet import Map, GeoData, LayersControl
import geopandas as gpd
import math

#Open tif file as select band
rasterDs = gdal.Open('G://GIS/GEBCO_2020_22_Jun_2021_0166d46f7a9a/gebco_2020_n60.0_s10.0_w110.0_e150.0.tif')
rasterBand = rasterDs.GetRasterBand(1)
proj = osr.SpatialReference(wkt=rasterDs.GetProjection())



elevArray = rasterBand.ReadAsArray()
print(elevArray[:4,:4])

#define not a number
demNan = -32768

#get dem max and min
demMax = elevArray.max()
demMin = elevArray[elevArray!=demNan].min()
print("Maximun dem elevation: %.2f, minimum dem elevation: %.2f"%(demMax,demMin))



contourPath = 'G://GIS/GEBCO_2020_22_Jun_2021_0166d46f7a9a/contours_auto.shp'
contourDs = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(contourPath)


contourShp = contourDs.CreateLayer('contour', proj)


#define fields of id and elev
fieldDef = ogr.FieldDefn("ID", ogr.OFTInteger)
contourShp.CreateField(fieldDef)
fieldDef = ogr.FieldDefn("elev", ogr.OFTReal)
contourShp.CreateField(fieldDef)

conNum=1000
conList =[int(x) for x in np.linspace(math.floor(demMin/1000)*1000,math.floor(demMax/1000)*1000,conNum)]


gdal.ContourGenerate(rasterBand, 0, 0, conList, 1, -32768., contourShp, 0, 1)
contourDs.Destroy()

map1 = Map(center=(25, 123), zoom=3)

contourDf = gpd.read_file('G://GIS/GEBCO_2020_22_Jun_2021_0166d46f7a9a/contoursbyset.shp')
contourDfWgs84 = contourDf.to_crs(epsg=4326)

geo_data = GeoData(geo_dataframe = contourDfWgs84 )

map1.add_layer(geo_data)
map1.add_control(LayersControl())

map1






#give contour list


contourPath = 'G://GIS/GEBCO_2020_22_Jun_2021_0166d46f7a9a/contoursbyset.shp'
contourDs = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(contourPath)


contourShp = contourDs.CreateLayer('contour', proj)


#define fields of id and elev
fieldDef = ogr.FieldDefn("ID", ogr.OFTInteger)
contourShp.CreateField(fieldDef)
fieldDef = ogr.FieldDefn("elev", ogr.OFTReal)
contourShp.CreateField(fieldDef)


conList =[-40000,-30000,-20000,-10000,-5000,-4000,-3000,-2000,-1000,-500,-300,-200,-100,-50,0,50,100,500,1000,2000,3000,4000]


gdal.ContourGenerate(rasterBand, 0, 0, conList, 1, -32768., contourShp, 0, 1)
contourDs.Destroy()


m = Map(center=(25, 123), zoom=3)

contourDf = gpd.read_file('G://GIS/GEBCO_2020_22_Jun_2021_0166d46f7a9a/contoursbyset.shp')
contourDfWgs84 = contourDf.to_crs(epsg=4326)

geo_data = GeoData(geo_dataframe = contourDfWgs84 )

m.add_layer(geo_data)
m.add_control(LayersControl())

m
