## Key Features

### 1. **CRS Detection and Conversion**
- Automatically detects and converts input data's CRS to `EPSG:3826`.
- Ensures consistency across datasets for accurate spatial operations.

### 2. **Data Sampling Along Lines**
- **Input:** Line geometries from vector files.
- **Output:** Sampled points at user-defined intervals, including:
  - Coordinates (Easting, Northing, Latitude, Longitude).
  - Elevation values derived from GeoTIFF.
  - Distances (2D and 3D).
  - Total accumulated distances.

### 3. **Flexible User Configuration**
- Asks for:
  - Sampling interval (`fixed_distance`).
  - Inclusion of original nodes.
  - Retention of line attributes.
  - Field for segment classification.
  - Whether to output Shapefiles.

### 4. **Comprehensive Output**
- Per-segment CSV files with detailed attributes.
- Optional Shapefiles for visual integration in GIS.
- Summary report consolidating 2D and 3D distances and file paths.


## Workflow

1. **User Input**
   - Sampling distance (`fixed_distance`).
   - Configuration for Shapefile output, original nodes, and attributes.

2. **File Processing**
   - Reads vector files (`.gpkg`, `.geojson`, `.shp`).
   - Reads GeoTIFF for elevation data (if available).

3. **Data Generation**
   - Creates interpolated points along line geometries.
   - Computes distances and appends attributes.

4. **Output**
   - CSV files for each segment.
   - Optional Shapefile for spatial visualization.
   - Summary CSV consolidating distances and file locations.


## Outputs

### CSV Format
- Includes:
  - Spatial coordinates (`Easting`, `Northing`, `Longitude`, `Latitude`).
  - Elevation.
  - Distances:
    - `Distance_Meters`: Segment distance between consecutive points.
    - `Length_3D`: 3D distance considering elevation.
    - `Total_Distance`: Cumulative 2D distance.
    - `Total_3D_Length`: Cumulative 3D distance.

### Summary Report
- Consolidates:
  - Total 2D and 3D distances for each segment.
  - Paths to output files (CSV, Shapefile).
