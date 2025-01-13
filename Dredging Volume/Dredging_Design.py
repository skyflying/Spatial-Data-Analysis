import geopandas as gpd
import rasterio
from rasterio import features
from rasterio.transform import rowcol
import numpy as np
from scipy.ndimage import distance_transform_edt
from tqdm import tqdm  
from shapely.geometry import box

# File paths (update these paths if needed)
geotiff_path = r'Dredging Level with buffer zone.tif'
gpkg_path = r'With_buffer.gpkg'
output_geotiff = r'output_new_geotiff_vh_corrected_position.tif'


# Parameters for user to adjust
vh_ratio = 3  # V:H ratio (e.g., 1:3 as 3)
threshold_distance_meters = 20  # Set the maximum distance for V:H adjustment in meters

# Load GPKG data
gpkg_data = gpd.read_file(gpkg_path)

# Load GeoTIFF data
with rasterio.open(geotiff_path) as src:
    geotiff_data = src.read(1)  # Read first band
    geotiff_transform = src.transform
    geotiff_profile = src.profile
    geotiff_bounds = src.bounds  # Get GeoTIFF bounds
    geotiff_resolution = src.res[0]  # Get resolution (meters per pixel)

# Convert threshold distance from meters to pixels
threshold_distance_pixels = threshold_distance_meters / geotiff_resolution

# Create a copy of the GeoTIFF data for adjusted depths
adjusted_surface = np.copy(geotiff_data)

# Create an empty surface to store the polygon depth values
flat_surface = np.full(geotiff_data.shape, np.nan)

# Function to adjust depths starting from the polygon boundary outward
def adjust_depth_from_boundary(y, x, flat_surface, geotiff_data, distance_to_boundary, vh_ratio, boundary_depth):
    delta_z = distance_to_boundary[y, x] / vh_ratio
    new_depth = boundary_depth + delta_z
    # Ensure the depth does not become shallower than the GeoTIFF value
    return min(new_depth, geotiff_data[y, x])

# Process each polygon
for index, row in gpkg_data.iterrows():
    polygon = row['geometry']
    depth_value = row['Depth']

    # Create a buffer to limit calculations, but not to calculate every point within the buffer
    buffered_polygon = polygon.buffer(threshold_distance_meters)

    # Clip the buffered polygon to GeoTIFF bounds to avoid unnecessary calculations
    clipped_polygon = buffered_polygon.intersection(box(*geotiff_bounds))

    if clipped_polygon.is_empty:
        continue

    # Calculate the bounding box of the clipped polygon to limit the calculation range
    minx, miny, maxx, maxy = clipped_polygon.bounds

    # Use the 'src.index' method to convert world coordinates (lon/lat) to row/col
    row_min, col_min = src.index(minx, maxy)  # Top-left corner
    row_max, col_max = src.index(maxx, miny)  # Bottom-right corner

    # Convert to integers
    row_min, row_max = int(row_min), int(row_max)
    col_min, col_max = int(col_min), int(col_max)

    # Ensure valid dimensions for the sub-region
    if row_min >= row_max or col_min >= col_max or row_min < 0 or col_min < 0:
        print(f"Invalid bounding box for polygon at index {index}. Skipping this polygon.")
        continue

    # Check if the calculated shape is valid
    block_shape = (row_max - row_min, col_max - col_min)
    if block_shape[0] <= 0 or block_shape[1] <= 0:
        print(f"Skipping polygon at index {index} due to invalid block shape.")
        continue

    # Extract the sub-region of the GeoTIFF and flat_surface for this polygon
    flat_surface_block = flat_surface[row_min:row_max, col_min:col_max]
    adjusted_surface_block = adjusted_surface[row_min:row_max, col_min:col_max]
    geotiff_block = geotiff_data[row_min:row_max, col_min:col_max]

    # Define the transform for this sub-region
    sub_transform = rasterio.transform.from_bounds(minx, miny, maxx, maxy, block_shape[1], block_shape[0])

    # Create mask for the original polygon to define the true boundary
    polygon_mask = features.geometry_mask([polygon], out_shape=block_shape, transform=sub_transform, invert=True)

    # Debug information: Check the mask and block shape
    print(f"Index {index}: polygon_mask shape: {polygon_mask.shape}, flat_surface_block shape: {flat_surface_block.shape}")

    # Ensure the mask has the correct shape before applying
    if polygon_mask.shape != flat_surface_block.shape:
        print(f"Shape mismatch at index {index}: polygon_mask shape {polygon_mask.shape}, flat_surface_block shape {flat_surface_block.shape}")
        continue

    # Assign depth values inside the original polygon
    flat_surface_block[polygon_mask] = depth_value
    adjusted_surface_block[polygon_mask] = np.where(geotiff_block[polygon_mask] < depth_value,
                                                    geotiff_block[polygon_mask], depth_value)

    # Calculate distance from the original polygon boundary outward, limited to the buffer area
    distance_to_boundary = distance_transform_edt(~polygon_mask) * geotiff_resolution

    # Initialize progress bar
    with tqdm(total=np.count_nonzero(polygon_mask), desc="Optimized depth calculation", unit="pixel") as pbar:
        # Adjust depths based on distance and V:H ratio, limited to the bounding box and within the buffer area
        for y in range(row_max - row_min):
            for x in range(col_max - col_min):
                if np.isnan(flat_surface_block[y, x]) and distance_to_boundary[y, x] <= threshold_distance_pixels:
                    adjusted_surface_block[y, x] = adjust_depth_from_boundary(y, x, flat_surface_block, geotiff_block,
                                                                              distance_to_boundary, vh_ratio, depth_value)
                pbar.update(1)

# Save the adjusted GeoTIFF
geotiff_profile.update(dtype=rasterio.float32, count=1, compress='lzw')

with rasterio.open(output_geotiff, 'w', **geotiff_profile) as dst:
    dst.write(adjusted_surface.astype(rasterio.float32), 1)

print(f"New GeoTIFF file saved at: {output_geotiff}")
