# -*- coding: utf-8 -*-
"""
Course DXF generator for AutoCAD 2018 (DXF R2010).

Input:
  - ZBAA_tables.json (preferred): parse runway 18R/36L dimensions (length/width, strip, RESA)
Output:
  - output/airport_course_ZBAA18R_R2010.dxf

What it draws (meets course deliverables in one figure):
  1) Runway system: surface + centerline + key runway markings (THR, designator, edge line, center line, TDZ, aiming point)
  2) Taxiway system (schematic if no real geometry): parallel TWY + connectors + holding positions + TWY centerline/edge
  3) Visual aids: runway edge lights + runway centerline lights + simple approach light bars
  4) Signage: taxiing guidance signs at RWY/TWY intersections & holding positions (schematic sign boards)

Notes:
  - Geometry is in a local metric frame: RWY threshold 18R at (0,0), runway along +Y.
  - If table parsing fails, falls back to values consistent with AIP:
      RWY 18R/36L = 3200 x 50
      Strip = 3320 x 280
      RESA = 240 x 100
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from ezdxf.enums import TextEntityAlignment
import ezdxf

Point = Tuple[float, float]


# ----------------------------
# Utilities
# ----------------------------
def as_float(x: Any, default: float) -> float:
    try:
        if x is None:
            return default
        return float(str(x).strip())
    except Exception:
        return default


def as_int(x: Any, default: int) -> int:
    try:
        if x is None:
            return default
        return int(float(str(x).strip()))
    except Exception:
        return default


def normalize(v: Point, fallback: Point = (0.0, 1.0)) -> Point:
    lx = math.hypot(v[0], v[1])
    if lx <= 1e-12:
        return fallback
    return (v[0] / lx, v[1] / lx)


def offset_polyline(points: List[Point], offset: float) -> Tuple[List[Point], List[Point]]:
    """Return (left, right) offset polylines for a polyline (simple miter)."""
    if len(points) < 2:
        return [], []

    # segment normals
    seg_normals: List[Point] = []
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        L = math.hypot(dx, dy)
        if L < 1e-12:
            seg_normals.append((0.0, 0.0))
        else:
            seg_normals.append((-dy / L, dx / L))

    left: List[Point] = []
    right: List[Point] = []
    for i, p in enumerate(points):
        if i == 0:
            n = seg_normals[0]
        elif i == len(points) - 1:
            n = seg_normals[-1]
        else:
            n = (seg_normals[i - 1][0] + seg_normals[i][0], seg_normals[i - 1][1] + seg_normals[i][1])
            n = normalize(n, seg_normals[i])
        left.append((p[0] + n[0] * offset, p[1] + n[1] * offset))
        right.append((p[0] - n[0] * offset, p[1] - n[1] * offset))
    return left, right


def rect(center: Point, w: float, h: float) -> List[Point]:
    cx, cy = center
    hw, hh = w / 2.0, h / 2.0
    return [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]


def add_closed_lwpoly(msp, pts: List[Point], layer: str) -> None:
    if len(pts) < 3:
        return
    pl = msp.add_lwpolyline(pts, dxfattribs={"layer": layer})
    pl.close(True)


def add_lwpoly(msp, pts: List[Point], layer: str) -> None:
    if len(pts) < 2:
        return
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


# ----------------------------
# Parser: ZBAA_tables.json
# ----------------------------
def _flatten_cells(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


def parse_zbaa_tables_runway_18r(tables_path: str) -> Dict[str, float]:
    """
    Try to parse:
      - runway length/width: "18R" row with "3200×50"
      - strip dimensions: "3320×280"
      - RESA: "240×100"
    from ZBAA_tables.json.

    Returns dict:
      runway_length_m, runway_width_m, strip_length_m, strip_width_m, resa_length_m, resa_width_m
    """
    defaults = {
        "runway_length_m": 3200.0,
        "runway_width_m": 50.0,
        "strip_length_m": 3320.0,
        "strip_width_m": 280.0,
        "resa_length_m": 240.0,
        "resa_width_m": 100.0,
    }

    try:
        with open(tables_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return defaults

    # ZBAA_tables.json is a list of {page, table_index, data:[[...],[...]]}
    entries = obj if isinstance(obj, list) else []
    text_blobs: List[str] = []

    for e in entries:
        data = e.get("data")
        if not isinstance(data, list):
            continue
        for row in data:
            if isinstance(row, list):
                text_blobs.append(" | ".join(_flatten_cells(x) for x in row))
            else:
                text_blobs.append(_flatten_cells(row))

    big = "\n".join(text_blobs)

    # 1) runway dimensions (prefer "18R ... 3200×50" or "18R ... 3200x50")
    m = re.search(r"\b18R\b[\s\S]{0,120}?(?P<len>\d{3,4})\s*[×xX]\s*(?P<w>\d{2,3})", big)
    if m:
        defaults["runway_length_m"] = float(m.group("len"))
        defaults["runway_width_m"] = float(m.group("w"))

    # 2) strip dimensions (look near 18R and "Strip dimensions")
    m2 = re.search(r"\b18R\b[\s\S]{0,220}?(?P<sl>\d{4})\s*[×xX]\s*(?P<sw>\d{2,4})", big)
    # This might still capture runway; ensure it's bigger than runway length
    if m2:
        sl = float(m2.group("sl"))
        sw = float(m2.group("sw"))
        if sl > defaults["runway_length_m"]:
            defaults["strip_length_m"] = sl
            defaults["strip_width_m"] = sw

    # 3) RESA dimensions: often "240×100"
    m3 = re.search(r"\b18R\b[\s\S]{0,260}?(?P<rl>\d{2,4})\s*[×xX]\s*(?P<rw>\d{2,4})", big)
    # weak; validate with plausible range
    if m3:
        rl = float(m3.group("rl"))
        rw = float(m3.group("rw"))
        if 60 <= rl <= 500 and 30 <= rw <= 300:
            defaults["resa_length_m"] = rl
            defaults["resa_width_m"] = rw

    return defaults


# ----------------------------
# Generator
# ----------------------------
class CourseAirportDXF:
    def __init__(self, zbaa_tables_json: str) -> None:
        self.tables_path = zbaa_tables_json
        self.p: Dict[str, float] = {}

        # DXF
        self.doc = ezdxf.new("R2010", setup=True)
        self.doc.header["$INSUNITS"] = 6  # meters
        self.msp = self.doc.modelspace()

        # layers
        self._setup_layers()

    def _setup_layers(self) -> None:
        layers = {
            "RUNWAY": 7,
            "RUNWAY_MARKINGS": 1,
            "RUNWAY_LIGHTS": 2,
            "APPROACH_LIGHTS": 4,
            "SAFETY": 3,
            "TAXIWAY": 5,
            "TAXIWAY_MARKINGS": 140,
            "SIGNS": 30,
            "TEXT": 8,
            "CENTERLINE": 6,
        }
        for name, color in layers.items():
            try:
                self.doc.layers.new(name=name, dxfattribs={"color": color})
            except ezdxf.DXFError:
                pass

    def load(self) -> None:
        self.p = parse_zbaa_tables_runway_18r(self.tables_path)

    # ---- Runway base geometry (18R threshold at y=0; 36L at y=L) ----
    def runway_centerline(self) -> List[Point]:
        L = self.p["runway_length_m"]
        return [(0.0, 0.0), (0.0, L)]

    def draw_runway_surface(self) -> None:
        L = self.p["runway_length_m"]
        W = self.p["runway_width_m"]
        cl = self.runway_centerline()
        left, right = offset_polyline(cl, W / 2.0)
        boundary = left + list(reversed(right))
        add_closed_lwpoly(self.msp, boundary, "RUNWAY")
        add_lwpoly(self.msp, cl, "CENTERLINE")

    # ---- Runway markings (simplified, but includes required set) ----
    def draw_runway_markings(self) -> None:
        L = self.p["runway_length_m"]
        W = self.p["runway_width_m"]
        cl = self.runway_centerline()

        # edge lines (inboard a little)
        edge_inboard = 2.0
        left_edge, right_edge = offset_polyline(cl, W / 2.0 - edge_inboard)
        add_lwpoly(self.msp, left_edge, "RUNWAY_MARKINGS")
        add_lwpoly(self.msp, right_edge, "RUNWAY_MARKINGS")

        # centerline dashed
        dash = 30.0
        gap = 20.0
        y = 0.0
        while y < L:
            y2 = min(L, y + dash)
            self.msp.add_line((0.0, y), (0.0, y2), dxfattribs={"layer": "RUNWAY_MARKINGS"})
            y = y2 + gap

        # threshold stripes (schematic, symmetric)
        stripe_w = 3.0
        stripe_gap = 3.0
        stripe_len = 60.0
        half = W / 2.0
        x = stripe_gap + stripe_w / 2.0
        xs: List[float] = []
        while x < half - stripe_w:
            xs.append(x)
            x += stripe_w + stripe_gap

        def stripes(at_18r: bool) -> None:
            base_y = 0.0 if at_18r else (L - stripe_len)
            for sgn in (-1.0, 1.0):
                for off in xs:
                    cx = sgn * off
                    pts = rect((cx, base_y + stripe_len / 2.0), stripe_w, stripe_len)
                    add_closed_lwpoly(self.msp, pts, "RUNWAY_MARKINGS")

        stripes(True)
        stripes(False)

        # aiming point (schematic): 300m from each threshold
        aim_dist = 300.0
        aim_len = 180.0
        bar_w = 6.0
        aim_lat = min(22.5, W * 0.45)

        def aiming(at_18r: bool) -> None:
            cy = aim_dist + aim_len / 2.0 if at_18r else (L - aim_dist - aim_len / 2.0)
            for sgn in (-1.0, 1.0):
                cx = sgn * aim_lat
                pts = rect((cx, cy), bar_w, aim_len)
                add_closed_lwpoly(self.msp, pts, "RUNWAY_MARKINGS")

        aiming(True)
        aiming(False)

        # TDZ (touchdown zone) bars: 2 zones each side (schematic)
        tdz_zones = 2
        tdz_spacing = 150.0
        tdz_len = 45.0
        tdz_bar_w = 6.0
        tdz_start = 300.0

        def tdz(at_18r: bool) -> None:
            for i in range(tdz_zones):
                y0 = tdz_start + i * tdz_spacing
                cy = y0 + tdz_len / 2.0 if at_18r else (L - y0 - tdz_len / 2.0)
                for sgn in (-1.0, 1.0):
                    cx = sgn * aim_lat
                    pts = rect((cx, cy), tdz_bar_w, tdz_len)
                    add_closed_lwpoly(self.msp, pts, "RUNWAY_MARKINGS")

        tdz(True)
        tdz(False)

        # runway designators text
        self.msp.add_text(
                    "18R",
                    dxfattribs={"layer": "TEXT", "height": 20}
                ).set_placement((0, 120), align=ezdxf.enums.TextEntityAlignment.CENTER)

        self.msp.add_text(
                    "36L",
                    dxfattribs={"layer": "TEXT", "height": 20}
                ).set_placement((0, L - 120), align=ezdxf.enums.TextEntityAlignment.CENTER)

    # ---- Runway lights (match AIP spacings; colors not modeled, only symbols) ----
    def draw_runway_lights(self) -> None:
        L = self.p["runway_length_m"]
        W = self.p["runway_width_m"]

        # edge lights spacing 60m
        edge_spacing = 60.0
        y = 0.0
        while y <= L + 1e-6:
            left = (-W / 2.0, y)
            right = (W / 2.0, y)
            self.msp.add_circle(left, 0.8, dxfattribs={"layer": "RUNWAY_LIGHTS"})
            self.msp.add_circle(right, 0.8, dxfattribs={"layer": "RUNWAY_LIGHTS"})
            y += edge_spacing

        # centerline lights spacing 15m
        cl_spacing = 15.0
        y = 0.0
        while y <= L + 1e-6:
            self.msp.add_circle((0.0, y), 0.5, dxfattribs={"layer": "RUNWAY_LIGHTS"})
            y += cl_spacing

        # simple threshold/end “bars”
        bar_w = W * 0.9
        self.msp.add_line((-bar_w / 2, 0.0), (bar_w / 2, 0.0), dxfattribs={"layer": "RUNWAY_LIGHTS"})
        self.msp.add_line((-bar_w / 2, L), (bar_w / 2, L), dxfattribs={"layer": "RUNWAY_LIGHTS"})

        # approach lights: PALS CAT I 900m -> bars every 60m (schematic)
        approach_len = 900.0
        bar_spacing = 60.0
        bars = int(approach_len // bar_spacing)
        for i in range(1, bars + 1):
            y = -i * bar_spacing  # approaching 18R from south (negative y)
            bw = min(120.0, W * 2.4)
            self.msp.add_line((-bw / 2, y), (bw / 2, y), dxfattribs={"layer": "APPROACH_LIGHTS"})
        # (Optionally for 36L end as well)
        for i in range(1, bars + 1):
            y = L + i * bar_spacing
            bw = min(120.0, W * 2.4)
            self.msp.add_line((-bw / 2, y), (bw / 2, y), dxfattribs={"layer": "APPROACH_LIGHTS"})

    # ---- Safety areas: Strip + RESA (schematic rectangles centered on RWY) ----
    def draw_safety_areas(self) -> None:
        L = self.p["runway_length_m"]
        strip_L = self.p["strip_length_m"]
        strip_W = self.p["strip_width_m"]
        resa_L = self.p["resa_length_m"]
        resa_W = self.p["resa_width_m"]

        # Strip: length extends beyond thresholds equally
        extra = max(0.0, strip_L - L)
        before = extra / 2.0
        after = extra / 2.0
        strip_poly = [
            (-strip_W / 2, -before),
            (strip_W / 2, -before),
            (strip_W / 2, L + after),
            (-strip_W / 2, L + after),
        ]
        add_closed_lwpoly(self.msp, strip_poly, "SAFETY")

        # RESA at both ends (in line with runway)
        resa_18 = [
            (-resa_W / 2, -resa_L),
            (resa_W / 2, -resa_L),
            (resa_W / 2, 0.0),
            (-resa_W / 2, 0.0),
        ]
        resa_36 = [
            (-resa_W / 2, L),
            (resa_W / 2, L),
            (resa_W / 2, L + resa_L),
            (-resa_W / 2, L + resa_L),
        ]
        add_closed_lwpoly(self.msp, resa_18, "SAFETY")
        add_closed_lwpoly(self.msp, resa_36, "SAFETY")

    # ---- Taxiway system (schematic, because tables do not include geometry) ----
    def draw_taxiway_system(self) -> None:
        """
        Build a reasonable schematic:
          - One parallel taxiway at x = +200m (east side), width 23m
          - Three connectors to runway (like exits/entries) at y=700, 1600, 2500
          - Holding positions at connector-runway side (painted + signs)
        """
        L = self.p["runway_length_m"]
        twy_w = 23.0
        twy_x = 200.0

        # parallel taxiway centerline
        twy_cl = [(twy_x, -200.0), (twy_x, L + 200.0)]
        left, right = offset_polyline(twy_cl, twy_w / 2.0)
        add_closed_lwpoly(self.msp, left + list(reversed(right)), "TAXIWAY")
        add_lwpoly(self.msp, twy_cl, "TAXIWAY_MARKINGS")

        # connectors
        x_runway_edge = self.p["runway_width_m"] / 2.0 + 10.0
        hold_span = twy_w + 10.0
        conn_ys = [700.0, 1600.0, 2500.0]
        for idx, y0 in enumerate(conn_ys, start=1):
            if idx == 2:
                angle_deg = 30.0
                dx = x_runway_edge - twy_x
                dy = -abs(dx) / math.tan(math.radians(angle_deg))
                y_touch = y0 + dy
                conn = [(twy_x, y0), (x_runway_edge, y_touch)]
            else:
                conn = [(twy_x, y0), (x_runway_edge, y0)]

            left2, right2 = offset_polyline(conn, twy_w / 2.0)
            add_closed_lwpoly(self.msp, left2 + list(reversed(right2)), "TAXIWAY")
            add_lwpoly(self.msp, conn, "TAXIWAY_MARKINGS")

            if idx == 2:
                dir_vec = normalize((conn[-1][0] - conn[0][0], conn[-1][1] - conn[0][1]))
                n_vec = (-dir_vec[1], dir_vec[0])
                hold_offset = 20.0
                base_hold_center = (
                    conn[-1][0] - dir_vec[0] * hold_offset,
                    conn[-1][1] - dir_vec[1] * hold_offset,
                )
                half_span_vec = (n_vec[0] * hold_span / 2.0, n_vec[1] * hold_span / 2.0)

                def _hold_line(center: Point) -> None:
                    p1 = (center[0] - half_span_vec[0], center[1] - half_span_vec[1])
                    p2 = (center[0] + half_span_vec[0], center[1] + half_span_vec[1])
                    self.msp.add_line(p1, p2, dxfattribs={"layer": "TAXIWAY_MARKINGS"})

                _hold_line(base_hold_center)
                offset_center = (
                    base_hold_center[0] - dir_vec[0] * 2.0,
                    base_hold_center[1] - dir_vec[1] * 2.0,
                )
                _hold_line(offset_center)
                hold_sign_pos = (
                    base_hold_center[0] + n_vec[0] * 12.0 - dir_vec[0] * 4.0,
                    base_hold_center[1] + n_vec[1] * 12.0 - dir_vec[1] * 4.0,
                )
                twy_label = "FAST EXIT\nTWY F"
            else:
                hold_x = x_runway_edge + 20.0
                self.msp.add_line((hold_x, y0 - hold_span / 2), (hold_x, y0 + hold_span / 2),
                                  dxfattribs={"layer": "TAXIWAY_MARKINGS"})
                self.msp.add_line((hold_x + 2.0, y0 - hold_span / 2), (hold_x + 2.0, y0 + hold_span / 2),
                                  dxfattribs={"layer": "TAXIWAY_MARKINGS"})
                hold_sign_pos = (hold_x + 18.0, y0 + 18.0)
                twy_label = f"TWY P{idx}"

            self._add_sign(
                insert=hold_sign_pos,
                text=f"RWY 18R-36L\nHOLD",
                board_w=28.0,
                board_h=16.0,
            )
            self._add_sign(
                insert=(twy_x + 18.0, y0 - 18.0),
                text=twy_label,
                board_w=22.0,
                board_h=12.0,
            )

        # annotate taxiway label
        self.msp.add_text(
                    "PARALLEL TWY (schematic)",
                    dxfattribs={"layer": "TEXT", "height": 12}
                ).set_placement((twy_x + 30, L / 2), align=TextEntityAlignment.LEFT)

    def _add_sign(self, insert: Point, text: str, board_w: float, board_h: float) -> None:
        """
        Simple sign board: rectangle + MTEXT.
        """
        x, y = insert
        poly = [(x, y), (x + board_w, y), (x + board_w, y + board_h), (x, y + board_h)]
        add_closed_lwpoly(self.msp, poly, "SIGNS")
        # Use MTEXT for multi-line
        self.msp.add_mtext(text, dxfattribs={"layer": "SIGNS", "char_height": 4.0}).set_location(
            (x + 1.5, y + board_h - 1.5)
        )

    def add_title_block(self) -> None:
        L = self.p["runway_length_m"]
        info = (
            f"ZBAA RWY 18R/36L COURSE DRAWING (schematic TWY)\n"
            f"RWY: {self.p['runway_length_m']:.0f}m x {self.p['runway_width_m']:.0f}m\n"
            f"Strip: {self.p['strip_length_m']:.0f}m x {self.p['strip_width_m']:.0f}m\n"
            f"RESA: {self.p['resa_length_m']:.0f}m x {self.p['resa_width_m']:.0f}m\n"
            f"DXF: R2010, Units: meters"
        )
        self.msp.add_mtext(info, dxfattribs={"layer": "TEXT", "char_height": 6.0}).set_location((-350, L + 350))

    def build(self) -> None:
        self.load()
        self.draw_safety_areas()
        self.draw_runway_surface()
        self.draw_runway_markings()
        self.draw_runway_lights()
        self.draw_taxiway_system()
        self.add_title_block()

    def save(self, out_path: str) -> None:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        self.doc.saveas(out_path)


def main() -> int:
    base = os.path.dirname(os.path.abspath(__file__))

    # input
    tables = os.path.join(base, "data", "ZBAA_tables.json")

    # output (same style as your previous script)
    out = os.path.join(base, "output", "airport_course_ZBAA18R_R2010.dxf")

    gen = CourseAirportDXF(tables)
    gen.build()
    gen.save(out)
    print(f"DXF saved to {out}")
    print("Completed. Open the DXF in AutoCAD 2018 to verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
