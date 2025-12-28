"""
CAD Generator (DXF) for Runway Geometry
--------------------------------------
Reads runway_geometry.json and generates a 2D plan-view DXF suitable for AutoCAD.

What it draws (layers):
- RUNWAY: runway outline (rectangle)
- MARK_CENTERLINE: dashed centerline (as many LINE segments)
- MARK_THRESHOLD: threshold "piano key" rectangles + side stripes
- MARK_AIM: aiming point rectangles (pair)
- MARK_TDZ: touchdown zone rectangles (simplified)
- LIGHT_EDGE: runway edge lights (POINT)
- LIGHT_THR: threshold lights (POINT)
- TEXT: runway designators

Notes:
- Coordinates are in meters in a local runway coordinate system:
  X increases from RWY primary threshold to the opposite end, Y is lateral.
- This is a teaching/graphics-oriented export. You can adjust parameters in runway_geometry.json.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
import ezdxf
from ezdxf.enums import TextEntityAlignment

base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, "runway_geometry.json")
runway_path = os.path.join(base_path, "runway_plan.dxf")

def add_rect(msp, layer: str, x0: float, x1: float, y0: float, y1: float) -> None:
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})

def main(json_path, runway_path) -> str:
    json_file = Path(json_path)
    out_path = Path(runway_path).resolve()

    data = json.loads(json_file.read_text(encoding="utf-8"))

    L = float(data["runwayDimensions"]["length"]["meters"])
    W = float(data["runwayDimensions"]["width"]["meters"])
    halfW = W / 2.0

    doc = ezdxf.new(dxfversion="R2010")
    doc.units = 6  # meters
    layers = {
        "RUNWAY": 7,
        "MARK_CENTERLINE": 1,
        "MARK_THRESHOLD": 1,
        "MARK_AIM": 1,
        "MARK_TDZ": 1,
        "LIGHT_EDGE": 3,
        "LIGHT_THR": 3,
        "TEXT": 2,
    }
    for name, color in layers.items():
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color})

    msp = doc.modelspace()

    # 1) Runway outline
    add_rect(msp, "RUNWAY", 0, L, -halfW, halfW)

    # 2) Side stripes (simplified)
    ss = data.get("runwayMarkings", {}).get("side_stripes", {})
    dist_from_edge = float(ss.get("distance_from_edge", 5))
    stripe_offset = halfW - dist_from_edge
    msp.add_line((0, stripe_offset), (L, stripe_offset), dxfattribs={"layer": "MARK_THRESHOLD"})
    msp.add_line((0, -stripe_offset), (L, -stripe_offset), dxfattribs={"layer": "MARK_THRESHOLD"})

    # 3) Centerline dashes
    cl = data.get("runwayMarkings", {}).get("centerline_marking", {})
    dash = float(cl.get("dashLength", 30))
    gap = float(cl.get("gapLength", 20))
    x = 0.0
    while x < L:
        x2 = min(x + dash, L)
        msp.add_line((x, 0), (x2, 0), dxfattribs={"layer": "MARK_CENTERLINE"})
        x += dash + gap

    # 4) Threshold "piano key" rectangles (simplified)
    th = data.get("runwayMarkings", {}).get("threshold_markings", {})
    stripe_w = float(th.get("dimensions", {}).get("width", 3))
    stripe_s = float(th.get("dimensions", {}).get("spacing", 3))
    stripe_len_1 = float(th.get("length_18R", 60))
    stripe_len_2 = float(th.get("length_36L", 60))

    # For 60m runway width, 12 stripes is common (teaching-friendly default).
    n = int(th.get("count", 12) or 12)
    total_w = n * stripe_w + (n - 1) * stripe_s
    start_y = -total_w / 2.0

    for i in range(n):
        y0 = start_y + i * (stripe_w + stripe_s)
        y1 = y0 + stripe_w
        add_rect(msp, "MARK_THRESHOLD", 0, stripe_len_1, y0, y1)
        add_rect(msp, "MARK_THRESHOLD", L - stripe_len_2, L, y0, y1)

    # 5) Aiming point (pair)
    ap = data.get("runwayMarkings", {}).get("aiming_point", {})
    ap_dist = float(ap.get("distance_from_threshold", 300))
    ap_len = float(ap.get("length", 180))
    ap_w = float(ap.get("width", 45))
    inner_gap = float(ap.get("inner_gap", 3.0))
    y_center = ap_w / 2.0 + inner_gap
    add_rect(msp, "MARK_AIM", ap_dist, ap_dist + ap_len, y_center - ap_w / 2.0, y_center + ap_w / 2.0)
    add_rect(msp, "MARK_AIM", ap_dist, ap_dist + ap_len, -(y_center + ap_w / 2.0), -(y_center - ap_w / 2.0))

    # 6) Touchdown zone markings (simplified as rectangles)
    tdz = data.get("runwayMarkings", {}).get("touchdown_zone_markings", {})
    spacing = float(tdz.get("spacing", 150))
    start = float(tdz.get("start_distance_from_threshold", 300))
    end = float(tdz.get("end_distance_from_threshold", 900))
    zone_len = float(tdz.get("length_per_zone", 150))
    rect_w = float(tdz.get("width_per_zone", 45))
    lateral_offset = float(tdz.get("lateral_offset", rect_w / 2.0 + 12.0))

    xpos = start + spacing  # start after the first zone (keeps it visually clean)
    while xpos <= end + 1e-6:
        add_rect(msp, "MARK_TDZ", xpos, xpos + zone_len, lateral_offset - rect_w / 2.0, lateral_offset + rect_w / 2.0)
        add_rect(msp, "MARK_TDZ", xpos, xpos + zone_len, -(lateral_offset + rect_w / 2.0), -(lateral_offset - rect_w / 2.0))
        xpos += spacing

    # 7) Runway edge lights (POINT)
    edge = data.get("lightingSystems", {}).get("runway_edge_lights", {})
    edge_sp = float(edge.get("spacing", 60))
    x = 0.0
    while x <= L + 1e-6:
        msp.add_point((x, halfW), dxfattribs={"layer": "LIGHT_EDGE"})
        msp.add_point((x, -halfW), dxfattribs={"layer": "LIGHT_EDGE"})
        x += edge_sp

    # 8) Threshold lights (POINT) — simplified across full width at 3m spacing
    thr_sp = float(data.get("lightingSystems", {}).get("threshold_lights", {}).get("spacing", 3.0) or 3.0)
    y = -halfW
    while y <= halfW + 1e-6:
        msp.add_point((0, y), dxfattribs={"layer": "LIGHT_THR"})
        msp.add_point((L, y), dxfattribs={"layer": "LIGHT_THR"})
        y += thr_sp

    # 9) Runway designators
    runway = data.get("runway", {})
    primary = runway.get("primaryDesignation", "18R")
    secondary = runway.get("secondaryDesignation", "36L")

    t1 = msp.add_text(primary, dxfattribs={"layer": "TEXT", "height": 20})
    t1.set_placement((60, 0), align=TextEntityAlignment.MIDDLE_CENTER)
    t2 = msp.add_text(secondary, dxfattribs={"layer": "TEXT", "height": 20})
    t2.set_placement((L - 60, 0), align=TextEntityAlignment.MIDDLE_CENTER)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out_path))
    return str(out_path)

if __name__ == "__main__":
    # Usage:
    #   python CAD_generator_dxf.py [runway_geometry.json] [runway_plan.dxf]
    import argparse

    parser = argparse.ArgumentParser(description="Generate runway DXF from geometry JSON.")
    parser.add_argument("json_path", nargs="?", default=json_path, help="Path to runway_geometry.json")
    parser.add_argument("runway_path", nargs="?", default=runway_path, help="Output DXF path")
    args = parser.parse_args()

    print(main(args.json_path, args.runway_path))
