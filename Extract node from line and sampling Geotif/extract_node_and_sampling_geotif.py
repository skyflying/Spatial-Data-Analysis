import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from math import sqrt
import os
from pyproj import Transformer
import rasterio

def display_fields_and_samples(gdf):
    """顯示可用的欄位和前 10 行數據。"""
    if gdf.empty:
        print("Error: The input GeoDataFrame is empty. Please check the input file.")
        return False

    print("\nAvailable columns:")
    for col in gdf.columns:
        print(f" - {col}")
    
    print("\nFirst 10 rows of data:")
    print(gdf.head(10))
    return True

def sample_elevation(point, src_array, transform, search_radius, nodata_value):
    """取樣 GeoTIFF 值，若無值則進行最近鄰內插。"""
    if src_array is None or transform is None:
        return None

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
    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:
        print(f"Error reading the input file: {e}")
        return

    # 檢查 CRS 並處理
    if gdf.crs is None:
        print("CRS is missing in the input GIS file.")
        gdf.set_crs("EPSG:3826", inplace=True)
        print("Manually set CRS to EPSG:3826.")
    else:
        print(f"Input file CRS: {gdf.crs}")

    # 顯示欄位和樣本
    if not display_fields_and_samples(gdf):
        return

    output_directory = "output_files_with_nodes_and_crs"
    os.makedirs(output_directory, exist_ok=True)

    fixed_distance = float(input("Enter the spacing distance: "))
    include_original_nodes = input("Include original nodes? (yes/no): ").strip().lower() == 'yes'
    retain_attributes = input("Retain original line attributes? (yes/no): ").strip().lower() == 'yes'
    export_shapefile = input("Export Shapefile? (yes/no): ").strip().lower() == 'yes'

    field_name = input("Classify the segment line naming: ")
    if field_name not in gdf.columns:
        print(f"Column '{field_name}' does not exist. Using sequential naming instead.")
        gdf['segment_name'] = gdf.index.to_series().astype(str)
        field_name = 'segment_name'

    use_geotiff = bool(geotiff_path)
    if use_geotiff:
        with rasterio.open(geotiff_path) as src:
            geotiff_array = src.read(1)
            transform = src.transform
            nodata_value = src.nodata
    else:
        geotiff_array, transform, nodata_value = None, None, None

    transformer_to_4326 = Transformer.from_crs(gdf.crs, "EPSG:4326", always_xy=True)
    segment_count = 0
    report_data = []

    for unique_value in gdf[field_name].unique():
        segment_gdf = gdf[gdf[field_name] == unique_value]
        nodes_data = []
        geometry_data = []

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

            if current_distance - fixed_distance < length:
                end_point = line.interpolate(length)
                points.add((end_point, length))

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
                    distance_meters = round(point.distance(Point(sorted_points[i-1][0])), 3)
                    total_2d_length += distance_meters

                    if use_geotiff and elevation is not None and prev_elevation is not None:
                        dz = elevation - prev_elevation
                        length_3d = sqrt(distance_meters ** 2 + dz ** 2)
                        total_3d_length += length_3d

                node_data = {
                    "Longitude": lon,
                    "Latitude": lat,
                    "Easting": point.x,
                    "Northing": point.y,
                    "Elevation": elevation,
                    "Distance_Meters": distance_meters,
                    "Length_3D": length_3d if use_geotiff else None,
                    "KP": round(distance_along_line, 3),
                    "Total_3D_Length": total_3d_length if use_geotiff else None,
                    field_name: unique_value
                }

                if retain_attributes:
                    for col in gdf.columns:
                        if col not in node_data:
                            node_data[col] = row[col]

                nodes_data.append(node_data)
                geometry_data.append(Point(point.x, point.y))
                prev_point = (lon, lat, elevation)

        if nodes_data:
            segment_count += 1
            nodes_df = pd.DataFrame(nodes_data)
            csv_file = os.path.join(output_directory, f"{unique_value}_nodes.csv")
            nodes_df.to_csv(csv_file, index=False)

            if export_shapefile:
                gdf_output = gpd.GeoDataFrame(nodes_df, geometry=geometry_data, crs=gdf.crs)
                shp_file = os.path.join(output_directory, f"{unique_value}_nodes.shp")
                gdf_output.to_file(shp_file, driver="ESRI Shapefile")
                print(f"Shapefile saved to: {shp_file} with EPSG: {gdf.crs.to_string()}")

            report_data.append({
                "Segment": unique_value,
                "Total 2D Distance": total_2d_length,
                "Total 3D Distance": total_3d_length if use_geotiff else None,
                "Output CSV": csv_file,
                "Output Shapefile": shp_file if export_shapefile else None
            })

    report_df = pd.DataFrame(report_data)
    report_file = os.path.join(output_directory, "processing_report.csv")
    report_df.to_csv(report_file, index=False)

    print(f"Complete. Total {segment_count} lines processed. Report saved to '{report_file}'.")

def main():
    directory = os.getcwd()
    geotiff_path = input("Enter the path to the GeoTIFF file (or leave blank to skip): ").strip() or None

    supported_extensions = [".gpkg", ".geojson", ".shp"]
    for filename in os.listdir(directory):
        if any(filename.endswith(ext) for ext in supported_extensions):
            file_path = os.path.join(directory, filename)
            process_line_data(file_path, geotiff_path)
            break
    else:
        print(f"No supported files ({', '.join(supported_extensions)}) found in the current directory.")

if __name__ == "__main__":
    main()
