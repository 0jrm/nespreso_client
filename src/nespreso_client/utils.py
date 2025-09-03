from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

import numpy as np


def _as_numpy_array(data) -> np.ndarray:
    """Best-effort conversion to a NumPy array without heavy optional deps.

    Avoids importing pandas/xarray so the client stays lightweight. If callers
    pass pandas Series or xarray DataArray, NumPy will coerce them properly.
    """
    try:
        return np.asarray(data)
    except Exception:
        # Fallback for exotic objects: wrap as a list then coerce
        return np.asarray([data])


def _to_float_list(data) -> list[float]:
    arr = _as_numpy_array(data)
    if arr.ndim > 1:
        arr = arr.ravel()
    return arr.astype(float).tolist()


def _datenum_to_iso_string(value: float) -> str:
    # MATLAB datenums count days from 0001-01-01 with an offset of 366
    try:
        days_since_year1 = float(value) - 366.0
        base = datetime(1, 1, 1)
        return (base + timedelta(days=days_since_year1)).strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def convert_date_to_iso_strings(date) -> list[str]:
    """Convert various date representations to ISO YYYY-MM-DD strings.

    Accepts scalars, iterables, numpy arrays, Python datetimes, numpy datetime64,
    MATLAB datenums (floats/ints), and strings.
    """
    # Normalize to a 1-D iterable
    if isinstance(date, (list, tuple, np.ndarray)):
        arr = _as_numpy_array(date)
    else:
        arr = _as_numpy_array([date])

    # Numeric types → MATLAB datenum semantics
    if arr.dtype.kind in {"f", "i"}:
        return [_datenum_to_iso_string(v) for v in arr.tolist()]

    # numpy datetime64
    if np.issubdtype(arr.dtype, np.datetime64):
        return [str(v.astype("M8[D]")) for v in arr]

    # Generic per-element handling
    out: list[str] = []
    for v in arr.tolist():
        if isinstance(v, (float, int, np.floating, np.integer)):
            out.append(_datenum_to_iso_string(v))
        elif isinstance(v, datetime):
            out.append(v.strftime("%Y-%m-%d"))
        else:
            out.append(str(v))
    return out


def preprocess_inputs(lat, lon, date):
    """Normalize inputs for API submission: lists of floats and ISO date strings."""
    lat_out = _to_float_list(lat)
    lon_out = _to_float_list(lon)
    date_out = convert_date_to_iso_strings(date)
    return lat_out, lon_out, date_out


def apply_netcdf_global_attributes(ds, extra_attrs: Mapping[str, str] | None = None):
    """Ensure NeSPReSO global attributes exist on an xarray Dataset-like object.

    Avoids importing xarray here. Any object with a mutable ``.attrs`` mapping
    will work (as provided by xarray). Returns the same object for chaining.
    """
    defaults = {
        "coordinate_system": "geographic",
        "institution": "COAPS, FSU",
        "author": "Jose Roberto Miranda",
        "contact": "jrm22n@fsu.edu",
        "DOI": "https://doi.org/10.1016/j.ocemod.2025.102550",
    }
    if extra_attrs:
        defaults.update({str(k): str(v) for k, v in dict(extra_attrs).items()})
    try:
        ds.attrs.update(defaults)
    except Exception:
        for k, v in defaults.items():
            try:
                ds.attrs[k] = v
            except Exception:
                pass
    return ds


