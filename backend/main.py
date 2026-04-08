from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np
import datetime
import osmnx as ox
import networkx as nx
import os
import sys
import hashlib
import glob
import torch
from torchvision import transforms
from PIL import Image
import functools

app = FastAPI(title="SafeRoute AI Backend", description="Risk Prediction and Routing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Load ML Models -----------------
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.join(current_dir, "..", "ml_pipeline")
sys.path.append(pipeline_dir)

try:
    from hybrid_train import NightlightCNN
except ImportError:
    NightlightCNN = None

models_dir = os.path.join(pipeline_dir, "models")
tabular_path = os.path.join(models_dir, "hybrid_tabular.pkl")
cnn_path = os.path.join(models_dir, "hybrid_cnn.pth")

hybrid_model = None
xgb_model = None
lgb_model = None
cnn_model = None

try:
    hybrid_tabular = joblib.load(tabular_path)
    xgb_model = hybrid_tabular['xgb']
    lgb_model = hybrid_tabular['lgb']
    print("Tabular models loaded successfully.")
    
    if NightlightCNN:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cnn_model = NightlightCNN().to(device)
        cnn_model.load_state_dict(torch.load(cnn_path, map_location=device, weights_only=True))
        cnn_model.eval()
        print("CNN model loaded successfully.")
        
    hybrid_model = True
except Exception as e:
    print(f"Warning: Could not load Hybrid models. Error: {str(e)}")

# Image Setup
image_dir = os.path.join(current_dir, "..", "database", "County_Wise_Nightlight_Images_Dataset", "dataset", "dataset")
images = glob.glob(os.path.join(image_dir, "*.jpeg"))

transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

@functools.lru_cache(maxsize=2048)
def assign_image(lat, lon):
    if not images:
        return ""
    coord_str = f"{lat}_{lon}"
    idx = int(hashlib.md5(coord_str.encode('utf-8')).hexdigest(), 16) % len(images)
    return images[idx]

@functools.lru_cache(maxsize=2048)
def load_image_tensor(path):
    try:
        if path and os.path.exists(path):
            img = Image.open(path).convert('RGB')
        else:
            img = Image.new('RGB', (64, 64), color='black')
    except:
        img = Image.new('RGB', (64, 64), color='black')
    return transform(img)

# Mobility Setup
mobility_path = os.path.join(current_dir, "..", "database", "Google_Mobility_Data", "2022_US_Region_Mobility_Report.csv")
mob_agg = {}
mobility_cols = [
    'retail_and_recreation_percent_change_from_baseline', 
    'grocery_and_pharmacy_percent_change_from_baseline', 
    'parks_percent_change_from_baseline', 
    'transit_stations_percent_change_from_baseline', 
    'workplaces_percent_change_from_baseline', 
    'residential_percent_change_from_baseline'
]

try:
    df_mob = pd.read_csv(mobility_path, on_bad_lines='skip')
    df_mob['date'] = pd.to_datetime(df_mob['date'], errors='coerce')
    df_mob = df_mob.dropna(subset=['date'])
    df_mob['DayOfWeek'] = df_mob['date'].dt.dayofweek
    df_mob_il = df_mob[df_mob['sub_region_1'] == 'Illinois']
    mob_df = df_mob_il.groupby('DayOfWeek')[mobility_cols].mean().reset_index()
    mob_df = mob_df.fillna(0)
    for _, row in mob_df.iterrows():
        mob_agg[int(row['DayOfWeek'])] = row[mobility_cols].to_dict()
    print("Mobility data cached successfully.")
except Exception as e:
    print(f"Warning: Could not cache mobility data. Error: {str(e)}")

import math
import requests as http_requests

class Coordinate(BaseModel):
    lat: float
    lon: float

class RiskRequest(BaseModel):
    coordinates: list[Coordinate]
    hour: int = None
    day: int = None

class RouteRequest(BaseModel):
    start: Coordinate
    end: Coordinate
    preference: str = "safest"

class SettingRequest(BaseModel):
    key: str
    value: bool

# In-memory settings state cache
user_settings = {
    "darkMode": True,
    "realTimeAlerts": True,
    "autoRerouting": False,
    "anonymousMode": False,
    "crowdSourcing": True
}

def _predict_fast(df):
    """Fast prediction using only XGBoost + LightGBM (skips CNN for speed)."""
    if not xgb_model or not lgb_model:
        return np.full(len(df), 50.0)
    
    for col in mobility_cols:
        df[col] = df['DayOfWeek'].apply(lambda d: mob_agg.get(d, {}).get(col, 0.0))
        
    xgb_features = ['Grid_Lat', 'Grid_Lon', 'HourOfDay', 'DayOfWeek']
    lgb_features = mobility_cols
    
    pred_xgb = xgb_model.predict(df[xgb_features])
    pred_lgb = lgb_model.predict(df[lgb_features])
    
    final_preds = (pred_xgb + pred_lgb) / 2.0
    return np.clip(final_preds, 0, 100)

def _predict_hybrid(df):
    """Full hybrid prediction with XGBoost + LightGBM + CNN."""
    for col in mobility_cols:
        df[col] = df['DayOfWeek'].apply(lambda d: mob_agg.get(d, {}).get(col, 0.0))
        
    xgb_features = ['Grid_Lat', 'Grid_Lon', 'HourOfDay', 'DayOfWeek']
    lgb_features = mobility_cols
    
    pred_xgb = xgb_model.predict(df[xgb_features])
    pred_lgb = lgb_model.predict(df[lgb_features])
    
    df['ImagePath'] = df.apply(lambda row: assign_image(row['Grid_Lat'], row['Grid_Lon']), axis=1)
    
    tensors = []
    for path in df['ImagePath']:
        tensors.append(load_image_tensor(path))
    
    if tensors:
        batch_tensors = torch.stack(tensors)
        device = next(cnn_model.parameters()).device if cnn_model else torch.device('cpu')
        batch_tensors = batch_tensors.to(device)
        with torch.no_grad():
            preds_list = []
            batch_size = 256
            for i in range(0, len(batch_tensors), batch_size):
                b = batch_tensors[i:i+batch_size]
                try:
                    preds = cnn_model(b).cpu().numpy().flatten()
                except:
                    preds = np.zeros(len(b))
                preds_list.append(preds)
            pred_cnn = np.concatenate(preds_list)
    else:
        pred_cnn = np.zeros(len(df))
        
    final_preds = (pred_xgb + pred_lgb + pred_cnn) / 3.0
    return np.clip(final_preds, 0, 100)

def _osrm_route_direct(start_lon, start_lat, end_lon, end_lat):
    """Get routes from OSRM with alternatives=true."""
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson&steps=true&alternatives=true"
    )
    resp = http_requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return []
    return data["routes"]


def _osrm_route_via_waypoint(start_lon, start_lat, end_lon, end_lat, wp_lon, wp_lat):
    """Get a single route that goes through an intermediate waypoint."""
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{wp_lon},{wp_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson&steps=true&alternatives=false"
    )
    try:
        resp = http_requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            return data["routes"][0]
    except Exception:
        pass
    return None


def _generate_offset_waypoints(start_lat, start_lon, end_lat, end_lon):
    """
    Generate waypoints offset perpendicular to the start→end line.
    Returns a list of (wp_lat, wp_lon) tuples that will force different routes.
    """
    mid_lat = (start_lat + end_lat) / 2
    mid_lon = (start_lon + end_lon) / 2

    # Direction vector from start to end
    dlat = end_lat - start_lat
    dlon = end_lon - start_lon
    dist = math.sqrt(dlat ** 2 + dlon ** 2)

    if dist < 1e-6:
        return []

    # Perpendicular unit vector (rotate 90 degrees)
    perp_lat = -dlon / dist
    perp_lon = dlat / dist

    # Offset magnitudes — proportional to route distance, capped at ~3 km worth of degrees
    # ~0.01 degree ≈ 1.1 km, so we use offsets of 0.015 and 0.025
    base_offset = max(0.008, min(dist * 0.25, 0.03))

    waypoints = []
    # Offset left
    waypoints.append((mid_lat + perp_lat * base_offset, mid_lon + perp_lon * base_offset))
    # Offset right
    waypoints.append((mid_lat - perp_lat * base_offset, mid_lon - perp_lon * base_offset))
    # Further offset left (larger detour)
    waypoints.append((mid_lat + perp_lat * base_offset * 2, mid_lon + perp_lon * base_offset * 2))
    # Further offset right (larger detour)
    waypoints.append((mid_lat - perp_lat * base_offset * 2, mid_lon - perp_lon * base_offset * 2))

    return waypoints


def _get_all_candidate_routes(start_lon, start_lat, end_lon, end_lat):
    """
    Get at least 3 distinct route candidates by combining:
    1. OSRM native alternatives
    2. Waypoint-forced detour routes
    """
    # Step 1: Get native OSRM alternatives
    routes = _osrm_route_direct(start_lon, start_lat, end_lon, end_lat)
    print(f"  OSRM native alternatives: {len(routes)}")

    # Step 2: If fewer than 3 routes, force more via waypoints
    if len(routes) < 3:
        waypoints = _generate_offset_waypoints(start_lat, start_lon, end_lat, end_lon)
        for wp_lat, wp_lon in waypoints:
            if len(routes) >= 5:
                break  # cap at 5 candidates
            wp_route = _osrm_route_via_waypoint(
                start_lon, start_lat, end_lon, end_lat, wp_lon, wp_lat
            )
            if wp_route:
                # Only add if route is meaningfully different (check distance difference > 5%)
                existing_distances = [r.get("distance", 0) for r in routes]
                new_dist = wp_route.get("distance", 0)
                is_unique = all(
                    abs(new_dist - d) / max(d, 1) > 0.05 for d in existing_distances
                )
                if is_unique:
                    routes.append(wp_route)
                    print(f"  Added waypoint-detour route (dist={new_dist/1000:.1f}km)")

    print(f"  Total candidate routes: {len(routes)}")
    return routes


