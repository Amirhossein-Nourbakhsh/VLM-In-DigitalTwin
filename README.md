# Vision-Language Models for Urban Digital Twins

A prototype system for enriching urban digital twins using mobile crowd-sensed street-level imagery, object-detection metadata, geospatial coordinates, and vision-language model interpretation.

## Overview

Urban digital twins require continuous and semantically rich updates to accurately represent changing real-world conditions. This project demonstrates a workflow that uses smartphone or vehicle-based image observations, object-detection outputs, GPS metadata, and a Vision-Language Model (VLM) to generate structured urban scene interpretations.

The resulting observations are visualized in an interactive geospatial dashboard, allowing users to explore image-based urban conditions, detected objects, infrastructure elements, mobility context, and safety-related observations.

## Key Features

- Mobile street-level image observation processing
- GPS-based geospatial positioning
- Object-detection metadata integration
- Vision-Language Model semantic enrichment
- Structured JSON output generation
- GeoJSON-based spatial visualization
- Interactive Mapbox GL JS dashboard
- Image-level inspection panel with VLM interpretation
- Detection confidence filtering
- Observation clustering on the map

## System Architecture

The system follows a multi-stage pipeline:

```text
Street-Level Image Collection
        ↓
GPS + Timestamp + Device Metadata
        ↓
Object Detection Metadata
        ↓
Vision-Language Model Interpretation
        ↓
Structured JSON / GeoJSON Records
        ↓
Interactive Geospatial Dashboard
        ↓
Urban Digital Twin Semantic Layer
```

## Methodology

The proposed workflow consists of five main stages:

1. **Data Acquisition**  
   Street-level images are collected using mobile devices or vehicle-mounted cameras. Each observation includes GPS coordinates, timestamp, device information, and sensor metadata.

2. **Object Detection Metadata**  
   Detected objects are stored with labels, confidence scores, and bounding boxes. These detections provide initial visual evidence for downstream interpretation.

3. **Vision-Language Interpretation**  
   A Vision-Language Model is used to analyze each image and generate structured semantic descriptions, including scene summary, visible objects, mobility context, infrastructure observations, safety notes, and uncertainty.

4. **Spatial Structuring**  
   Each interpreted observation is converted into a structured geospatial record using JSON and GeoJSON formats.

5. **Visualization and Digital Twin Integration**  
   The processed observations are visualized in an interactive Mapbox-based dashboard as geo-referenced semantic observations.

## Technologies Used

### Backend

- Python
- OpenAI Responses API
- Vision-Language Model: `gpt-5.4-mini`
- JSON / GeoJSON processing

### Frontend

- HTML
- CSS
- JavaScript
- Mapbox GL JS
- Mapbox Standard basemap
- 3D terrain visualization
- GeoJSON point layers
- Mapbox clustering

## Vision-Language Model

This project uses `gpt-5.4-mini` as the Vision-Language Model for semantic interpretation of street-level urban images.

The model receives:

- Image input
- Object-detection labels
- Confidence scores
- Bounding boxes
- GPS and timestamp metadata

The VLM outputs structured semantic information such as:

- Scene summary
- Urban interpretation
- Visible objects
- Mobility observations
- Infrastructure elements
- Safety notes
- Uncertainty description

## Frontend Visualization

The frontend is an interactive geospatial dashboard built with Mapbox GL JS.

It visualizes:

- Geo-referenced image observations
- Object-detection outputs
- Detection confidence
- VLM-generated semantic descriptions
- Clustered observation points
- Dashboard-level summary statistics

The map uses:

- Mapbox Standard basemap
- 3D terrain
- GeoJSON point features
- Interactive popup/detail panels

## Repository Structure

```text
.
├── app/
│   ├── vlm_image.py
│   └── ...
├── web/
│   ├── index.html
│   ├── images/
│   ├── metadata/
│   ├── manifest.json
│   └── models/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/vlm-urban-digital-twin.git
cd vlm-urban-digital-twin
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Then add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
MAPBOX_ACCESS_TOKEN=your_mapbox_access_token_here
```

Do not commit your real `.env` file to GitHub.

## Running the Project

### Backend / VLM Processing

Run the relevant Python processing script:

```bash
python app/vlm_image.py
```

### Frontend Dashboard

Open the frontend in a local web server.

For example, from the project root:

```bash
cd web
python -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

## Example Output

Each processed observation includes structured information similar to:

```json
{
  "summary": "Urban roadway scene with multiple vehicles and traffic infrastructure.",
  "scene_type": "urban intersection",
  "visible_objects": ["cars", "traffic light", "roadway", "buildings"],
  "mobility": ["vehicular traffic is present", "intersection is signal-controlled"],
  "infrastructure": ["multi-lane roadway", "traffic signal poles", "lane markings"],
  "safety_notes": ["driver caution required near intersection"],
  "uncertainty": "Some objects may be partially occluded or affected by image quality."
}
```

## Research Context

This project supports research on the integration of Vision-Language Models, mobile crowd-sensing, and geospatial visualization for dynamic urban digital twins.

The main research objective is to move beyond traditional object detection by generating semantically rich and human-interpretable urban observations that can support digital twin updating, infrastructure monitoring, and urban scene understanding.

## Limitations

- The current prototype is evaluated using a limited number of representative urban observations.
- VLM outputs may be affected by image quality, occlusion, reflections, camera orientation, and lighting conditions.
- GPS measurements from mobile devices may contain spatial noise.
- Some safety-related outputs are inferential and require uncertainty-aware validation.
- The current system does not yet perform temporal fusion across consecutive frames.

## Future Work

Future improvements include:

- Quantitative evaluation using expert-labelled urban-scene datasets
- Uncertainty-aware VLM output generation
- Detector-VLM consistency validation
- Temporal fusion across consecutive image frames
- Integration of road network, sidewalk, and traffic-signal GIS layers
- Domain adaptation or fine-tuning of open-source VLMs
- Development of an urban digital twin benchmark for semantic scene interpretation

## Citation

If you use this repository, please cite the associated paper:

```bibtex
@inproceedings{nourbakhshrezaei2026vlmurbantwin,
  title={Vision-Language Models for Urban Digital Twins},
  author={Nourbakhshrezaei, Amirhossein and Abbasi, Saeed and Jadidi, Mojgan},
  booktitle={ISPRS Congress},
  year={2026}
}
```

## Author

**Amirhossein Nourbakhshrezaei**  
Lassonde School of Engineering, York University  
Toronto, Ontario, Canada

## License

This project is currently released for academic and research demonstration purposes.

Please contact the author before using the code or data for commercial applications.
