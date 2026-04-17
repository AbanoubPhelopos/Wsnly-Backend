# Ai-Service — NLP Location Extraction + Geocoding

Ai-Service is a Python gRPC microservice that converts natural language trip requests (Arabic/English) into structured locations and coordinates.

## Responsibilities

- Parse free-form text (Arabic/English) to detect origin and destination
- Handle conversational Arabic patterns and common typo aliases for Cairo locations
- Geocode extracted places to latitude/longitude using Google Maps
- Return interpretation result to Wslny API over gRPC

Ai-Service does **not** calculate routes. Pathfinding is handled by `RoutingEngine`.

## How It Works

```text
Input: "عايز اروح العباسيه من مسكن"
                │
                ▼
    ┌───────────────────────┐
    │   Text Preprocessing  │  Normalize Arabic text, fix typos
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │   NER Model / Rules   │  Extract origin/destination names
    │   (fallback pipeline) │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │   Google Geocoding    │  Convert names to lat/lon
    │   (with in-memory     │
    │    cache)             │
    └───────────┬───────────┘
                │
                ▼
    Output: { from: "مسكن" (30.0, 31.0), to: "العباسية" (30.07, 31.28) }
```

## Communication Contract

- Service: `TransitInterpreter`
- RPC: `ExtractRoute(RouteRequest) -> RouteResponse`
- Proto source: `shared/protos/interpreter.proto`

```text
Wslny API ──gRPC──▶ Ai-Service
Ai-Service ──gRPC response (locations + coordinates)──▶ Wslny API
```

## Two-Stage Extraction

### Stage 1: Named Entity Recognition
- Primary: ML-based NER model when valid weights exist in `TransitModel/`
- Fallback: Rule-based extraction using regex patterns for Arabic/English location phrases
- The fallback is always active and handles most common patterns reliably

### Stage 2: Geocoding
- Extracted location names are geocoded via Google Maps Geocoding API
- Results are cached in-memory (`geocoder.py`) to reduce external API calls for repeated place names
- Returns coordinates + resolved name

## Destination-Only Requests

The service may return destination coordinates even when origin is missing:

```json
{
  "from_location": "",
  "to_location": "شيراتون",
  "to_coordinates": { "latitude": 30.10, "longitude": 31.37 },
  "intent": "standard"
}
```

In this case, the Wslny API completes the source using the client's `current_location`.

## Input/Output Examples

### Full extraction (origin + destination)

Input:
```json
{ "text": "عايز اروح العباسيه من مسكن" }
```

Output:
```json
{
  "from_location": "مسكن",
  "to_location": "العباسية",
  "from_coordinates": { "latitude": 30.05, "longitude": 31.34 },
  "to_coordinates": { "latitude": 30.07, "longitude": 31.28 },
  "intent": "standard"
}
```

### Destination only

Input:
```json
{ "text": "محطة مترو المنيب" }
```

Output:
```json
{
  "from_location": "",
  "to_location": "محطة مترو المنيب",
  "from_coordinates": null,
  "to_coordinates": { "latitude": 30.01, "longitude": 31.25 },
  "intent": "standard"
}
```

## Project Structure

```text
Ai-Service/
├── Server.py              # gRPC server entrypoint
├── geocoder.py            # Google Maps geocoding with in-memory cache
├── TransitModel/          # NER model weights (gitignored)
│   ├── tokenizer.json
│   └── tokenizer_config.json
├── protos/                # Local proto copy for Docker build
├── tests/
│   └── test_flow.py       # Regression tests for Arabic phrase extraction
├── Dockerfile
└── Requirements.txt
```

## Accuracy Strategy

| Layer | Strategy |
|-------|----------|
| ML NER | Fine-tuned model in `TransitModel/` — used when weights are available |
| Rule-based | Regex patterns for common Arabic/English location expressions — always active |
| Alias normalization | Maps frequent typos and colloquial names to canonical forms |
| Geocoding cache | Reduces API calls for repeated place names |
| Regression tests | `tests/test_flow.py` covers critical Arabic phrases |

## Required Environment

| Variable | Description |
|----------|-------------|
| `GOOGLE_MAPS_API_KEY` | Required for geocoding place names to coordinates |

## Running

Recommended via root compose:

```bash
docker compose up --build
```

Standalone:

```bash
docker build -f Ai-Service/Dockerfile -t ai-service .
docker run -p 50052:50052 -e GOOGLE_MAPS_API_KEY=your_key ai-service
```

## Why This Separation Matters

- Keeps NLP complexity isolated from pathfinding code
- Lets map-pin requests skip AI entirely for lower latency
- Allows independent scaling and tuning of model and geocoder behavior
- Geocoding cache reduces Google Maps API costs
