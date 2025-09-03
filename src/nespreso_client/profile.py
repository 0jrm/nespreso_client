from __future__ import annotations

import asyncio
import warnings
from typing import List

import httpx

from .utils import preprocess_inputs, apply_netcdf_global_attributes

# Default API endpoint
DEFAULT_API = "http://localhost:5000/v1/profile"

# Default timeout settings
DEFAULT_TIMEOUT = 1800  # 30 minutes
DEFAULT_CONNECT_TIMEOUT = 10.0  # 10 seconds


async def fetch_predictions(lat,
                            lon,
                            date,
                            filename: str = "output.nc",
                            api_url: str | None = None) -> str | None:
    """Fetch predictions from the NeSPReSO API asynchronously.

    Args:
        lat: Latitude values (single value, list, or array)
        lon: Longitude values (single value, list, or array)
        date: Date values in YYYY-MM-DD format (single value, list, or array)
        filename: Output NetCDF filename
        api_url: API endpoint URL (defaults to DEFAULT_API)

    Returns:
        Output filename on success, None on failure
    """
    api_url = api_url or DEFAULT_API

    # Warn about deprecated endpoint
    if api_url.endswith("/predict"):
        warnings.warn("You are using the deprecated /predict endpoint. Use /v1/profile.")

    # Prepare request data
    data = {"lat": lat, "lon": lon, "date": date}
    timeout = httpx.Timeout(DEFAULT_TIMEOUT, connect=DEFAULT_CONNECT_TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(api_url, json=data)
    except Exception as exc:
        print(f"HTTP error: {exc}")
        return None

    # Check response status
    if response.status_code != 200:
        print(f"Request failed: {response.status_code} – {response.text[:200]}")
        return None

    # Verify content type
    if not response.headers.get("Content-Type", "").startswith("application/x-netcdf"):
        print("Unexpected content type:", response.headers.get("Content-Type"))
        return None

    # Write NetCDF file
    try:
        with open(filename, "wb") as f:
            f.write(response.content)
    except Exception as exc:
        print(f"Failed to write {filename}: {exc}")
        return None

    return filename


def get_predictions(lat,
                    lon,
                    date,
                    filename: str = "output.nc",
                    api_url: str | None = None) -> str | None:
    """Synchronous wrapper around ``fetch_predictions`` with input preprocessing.

    Handles both synchronous and asynchronous host environments.
    """
    # Preprocess inputs (handles various input types)
    lat, lon, date = preprocess_inputs(lat, lon, date)
    print(f"Fetching predictions for {len(lat)} points...")

    # Check if we're in an async context
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Notebook/async host: schedule task and block until done
        return asyncio.run_coroutine_threadsafe(
            fetch_predictions(lat, lon, date, filename, api_url=api_url), loop
        ).result()
    else:
        # Standard sync context: run in new event loop
        return asyncio.run(fetch_predictions(lat, lon, date, filename, api_url=api_url))


def get_predictions_batch(lat,
                          lon,
                          date,
                          batch_size: int = 1000,
                          filename_prefix: str = "output",
                          api_url: str | None = None,
                          merge_output: bool = True):
    """Process large datasets in batches and optionally merge outputs.

    Returns the merged filename, a list of batch filenames, or None.
    """
    # Preprocess inputs
    lat, lon, date = preprocess_inputs(lat, lon, date)
    total_points = len(lat)
    print(f"Processing {total_points} points in batches of {batch_size}")

    successful_files: list[str] = []

    # Process each batch
    for start_index in range(0, total_points, batch_size):
        end_index = min(start_index + batch_size, total_points)
        batch_lat = lat[start_index:end_index]
        batch_lon = lon[start_index:end_index]
        batch_date = date[start_index:end_index]

        batch_filename = f"{filename_prefix}_batch_{start_index // batch_size + 1:03d}.nc"
        print(
            f"Processing batch {start_index // batch_size + 1} "
            f"({start_index + 1}-{end_index} of {total_points})"
        )

        try:
            result = get_predictions(
                batch_lat, batch_lon, batch_date, filename=batch_filename, api_url=api_url
            )
            if result:
                successful_files.append(result)
                print(
                    f"Batch {start_index // batch_size + 1} completed successfully: {result}"
                )
            else:
                print(f"Batch {start_index // batch_size + 1} failed")
        except Exception as exc:
            print(f"Batch {start_index // batch_size + 1} failed with error: {exc}")

    print(
        f"Completed {len(successful_files)} out of {(total_points + batch_size - 1) // batch_size} batches"
    )

    # Handle output based on merge setting and results
    if merge_output and len(successful_files) > 1:
        # Determine final output filename
        if filename_prefix.endswith('.nc'):
            final_output = filename_prefix
        else:
            final_output = f"{filename_prefix}.nc"

        print(f"Auto-merging {len(successful_files)} batch files into {final_output}")
        merged_file = merge_netcdf_files(successful_files, final_output)

        if merged_file:
            print(f"Successfully created merged output: {merged_file}")
            return merged_file
        else:
            print("Failed to merge files, returning batch file list")
            return successful_files
    elif len(successful_files) == 1:
        # Only one batch, return the single file
        return successful_files[0]
    else:
        # No successful batches or merge not requested
        return successful_files


def merge_netcdf_files(file_list: List[str], output_filename: str) -> str | None:
    """Merge multiple NetCDF files into a single file using xarray.

    The function imports xarray lazily so that it remains an optional dependency.
    """
    try:
        import xarray as xr
        import numpy as np
    except ImportError:
        print("xarray is required for merging NetCDF files. Install with: pip install nespreso-client[merge]")
        return None

    if not file_list:
        print("No files to merge")
        return None

    print(f"Merging {len(file_list)} NetCDF files into {output_filename}")

    datasets: list = []
    try:
        # Open all datasets
        for i, filename in enumerate(file_list):
            print(f"  Loading file {i+1}/{len(file_list)}: {filename}")
            ds = xr.open_dataset(filename)
            datasets.append(ds)

        # Concatenate along profile_number dimension
        print("  Concatenating datasets...")
        merged_ds = xr.concat(datasets, dim='profile_number')

        # Reindex profile_number to be sequential
        merged_ds = merged_ds.assign_coords(profile_number=np.arange(len(merged_ds.profile_number)))

        # Ensure global attributes on merged output
        merged_ds = apply_netcdf_global_attributes(merged_ds)

        # Write merged dataset
        print(f"  Writing merged dataset to {output_filename}")
        merged_ds.to_netcdf(output_filename)

        print(f"Successfully merged {len(file_list)} files into {output_filename}")
        return output_filename

    except Exception as exc:
        print(f"Error merging files: {exc}")
        return None
    finally:
        # Clean up - close all datasets
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass


