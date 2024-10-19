
# **Dredging Volume Calculation**

This script is designed to provide dredging desgin in a raster file based on the geometry and target depth values of polygons stored in a GPKG file. 
It accomplishes this by interpolating depth values between polygon boundaries and applying a user-defined vertical-to-horizontal (V)ratio. 

## **Parameter**
1. vh_ratio: This ratio controls how depth values change as the distance from the polygon boundary increases. For example, with a 1:3 ratio (represented as vh_ratio = 3), the depth will change more gradually as you move horizontally from a polygon's edge.
2. min_horizontal_distance: This ensures that there is a minimum horizontal distance when adjusting the depth values, preventing overly aggressive changes near polygon boundaries.

## Main Workflow

### Step 1: Loading Data
- The script reads the GeoTIFF data (raster) and GPKG data (vector/polygon).
- Rows with missing target depths in the GPKG file are filtered out.

### Step 2: Surface Preparation
- An empty `flat_surface` (initialized with `NaN` values) is created to store depth values from the polygons.
- For each polygon, the target depth (`target_dep`) is assigned to the corresponding area in the raster.

### Step 3: Distance Calculation
- A distance transform (`distance_transform_edt`) is applied to compute the distance from every pixel to the nearest polygon boundary.
- This distance information is essential for adjusting the depth values in areas outside the polygons.

### Step 4: Depth Adjustment
- For each pixel in the raster, the script checks if it’s inside or outside a polygon:
  - **Inside a polygon:** The depth remains the same as the `target_dep` value.
  - **Outside a polygon:** The script searches for the nearest valid depth in a neighborhood around the pixel, and then adjusts the depth by applying the user-defined V:H ratio based on the distance from the polygon boundary. The new depth value cannot exceed the original GeoTIFF depth at that location.

