import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from math import sqrt
import os
from pyproj import Transformer
import rasterio
import numpy as np

def display_fields_and_samples(gdf):
    if gdf.empty:
        print("Error: The input GeoDataFrame is empty. Please check the input file.")
        return False

    print("\nAvailable columns:")
    for col in gdf.columns:
        print(f" - {col}")

    print("\nFirst 10 rows of data:")
    print(gdf.head(10))
    return True

def detect_and_convert_crs(gdf, target_crs="EPSG:3826"):
    """Automatically detect and convert CRS to target CRS."""
    if gdf.crs is None or gdf.crs.to_string() == "EPSG:4326":
        gdf = gdf.to_crs(target_crs)
        print(f"CRS converted to {target_crs}")
    else:
        gdf = gdf.to_crs(target_crs)
        print(f"Original CRS: {gdf.crs}, converted to {target_crs}")
    return gdf

def sample_elevation(point, src_array, transform, search_radius, nodata_value):
    """Sample elevation value from GeoTIFF, return None if invalid."""
    if src_array is None:
        return None  # Invalid elevation value

    px, py = ~transform * (point.x, point.y)
    px, py = int(px), int(py)

    if 0 <= px < src_array.shape[1] and 0 <= py < src_array.shape[0]:
        value = src_array[py, px]
        if value != nodata_value:
            return value

    radius_pixels = int(search_radius / transform.a)
    neighbors = []

    for dx in range(-radius_pixels, radius_pixels + 1):
        for dy in range(-radius_pixels, radius_pixels + 1):
            nx, ny = px + dx, py + dy
            if 0 <= nx < src_array.shape[1] and 0 <= ny < src_array.shape[0]:
                value = src_array[ny, nx]
                if value != nodata_value:
                    distance = sqrt(dx ** 2 + dy ** 2)
                    neighbors.append((value, distance))

    if neighbors:
        neighbors.sort(key=lambda x: x[1])
        return neighbors[0][0]

    return None

def process_line_data(file_path, geotiff_path):
    """Process vector data and GeoTIFF."""
    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:
        print(f"Error reading the file: {e}")
        return

    if not display_fields_and_samples(gdf):
        return

    gdf = detect_and_convert_crs(gdf)

    geotiff_array, transform, nodata_value = None, None, None
    try:
        with rasterio.open(geotiff_path) as src:
            geotiff_array = src.read(1)
            transform = src.transform
            nodata_value = src.nodata
    except Exception as e:
        print(f"Error reading GeoTIFF file, elevation data will be omitted: {e}")

    output_shapefile = input("Do you want to output Shapefile format? (yes/no): ").strip().lower() == 'yes'

    output_directory = "output_files_with_nodes_and_crs"
    os.makedirs(output_directory, exist_ok=True)

    fixed_distance = float(input("Enter the sampling distance (meters): "))
    include_original_nodes = input("Include original nodes? (yes/no): ").strip().lower() == 'yes'
    retain_attributes = input("Retain original line attributes? (yes/no): ").strip().lower() == 'yes'

    field_name = input("Enter the field name for segment naming: ")
    if field_name not in gdf.columns:
        print(f"Column '{field_name}' does not exist. Using sequential naming instead.")
        gdf['segment_name'] = gdf.index.to_series().astype(str)
        field_name = 'segment_name'

    transformer_to_4326 = Transformer.from_crs(gdf.crs, "EPSG:4326", always_xy=True)

    report_data = []

    for unique_value in gdf[field_name].unique():
        segment_gdf = gdf[gdf[field_name] == unique_value]
        nodes_data = []

        total_2d_length = 0
        total_3d_length = 0

        for _, row in segment_gdf.iterrows():
            line = row.geometry
            length = line.length
            current_distance = 0

            original_points = []
            if include_original_nodes:
                if line.geom_type == 'LineString':
                    original_points = list(line.coords)
                elif line.geom_type == 'MultiLineString':
                    for linestring in line.geoms:
                        original_points.extend(linestring.coords)

            points = set()
            while current_distance <= length:
                point = line.interpolate(current_distance)
                points.add((point, current_distance))
                current_distance += fixed_distance

            if include_original_nodes:
                for pt in original_points:
                    point = Point(pt)
                    distance_along_line = line.project(point)
                    points.add((point, distance_along_line))

            sorted_points = sorted(points, key=lambda x: x[1])

            prev_point = None
            for i, (point, distance_along_line) in enumerate(sorted_points):
                lon, lat = transformer_to_4326.transform(point.x, point.y)
                elevation = sample_elevation(point, geotiff_array, transform, fixed_distance * 2, nodata_value)

                distance_meters = None
                length_3d = None
                if prev_point:
                    prev_lon, prev_lat, prev_elevation = prev_point
                    distance_meters = point.distance(Point(sorted_points[i-1][0]))
                    total_2d_length += distance_meters

                    if elevation is not None and prev_elevation is not None:
                        dz = elevation - prev_elevation
                        length_3d = sqrt(distance_meters ** 2 + dz ** 2)
                    else:
                        length_3d = distance_meters  # No elevation data, treat as 2D length

                    total_3d_length += length_3d

                node_data = {
                    "Longitude": lon,
                    "Latitude": lat,
                    "Easting": point.x,
                    "Northing": point.y,
                    "Elevation": elevation,
                    "Distance_Meters": distance_meters,
                    "Length_3D": length_3d,
                    "Total_Distance": distance_along_line,
                    "Total_3D_Length": total_3d_length,
                    field_name: unique_value
                }

                if retain_attributes:
                    for col in gdf.columns:
                        if col not in node_data:
                            node_data[col] = row[col]

                nodes_data.append(node_data)
                prev_point = (lon, lat, elevation)

        if nodes_data:
            nodes_gdf = gpd.GeoDataFrame(
                nodes_data, 
                geometry=[Point(d["Easting"], d["Northing"]) for d in nodes_data], 
                crs=gdf.crs
            )

            csv_file = os.path.join(output_directory, f"{unique_value}_nodes.csv")
            nodes_df = pd.DataFrame(nodes_data)
            nodes_df.to_csv(csv_file, index=False)
            print(f"CSV saved to: {csv_file}")

            if output_shapefile:
                shp_file = os.path.join(output_directory, f"{unique_value}_nodes.shp")
                nodes_gdf.to_file(shp_file, driver="ESRI Shapefile")
                print(f"Shapefile saved to: {shp_file}")

            report_data.append({
                "Segment": unique_value,
                "Total 2D Distance": total_2d_length,
                "Total 3D Distance": total_3d_length,
                "Output CSV": csv_file,
                "Output Shapefile": shp_file if output_shapefile else "Not generated"
            })

    report_df = pd.DataFrame(report_data)
    report_file = os.path.join(output_directory, "processing_report.csv")
    report_df.to_csv(report_file, index=False)
    print(f"Report saved to: {report_file}")

def main():
    directory = os.getcwd()
    geotiff_path = input("Enter the path to the GeoTIFF file: ")

    vector_files = [f for f in os.listdir(directory) if f.endswith((".gpkg", ".geojson", ".shp"))]
    if not vector_files:
        print("No vector files (.gpkg, .geojson, .shp) found in the current directory.")
        return

    for filename in vector_files:
        file_path = os.path.join(directory, filename)
        print(f"Processing file: {filename}")
        process_line_data(file_path, geotiff_path)

if __name__ == "__main__":
    main()
