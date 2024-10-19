
# **Dredging Volume Calculation**

This script is designed to provide dredging desgin in a raster file based on the geometry and target depth values of polygons stored in a GPKG file. 
It accomplishes this by interpolating depth values between polygon boundaries and applying a user-defined vertical-to-horizontal (V)ratio. 

## **Parameter**
1. vh_ratio: This ratio controls how depth values change as the distance from the polygon boundary increases. For example, with a 1:3 ratio (represented as vh_ratio = 3), the depth will change more gradually as you move horizontally from a polygon's edge.
2. min_horizontal_distance: This ensures that there is a minimum horizontal distance when adjusting the depth values, preventing overly aggressive changes near polygon boundaries.
