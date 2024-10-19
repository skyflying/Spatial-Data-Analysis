import geopandas as gpd
import rasterio
from rasterio import features
import numpy as np
from scipy.ndimage import distance_transform_edt
from tqdm import tqdm  


geotiff_path = r'C:\Users\MingyiHsu\OneDrive - HL\Desktop\test2024.tif'
gpkg_path = r'G:\Shared drives\Project Work Clients Other\Hai Long\2_Working_Data\20241014_HL3_EXP_Site_Volume_Calc_\output_buffers_2024 part\all_buffers.gpkg'
output_geotiff = r'output_new_geotiff_vh_corrected_with_progress_ff.tif'


min_horizontal_distance = 20.0  # Minimum horizontal distance in pixel
vh_ratio = 3.0  # V:H ratio (e.g., 1:3 as 3)

# Load the GPKG (polygon) data
gpkg_data = gpd.read_file(gpkg_path)

# Filter out rows with NaN in 'Depth' column
gpkg_data = gpkg_data[~gpkg_data['target_dep'].isnull()]

# Load the GeoTIFF (raster) data
with rasterio.open(geotiff_path) as src:
    geotiff_data = src.read(1)  # Read the first band
    geotiff_transform = src.transform
    geotiff_crs = src.crs
    geotiff_bounds = src.bounds
    geotiff_profile = src.profile

# Create an empty surface to store adjusted depths
adjusted_surface = np.copy(geotiff_data)

# Initialize a mask with NaNs to store the depth from the polygons
flat_surface = np.full(geotiff_data.shape, np.nan)

# Loop over each polygon and set depth values
for index, row in gpkg_data.iterrows():
    polygon = row['geometry']
    depth_value = row['target_dep']
    
    # Create mask for the polygon
    mask = features.geometry_mask([polygon], out_shape=flat_surface.shape, transform=geotiff_transform, invert=True)
    
    # Fill the mask area with the depth value
    flat_surface[mask] = depth_value

# Calculate distance to the nearest polygon boundary using distance transform
distance_to_polygon = distance_transform_edt(np.isnan(flat_surface))

# Function to adjust depth based on neighborhood and distance
def adjust_depth(y, x, flat_surface, distance_to_polygon, vh_ratio, geotiff_data, min_horizontal_distance):
    if not np.isnan(flat_surface[y, x]):
        return flat_surface[y, x]  # Inside the polygon, keep the flat depth
    else:
        effective_distance = max(distance_to_polygon[y, x], min_horizontal_distance)  # Ensure a minimum horizontal distance
        if effective_distance > 0:
            # Get valid neighboring depths within a larger neighborhood (e.g., 5x5)
            neighborhood = flat_surface[max(0, y-5):min(flat_surface.shape[0], y+5), max(0, x-5):min(flat_surface.shape[1], x+5)]
            valid_depths = neighborhood[~np.isnan(neighborhood)]
            
            if len(valid_depths) > 0:
                nearest_depth = np.min(valid_depths)
                delta_z = effective_distance / vh_ratio  # Apply user-defined V:H ratio
                new_value = nearest_depth + delta_z
                return min(new_value, geotiff_data[y, x])  # Ensure new value does not exceed the original GeoTIFF value
        return geotiff_data[y, x]  # If no valid neighboring depth, keep the original GeoTIFF value

# Initialize progress bar
total_pixels = flat_surface.shape[0] * flat_surface.shape[1]
with tqdm(total=total_pixels, desc="Processing GeoTIFF with adjustable parameters") as pbar:
    # Adjust the surrounding areas based on the user-defined V:H ratio
    for y in range(flat_surface.shape[0]):
        for x in range(flat_surface.shape[1]):
            adjusted_surface[y, x] = adjust_depth(y, x, flat_surface, distance_to_polygon, vh_ratio, geotiff_data, min_horizontal_distance)
        pbar.update(flat_surface.shape[1])  # Update after processing each row

# Update the GeoTIFF profile for output (new GeoTIFF)
geotiff_profile.update(dtype=rasterio.float32, count=1, compress='lzw')

# Write the new GeoTIFF
with rasterio.open(output_geotiff, 'w', **geotiff_profile) as dst:
    dst.write(adjusted_surface.astype(rasterio.float32), 1)

print(f"New GeoTIFF file saved at: {output_geotiff}")
