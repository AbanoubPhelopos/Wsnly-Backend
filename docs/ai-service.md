# AI Service

## Overview

The AI Service is a Python gRPC microservice that extracts origin and destination locations from natural language text (Arabic/English) and geocodes them to coordinates using Google Maps.

## How It Works

### Two-Stage Pipeline

**Stage 1 — Named Entity Recognition (NER)**

Extracts location names from user text using a two-layer approach:

1. **ML Model** (primary): A fine-tuned NER model loaded from `TransitModel/` directory. Model weights are gitignored — the fallback is always active.

2. **Rule-based extraction** (fallback/always-active): Regex patterns that match common Arabic and English location expressions:
   - "عايز اروح [DESTINATION] من [ORIGIN]"
   - "from [ORIGIN] to [DESTINATION]"
   - Destination-only patterns like just a place name

The rule-based system handles aliases — common typos and colloquial names are mapped to canonical forms.

**Stage 2 — Geocoding**

Extracted location names are geocoded via Google Maps Geocoding API:

```text
"العباسية" → Google Maps API → { lat: 30.0728, lon: 31.2841, name: "العباسية" }
```

Results are cached in-memory to reduce API calls for repeated place names.

### Destination-Only Requests

The service can return a valid result with only a destination:

```json
{
  "from_location": "",
  "from_coordinates": null,
  "to_location": "شيراتون",
  "to_coordinates": { "latitude": 30.10, "longitude": 31.37 },
  "intent": "standard"
}
```

In this case, the Wslny API uses the client's `current_location` as the origin.

## gRPC Contract

```protobuf
service TransitInterpreter {
  rpc ExtractRoute (RouteRequest) returns (RouteResponse) {}
}

message RouteRequest {
  string text = 1;
}

message RouteResponse {
  string from_location = 1;
  string to_location = 2;
  repeated RouteStep steps = 3;
  double total_distance_meters = 4;
  double total_duration_seconds = 5;
  Location from_coordinates = 6;
  Location to_coordinates = 7;
  string intent = 8;
}
```

## Project Structure

```text
Ai-Service/
├── Server.py              # gRPC server (port 50052)
├── geocoder.py            # Google Maps geocoding + in-memory cache
├── TransitModel/          # NER model weights (gitignored)
│   ├── tokenizer.json
│   └── tokenizer_config.json
├── protos/                # Proto copy for Docker build
├── tests/
│   └── test_flow.py       # Regression tests for Arabic phrases
├── Dockerfile
└── Requirements.txt
```

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_MAPS_API_KEY` | Yes | Google Maps Geocoding API key |

## Caching

| Cache | Type | What | Lifetime |
|-------|------|------|----------|
| Geocoding | In-memory dict | Place name → coordinates | Process lifetime |
| Model | File-based | NER tokenizer weights | Loaded at startup |

## Error Handling

If geocoding fails for a location, the service returns the location name without coordinates. The Wslny API handles missing coordinates by returning an error to the client.

## Testing

```bash
# Run tests inside Docker
docker compose exec ai-service python -m pytest tests/

# Or test a real request
docker compose exec ai-service python test_real_request.py
```

## Why This Service Is Separate

- NLP complexity is isolated — changes to extraction logic don't affect routing
- Map-pin requests skip this service entirely (direct to routing engine)
- Can be scaled independently based on text vs. map traffic ratio
- Geocoding API costs can be managed through caching
