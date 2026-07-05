# app/main.py
import os, io, json, uuid, gzip, datetime as dt
from typing import List, Optional
from functools import lru_cache
from botocore.client import Config
from dotenv import load_dotenv
load_dotenv()  # loads .env in your project root

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import boto3

from fastapi.staticfiles import StaticFiles
#from find_closest_sidewalk import snap_to_osm_sidewalk  

from .find_closest_sidewalk import snap_to_osm_sidewalk


AWS_REGION = os.getenv("AWS_REGION","us-east-2")
S3_BUCKET  = os.getenv("S3_BUCKET")
if not S3_BUCKET:
    raise RuntimeError("S3_BUCKET env var is required")

s3 = boto3.client("s3", region_name=AWS_REGION, config=Config(signature_version="s3v4"))

app = FastAPI(title="Vision/Trajectory API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------- Models ----------------
class TrajPoint(BaseModel):
    ts: dt.datetime
    lat: float
    lon: float
    speed_mps: Optional[float] = 0
    bearing_deg: Optional[float] = 0
    acc_m: Optional[float] = 0
    provider: Optional[str] = "fused"

class Detection(BaseModel):
    label: str
    confidence: float
    bbox: List[float]  # [x0,y0,x1,y1] (pixels or normalized — your choice)

class FrameMeta(BaseModel):
    ts: dt.datetime
    lat: float
    lon: float
    acc_m: float
    frame_w: int
    frame_h: int
    detections: List[Detection] = Field(default_factory=list)

# --------------- Helpers ----------------
def _date_parts(ts: dt.datetime):
    t = ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)
    return t.strftime("%Y"), t.strftime("%m"), t.strftime("%d")

def _put_json(key: str, obj: dict):
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType="application/json")

def _put_gz_ndjson(key: str, rows: List[dict]):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        for r in rows:
            gz.write((json.dumps(r, separators=(",", ":")) + "\n").encode("utf-8"))
    s3.put_object(
        Bucket=S3_BUCKET, Key=key, Body=buf.getvalue(),
        ContentType="application/x-ndjson", ContentEncoding="gzip"
    )

def _presign_get(key: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": S3_BUCKET, "Key": key}, ExpiresIn=expires
    )

# --------------- Auth stub --------------
def get_device_id() -> str:
    # TODO: parse Authorization header and validate a token.
    print("Device ID=", "dev-00000000")
    return "dev-00000000"

# --------------- Routes -----------------
@app.get("/health")
def health():
    return {"status": "ok", "region": AWS_REGION, "bucket": S3_BUCKET}

@app.post("/v1/trajectory/batch")
def post_traj_batch(points: List[TrajPoint], device_id: str = Depends(get_device_id)):
    if not points:
        raise HTTPException(400, "empty payload")
    y, m, d = _date_parts(points[0].ts)
    key = f"trajectory/{device_id}/{y}{m}{d}/{uuid.uuid4()}.ndjson.gz"

    rows = [
        {
            "device_id": device_id,
            "ts": p.ts.isoformat(),
            "lat": p.lat, "lon": p.lon,
            "speed_mps": p.speed_mps, "bearing_deg": p.bearing_deg,
            "acc_m": p.acc_m, "provider": p.provider,
        } for p in points
    ]
    _put_gz_ndjson(key, rows)
    return {"ok": True, "key": key, "count": len(points)}

