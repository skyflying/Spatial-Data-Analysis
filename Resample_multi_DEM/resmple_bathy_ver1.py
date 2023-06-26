import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import gaussian_filter
import scipy.ndimage
from scipy.spatial import cKDTree
import numpy as np



quality_dict = {'A2': 0, 'B': 1, 'C': 2, 'D': 3}
df['quality_sortable'] = df['quality'].map(quality_dict)

# Sort by date and quality
df = df.sort_values(by=['date', 'quality_sortable'], ascending=[False, True])

# Step 1: Read CSV file
df = pd.read_csv('file_list.csv')

# Function to get the bounding box of a raster dataset
def get_bounds(dataset):
    left, bottom, right, top = dataset.bounds
    return left, bottom, right, top

# Step 2: Calculate the overall bounding box
overall_left = float('inf')
overall_bottom = float('inf')
overall_right = float('-inf')
overall_top = float('-inf')

for index, row in df.iterrows():
    file_path = row['path']
    try:
        with rasterio.open(file_path) as dataset:
            left, bottom, right, top = get_bounds(dataset)
            overall_left = min(overall_left, left)
            overall_bottom = min(overall_bottom, bottom)
            overall_right = max(overall_right, right)
            overall_top = max(overall_top, top)
    except rasterio.errors.RasterioIOError:
        print(f"Could not load {file_path}")

# Step 3: Create a new raster that covers the overall bounding box
resolution = 1  # 10 meters per pixel
width = int((overall_right - overall_left) / resolution)
height = int((overall_top - overall_bottom) / resolution)
transform = rasterio.transform.from_origin(overall_left, overall_top, resolution, resolution)

with rasterio.open(df['path'][0]) as first_dataset:
    crs = first_dataset.crs if first_dataset.crs else rasterio.crs.CRS.from_string('EPSG:3826')

data = np.full((height, width), np.nan)

filled_mask = np.zeros((height, width), dtype=bool)


with rasterio.open('output.tif', 'w', driver='GTiff',
                   height=height, width=width, count=1, dtype=str(data.dtype),
                   crs=crs, transform=transform) as dst:
    dst.write(data, 1)



with rasterio.open('output.tif', 'r+') as dst:
    for index, row in df.iterrows():
        # If all pixels have been filled, we can stop
        if filled_mask.all():
            print(f"All pixels filled after {index} files.")
            break

        file_path = row['path']
        try:
            with rasterio.open(file_path) as src:
                # Check if the CRS is defined, if not assume it is 'EPSG:3826'
                src_crs = src.crs if src.crs else rasterio.crs.CRS.from_string('EPSG:3826')

                # Create a temporary array for the reprojected data
                reprojected_data = np.empty_like(dst.read(1))

                reproject(
                    source=rasterio.band(src, 1),
                    destination=reprojected_data,
                    src_transform=src.transform,
                    src_crs=src_crs,
                    dst_transform=dst.transform,
                    dst_crs=dst.crs,
                    resampling=Resampling.average)

                # Only fill the pixels that have not been filled yet
                data = dst.read(1)  # Read the current data
                np.copyto(data, reprojected_data, where=~filled_mask)  # Update the data with the reprojected data
                dst.write(data, 1)  # Write the data back to the GeoTIFF file

                # Update the filled_mask
                filled_mask[~np.isnan(reprojected_data)] = True

        except rasterio.errors.RasterioIOError:
            print(f"Could not load {file_path}")

    data = dst.read(1)
    smoothed_data = scipy.ndimage.gaussian_filter(data, sigma=1)  # Adjust sigma as needed

    # Fill holes that are within 10 pixels from valid data
    y_indices, x_indices = np.indices(data.shape)
    valid_mask = ~np.isnan(smoothed_data)
    valid_y_indices = y_indices[valid_mask]
    valid_x_indices = x_indices[valid_mask]
    valid_values = smoothed_data[valid_mask]

    tree = cKDTree(np.column_stack((valid_y_indices, valid_x_indices)))
    hole_y_indices = y_indices[~valid_mask]
    hole_x_indices = x_indices[~valid_mask]
    distances, indices = tree.query(np.column_stack((hole_y_indices, hole_x_indices)), k=5, distance_upper_bound=10)    
    
    # Create a mask for valid indices
    valid_indices_mask = indices != tree.n
    
    # Average the values of the 5 nearest pixels
    hole_values = np.empty(len(indices))
    for i, (index_row, distance_row) in enumerate(zip(indices, distances)):
        valid_indices = index_row[valid_indices_mask[i]]
        valid_distances = distance_row[valid_indices_mask[i]]
    
        if len(valid_indices) > 0:
            hole_values[i] = np.average(valid_values[valid_indices], weights=(1/valid_distances))
        else:
            hole_values[i] = np.nan

    smoothed_data[~valid_mask] = hole_values

    dst.write(smoothed_data, 1)
	
	
# Smooth
def smooth_lowess(data, frac=0.3):
    x = np.arange(len(data))
    valid_mask = ~np.isnan(data)
    x_valid = x[valid_mask]
    data_valid = data[valid_mask]
    if len(x_valid) == 0:
        return data
    smoothed_valid = lowess(data_valid, x_valid, frac=frac)
    # Sort smoothed data by x values
    smoothed_valid = smoothed_valid[smoothed_valid[:, 0].argsort()]
    smoothed = np.empty_like(data)
    smoothed[:] = np.nan
    # Interpolate the smoothed data to match the original data size
    smoothed[valid_mask] = np.interp(x_valid, smoothed_valid[:, 0], smoothed_valid[:, 1])
    return smoothed

with rasterio.open('output.tif') as src:
    profile = src.profile
    data = src.read(1)

# Initialize an empty array for the smoothed band
smoothed_band = np.empty_like(data)

# Apply the smoothing function to each column
for i in range(data.shape[1]):
    smoothed_band[:, i] = smooth_lowess(data[:, i])

with rasterio.open('output_smoothed.tif', 'w', **src.profile) as dst:
    dst.write(smoothed_band, 1)
	
def geotiff_to_xyz(input_geotiff, output_xyz):
    with rasterio.open(input_geotiff) as src:
        affine = src.transform
        array = src.read(1)
        array[array == src.nodata] = np.nan  # handle nodata values if any

    height, width = array.shape

    x_coordinates = np.arange(width) * affine[0] + affine[2]
    y_coordinates = np.arange(height) * affine[4] + affine[5]

    x_coordinates, y_coordinates = np.meshgrid(x_coordinates, y_coordinates)

    stacked_coordinates = np.column_stack((x_coordinates.flatten(), y_coordinates.flatten(), array.flatten()))

    np.savetxt(output_xyz, stacked_coordinates, delimiter=',', fmt='%f')


geotiff_to_xyz('output.tif', 'output.xyz')
geotiff_to_xyz('output_smoothed.tif', 'utput_smoothed.xyz')