def _score_route(route_geojson, hour, day):
    """Score a single OSRM route using ML models."""
    coords_geojson = route_geojson["geometry"]["coordinates"]  # [lon, lat]
    route_coords = [{"lat": c[1], "lon": c[0]} for c in coords_geojson]

    # Subsample waypoints for risk scoring
    max_score_points = 50
    step = max(1, len(route_coords) // max_score_points)
    sample_coords = route_coords[::step]

    avg_risk = 50.0
    if hybrid_model and sample_coords:
        score_data = [{
            'Grid_Lat': round(c['lat'], 3),
            'Grid_Lon': round(c['lon'], 3),
            'HourOfDay': hour,
            'DayOfWeek': day
        } for c in sample_coords]

        df_score = pd.DataFrame(score_data)
        risk_scores = _predict_fast(df_score)
        avg_risk = float(np.mean(risk_scores))

    distance_km = route_geojson.get("distance", 0) / 1000
    duration_min = route_geojson.get("duration", 0) / 60

    return {
        "route_coords": route_coords,
        "avg_risk": avg_risk,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "sample_count": len(sample_coords),
    }


@app.get("/")
def read_root():
    return {"status": "ok", "message": "SafeRoute AI Hybrid Engine is running."}

@app.post("/settings")
def update_settings(req: SettingRequest):
    user_settings[req.key] = req.value
    return {"status": "success", "settings": user_settings}

@app.post("/predict_risk")
def predict_risk(req: RiskRequest):
    if not hybrid_model:
        results = [{"lat": coord.lat, "lon": coord.lon, "risk_score": 50.0} 
                   for coord in req.coordinates]
        return {"predictions": results}
    
    hour = req.hour if req.hour is not None else 12
    day = req.day if req.day is not None else 2
    
    data = []
    for coord in req.coordinates:
        data.append({
            'Grid_Lat': round(coord.lat, 3),
            'Grid_Lon': round(coord.lon, 3),
            'HourOfDay': hour,
            'DayOfWeek': day
        })
    df = pd.DataFrame(data)
    
    predictions = _predict_hybrid(df)
    
    results = [{"lat": coord.lat, "lon": coord.lon, "risk_score": float(pred)} 
               for coord, pred in zip(req.coordinates, predictions)]
    
    return {"predictions": results}

@app.post("/route")
def calculate_route(req: RouteRequest):
    """
    Requests multiple alternative routes from OSRM, ML-scores each one,
    and picks the best route based on the preference:
      - 'safest'  → lowest avg risk score
      - 'fastest' → shortest duration
      - 'balanced'→ weighted combination of risk and duration
    """
    start_lat, start_lon = req.start.lat, req.start.lon
    end_lat, end_lon = req.end.lat, req.end.lon

    now = datetime.datetime.now()
    hour = now.hour
    day = now.weekday()

    # 1. Get multiple candidate routes (OSRM native + waypoint-forced)
    try:
        osrm_routes = _get_all_candidate_routes(start_lon, start_lat, end_lon, end_lat)
        if not osrm_routes:
            raise Exception("No routes returned from OSRM")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Routing failed: {str(e)}")

    print(f"[Route] OSRM returned {len(osrm_routes)} alternative route(s) for preference='{req.preference}'")

    # 2. Score every alternative route with the ML model
    scored_routes = []
    for i, osrm_route in enumerate(osrm_routes):
        info = _score_route(osrm_route, hour, day)
        scored_routes.append(info)
        print(f"  Route {i}: risk={info['avg_risk']:.1f}, duration={info['duration_min']:.1f}min, distance={info['distance_km']:.1f}km")

    # 3. Rank routes with preference-specific logic
    #    When risk scores are similar, use distance/duration to differentiate.
    
    if len(scored_routes) >= 2:
        risks = [r["avg_risk"] for r in scored_routes]
        durations = [r["duration_min"] for r in scored_routes]
        distances = [r["distance_km"] for r in scored_routes]
        
        # Check if risk scores are effectively identical (within 5 points)
        risk_spread = max(risks) - min(risks)
        risks_are_similar = risk_spread < 5.0
        
        if risks_are_similar:
            # When risk is similar, differentiate by route characteristics:
            # - Safest: pick the LONGEST route (detour = avoids main roads = safer)
            # - Fastest: pick the SHORTEST duration route (direct = fastest)
            # - Balanced: pick the median-distance route
            print(f"  Risk scores similar (spread={risk_spread:.1f}), using distance/duration to differentiate")
            
            if req.preference == "safest":
                # Longest detour route avoids busy highways → safer
                scored_routes.sort(key=lambda r: r["distance_km"], reverse=True)
                best = scored_routes[0]
            elif req.preference == "fastest":
                # Shortest duration → fastest
                scored_routes.sort(key=lambda r: r["duration_min"])
                best = scored_routes[0]
            else:  # balanced
                # Middle route by distance
                scored_routes.sort(key=lambda r: r["distance_km"])
                mid_idx = len(scored_routes) // 2
                best = scored_routes[mid_idx]
        else:
            # Risk scores differ meaningfully — use weighted scoring
            risk_min, risk_max = min(risks), max(risks)
            dur_min, dur_max = min(durations), max(durations)
            risk_range = risk_max - risk_min if risk_max != risk_min else 1.0
            dur_range = dur_max - dur_min if dur_max != dur_min else 1.0
            
            for r in scored_routes:
                r["norm_risk"] = (r["avg_risk"] - risk_min) / risk_range
                r["norm_dur"] = (r["duration_min"] - dur_min) / dur_range
            
            if req.preference == "safest":
                for r in scored_routes:
                    r["score"] = 0.95 * r["norm_risk"] + 0.05 * r["norm_dur"]
            elif req.preference == "fastest":
                for r in scored_routes:
                    r["score"] = 0.05 * r["norm_risk"] + 0.95 * r["norm_dur"]
            else:
                for r in scored_routes:
                    r["score"] = 0.5 * r["norm_risk"] + 0.5 * r["norm_dur"]
            
            scored_routes.sort(key=lambda r: r["score"])
            
            if req.preference == "balanced":
                mid_idx = len(scored_routes) // 2
                best = scored_routes[mid_idx]
            else:
                best = scored_routes[0]
    else:
        # Only one route available
        best = scored_routes[0]

    print(f"  → Selected: risk={best['avg_risk']:.1f}, duration={best['duration_min']:.1f}min ({req.preference})")

    return {
        "preference": req.preference,
        "route": best["route_coords"],
        "avg_risk": round(best["avg_risk"], 1),
        "distance_km": round(best["distance_km"], 2),
        "duration_min": round(best["duration_min"], 1),
        "nodes": len(best["route_coords"]),
        "edges_scored": best["sample_count"],
        "alternatives_found": len(scored_routes),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
