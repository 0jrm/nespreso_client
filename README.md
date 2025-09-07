# nespreso-client

Lightweight Python client for the NeSPReSO API (synthetic temperature/salinity profiles and grid queries).

## Install

```bash
pip install nespreso-client
```

Requires Python 3.10+.

## Endpoints (FSU Ozavala deployment)

If you are using the public deployment via Ozavala, use these proxied HTTPS endpoints:

```python
PROFILE_API = "https://ozavala.coaps.fsu.edu/nespreso_profile"
GRID_API    = "https://ozavala.coaps.fsu.edu/nespreso_grid"
```

For self-hosted setups, point to your API directly (e.g., Gunicorn on port 5000):

```python
PROFILE_API = "http://your-server:5000/v1_profile"
GRID_API    = "http://your-server:5000/v1_profile/grid"
```

## Quickstart

```python
from nespreso_client import (
    get_predictions,
    get_predictions_batch,
    query_grid,
    query_multiple_dates,
    generate_date_range,
    get_common_bbox_regions,
)

# --- Profiles: single-point ---
out = get_predictions(
    lat=[25.0], lon=[-83.0], date=["2016-12-31"],
    filename="single.nc", api_url="https://ozavala.coaps.fsu.edu/nespreso_profile",
)
print(out)  # -> "single.nc" on success

# --- Profiles: batch with optional merge (requires xarray for merge) ---
merged = get_predictions_batch(
    [25.0, 26.0, 27.0],
    [-83.0, -84.0, -85.0],
    ["2016-12-31", "2016-12-30", "2016-12-29"],
    batch_size=100,
    filename_prefix="example",
    api_url="https://ozavala.coaps.fsu.edu/nespreso_profile",
    merge_output=True,
)
print(merged)

# --- Grid query ---
bbox = get_common_bbox_regions()["western_gulf"]
res = query_grid(
    "2016-12-31",
    bbox=bbox,
    api_url="https://ozavala.coaps.fsu.edu/nespreso_grid",
)
print(res)  # includes saved filename and size

# --- Grid over multiple dates ---
dates = generate_date_range("2016-12-01", "2016-12-31")
summary = query_multiple_dates(dates, api_url="https://ozavala.coaps.fsu.edu/nespreso_grid")
print(summary)
```

Notes
- Grid downloads are saved under `uses/grid/` by default.
- Large requests can take minutes. Defaults: profiles timeout 30 min; grid timeout 10 min.

## Dependencies

- Required: `httpx`, `numpy`, `requests`
- Optional extra `merge`: `xarray`

No server-side models or data are needed on the client.

## License

MIT
