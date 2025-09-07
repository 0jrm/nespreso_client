from __future__ import annotations

import os
from typing import Dict, List, Optional
from datetime import datetime

import requests


# Configuration
GRID_OUTPUT_DIR = os.path.join("uses", "grid")
DEFAULT_API_URL = "https://ozavala.coaps.fsu.edu/nespreso_grid"
DEFAULT_TIMEOUT = 600  # 10 minutes


def ensure_grid_output_dir() -> None:
    """Create the grid output directory if it doesn't exist."""
    if not os.path.exists(GRID_OUTPUT_DIR):
        os.makedirs(GRID_OUTPUT_DIR, exist_ok=True)
        print(f"Created output directory: {GRID_OUTPUT_DIR}")


def query_grid(date_str: str,
               bbox: Optional[List[float]] = None,
               resolution: Optional[float] = None,
               api_url: str = DEFAULT_API_URL) -> Dict:
    """Query the grid endpoint for a specific date, optionally with BBOX and resolution.

    Returns a dictionary with success status and details.
    """
    ensure_grid_output_dir()

    # Prepare the request
    request_data = {"date": date_str}

    # Validate date
    try:
        datetime.strptime(request_data["date"], "%Y-%m-%d")
    except Exception:
        print("Invalid date. Use YYYY-MM-DD.")
        return {"success": False, "error": "Invalid date. Use YYYY-MM-DD."}
    if bbox is not None:
        # Validate bbox
        try:
            if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
                return {"success": False, "error": "Invalid bbox. Use [lon_min, lat_min, lon_max, lat_max]."}
            lon_min, lat_min, lon_max, lat_max = [float(x) for x in bbox]
        except Exception:
            return {"success": False, "error": "Invalid bbox values. Must be numeric [lon_min, lat_min, lon_max, lat_max]."}
        if not (-180.0 <= lon_min <= 180.0 and -180.0 <= lon_max <= 180.0 and -90.0 <= lat_min <= 90.0 and -90.0 <= lat_max <= 90.0):
            return {"success": False, "error": "BBOX out of range. Lon in [-180,180], Lat in [-90,90]."}
        if not (lon_min < lon_max and lat_min < lat_max):
            return {"success": False, "error": "BBOX order invalid. Require lon_min < lon_max and lat_min < lat_max."}
        request_data["bbox"] = [lon_min, lat_min, lon_max, lat_max]
    if resolution is not None:
        try:
            res = float(resolution)
        except Exception:
            return {"success": False, "error": "Resolution must be a positive number (degrees)."}
        if not (res > 0):
            return {"success": False, "error": "Resolution must be > 0 (degrees)."}
        request_data["resolution"] = res

    if bbox is not None and resolution is not None:
        print(
            f"Querying grid for date: {date_str} with BBOX: {bbox} at resolution: {resolution}"
        )
    elif bbox is not None:
        print(f"Querying grid for date: {date_str} with BBOX: {bbox}")
    elif resolution is not None:
        print(f"Querying grid for date: {date_str} at resolution: {resolution}")
    else:
        print(f"Querying grid for date: {date_str} (full grid)")

    print(f"API endpoint: {api_url}")

    try:
        # Make the request
        response = requests.post(api_url, json=request_data, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 200:
            # Success - save the NetCDF file
            parts = [f"nespreso_grid_{date_str}"]
            if bbox:
                parts.append(
                    f"_bbox_{bbox[0]:.2f}_{bbox[1]:.2f}_{bbox[2]:.2f}_{bbox[3]:.2f}"
                )
            if resolution is not None:
                parts.append(f"_res_{float(resolution):.3f}")
            output_filename = "".join(parts) + ".nc"

            output_path = os.path.join(GRID_OUTPUT_DIR, output_filename)
            with open(output_path, 'wb') as f:
                f.write(response.content)

            print("✅ Grid query successful!")
            print(f"Output saved to: {output_path}")
            print(f"File size: {len(response.content)} bytes")

            return {
                "success": True,
                "filename": output_path,
                "size_bytes": len(response.content),
                "status_code": response.status_code,
            }

        else:
            # Error response
            print(f"❌ Grid query failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except Exception:
                print(f"Error response: {response.text}")

            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
            }

    except requests.exceptions.Timeout:
        print("❌ Request timed out (10 minutes)")
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException as exc:
        print(f"❌ Request failed: {exc}")
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        print(f"❌ Unexpected error: {exc}")
        return {"success": False, "error": str(exc)}


def query_multiple_dates(date_list: List[str],
                         bbox: Optional[List[float]] = None,
                         resolution: Optional[float] = None,
                         api_url: str = DEFAULT_API_URL) -> Dict:
    """Query the grid endpoint for multiple dates, optionally with BBOX and resolution."""
    bbox_info = f" with BBOX {bbox}" if bbox else ""
    res_info = f" at resolution {resolution}" if resolution is not None else ""
    print(f"Querying grid for {len(date_list)} dates{bbox_info}{res_info}...")

    results: list[Dict] = []
    successful = 0
    failed = 0

    for i, date_str in enumerate(date_list, 1):
        print(f"\n[{i}/{len(date_list)}] Processing date: {date_str}")

        result = query_grid(date_str, bbox=bbox, resolution=resolution, api_url=api_url)
        results.append(result)

        if result.get("success"):
            successful += 1
        else:
            failed += 1

    # Summary
    print("\n=== Summary ===")
    print(f"Total dates: {len(date_list)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    return {
        "total": len(date_list),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """Generate a list of dates between start_date and end_date (inclusive)."""
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    date_list: list[str] = []
    current = start
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return date_list


def get_common_bbox_regions() -> Dict[str, List[float]]:
    """Get commonly used BBOX regions for the Gulf of Mexico."""
    return {
        "full_gulf": [-97.0, 18.0, -82.0, 31.0],
        "western_gulf": [-97.0, 20.0, -90.0, 29.0],
        "eastern_gulf": [-90.0, 20.0, -82.0, 29.0],
        "northern_gulf": [-97.0, 25.0, -82.0, 29.0],
        "southern_gulf": [-97.0, 18.0, -82.0, 25.0],
        "florida_straits": [-82.0, 24.0, -79.0, 26.0],
        "yucatan_channel": [-87.0, 20.0, -84.0, 22.0],
    }


