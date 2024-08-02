import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
import numpy as np
import os
from pyproj import Transformer
from shapely.geometry import MultiLineString

def main():
    # Input the line data
    file_path = input("Enter the file path for the line data (e.g., data.gpkg): ")
    gdf = gpd.read_file(file_path)

    output_directory = "output_files_with_nodes_and_crs"
    os.makedirs(output_directory, exist_ok=True)

    fixed_distance = input("Enter the spacing distance: ")
    fixed_distance = float(fixed_distance)
    include_original_nodes = input("Include original nodes? (yes/no): ").strip().lower() == 'yes'
    retain_attributes = input("Retain original line attributes? (yes/no): ").strip().lower() == 'yes'

    print("All the columns:", gdf.columns.tolist())
    print("First 10 rows:")
    print(gdf.head(10))
    field_name = input("Classify the segment line naming: ")

    # Check if the field_name is valid
    if field_name not in gdf.columns:
        print(f"Column '{field_name}' does not exist. Using sequential naming instead.")
        gdf['segment_name'] = gdf.index.to_series().astype(str)
        field_name = 'segment_name'

    transformer_4326_to_3826 = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    transformer_to_4326 = Transformer.from_crs(gdf.crs, "EPSG:4326", always_xy=True)

    segment_count = 0

    for unique_value in gdf[field_name].unique():
        segment_gdf = gdf[gdf[field_name] == unique_value]
        
        nodes_data = []
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

            # Collect all points, both interpolated and original, without duplication
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
            
            # Sort points by distance along the line
            sorted_points = sorted(points, key=lambda x: x[1])
            
            # Generate nodes data with recalculated distances
            for i, (point, distance_along_line) in enumerate(sorted_points):
                lon, lat = transformer_to_4326.transform(point.x, point.y)
                easting, northing = transformer_4326_to_3826.transform(lon, lat)

                distance_meters = None if i == 0 else point.distance(Point(sorted_points[i-1][0]))
                node_data = {
                    "Longitude": lon,
                    "Latitude": lat,
                    "Easting": easting,
                    "Northing": northing,
                    "Distance_Meters": distance_meters,
                    "Total_Distance": distance_along_line,
                    field_name: unique_value
                }

                if retain_attributes:
                    for col in gdf.columns:
                        if col not in node_data:
                            node_data[col] = row[col]

                nodes_data.append(node_data)

        if nodes_data:
            segment_count += 1

            nodes_df = pd.DataFrame(nodes_data)
            csv_file_name = input(f"Enter the file name for the CSV output for segment '{unique_value}' (without extension): ")
            csv_file = os.path.join(output_directory, f"{csv_file_name}_nodes.csv")
            nodes_df.to_csv(csv_file, index=False)

            geometry = [Point(xy) for xy in zip(nodes_df.Longitude, nodes_df.Latitude)]
            nodes_gdf = gpd.GeoDataFrame(nodes_df, geometry=geometry, crs="EPSG:4326")

            shp_file_name = input(f"Enter the file name for the Shapefile output for segment '{unique_value}' (without extension): ")
            shp_file = os.path.join(output_directory, f"{shp_file_name}_nodes.shp")
            nodes_gdf.to_file(shp_file)

    print(f"Complete. Total {segment_count} lines processed, output under '{output_directory}'.")

if __name__ == "__main__":
    main()
