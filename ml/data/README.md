# Municipal Complaints Development Dataset (Synthetic / Benchmark)

## Overview & Purpose
This dataset (`municipal_complaints_dev.csv`) serves as a development and evaluation benchmark for **CityMind AI's automated civic complaint classification engine**. It provides a balanced set of text records designed to train and validate text classification models across six core municipal service domains.

## Synthetic & Development Disclosure
> [!IMPORTANT]
> **This dataset is synthetic and development-focused.** It does **not** represent real municipal archives or actual citizen identities. 
> 
> The complaints have been synthetically composed with varied phrasing, natural citizen complaints, indirect descriptions, typos, and varying degrees of urgency to mirror the real-world linguistic diversity of municipal helpdesks without exposing private citizen data.

## Municipal Service Categories
The dataset covers six municipal categories matching CityMind AI's operational departments:

1. **`ROADS`**: Potholes, damaged tarmac, cracked pavement, road cave-ins, broken curb stones, hazardous street surfaces.
2. **`WATER`**: Main pipeline bursts, dirty/contaminated drinking water supply, zero tap pressure, residential water cuts, leaking distribution valves.
3. **`WASTE`**: Overflowing community dumpsters, uncollected garbage, illegal debris dumping on roadsides, rotting trash heaps, foul odor from refuse.
4. **`ELECTRICITY`**: Non-functioning streetlights, flickering public lamps, sparking transformers, dangling overhead wires, municipal power grid outages.
5. **`TRAFFIC`**: Defective traffic lights, signals stuck on blinking/red, missing lane dividers, obscured road signs, vehicle gridlocks at major intersections.
6. **`HEALTH`**: Stagnant sewage in open drains, severe mosquito breeding spots, unsanitary public hygiene conditions, sewage backflow into streets.

## Structure & Fields
- `id`: Unique sample identifier (integer)
- `title`: Citizen complaint summary line
- `description`: Detailed description submitted by citizen
- `category`: Ground truth category label (`ROADS`, `WATER`, `WASTE`, `ELECTRICITY`, `TRAFFIC`, `HEALTH`)
- `urgency_hint`: Reference urgency tag (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) used for developing and calibrating heuristic priority baselines

## Limitations & Intended Use
- **Development Only**: Designed for testing, local model training, and student/academic demonstrations.
- **English Language**: The current development dataset consists primarily of English civic descriptions.
- **Model Baseline**: Intended for standard TF-IDF and linear/probabilistic classification pipelines.
