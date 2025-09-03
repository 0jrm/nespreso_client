# nespreso-client

Lightweight Python client for the NeSPReSO API (synthetic temperature/salinity profiles and grid queries).

## Install

```bash
# From source (editable)
pip install -e /unity/g2/jmiranda/nespreso_client

# Or when published to PyPI (example)
pip install nespreso-client

# Optional extras for merging NetCDF batches
pip install 'nespreso-client[merge]'
```

Python 3.10+ is required.

## Usage

```python
from nespreso_client import (
    get_predictions,
    get_predictions_batch,
    query_grid,
    query_multiple_dates,
    generate_date_range,
    get_common_bbox_regions,
)

# API base URLs (adjust to your server)
PROFILE_API = "http://your-server:5000/v1/profile"
GRID_API = "http://your-server:5000/v1/profile/grid"

# Single-point predictions
out = get_predictions([25.0], [-83.0], ["2016-12-31"], filename="single.nc", api_url=PROFILE_API)
print(out)

# Batch processing with optional merge (requires xarray)
merged = get_predictions_batch(
    [25.0, 26.0, 27.0],
    [-83.0, -84.0, -85.0],
    ["2016-12-31", "2016-12-30", "2016-12-29"],
    batch_size=100,
    filename_prefix="example",
    api_url=PROFILE_API,
    merge_output=True,
)
print(merged)

# Grid queries
bbox = get_common_bbox_regions()["western_gulf"]
res = query_grid("2016-12-31", bbox=bbox, api_url=GRID_API)
print(res)

# Multiple dates
dates = generate_date_range("2016-12-01", "2016-12-31")
summary = query_multiple_dates(dates, api_url=GRID_API)
print(summary)
```

## What gets installed

- Required: httpx, numpy, requests
- Optional extra `merge`: xarray

No server-side models or data are needed on the client.

## License

MIT


