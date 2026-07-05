# ---- OSM sidewalk snapping via Overpass (no heavy GIS deps) ----
import math, requests
from typing import List, Tuple, Optional

# Try multiple public Overpass mirrors (they’re rate-limited).
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

def snap_to_osm_sidewalk(
    lon: float,
    lat: float,
    radius_m: int = 80,
    timeout_s: float = 10.0,
) -> Optional[Tuple[float, float]]:
    """
    Return (snapped_lon, snapped_lat) on the nearest OSM sidewalk line
    within `radius_m` meters of (lon, lat). If no sidewalks are found, return None.
    Sidewalks are ways tagged: highway=footway + footway=sidewalk
    """

    # 1) Query Overpass for nearby sidewalks
    query = f"""
    [out:json][timeout:8];
    (
      way(around:{radius_m},{lat},{lon})["highway"="footway"]["footway"="sidewalk"];
    );
    (._;>;);
    out geom;
    """

    data = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(
                url, data=query.encode("utf-8"), timeout=timeout_s,
                headers={"User-Agent": "sidewalk-snapper/0.1"}
            )
            r.raise_for_status()
            data = r.json()
            break
        except Exception:
            data = None
            continue

    if not data:
        return None

    # Extract sidewalk polylines as [[lon,lat], ...]
    lines: List[List[List[float]]] = []
    for el in data.get("elements", []):
        if el.get("type") == "way" and "geometry" in el:
            coords = [[n["lon"], n["lat"]] for n in el["geometry"]]
            if len(coords) >= 2:
                lines.append(coords)

    if not lines:
        return None

    # 2) Work in local meters (equirectangular) for more accurate geometry
    lon0, lat0 = lon, lat

    def to_xy(lon_, lat_):
        R = 6378137.0
        x = math.radians(lon_ - lon0) * R * math.cos(math.radians(lat0))
        y = math.radians(lat_ - lat0) * R
        return x, y

    def to_lonlat(x, y):
        R = 6378137.0
        lon_ = lon0 + math.degrees(x / (R * math.cos(math.radians(lat0))))
        lat_ = lat0 + math.degrees(y / R)
        return lon_, lat_

    px, py = to_xy(lon, lat)

    def nearest_point_on_segment(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        seg_len2 = vx*vx + vy*vy
        if seg_len2 == 0:
            # A==B
            return ax, ay
        t = max(0.0, min(1.0, (wx*vx + wy*vy) / seg_len2))
        return ax + t*vx, ay + t*vy

    best_dist2 = None
    best_xy: Optional[Tuple[float,float]] = None

    # 3) Find closest point across all sidewalk segments
    for line in lines:
        # convert line to local XY
        xy = [to_xy(lon_, lat_) for lon_, lat_ in line]
        for i in range(len(xy) - 1):
            ax, ay = xy[i]
            bx, by = xy[i+1]
            qx, qy = nearest_point_on_segment(px, py, ax, ay, bx, by)
            dx, dy = px - qx, py - qy
            d2 = dx*dx + dy*dy
            if best_dist2 is None or d2 < best_dist2:
                best_dist2 = d2
                best_xy = (qx, qy)

    if best_xy is None:
        return None

    snapped_lon, snapped_lat = to_lonlat(*best_xy)
    return (snapped_lon, snapped_lat)


snapped = snap_to_osm_sidewalk(lon=-79.47991663636664, lat=43.62354547771446, radius_m=80) 
if snapped:
    print("Snapped:", snapped)  # (lon, lat) on the nearest sidewalk
else:
    print("No sidewalk found nearby.")