@app.post("/v1/frames")
def post_frame(
    image: UploadFile = File(...),
    meta: str = Form(...),
    device_id: str = Depends(get_device_id),
):
    # meta is a JSON string sent from the app
    try:
        fm = FrameMeta.model_validate_json(meta)
    except Exception as e:
        raise HTTPException(400, f"invalid meta: {e}")

    # Snap location to nearest sidewalk
    snapped_location = snap_to_osm_sidewalk(lon=fm.lon, lat=fm.lat, radius_m=80)

    # Use snapped location if found, otherwise use original coordinates
    final_lon = snapped_location[0] if snapped_location else fm.lon
    final_lat = snapped_location[1] if snapped_location else fm.lat

    y, m, d = _date_parts(fm.ts)
    base = f"frames/{device_id}/{y}{m}{d}/{uuid.uuid4()}"
    img_ext = ".jpg" if (image.filename or "").lower().endswith(".jpg") or (image.content_type == "image/jpeg") else ".bin"
    img_key  = f"{base}{img_ext}"
    meta_key = f"{base}.json"

    # 1) store the image
    s3.upload_fileobj(
        image.file, S3_BUCKET, img_key,
        ExtraArgs={"ContentType": image.content_type or "image/jpeg"}
    )

    # 2) store sidecar JSON with location + detections
    meta_obj = {
        "device_id": device_id,
        "ts": fm.ts.isoformat(),
        "lat": final_lat,
        "lon": final_lon,
        "original_lat": fm.lat,  # Store original coordinates
        "original_lon": fm.lon,
        "acc_m": fm.acc_m,
        "frame_w": fm.frame_w, "frame_h": fm.frame_h,
        "detections": [d.model_dump() for d in fm.detections],
        "image_key": img_key,
        # quick GeoJSON for mapping later
        "feature": {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [final_lon, final_lat]},
            "properties": {
                "device_id": device_id,
                "ts": fm.ts.isoformat(),
                "labels": list({d.label for d in fm.detections}),
                "image_key": img_key
            }
        }
    }
    _put_json(meta_key, meta_obj)

    return {
        "ok": True,
        "image_key": img_key,
        "meta_key": meta_key,
        "image_url": _presign_get(img_key),  # handy for quick testing
    }


'''
@lru_cache(maxsize=1)
def _bucket_region(bucket: str) -> str:
    # global endpoint works for GetBucketLocation
    s3_global = boto3.client("s3", region_name="us-east-1")
    loc = s3_global.get_bucket_location(Bucket=bucket)["LocationConstraint"]
    return "us-east-1" if loc is None else loc

@lru_cache(maxsize=1)
def _s3_for_bucket(bucket: str):
    region = _bucket_region(bucket)
    return boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))

# Use this client everywhere below
s3 = _s3_for_bucket(S3_BUCKET)'''


# (Optional) tiny reader to test map later
@app.get("/v1/frames/recent")
def recent_frames(device_id: str, limit: int = 25):
    today = dt.datetime.utcnow().date()
    keys = []
    for delta in range(0, 3):  # look back 3 days
        d = today - dt.timedelta(days=delta)
        prefix = f"frames/{device_id}/{d.year:04d}{d.month:02d}{d.day:02d}/"
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".json"):
                    keys.append(obj["Key"])
    keys = sorted(keys, reverse=True)[:limit]
    feats = []
    for k in keys:
        body = s3.get_object(Bucket=S3_BUCKET, Key=k)["Body"].read()
        meta = json.loads(body)
        meta["feature"]["properties"]["image_url"] = _presign_get(meta["image_key"])
        feats.append(meta["feature"])
    return {"type": "FeatureCollection", "features": feats}


@app.get("/v1/trajectory/geojson")
def trajectory_geojson(device_id: str = "dev-00000000", days: int = 10):
    import gzip, io, json, datetime as dt
    today = dt.datetime.utcnow().date()
    pts = []
    for delta in range(max(1, days)):
        d = today - dt.timedelta(days=delta)
        prefix = f"trajectory/{device_id}/{d.year:04d}{d.month:02d}{d.day:02d}/"
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".ndjson.gz"): 
                    continue
                body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
                with gzip.GzipFile(fileobj=io.BytesIO(body), mode="rb") as gz:
                    for line in gz:
                        try:
                            r = json.loads(line)
                            pts.append((r["ts"], r["lon"], r["lat"]))
                        except Exception:
                            pass
    pts.sort(key=lambda x: x[0])
    coords = [[lon, lat] for _, lon, lat in pts]
    if not coords:
        return {"type":"FeatureCollection","features":[]}
    return {"type":"FeatureCollection","features":[{
        "type":"Feature",
        "geometry":{"type":"LineString","coordinates":coords},
        "properties":{"count":len(coords),"device_id":device_id}
    }]}


app.mount("/models", StaticFiles(directory="web/models"), name="models")
app.mount("/", StaticFiles(directory="web", html=True), name="web")