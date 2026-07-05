import os
import json
import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from web folder
env_path = Path(__file__).resolve().parent.parent  / ".env"
print("Looking for .env at:", env_path)
print("Exists?", env_path.exists())

load_dotenv(env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("Loaded key:", OPENAI_API_KEY)
# =========================
# Configuration
# =========================
IMAGES_DIR = Path("./backend/web/images")
METADATA_DIR = Path("./backend/web/metadata")
MODEL_NAME = "gpt-5.4-mini"   # use gpt-5.4 for strongest quality, mini for lower cost
OVERWRITE_EXISTING = False    # True = re-run even if "vlm" already exists in JSON

# Supported image extensions
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

#client = OpenAI()  # reads OPENAI_API_KEY from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def image_to_data_url(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def build_prompt(existing_meta: Dict[str, Any]) -> str:
    detections = existing_meta.get("detections", [])
    detected_labels = sorted({d.get("label") for d in detections if d.get("label")})

    return f"""
You are analyzing a geo-referenced urban street image for an urban digital twin system.

Use the image as the primary source of truth.
You may use the detector labels below as weak supporting hints only, and only when they are consistent with the image.

Detector labels: {detected_labels}

Return STRICT JSON with exactly these keys:
- summary
- interpretation
- objects
- context
- observations
- scene_type
- mobility
- infrastructure
- safety_notes
- uncertainty

Rules:
- Be factual and concise.
- Do not invent details that are not visible.
- If something is uncertain, say so in uncertainty.
- "objects", "mobility", "infrastructure", and "safety_notes" must be arrays of strings.
- "summary", "interpretation", "context", "scene_type", and "uncertainty" must be strings.
- "observations" must be an array of short strings.
""".strip()


def interpret_image(image_path: Path, existing_meta: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt(existing_meta)
    image_data_url = image_to_data_url(image_path)

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                        "detail": "high",
                    },
                ],
            }
        ],
    )

    text = response.output_text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model did not return valid JSON for {image_path.name}.\nRaw output:\n{text}"
        ) from e

    return parsed


def find_matching_image(json_path: Path) -> Optional[Path]:
    stem = json_path.stem
    for ext in IMAGE_EXTENSIONS:
        candidate = IMAGES_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def process_one(json_path: Path) -> bool:
    image_path = find_matching_image(json_path)
    if image_path is None:
        print(f"[SKIP] No matching image found for {json_path.name}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if not OVERWRITE_EXISTING and "vlm" in meta:
        print(f"[SKIP] VLM already exists in {json_path.name}")
        return False

    try:
        vlm_result = interpret_image(image_path, meta)
    except Exception as e:
        print(f"[ERROR] Failed on {image_path.name}: {e}")
        return False

    meta["vlm"] = vlm_result
    meta["vlm_model"] = MODEL_NAME
    meta["vlm_processed"] = True

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[OK] Updated {json_path.name}")
    return True


def main() -> None:
    if not IMAGES_DIR.exists():
        raise FileNotFoundError(f"Images folder not found: {IMAGES_DIR.resolve()}")
    if not METADATA_DIR.exists():
        raise FileNotFoundError(f"Metadata folder not found: {METADATA_DIR.resolve()}")

    json_files = sorted(METADATA_DIR.glob("*.json"))
    if not json_files:
        print("[INFO] No JSON files found.")
        return

    total = len(json_files)
    updated = 0

    for json_file in json_files:
        if process_one(json_file):
            updated += 1

    print(f"\nDone. Updated {updated}/{total} metadata files.")


if __name__ == "__main__":
    main()