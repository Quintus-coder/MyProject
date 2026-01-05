# -*- coding: utf-8 -*-
"""
cad_integrated_final.py (课件完全符合版)
北京首都国际机场18R/36L跑道系统CAD图纸生成器

完全符合课件要求：
 跑道系统：50m道面 + 道肩 + 300m升降带(延伸60m) + RESA
 滑行道系统：C + P0-P9，P2-P7标注RET
 道面标志：编号 + 中心线 + TDZ + 瞄准点 + 等待位置
 灯光系统：PAPI + ALS
 图层：RWY/TWY/RET/STRIP/RESA/MARK/LIGHT/TEXT
 无公布距离标注

数据来源:  
- 几何数据: OpenStreetMap → runway_geometry.json
- 参数数据: ZBAA_tables.json + 课件要求
"""

import ezdxf, math, json, os, sys
from pathlib import Path
from ezdxf.enums import TextEntityAlignment
from typing import List, Tuple, Dict, Any
from airport_parameters import AirportParameterExtractor


class IntegratedAirportCAD:
    """集成的机场CAD生成器（课件完全符合版）"""
    
    def __init__(self, 
                 geojson_data_file: str = 'runway_geometry.json',
                 tables_file: str = 'ZBAA_tables.json'):
        """初始化"""
        self.geojson_file = geojson_data_file
        self.tables_file = tables_file
        
        # 数据容器
        self.real_geometry = None
        self.parameters = None
        self.lighting_params = {}
        self.enable_text = False
        self.enable_sign_text = True
        self.enable_hatch = True
        self.force_swap_ends = False
        self._runway_ref = None
        self._twy_draw_data = None
        self._twy_hatch_count = 0
        self._twy_centerline_count = 0
        self._qa = {
            'centerline': {},
            'tdz': {'start': {}, 'end': {}},
            'aiming': {},
            'twy_edge': {},
            'twy_center': {},
            'lights': {},
        }
        self.standard_defaults = {
            'centerline': {
                'block_length': 30.0,
                'gap_length': 20.0,
                'block_width': 0.6,
            },
            'tdz': {
                'bar_length': 22.5,
                'bar_width': 4.0,
                'bars_per_side': 3,
                'group_start': 150.0,
                'group_spacing': 150.0,
                'group_count': 6,
                'inner_clearance': 4.0,
                'bar_spacing': 6.0,
            },
            'pals_cati': {
                'length': 900.0,
                'center_spacing': 30.0,
                'crossbar_positions': [150.0, 300.0, 450.0, 600.0, 750.0, 900.0],
                'crossbar_half': 65.0,
                'crossbar_step': 15.0,
                'barrette_spacing': 60.0,
                'barrette_lateral': 30.0,
                'barrette_span': 20.0,
                'barrette_step': 5.0,
                'barrette_start': 60.0,
                'barrette_end': 900.0,
            },
        }
        
        # DXF文档
        self. doc = ezdxf.new('R2010', setup=True)
        self.doc.header['$INSUNITS'] = 6
        self.msp = self.doc.modelspace()
        
        self._setup_layers()
    
    def _setup_layers(self):
        """设置图层（按课件要求）"""
        print(" Setting up layers...")
        
        layers_config = [
            # 跑道系统
            ('RWY', 7, 'Continuous'),              # 白色 - 跑道面
            ('RWY_CENTERLINE', 1, 'Continuous'),   # 红色 - 跑道中心线
            ('RWY_SHOULDER', 8, 'Continuous'),     # 灰色 - 道肩
            ('STRIP', 9, 'DASHED'),                # 浅灰 - 升降带
            ('RESA', 1, 'Continuous'),             # 红色 - RESA
            ('MARK', 7, 'Continuous'),             # 白色 - 道面标志
            
            # 滑行道系统
            ('TWY', 5, 'Continuous'),              # 蓝色 - 滑行道面
            ('TWY_CENTERLINE', 2, 'Continuous'),   # 黄色 - 滑行道中心线
            ('RET', 5, 'Continuous'),              # 蓝色 - 快速出口（与TWY同色）
            
            # 灯光和标注
            ('LIGHT', 3, 'Continuous'),            # 绿色 - 灯光系统
            ('SIGN', 7, 'Continuous'),             # 白色 - 标志牌
            ('TEXT', 3, 'Continuous'),             # 绿色 - 文字
            ('TITLE_BLOCK', 7, 'Continuous'),      # 白色 - 图框
        ]
        
        layers_config = [
            # Runway system
            ('RWY', 7, 'Continuous'),
            ('RWY_CENTERLINE', 1, 'Continuous'),
            ('RWY_SHOULDER', 8, 'Continuous'),
            ('STRIP', 9, 'DASHED'),
            ('RESA', 1, 'Continuous'),
            ('MARK_RWY', 7, 'Continuous'),
            ('MARK_TWY', 2, 'Continuous'),
            ('MARK', 7, 'Continuous'),

            # Taxiway system
            ('TWY', 5, 'Continuous'),
            ('TWY_PAVEMENT', 8, 'Continuous'),
            ('TWY_EDGE', 2, 'Continuous'),
            ('TWY_CENTERLINE', 2, 'Continuous'),
            ('RET', 5, 'Continuous'),

            # Lighting system (split by function/color)
            ('LGT_APCH_WHITE', 7, 'Continuous'),
            ('LGT_APCH_RED', 1, 'Continuous'),
            ('LGT_THR_BICOLOR', 7, 'Continuous'),
            ('LGT_EDGE_WHITE', 7, 'Continuous'),
            ('LGT_EDGE_YELLOW', 2, 'Continuous'),
            ('LGT_RCL_WHITE', 7, 'Continuous'),
            ('LGT_RCL_RED', 1, 'Continuous'),
            ('LGT_TDZ', 7, 'Continuous'),
            ('LGT_PAPI', 7, 'Continuous'),
            ('LGT_TWY_BLUE', 5, 'Continuous'),
            ('LGT_STOP_RED', 1, 'Continuous'),
            ('LIGHT', 3, 'Continuous'),

            # Sign system
            ('SIGN_MANDATORY', 1, 'Continuous'),
            ('SIGN_LOCATION', 8, 'Continuous'),
            ('SIGN_DIRECTION', 2, 'Continuous'),
            ('SIGN_TEXT', 7, 'Continuous'),
            ('SIGN', 7, 'Continuous'),
            ('TEXT', 3, 'Continuous'),
            ('TITLE_BLOCK', 7, 'Continuous'),
        ]

        for name, color, linetype in layers_config:
            if not self. doc.layers.has_entry(name):
                layer = self.doc.layers.new(name)
                layer. dxf.color = color
                try:
                    layer.dxf.linetype = linetype
                except:
                    pass
        
        print(f"   Created {len(layers_config)} layers (课件标准)")
    
    def load_data(self):
        """加载所有数据"""
        print("\n Loading data...")
        
        # 1. 加载真实几何数据
        with open(self.geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.real_geometry = data. get('real_geometry', {})
        
        runway = self.real_geometry.get('runway', {})
        taxiways = self.real_geometry.get('taxiways', [])
        
        print(f"   Loaded real geometry:")
        print(f"    - Runway: {runway.get('designator', 'N/A')}")
        print(f"    - Taxiways: {len(taxiways)}")
        
        # 2. 提取参数（课件要求优先）
        print(f"\n   Extracting parameters (课件标准)...")
        extractor = AirportParameterExtractor(self.tables_file)
        self.parameters = extractor.get_all_parameters()
        
        # 覆盖为统一宽度（优先真实数据）
        runway_width = runway.get('width_meters') or 50.0
        self.parameters['runway']['width'] = float(runway_width)
        self.parameters['strip']['width'] = 300.0   # 课件要求
        self.parameters['strip']['extension'] = 60.0  # 两端各60m

        # 解析灯光参数（表格驱动）
        self.lighting_params = self._extract_lighting_params()
        
        print(f"   Parameters adjusted to 课件 requirements:")
        print(f"    - Runway width: {self.parameters['runway']['width']}m (final)")
        print(f"    - Strip width: 300m")
        print(f"    - Strip extension: 60m each end")
    
    # ========== 方向计算辅助方法 ==========
    
    def _get_runway_direction(self, runway_coords):
        """计算跑道方向"""
        start = runway_coords[0]
        end = runway_coords[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)
        
        if length < 1e-6:
            return start, end, (0, 1), (-1, 0), 0
        
        dir_x = dx / length
        dir_y = dy / length
        
        perp_x = -dir_y
        perp_y = dir_x
        
        return start, end, (dir_x, dir_y), (perp_x, perp_y), length
    
    def _point_along_runway(self, start, direction, distance):
        """沿跑道方向移动"""
        dir_x, dir_y = direction
        return (start[0] + dir_x * distance, start[1] + dir_y * distance)
    
    def _point_perpendicular(self, base, perpendicular, distance):
        """垂直于跑道方向移动"""
        perp_x, perp_y = perpendicular
        return (base[0] + perp_x * distance, base[1] + perp_y * distance)
    
    # ========== 原有辅助方法 ==========
    
    def _get_runway_reference(self, runway_coords, runway_width):
        start, end, direction, perpendicular, length = self._get_runway_direction(runway_coords)
        half = runway_width / 2.0
        start_left = self._point_perpendicular(start, perpendicular, half)
        start_right = self._point_perpendicular(start, perpendicular, -half)
        end_right = self._point_perpendicular(end, perpendicular, -half)
        end_left = self._point_perpendicular(end, perpendicular, half)
        polygon = [start_left, start_right, end_right, end_left, start_left]
        return {
            'start': start,
            'end': end,
            'direction': direction,
            'perpendicular': perpendicular,
            'length': length,
            'width': runway_width,
            'half_width': half,
            'polygon': polygon,
        }

    def _to_runway_frame(self, p, runway_ref):
        sx, sy = runway_ref['start']
        dx, dy = runway_ref['direction']
        px, py = runway_ref['perpendicular']
        vx = p[0] - sx
        vy = p[1] - sy
        u = vx * dx + vy * dy
        v = vx * px + vy * py
        return (u, v)

    def _from_runway_frame(self, uv, runway_ref):
        u, v = uv
        sx, sy = runway_ref['start']
        dx, dy = runway_ref['direction']
        px, py = runway_ref['perpendicular']
        return (sx + dx * u + px * v, sy + dy * u + py * v)

    def is_point_inside_runway(self, p, runway_ref, buffer=0.0):
        u, v = self._to_runway_frame(p, runway_ref)
        eps = 1e-6
        return (
            (0.0 - buffer - eps) <= u <= (runway_ref['length'] + buffer + eps)
            and abs(v) <= (runway_ref['half_width'] + buffer + eps)
        )

    def clamp_point_to_runway(self, p, runway_ref):
        u, v = self._to_runway_frame(p, runway_ref)
        u = max(0.0, min(runway_ref['length'], u))
        v = max(-runway_ref['half_width'], min(runway_ref['half_width'], v))
        return self._from_runway_frame((u, v), runway_ref)

    def _clip_poly_to_rect(self, poly, u_min, u_max, v_min, v_max):
        def intersect(p1, p2, axis, bound):
            denom = p2[axis] - p1[axis]
            if abs(denom) < 1e-9:
                t = 0.0
            else:
                t = (bound - p1[axis]) / denom
            other = 1 - axis
            other_val = p1[other] + t * (p2[other] - p1[other])
            return (bound, other_val) if axis == 0 else (other_val, bound)

        def clip_axis(subject, axis, bound, keep_greater):
            if not subject:
                return []
            output = []
            prev = subject[-1]
            prev_inside = (prev[axis] >= bound) if keep_greater else (prev[axis] <= bound)
            for curr in subject:
                curr_inside = (curr[axis] >= bound) if keep_greater else (curr[axis] <= bound)
                if curr_inside:
                    if not prev_inside:
                        output.append(intersect(prev, curr, axis, bound))
                    output.append(curr)
                elif prev_inside:
                    output.append(intersect(prev, curr, axis, bound))
                prev, prev_inside = curr, curr_inside
            return output

        poly = clip_axis(poly, 0, u_min, True)
        poly = clip_axis(poly, 0, u_max, False)
        poly = clip_axis(poly, 1, v_min, True)
        poly = clip_axis(poly, 1, v_max, False)
        return poly

    def _clip_poly_to_runway(self, poly, runway_ref):
        if not poly:
            return []
        coords = poly
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        local = [self._to_runway_frame(p, runway_ref) for p in coords]
        clipped = self._clip_poly_to_rect(
            local,
            0.0,
            runway_ref['length'],
            -runway_ref['half_width'],
            runway_ref['half_width'],
        )
        if len(clipped) < 3:
            return []
        world = [self._from_runway_frame(uv, runway_ref) for uv in clipped]
        world.append(world[0])
        return world

    def _segment_outside_rect(self, p0, p1, u_min, u_max, v_min, v_max):
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        t0, t1 = 0.0, 1.0

        def clip(p, q):
            nonlocal t0, t1
            if abs(p) < 1e-9:
                return q >= 0
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
            return True

        if not clip(-dx, p0[0] - u_min):
            return [(p0, p1)]
        if not clip(dx, u_max - p0[0]):
            return [(p0, p1)]
        if not clip(-dy, p0[1] - v_min):
            return [(p0, p1)]
        if not clip(dy, v_max - p0[1]):
            return [(p0, p1)]

        if t0 <= 0.0 and t1 >= 1.0:
            return []

        outside = []
        if t0 > 0.0:
            outside.append((p0, (p0[0] + dx * t0, p0[1] + dy * t0)))
        if t1 < 1.0:
            outside.append(((p0[0] + dx * t1, p0[1] + dy * t1), p1))
        return outside

    def _clip_polyline_outside_runway(self, poly, runway_ref, buffer=0.0, closed=False):
        if not poly:
            return [], 0.0, 0
        coords = list(poly)
        if closed and coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        local = [self._to_runway_frame(p, runway_ref) for p in coords]

        u_min = 0.0 - buffer
        u_max = runway_ref['length'] + buffer
        v_min = -runway_ref['half_width'] - buffer
        v_max = runway_ref['half_width'] + buffer

        result = []
        current = []
        removed_len = 0.0
        removed_segments = 0

        for i in range(len(local) - 1):
            p0 = local[i]
            p1 = local[i + 1]
            seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            outside_segments = self._segment_outside_rect(p0, p1, u_min, u_max, v_min, v_max)

            if not outside_segments:
                removed_len += seg_len
                removed_segments += 1
                if current:
                    result.append(current)
                    current = []
                continue

            kept_len = 0.0
            for seg in outside_segments:
                kept_len += math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])

            if kept_len < seg_len - 1e-6:
                removed_len += seg_len - kept_len
                removed_segments += 1

            for seg in outside_segments:
                w0 = self._from_runway_frame(seg[0], runway_ref)
                w1 = self._from_runway_frame(seg[1], runway_ref)
                if current and math.hypot(current[-1][0] - w0[0], current[-1][1] - w0[1]) > 1e-6:
                    result.append(current)
                    current = []
                if not current:
                    current = [w0, w1]
                else:
                    current.append(w1)

        if current:
            result.append(current)
        return result, removed_len, removed_segments

    def _point_in_polygon(self, point, poly):
        if not poly:
            return False
        x, y = point
        coords = poly
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        inside = False
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            if (y1 > y) != (y2 > y):
                denom = (y2 - y1)
                if abs(denom) < 1e-12:
                    continue
                x_int = (x2 - x1) * (y - y1) / denom + x1
                if x < x_int:
                    inside = not inside
        return inside

    def _perp_from_dir(self, direction):
        return (-direction[1], direction[0])

    def _bearing_deg_from_dir(self, direction):
        dx, dy = direction
        angle = math.degrees(math.atan2(dx, dy)) % 360.0
        return angle

    def _ang_diff(self, a, b):
        diff = abs(a - b) % 360.0
        return min(diff, 360.0 - diff)

    def _map_runway_ends(self, runway_coords, runway_width):
        # Use runway_geometry.json ordering: local_coordinates start=18R, end=36L
        start, end, direction, _, _ = self._get_runway_direction(runway_coords)
        thr18 = start
        in_dir18 = direction
        thr36 = end
        in_dir36 = (-direction[0], -direction[1])

        if self.force_swap_ends:
            thr18, thr36 = thr36, thr18
            in_dir18, in_dir36 = in_dir36, in_dir18

        print(f"  [DEBUG] thr18: {thr18}, thr36: {thr36}")

        return thr18, in_dir18, thr36, in_dir36

    def _taxiway_runway_s(self, ref, runway_coords, runway_ref):
        taxiways = self.real_geometry.get('taxiways', []) if self.real_geometry else []
        for tw in taxiways:
            if tw.get('ref') != ref:
                continue
            coords = tw['geometry']['local_coordinates']
            best_dist = None
            best_closest = None
            for pt in coords:
                dist, closest = self._find_closest_point_on_line(pt, runway_coords)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_closest = closest
            if best_closest is None:
                return None
            u, _ = self._to_runway_frame(best_closest, runway_ref)
            return u
        return None

    def _extract_lighting_params(self):
        try:
            data = json.loads(Path(self.tables_file).read_text(encoding='utf-8'))
        except Exception:
            return {}

        params = {}
        for table in data:
            for row in table.get('data', []):
                if not row or not isinstance(row, list):
                    continue
                key = str(row[0]).strip()
                if key in ('18R', '36L'):
                    if len(row) >= 8 and 'PALS' in str(row[1]):
                        params[key] = self._parse_lighting_row(row)
        return params

    def _parse_lighting_row(self, row):
        apch_len = self._parse_length(row[1]) or 900
        apch_cat = self._parse_apch_cat(row[1])
        thr_color = self._parse_color_name(row[2]) or 'GREEN'
        wbar = 'YES' in str(row[2]).upper()
        papi_side = 'LEFT' if 'LEFT' in str(row[3]).upper() else 'RIGHT' if 'RIGHT' in str(row[3]).upper() else 'LEFT'
        papi_dist = self._parse_length(str(row[3]).replace('inward', 'm inward')) or 420
        papi_lateral = self._parse_last_length(row[3])
        tdzl_len = self._parse_length(row[4])
        rcll_len = self._parse_length(row[5])
        rcll_spacing = self._parse_spacing(row[5])
        rcll_segments = self._parse_segments(row[5])
        edge_len = self._parse_length(row[6])
        edge_spacing = self._parse_spacing(row[6])
        edge_segments = self._parse_segments(row[6])
        end_color = self._parse_color_name(row[7]) or 'RED'
        return {
            'apch_len': apch_len,
            'apch_cat': apch_cat,
            'thr_color': thr_color,
            'wbar': wbar,
            'papi_side': papi_side,
            'papi_dist': papi_dist,
            'papi_lateral': papi_lateral,
            'tdzl_len': tdzl_len,
            'rcll_len': rcll_len,
            'rcll_spacing': rcll_spacing,
            'rcll_segments': rcll_segments,
            'edge_len': edge_len,
            'edge_spacing': edge_spacing,
            'edge_segments': edge_segments,
            'end_color': end_color,
        }

    def _parse_length(self, text):
        if text is None:
            return None
        import re
        match = re.search(r'(\d+)\s*m', str(text))
        return int(match.group(1)) if match else None

    def _parse_last_length(self, text):
        if text is None:
            return None
        import re
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*m', str(text))
        return float(matches[-1]) if matches else None

    def _parse_apch_cat(self, text):
        if text is None:
            return None
        import re
        upper = str(text).upper()
        upper = upper.replace('Ⅰ', 'I').replace('Ⅱ', 'II').replace('Ⅲ', 'III')
        match = re.search(r'CAT\s*([IV]{1,3})', upper)
        if not match:
            return None
        return f"CAT {match.group(1)}"

    def _parse_spacing(self, text):
        if text is None:
            return None
        import re
        match = re.search(r'spacing\s*(\d+)\s*m', str(text))
        return int(match.group(1)) if match else None

    def _parse_segments(self, text):
        if text is None:
            return []
        import re
        segments = []
        for match in re.finditer(r'(\d+)\s*-\s*(\d+)m\s*,\s*([A-Z/]+)', str(text).upper()):
            segments.append({'start': int(match.group(1)), 'end': int(match.group(2)), 'color': match.group(3)})
        return segments

    def _parse_color_name(self, text):
        if text is None:
            return None
        upper = str(text).upper()
        for name in ['GREEN', 'RED', 'YELLOW', 'WHITE', 'BLUE']:
            if name in upper:
                return name
        return None

    def _segment_color(self, dist, segments):
        for seg in segments:
            if seg['start'] <= dist <= seg['end']:
                return seg['color']
        return None

    def _resolve_segment_color(self, color_name, index):
        if color_name == 'RED/WHITE':
            return 'WHITE' if index % 2 == 0 else 'RED'
        return color_name

    def _color_to_aci(self, color_name):
        mapping = {
            'RED': 1,
            'GREEN': 3,
            'YELLOW': 2,
            'WHITE': 7,
            'BLUE': 5,
        }
        return mapping.get(color_name, 7)

    def _color_from_segments(self, dist_to_start, dist_to_end, spacing, params_start, params_end, key):
        if dist_to_start <= dist_to_end:
            dist = dist_to_start
            segments = params_start.get(key) or params_end.get(key) or []
        else:
            dist = dist_to_end
            segments = params_end.get(key) or params_start.get(key) or []
        index = int(round(dist / spacing)) if spacing else 0
        base = self._segment_color(dist, segments) or 'WHITE'
        return self._resolve_segment_color(base, index)

    def _color_from_segments_symmetric(self, dist, total_len, spacing, segments):
        if not segments:
            return 'WHITE'
        d_end = min(dist, total_len - dist)
        end_based = []
        for seg in segments:
            start = max(0.0, total_len - seg['end'])
            end = max(0.0, total_len - seg['start'])
            end_based.append({'start': start, 'end': end, 'color': seg['color']})
        base = self._segment_color(d_end, end_based) or 'WHITE'
        index = int(round(d_end / spacing)) if spacing else 0
        return self._resolve_segment_color(base, index)

    def _get_aiming_distance(self):
        try:
            return float(self.parameters['markings']['aiming_point']['distance_from_threshold'])
        except Exception:
            return 400.0

    def _add_mark_poly(self, poly, layer='MARK_RWY', color=7):
        if not poly:
            return
        self.msp.add_lwpolyline(poly, dxfattribs={'layer': layer, 'color': color})
        if not self.enable_hatch:
            return
        path = poly[:-1] if len(poly) > 1 and poly[0] == poly[-1] else poly
        if len(path) < 3:
            return
        hatch = self.msp.add_hatch(color=color)
        hatch.dxf.layer = layer
        hatch.set_solid_fill(color=color)
        hatch.paths.add_polyline_path(path, is_closed=True)

    def _add_filled_circle(self, center, radius, color, layer):
        import math
        steps = 24
        points = []
        for i in range(steps):
            ang = math.radians(i * 360.0 / steps)
            points.append((center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang)))
        hatch = self.msp.add_hatch(color=color)
        hatch.dxf.layer = layer
        hatch.set_solid_fill(color=color)
        hatch.paths.add_polyline_path(points, is_closed=True)

    def _add_filled_semicircle(self, center, radius, start_deg, end_deg, color, layer):
        import math
        span = (end_deg - start_deg) % 360
        if span <= 0.0:
            span += 360.0
        steps = max(12, int(span / 10.0))
        points = []
        for i in range(steps + 1):
            ang = math.radians(start_deg + span * i / steps)
            points.append((center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang)))
        hatch = self.msp.add_hatch(color=color)
        hatch.dxf.layer = layer
        hatch.set_solid_fill(color=color)
        hatch.paths.add_polyline_path(points, is_closed=True)

    def _add_light_circle(self, center, radius, color, layer, outline_color=7):
        self.msp.add_circle(center, radius, dxfattribs={'layer': layer, 'color': outline_color})
        self._add_filled_circle(center, radius, color, layer)

    def _add_bicolor_half_circle(self, center, radius, in_dir, layer='LGT_THR_BICOLOR'):
        import math
        dx, dy = in_dir
        theta_in = math.degrees(math.atan2(dy, dx)) % 360.0
        red_start = theta_in - 90.0
        red_end = theta_in + 90.0
        green_start = theta_in + 90.0
        green_end = theta_in + 270.0
        self.msp.add_circle(center, radius, dxfattribs={'layer': layer, 'color': 7})
        self._add_filled_semicircle(center, radius, red_start, red_end, 1, layer)
        self._add_filled_semicircle(center, radius, green_start, green_end, 3, layer)

    def _draw_end_lighting(self, thr, in_dir, runway_ref, runway_width, light_radius, params):
        out_dir = (-in_dir[0], -in_dir[1])
        perp_out = self._perp_from_dir(out_dir)
        stats = {
            'als_center': 0,
            'als_center_min': None,
            'als_center_max': None,
            'als_bars': 0,
            'als_bar_lights': 0,
            'als_bar_positions': [],
            'als_red_side': 0,
            'als_red_min': None,
            'als_red_max': None,
            'als_red_offset': None,
            'als_total': 0,
            'als_barrette_groups': 0,
            'als_barrette_points': 0,
            'als_barrette_min': None,
            'als_barrette_max': None,
            'als_barrette_lateral': None,
            'als_barrette_span': None,
            'als_crossbar_points': 0,
            'als_crossbar_present': False,
            'als_crossbar_offsets': None,
            'als_dupe': 0,
            'als_inside_runway': 0,
            'thr': 0,
            'thr_offset_min': None,
            'thr_offset_max': None,
            'end': 0,
            'papi': 0,
            'papi_base': None,
            'papi_lateral': None,
            'papi_spacing': None,
        }

        # ALS (PALS CAT I)
        defaults = self.standard_defaults['pals_cati']
        apch_len = params.get('apch_len') or defaults['length']
        apch_cat = (params.get('apch_cat') or 'CAT I').upper()
        als_start = 30.0
        center_spacing = params.get('apch_spacing') or defaults['center_spacing']
        crossbar_positions = params.get('apch_crossbar_positions') or defaults['crossbar_positions']
        if not isinstance(crossbar_positions, list):
            crossbar_positions = [float(crossbar_positions)]
        crossbar_half = params.get('apch_crossbar_half') or defaults['crossbar_half']
        crossbar_step = params.get('apch_crossbar_step') or defaults['crossbar_step']
        crossbar_offsets = []
        off = -crossbar_half
        while off <= crossbar_half + 1e-6:
            crossbar_offsets.append(round(off, 2))
            off += crossbar_step
        stats['als_crossbar_offsets'] = crossbar_offsets

        def bump_range(min_key, max_key, value):
            if stats[min_key] is None or value < stats[min_key]:
                stats[min_key] = value
            if stats[max_key] is None or value > stats[max_key]:
                stats[max_key] = value

        als_keys = set()

        def add_als_light(pos, color, layer):
            key = (round(pos[0], 2), round(pos[1], 2))
            if key in als_keys:
                stats['als_dupe'] += 1
                return False
            als_keys.add(key)
            if self.is_point_inside_runway(pos, runway_ref):
                stats['als_inside_runway'] += 1
            self._add_light_circle(pos, light_radius, color, layer)
            return True

        d = als_start
        while d <= apch_len + 0.1:
            pos = self._point_along_runway(thr, out_dir, d)
            if add_als_light(pos, 7, 'LGT_APCH_WHITE'):
                stats['als_center'] += 1
                bump_range('als_center_min', 'als_center_max', d)
            d += center_spacing

        barrette_spacing = params.get('apch_barrette_spacing', defaults['barrette_spacing'])
        barrette_lateral = params.get('apch_barrette_lateral', defaults['barrette_lateral'])
        barrette_span = params.get('apch_barrette_span', defaults['barrette_span'])
        barrette_step = params.get('apch_barrette_step', defaults['barrette_step'])
        barrette_start = params.get('apch_barrette_start', defaults['barrette_start'])
        barrette_end = params.get('apch_barrette_end', defaults['barrette_end'])
        barrette_end = min(apch_len, float(barrette_end))
        stats['als_barrette_lateral'] = barrette_lateral
        stats['als_barrette_span'] = barrette_span
        barrette_offsets = []
        off = -barrette_span / 2.0
        while off <= barrette_span / 2.0 + 1e-6:
            barrette_offsets.append(round(off, 2))
            off += barrette_step
        if barrette_end > 0.0 and barrette_lateral > 0.0 and barrette_offsets:
            d = barrette_start
            while d <= barrette_end + 0.1:
                base = self._point_along_runway(thr, out_dir, d)
                for side in (-1, 1):
                    for off in barrette_offsets:
                        pos = self._point_perpendicular(base, perp_out, side * barrette_lateral + off)
                        if add_als_light(pos, 7, 'LGT_APCH_WHITE'):
                            stats['als_barrette_points'] += 1
                            bump_range('als_barrette_min', 'als_barrette_max', d)
                stats['als_barrette_groups'] += 1
                d += barrette_spacing

        if apch_cat in ('CAT II', 'CAT III'):
            bar_positions = crossbar_positions
        else:
            bar_positions = crossbar_positions

        for d in bar_positions:
            if d > apch_len:
                continue
            base = self._point_along_runway(thr, out_dir, d)
            stats['als_bars'] += 1
            stats['als_bar_positions'].append(d)
            for off in crossbar_offsets:
                p = self._point_perpendicular(base, perp_out, off)
                if add_als_light(p, 7, 'LGT_APCH_WHITE'):
                    stats['als_bar_lights'] += 1
                    stats['als_crossbar_points'] += 1
            if stats['als_bar_lights'] > 0:
                stats['als_crossbar_present'] = True

        if apch_cat in ('CAT II', 'CAT III'):
            red_end = min(apch_len, 270.0)
            red_offset = 30.0
            stats['als_red_offset'] = red_offset
            d = als_start
            while d <= red_end + 0.1:
                base = self._point_along_runway(thr, out_dir, d)
                for side in (-1, 1):
                    p = self._point_perpendicular(base, perp_out, side * red_offset)
                    self._add_light_circle(p, light_radius, 1, 'LGT_APCH_RED')
                    stats['als_red_side'] += 1
                bump_range('als_red_min', 'als_red_max', d)
                d += center_spacing

        # Threshold bicolor lights
        n_thr = 8
        half = runway_width / 2 - 1.0
        if half <= 0.0:
            half = runway_width / 2
        if n_thr == 1:
            offsets = [0.0]
        else:
            step = (half * 2.0) / (n_thr - 1)
            offsets = [-half + i * step for i in range(n_thr)]

        if offsets:
            stats['thr_offset_min'] = min(offsets)
            stats['thr_offset_max'] = max(offsets)
        thr_keys = set()
        for off in offsets:
            c = self._point_perpendicular(thr, runway_ref['perpendicular'], off)
            key = (round(c[0], 2), round(c[1], 2), 'THR')
            if key in thr_keys:
                continue
            thr_keys.add(key)
            self._add_bicolor_half_circle(c, light_radius * 0.9, in_dir, 'LGT_THR_BICOLOR')
            stats['thr'] += 1
        stats['end'] = stats['thr']
        stats['als_total'] = len(als_keys)

        # PAPI (left/right of approach direction)
        papi_dist = params.get('papi_dist') or 300
        papi_side = (params.get('papi_side') or 'LEFT').upper()
        papi_base = self._point_along_runway(thr, in_dir, papi_dist)
        papi_perp = self._perp_from_dir(in_dir)
        if papi_side == 'RIGHT':
            papi_perp = (-papi_perp[0], -papi_perp[1])
        papi_lateral = runway_width / 2 + 15.0
        papi_base = self._point_perpendicular(papi_base, papi_perp, papi_lateral)
        spacing = 10.0
        stats['papi_lateral'] = papi_lateral
        stats['papi_spacing'] = spacing
        for k in range(4):
            p = self._point_perpendicular(papi_base, papi_perp, k * spacing)
            color = 1 if k < 2 else 7
            self._add_light_circle(p, light_radius * 1.2, color, 'LGT_PAPI')
            stats['papi'] += 1
        stats['papi_base'] = papi_base
        return stats

    def _draw_runway_centerline_and_edge_lights(self, runway_ref, runway_width, light_radius, params_start, params_end):
        length = runway_ref['length']
        stats = {
            'rcl': 0,
            'rcl_min': None,
            'rcl_max': None,
            'rcl_red': 0,
            'rcl_white': 0,
            'rcl_red_min': None,
            'rcl_red_max': None,
            'rcl_white_min': None,
            'rcl_white_max': None,
            'rcl_outside': 0,
            'rcl_dupe': 0,
            'edge': 0,
            'edge_min': None,
            'edge_max': None,
            'edge_white': 0,
            'edge_yellow': 0,
            'edge_white_min': None,
            'edge_white_max': None,
            'edge_yellow_min': None,
            'edge_yellow_max': None,
            'edge_offset': None,
            'edge_outside': 0,
            'edge_dupe': 0,
        }

        def bump_range(key_min, key_max, value):
            if stats[key_min] is None or value < stats[key_min]:
                stats[key_min] = value
            if stats[key_max] is None or value > stats[key_max]:
                stats[key_max] = value

        # Centerline lights (single pass, symmetric segmentation)
        rcll_spacing = params_start.get('rcll_spacing') or params_end.get('rcll_spacing') or 15
        rcll_len = params_start.get('rcll_len') or params_end.get('rcll_len') or length
        rcll_total = min(rcll_len, length)
        count = int(rcll_total // rcll_spacing) + 1
        rcl_keys = set()
        for i in range(count):
            dist = i * rcll_spacing
            if dist <= 0.0 or dist >= rcll_total:
                continue
            d_end = min(dist, rcll_total - dist)
            if d_end < 300.0:
                color_name = 'RED'
            elif d_end < 900.0:
                idx = int((d_end - 300.0) // rcll_spacing)
                color_name = 'RED' if idx % 2 == 0 else 'WHITE'
            else:
                color_name = 'WHITE'
            pos = self._from_runway_frame((dist, 0.0), runway_ref)
            key = (round(pos[0], 2), round(pos[1], 2), 'RCL')
            if key in rcl_keys:
                stats['rcl_dupe'] += 1
                continue
            rcl_keys.add(key)
            layer = 'LGT_RCL_RED' if color_name == 'RED' else 'LGT_RCL_WHITE'
            self._add_light_circle(pos, light_radius, self._color_to_aci(color_name), layer)
            stats['rcl'] += 1
            bump_range('rcl_min', 'rcl_max', d_end)
            if color_name == 'RED':
                stats['rcl_red'] += 1
                bump_range('rcl_red_min', 'rcl_red_max', d_end)
            else:
                stats['rcl_white'] += 1
                bump_range('rcl_white_min', 'rcl_white_max', d_end)
            if not self.is_point_inside_runway(pos, runway_ref):
                stats['rcl_outside'] += 1

        # Edge lights (single pass, symmetric segmentation)
        edge_spacing = params_start.get('edge_spacing') or params_end.get('edge_spacing') or 60
        edge_len = params_start.get('edge_len') or params_end.get('edge_len') or length
        edge_total = min(edge_len, length)
        edge_offset = runway_width / 2 - 0.5
        stats['edge_offset'] = edge_offset
        count = int(edge_total // edge_spacing) + 1
        edge_keys = set()
        for i in range(count):
            dist = i * edge_spacing
            if dist <= 0.0 or dist >= edge_total:
                continue
            d_end = min(dist, edge_total - dist)
            if d_end < 600.0:
                color_name = 'YELLOW'
                layer = 'LGT_EDGE_YELLOW'
            else:
                color_name = 'WHITE'
                layer = 'LGT_EDGE_WHITE'
            color = self._color_to_aci(color_name)
            base = self._from_runway_frame((dist, 0.0), runway_ref)
            for side, sgn in (('L', -1), ('R', 1)):
                pt = self._point_perpendicular(base, runway_ref['perpendicular'], sgn * edge_offset)
                key = (round(pt[0], 2), round(pt[1], 2), 'EDGE')
                if key in edge_keys:
                    stats['edge_dupe'] += 1
                    continue
                edge_keys.add(key)
                self._add_light_circle(pt, light_radius, color, layer)
                stats['edge'] += 1
                if color_name == 'YELLOW':
                    stats['edge_yellow'] += 1
                    bump_range('edge_yellow_min', 'edge_yellow_max', d_end)
                else:
                    stats['edge_white'] += 1
                    bump_range('edge_white_min', 'edge_white_max', d_end)
                if not self.is_point_inside_runway(pt, runway_ref):
                    stats['edge_outside'] += 1
            bump_range('edge_min', 'edge_max', d_end)
        return stats

    def _add_sign_panel(self, center, width, height, face_color, layer):
        cx, cy = center
        w2 = width / 2.0
        h2 = height / 2.0
        p1 = (cx - w2, cy - h2)
        p2 = (cx + w2, cy - h2)
        p3 = (cx + w2, cy + h2)
        p4 = (cx - w2, cy + h2)
        poly = [p1, p2, p3, p4, p1]
        self.msp.add_lwpolyline(poly, dxfattribs={'layer': layer, 'color': face_color})
        if self.enable_hatch:
            hatch = self.msp.add_hatch(color=face_color)
            hatch.dxf.layer = layer
            hatch.set_solid_fill(color=face_color)
            hatch.paths.add_polyline_path([p1, p2, p3, p4], is_closed=True)

    def _add_sign_text(self, text, center, height, color, layer='SIGN_TEXT'):
        if not self.enable_sign_text:
            return
        self.msp.add_text(
            text,
            dxfattribs={'layer': layer, 'height': height, 'color': color}
        ).set_placement(center, align=TextEntityAlignment.CENTER)

    def draw_taxiway_signs(self, runway_coords, runway_width):
        print("  Drawing taxiway signs...")
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        target_refs = ['P0', 'P1', 'P2', 'P3', 'P6', 'P7', 'P8', 'P9', 'C']

        for tw in self.real_geometry.get('taxiways', []):
            ref = tw.get('ref')
            if ref not in target_refs:
                continue
            coords = tw['geometry']['local_coordinates']
            if len(coords) < 2:
                continue

            # Find closest point on runway
            best_dist = None
            best_closest = None
            best_idx = None
            for i, pt in enumerate(coords):
                dist, closest = self._find_closest_point_on_line(pt, runway_coords)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_closest = closest
                    best_idx = i
            if best_closest is None:
                continue

            # Determine taxiway direction near intersection
            if best_idx <= 0:
                dx = coords[1][0] - coords[0][0]
                dy = coords[1][1] - coords[0][1]
            elif best_idx >= len(coords) - 1:
                dx = coords[-1][0] - coords[-2][0]
                dy = coords[-1][1] - coords[-2][1]
            else:
                dx = coords[best_idx + 1][0] - coords[best_idx - 1][0]
                dy = coords[best_idx + 1][1] - coords[best_idx - 1][1]
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue
            dir_x, dir_y = dx / length, dy / length

            # Pick direction away from runway centerline
            step = 20.0
            cand1 = (best_closest[0] + dir_x * step, best_closest[1] + dir_y * step)
            cand2 = (best_closest[0] - dir_x * step, best_closest[1] - dir_y * step)
            dist1, _ = self._find_closest_point_on_line(cand1, runway_coords)
            dist2, _ = self._find_closest_point_on_line(cand2, runway_coords)
            if dist2 > dist1:
                dir_x, dir_y = -dir_x, -dir_y

            away_dir = (dir_x, dir_y)
            perp = self._perp_from_dir(away_dir)

            base = (best_closest[0] + away_dir[0] * 40.0, best_closest[1] + away_dir[1] * 40.0)
            while self.is_point_inside_runway(base, runway_ref):
                base = (base[0] + away_dir[0] * 5.0, base[1] + away_dir[1] * 5.0)

            # Holding position signs (both sides)
            sign_width = 10.0
            sign_height = 4.0
            lateral = 8.0
            for sgn in (-1, 1):
                center = (base[0] + perp[0] * lateral * sgn, base[1] + perp[1] * lateral * sgn)
                self._add_sign_panel(center, sign_width, sign_height, 1, 'SIGN_MANDATORY')
                self._add_sign_text("18R-36L", center, 2.5, 7)

            # Location sign (one side)
            loc_center = (base[0] + perp[0] * (lateral + 10.0), base[1] + perp[1] * (lateral + 10.0))
            self._add_sign_panel(loc_center, 8.0, 3.5, 8, 'SIGN_LOCATION')
            self._add_sign_text(ref, loc_center, 2.2, 2)

    def _draw_tdz_lights(self, thr, in_dir, runway_ref, runway_width, light_radius, length):
        spacing = 30.0
        offset = runway_width / 4
        count = int(length // spacing) + 1
        for i in range(1, count + 1):
            dist = i * spacing
            if dist > length:
                break
            base = self._point_along_runway(thr, in_dir, dist)
            for side in (-1, 1):
                pos = self._point_perpendicular(base, runway_ref['perpendicular'], side * offset)
                self._add_light_circle(pos, light_radius * 0.9, 7, 'LGT_TDZ')

    def _calculate_polyline_length(self, coords):
        """计算折线总长度"""
        total_length = 0.0
        for i in range(len(coords) - 1):
            dx = coords[i+1][0] - coords[i][0]
            dy = coords[i+1][1] - coords[i][1]
            total_length += math.sqrt(dx**2 + dy**2)
        return total_length

    def _point_line_distance(self, p, a, b):
        ax, ay = a
        bx, by = b
        px, py = p
        dx = bx - ax
        dy = by - ay
        denom = dx * dx + dy * dy
        if denom <= 1e-12:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * dx + (py - ay) * dy) / denom
        t = max(0.0, min(1.0, t))
        proj = (ax + t * dx, ay + t * dy)
        return math.hypot(px - proj[0], py - proj[1])

    def _simplify_polyline(self, coords, tolerance):
        if not coords or len(coords) <= 2:
            return coords
        simplified = [coords[0]]
        for i in range(1, len(coords) - 1):
            prev = simplified[-1]
            curr = coords[i]
            nxt = coords[i + 1]
            if self._point_line_distance(curr, prev, nxt) <= tolerance:
                continue
            simplified.append(curr)
        simplified.append(coords[-1])
        return simplified
    
    def _offset_polyline(self, coords, offset):
        """将折线向两侧偏移"""
        left_coords = []
        right_coords = []
        
        for i in range(len(coords)):
            x, y = coords[i]
            
            if i == 0:
                dx = coords[i+1][0] - coords[i][0]
                dy = coords[i+1][1] - coords[i][1]
            elif i == len(coords) - 1:
                dx = coords[i][0] - coords[i-1][0]
                dy = coords[i][1] - coords[i-1][1]
            else:
                dx = coords[i+1][0] - coords[i-1][0]
                dy = coords[i+1][1] - coords[i-1][1]
            
            length = math.sqrt(dx**2 + dy**2)
            if length < 1e-10:
                continue
            
            nx = -dy / length
            ny = dx / length
            
            left_coords.append((x + nx * offset, y + ny * offset))
            right_coords.append((x - nx * offset, y - ny * offset))
        
        return left_coords, right_coords
    
    def _find_closest_point_on_line(self, point, line_points):
        """找到点到折线的最近点"""
        px, py = point
        min_dist = float('inf')
        closest_point = line_points[0]
        
        for i in range(len(line_points) - 1):
            x1, y1 = line_points[i]
            x2, y2 = line_points[i + 1]
            
            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy
            
            if length_sq < 1e-10:
                closest = (x1, y1)
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
                closest = (x1 + t * dx, y1 + t * dy)
            
            dist = math.sqrt((px - closest[0])**2 + (py - closest[1])**2)
            
            if dist < min_dist: 
                min_dist = dist
                closest_point = closest
        
        return min_dist, closest_point
    
    def connect_taxiway_to_runway(self, taxiway_coords, runway_coords, threshold=100.0):
        """自动连接滑行道到跑道"""
        if len(taxiway_coords) < 2 or len(runway_coords) < 2:
            return taxiway_coords, False
        
        start = taxiway_coords[0]
        end = taxiway_coords[-1]
        
        start_dist, start_closest = self._find_closest_point_on_line(start, runway_coords)
        end_dist, end_closest = self._find_closest_point_on_line(end, runway_coords)
        
        new_coords = list(taxiway_coords)
        modified = False
        
        if start_dist < threshold and start_dist > 0.01:
            new_coords.insert(0, start_closest)
            modified = True
        
        if end_dist < threshold and end_dist > 0.01:
            new_coords.append(end_closest)
            modified = True
        
        return new_coords, modified
    
    # ========== 阶段1：基础几何 ==========
    
    def draw_runway_from_real_geometry(self):
        """从真实几何数据绘制跑道（50m宽度）"""
        print("\n Drawing runway from real geometry...")
        
        runway = self.real_geometry['runway']
        designator = runway['designator']
        coords = runway['geometry']['local_coordinates']
        width = self.parameters['runway']['width']  # 使用课件标准50m
        
        print(f"  Runway: {designator}")
        print(f"  Points: {len(coords)}")
        print(f"  Width:  {width}m (50m)")
        
        centerline = [(x, y) for x, y in coords]
        
        # 绘制中心线
        self.msp.add_lwpolyline(centerline, 
                               dxfattribs={'layer': 'RWY_CENTERLINE',
                                          'color': 1})
        
        # 绘制跑道边界
        left, right = self._offset_polyline(centerline, width / 2.0)
        boundary = left + list(reversed(right))
        if self.enable_hatch:
            hatch = self.msp.add_hatch(color=8)
            hatch.dxf.layer = 'RWY'
            hatch.set_solid_fill(color=8)
            hatch.paths.add_polyline_path(boundary, is_closed=True)

        pline = self.msp.add_lwpolyline(boundary,
                                       dxfattribs={'layer':  'RWY',
                                                  'color':  7})
        pline.close()
        
        length = self._calculate_polyline_length(centerline)
        
        print(f"   Runway drawn:  {length:.1f}m × {width}m")
        
        self._runway_ref = self._get_runway_reference(centerline, width)
        return centerline, width
    
    def _draw_taxiways_from_real_geometry_old(self, runway_coords):
        """从真实几何数据绘制滑行道（标注RET）"""
        print("\n  Drawing taxiways from real geometry...")
        
        taxiways = self.real_geometry['taxiways']
        
        # RET列表（课件要求P2-P7为快速出口）
        ret_list = ['P2', 'P3', 'P4', 'P5', 'P6', 'P7']
        
        series_count = {}
        drawn_count = 0
        connected_count = 0
        ret_count = 0
        
        for tw in taxiways:
            ref = tw['ref']
            coords = tw['geometry']['local_coordinates']
            width = tw. get('width_meters', 23)
            
            series = ref[0] if ref else '? '
            series_count[series] = series_count.get(series, 0) + 1
            
            centerline = [(x, y) for x, y in coords]
            
            if len(centerline) < 2:
                continue
            
            # 自动连接
            connected_centerline, was_connected = self.connect_taxiway_to_runway(
                centerline, runway_coords, threshold=100.0
            )
            
            if was_connected:
                connected_count += 1
            
            # 判断是否是RET
            is_ret = ref in ret_list
            layer_name = 'RET' if is_ret else 'TWY'
            
            # 绘制中心线
            self.msp.add_lwpolyline(connected_centerline, 
                                   dxfattribs={'layer': 'TWY_CENTERLINE',
                                              'color': 2})
            
            # 绘制边界
            if len(connected_centerline) >= 2:
                left, right = self._offset_polyline(connected_centerline, width / 2.0)
                boundary = left + list(reversed(right))
                if self.enable_hatch:
                    hatch = self.msp.add_hatch(color=8)
                    hatch.dxf.layer = 'TWY'
                    hatch.set_solid_fill(color=8)
                    hatch.paths.add_polyline_path(boundary, is_closed=True)

                pline = self.msp.add_lwpolyline(boundary,
                                               dxfattribs={'layer': layer_name,
                                                          'color': 5})
                pline.close()
            
            # 如果是RET，添加文字标注
            if is_ret:
                ret_count += 1
                mid_point = connected_centerline[len(connected_centerline)//2]
                if self.enable_text:
                    self.msp.add_text(
                        f"{ref}\n(RET)",
                        dxfattribs={'layer': 'TEXT', 'height': 8, 'color': 3}
                    ).set_placement(mid_point, align=TextEntityAlignment.CENTER)
            else:
                # 普通滑行道标注
                mid_point = connected_centerline[len(connected_centerline)//2]
                if self.enable_text:
                    self.msp.add_text(
                        ref,
                        dxfattribs={'layer': 'TEXT', 'height': 10, 'color': 3}
                    ).set_placement(mid_point, align=TextEntityAlignment.CENTER)
            
            drawn_count += 1
        
        print(f"   Drew {drawn_count} taxiway segments")
        print(f"   Auto-connected {connected_count} to runway")
        print(f"   Marked {ret_count} as RET (P2-P7)")
        print(f"\n   By series:")
        for series in sorted(series_count.keys()):
            print(f"    {series}:  {series_count[series]} taxiway(s)")

    def _prepare_taxiway_draw_data(self, runway_coords):
        if self._twy_draw_data is not None:
            return self._twy_draw_data

        taxiways = self.real_geometry['taxiways']
        ret_list = ['P2', 'P3', 'P4', 'P5', 'P6', 'P7']

        series_count = {}
        drawn_count = 0
        connected_count = 0
        ret_count = 0
        draw_data = []

        for tw in taxiways:
            ref = tw.get('ref')
            coords = tw['geometry']['local_coordinates']
            width = tw.get('width_meters', 23)

            series = ref[0] if ref else '?'
            series_count[series] = series_count.get(series, 0) + 1

            centerline = [(x, y) for x, y in coords]
            if len(centerline) < 2:
                continue

            connected_centerline, was_connected = self.connect_taxiway_to_runway(
                centerline, runway_coords, threshold=100.0
            )
            if was_connected:
                connected_count += 1

            left, right = self._offset_polyline(connected_centerline, width / 2.0)
            boundary = left + list(reversed(right))

            is_ret = ref in ret_list
            draw_data.append({
                'ref': ref,
                'width': width,
                'centerline': connected_centerline,
                'boundary': boundary,
                'is_ret': is_ret,
            })

            drawn_count += 1
            if is_ret:
                ret_count += 1

        self._twy_draw_data = draw_data
        print(f"   Prepared {drawn_count} taxiway segments")
        print(f"   Auto-connected {connected_count} to runway")
        print(f"   Marked {ret_count} as RET (P2-P7)")
        print(f"\n   By series:")
        for series in sorted(series_count.keys()):
            print(f"    {series}:  {series_count[series]} taxiway(s)")
        return draw_data

    def draw_taxiway_pavement(self, runway_coords):
        """Draw taxiway pavement (hatch + outline) first."""
        print("\n  Drawing taxiway pavement...")
        data = self._prepare_taxiway_draw_data(runway_coords)
        hatch_count = 0

        for item in data:
            boundary = item['boundary']
            if self.enable_hatch:
                hatch = self.msp.add_hatch(color=8)
                hatch.dxf.layer = 'TWY_PAVEMENT'
                hatch.set_solid_fill(color=8)
                hatch.paths.add_polyline_path(boundary, is_closed=True)
                hatch_count += 1

            pline = self.msp.add_lwpolyline(boundary, dxfattribs={'layer': 'TWY_PAVEMENT', 'color': 8})
            pline.close()

        self._twy_hatch_count = hatch_count
        print(f"   Taxiway pavement hatches: {hatch_count}")

    def draw_taxiway_edges(self, runway_coords):
        """Draw taxiway edges after pavement."""
        print("  Drawing taxiway edges...")
        data = self._prepare_taxiway_draw_data(runway_coords)
        runway_ref = self._get_runway_reference(runway_coords, self.parameters['runway']['width'])
        eps = 1.0
        clip_eps = 0.3
        min_seg_len = 2.0
        removed_total = 0.0
        removed_segments = 0
        all_polys = [(item.get('ref') or '', item['boundary']) for item in data if item.get('boundary')]

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        def merge_segments(segments):
            segs = [list(seg) for seg in segments if len(seg) >= 2]
            chains = []
            merge_count = 0
            snap_count = 0
            while segs:
                chain = segs.pop(0)
                changed = True
                while changed:
                    changed = False
                    for i in range(len(segs)):
                        seg = segs[i]
                        if dist(chain[-1], seg[0]) <= eps:
                            chain.extend(seg[1:])
                        elif dist(chain[-1], seg[-1]) <= eps:
                            chain.extend(list(reversed(seg[:-1])))
                        elif dist(chain[0], seg[-1]) <= eps:
                            chain = seg[:-1] + chain
                        elif dist(chain[0], seg[0]) <= eps:
                            chain = list(reversed(seg[1:])) + chain
                        else:
                            continue
                        merge_count += 1
                        snap_count += 1
                        segs.pop(i)
                        changed = True
                        break
                chains.append(chain)
            return chains, merge_count, snap_count

        ref_segments = {}
        ref_removed = {}
        ref_segcount = {}
        ref_pre_len = {}
        ref_post_len = {}
        ref_inside_pts = {}

        for item in data:
            ref = item.get('ref') or ''
            boundary = item.get('boundary')
            if not boundary:
                continue
            boundary_len = self._calculate_polyline_length(boundary + [boundary[0]])
            ref_pre_len[ref] = ref_pre_len.get(ref, 0.0) + boundary_len
            other_polys = [poly for r, poly in all_polys if r != ref]
            outside_polys, removed_len, removed_seg = self._clip_polyline_outside_runway(
                boundary, runway_ref, buffer=clip_eps, closed=True
            )
            removed_total += removed_len
            removed_segments += removed_seg

            kept_polys = []
            removed_other = 0
            inside_count = 0

            for poly in outside_polys:
                if len(poly) < 2:
                    continue
                current = []
                for i in range(len(poly) - 1):
                    p0 = poly[i]
                    p1 = poly[i + 1]
                    mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
                    inside_other = False
                    for op in other_polys:
                        if self._point_in_polygon(mid, op):
                            inside_other = True
                            break
                    if inside_other:
                        removed_other += 1
                        if current:
                            kept_polys.append(current)
                            current = []
                        continue
                    if not current:
                        current = [p0]
                    current.append(p1)
                if current:
                    kept_polys.append(current)

            for poly in kept_polys:
                for p in poly:
                    if self.is_point_inside_runway(p, runway_ref):
                        inside_count += 1

            ref_segments.setdefault(ref, []).extend(kept_polys)
            ref_removed[ref] = ref_removed.get(ref, 0) + removed_other
            ref_segcount[ref] = ref_segcount.get(ref, 0) + len(kept_polys)
            ref_inside_pts[ref] = ref_inside_pts.get(ref, 0) + inside_count
            removed_segments += removed_other

        for ref, segments in sorted(ref_segments.items()):
            chains, merge_count, snap_count = merge_segments(segments)
            post_len = 0.0
            drawn_segments = 0
            for chain in chains:
                if len(chain) < 2:
                    continue
                length = self._calculate_polyline_length(chain)
                if length < min_seg_len:
                    removed_segments += 1
                    continue
                self.msp.add_lwpolyline(
                    chain, dxfattribs={'layer': 'TWY_EDGE', 'color': 2, 'lineweight': 20}
                )
                post_len += length
                drawn_segments += 1
            ref_post_len[ref] = ref_post_len.get(ref, 0.0) + post_len
            print(
                f"     TWY {ref}: segments={ref_segcount.get(ref, 0)}-> {drawn_segments}, "
                f"len={ref_pre_len.get(ref, 0.0):.1f}->{ref_post_len.get(ref, 0.0):.1f}m, "
                f"merges={merge_count}, snaps={snap_count}, clipped_segments={ref_removed.get(ref, 0)}, "
                f"inside_pts={ref_inside_pts.get(ref, 0)}"
            )
            if ref_inside_pts.get(ref, 0) > 0:
                print(f"       ⚠ TWY {ref} edge points inside runway: {ref_inside_pts.get(ref, 0)}")

        total_pre = sum(ref_pre_len.values())
        total_post = sum(ref_post_len.values())
        total_inside = sum(ref_inside_pts.values())
        print(
            f"   Taxiway edge clipped: len={total_pre:.1f}->{total_post:.1f}m, "
            f"removed_length={removed_total:.1f}m, affected_segments={removed_segments}, "
            f"inside_points={total_inside}"
        )
        self._qa['twy_edge'] = {
            'length_pre': total_pre,
            'length_post': total_post,
            'inside_points': total_inside,
            'removed_length': removed_total,
            'removed_segments': removed_segments,
        }

    def draw_taxiway_centerlines(self, runway_coords):
        """Draw taxiway centerlines last for visibility."""
        print("  Drawing taxiway centerlines...")
        data = self._prepare_taxiway_draw_data(runway_coords)
        eps = 0.5
        clip_eps = 0.3
        simplify_tol = 0.2
        min_seg_len = 1.0
        centerline_count = 0
        runway_ref = self._get_runway_reference(runway_coords, self.parameters['runway']['width'])

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        def merge_segments(segments):
            segs = [list(seg) for seg in segments if len(seg) >= 2]
            chains = []
            merge_count = 0
            snap_count = 0
            while segs:
                chain = segs.pop(0)
                while True:
                    best_idx = None
                    best_mode = None
                    best_dist = None
                    for i, seg in enumerate(segs):
                        candidates = [
                            ('end-start', dist(chain[-1], seg[0])),
                            ('end-end', dist(chain[-1], seg[-1])),
                            ('start-end', dist(chain[0], seg[-1])),
                            ('start-start', dist(chain[0], seg[0])),
                        ]
                        mode, dval = min(candidates, key=lambda x: x[1])
                        if best_dist is None or dval < best_dist:
                            best_dist = dval
                            best_idx = i
                            best_mode = mode
                    if best_dist is None or best_dist > eps:
                        break
                    seg = segs.pop(best_idx)
                    if best_mode == 'end-start':
                        chain.extend(seg[1:])
                    elif best_mode == 'end-end':
                        chain.extend(list(reversed(seg[:-1])))
                    elif best_mode == 'start-end':
                        chain = seg[:-1] + chain
                    else:
                        chain = list(reversed(seg[1:])) + chain
                    merge_count += 1
                    snap_count += 1
                chains.append(chain)
            return chains, merge_count, snap_count

        grouped = {}
        ref_pre_len = {}
        for item in data:
            ref = item.get('ref') or ''
            centerline = item['centerline']
            grouped.setdefault(ref, []).append(centerline)
            ref_pre_len[ref] = ref_pre_len.get(ref, 0.0) + self._calculate_polyline_length(centerline)

        total_post = 0.0
        total_merges = 0
        total_snaps = 0
        total_inside = 0
        for ref, segments in sorted(grouped.items()):
            chains, merge_count, snap_count = merge_segments(segments)
            total_points = 0
            clipped_segments = 0
            post_len = 0.0
            inside_pts = 0
            for chain in chains:
                if len(chain) < 2:
                    continue
                outside_polys, _, removed_seg = self._clip_polyline_outside_runway(
                    chain, runway_ref, buffer=clip_eps, closed=False
                )
                clipped_segments += removed_seg
                for poly in outside_polys:
                    if len(poly) < 2:
                        continue
                    simplified = self._simplify_polyline(poly, simplify_tol)
                    if len(simplified) < 2:
                        continue
                    length = self._calculate_polyline_length(simplified)
                    if length < min_seg_len:
                        continue
                    for p in simplified:
                        if self.is_point_inside_runway(p, runway_ref):
                            inside_pts += 1
                    self.msp.add_lwpolyline(
                        simplified,
                        dxfattribs={'layer': 'TWY_CENTERLINE', 'color': 2, 'lineweight': 35}
                    )
                    centerline_count += 1
                    total_points += len(simplified)
                    post_len += length
            print(
                f"     TWY {ref}: segments={len(segments)}, len={ref_pre_len.get(ref, 0.0):.1f}->{post_len:.1f}m, "
                f"points={total_points}, merges={merge_count}, snaps={snap_count}, "
                f"clipped_segments={clipped_segments}, inside_pts={inside_pts}"
            )
            if inside_pts > 0:
                print(f"       ⚠ TWY {ref} centerline points inside runway: {inside_pts}")
            total_post += post_len
            total_inside += inside_pts
            total_merges += merge_count
            total_snaps += snap_count

        self._twy_centerline_count = centerline_count
        total_pre = sum(ref_pre_len.values())
        print(
            f"   Taxiway centerlines: {centerline_count} (after {self._twy_hatch_count} pavement hatches), "
            f"len={total_pre:.1f}->{total_post:.1f}m, inside_points={total_inside}"
        )
        self._qa['twy_center'] = {
            'length_pre': total_pre,
            'length_post': total_post,
            'inside_points': total_inside,
            'count': centerline_count,
            'merges': total_merges,
            'snaps': total_snaps,
        }

    def draw_taxiways_from_real_geometry(self, runway_coords):
        """Compatibility wrapper for taxiway drawing order."""
        self.draw_taxiway_pavement(runway_coords)
        self.draw_taxiway_edges(runway_coords)
        self.draw_taxiway_centerlines(runway_coords)
    
    # ========== 阶段2：跑道系统完善 ==========
    
    def draw_runway_shoulder(self, runway_coords, runway_width):
        """绘制道肩"""
        print("   Drawing runway shoulder...")
        
        shoulder_width = self.parameters['shoulder_width']
        
        left_runway, right_runway = self._offset_polyline(runway_coords, runway_width / 2.0)
        left_shoulder_outer, _ = self._offset_polyline(left_runway, shoulder_width)
        _, right_shoulder_outer = self._offset_polyline(right_runway, shoulder_width)
        
        # 左侧道肩
        left_shoulder_poly = left_runway + list(reversed(left_shoulder_outer))
        pline = self.msp.add_lwpolyline(left_shoulder_poly, 
                                       dxfattribs={'layer': 'RWY_SHOULDER',
                                                  'color': 8})
        pline.close()
        
        # 右侧道肩
        right_shoulder_poly = right_runway + list(reversed(right_shoulder_outer))
        pline = self.msp.add_lwpolyline(right_shoulder_poly,
                                       dxfattribs={'layer': 'RWY_SHOULDER',
                                                  'color': 8})
        pline.close()
        
        total_width = runway_width + 2 * shoulder_width
        print(f"     Shoulder:  {shoulder_width}m each side (总宽{total_width}m ≥ 60m )")
    
    def draw_runway_strip(self, runway_coords, runway_width):
        """绘制升降带（300m宽 + 两端各延伸60m）"""
        print("   Drawing runway strip...")
        
        strip_width = self.parameters['strip']['width']
        strip_extension = self.parameters['strip']['extension']
        
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        # 延伸后的起点和终点
        extended_start = self._point_along_runway(start, direction, -strip_extension)
        extended_end = self._point_along_runway(end, direction, strip_extension)
        
        # 创建延伸后的中心线
        extended_centerline = [extended_start] + runway_coords + [extended_end]
        
        # 计算升降带边界
        left_strip, right_strip = self._offset_polyline(extended_centerline, strip_width / 2.0)
        strip_boundary = left_strip + list(reversed(right_strip))
        
        pline = self.msp.add_lwpolyline(strip_boundary,
                                       dxfattribs={'layer': 'STRIP',
                                                  'color': 9})
        pline.close()
        
        print(f"     Strip: {strip_width}m wide, 两端各延伸{strip_extension}m")
    
    def draw_resa(self, runway_coords, runway_width):
        """绘制RESA"""
        print("   Drawing RESA...")
        
        resa_params = self.parameters['resa']
        resa_length = resa_params['length']
        resa_width = resa_params['width']
        
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        # 18R端RESA
        center_18r = self._point_along_runway(start, direction, -resa_length/2)
        
        p1 = self._point_perpendicular(
            self._point_along_runway(center_18r, direction, -resa_length/2),
            perpendicular, -resa_width/2
        )
        p2 = self._point_perpendicular(
            self._point_along_runway(center_18r, direction, -resa_length/2),
            perpendicular, resa_width/2
        )
        p3 = self._point_perpendicular(
            self._point_along_runway(center_18r, direction, resa_length/2),
            perpendicular, resa_width/2
        )
        p4 = self._point_perpendicular(
            self._point_along_runway(center_18r, direction, resa_length/2),
            perpendicular, -resa_width/2
        )
        
        resa_18r = [p1, p2, p3, p4]
        pline = self.msp.add_lwpolyline(resa_18r, 
                                       dxfattribs={'layer': 'RESA', 'color': 1})
        pline.close()
        
        # 36L端RESA
        center_36l = self._point_along_runway(end, direction, resa_length/2)
        
        p1 = self._point_perpendicular(
            self._point_along_runway(center_36l, direction, -resa_length/2),
            perpendicular, -resa_width/2
        )
        p2 = self._point_perpendicular(
            self._point_along_runway(center_36l, direction, -resa_length/2),
            perpendicular, resa_width/2
        )
        p3 = self._point_perpendicular(
            self._point_along_runway(center_36l, direction, resa_length/2),
            perpendicular, resa_width/2
        )
        p4 = self._point_perpendicular(
            self._point_along_runway(center_36l, direction, resa_length/2),
            perpendicular, -resa_width/2
        )
        
        resa_36l = [p1, p2, p3, p4]
        pline = self.msp.add_lwpolyline(resa_36l, 
                                       dxfattribs={'layer': 'RESA', 'color': 1})
        pline.close()
        
        print(f"     RESA: {resa_length}m × {resa_width}m (both ends)")
    
    def draw_runway_markings(self, runway_coords, runway_width):
        """绘制跑道标记（完整版）"""
        print("   Drawing runway markings...")
        
        markings = self.parameters['markings']
        
        # 1. 跑道中心线虚线
        self._draw_runway_centerline_dashed(runway_coords, markings['centerline'])
        
        # 2. 入口标志
        self._draw_threshold_markings(runway_coords, runway_width, markings['threshold'], at_start=True)
        self._draw_threshold_markings(runway_coords, runway_width, markings['threshold'], at_start=False)
        
        # 3. 接地带标记（TDZ）
        self._draw_tdz_markings(runway_coords, runway_width, markings['tdz'], at_start=True)
        self._draw_tdz_markings(runway_coords, runway_width, markings['tdz'], at_start=False)
        
        # 4. 瞄准点
        self._draw_aiming_point(runway_coords, runway_width, markings['aiming_point'], at_start=True)
        self._draw_aiming_point(runway_coords, runway_width, markings['aiming_point'], at_start=False)
        
        # 5. 跑道编号
        self._draw_runway_designators(runway_coords)
        
        # ========== 新增：6. 跑道边线标记 ==========
        self._draw_runway_edge_lines(runway_coords, runway_width)

        print(f"     Markings:   Threshold, TDZ, Aiming point, Designators, Edge lines")
    
    def _draw_runway_centerline_dashed(self, runway_coords, params):
        """绘制跑道中心线虚线"""
        defaults = self.standard_defaults['centerline']
        dash_length = float(params.get('dash_length', defaults['block_length']))
        gap_length = float(params.get('gap_length', defaults['gap_length']))
        block_width = float(params.get('block_width', defaults['block_width']))

        if dash_length <= 0.0 or gap_length < 0.0:
            dash_length, gap_length = 60.0, 15.0

        cycle = dash_length + gap_length
        target_cycle = min(max(cycle, 50.0), 75.0)
        if cycle > 0.0:
            ratio = dash_length / cycle
            dash_length = target_cycle * ratio
            gap_length = target_cycle - dash_length
        else:
            dash_length, gap_length = 60.0, 15.0

        if dash_length < 30.0 or dash_length < gap_length:
            dash_length = max(30.0, gap_length)
            gap_length = target_cycle - dash_length
            if gap_length <= 0.0:
                dash_length, gap_length = 60.0, 15.0

        cycle = dash_length + gap_length
        if cycle < 50.0 or cycle > 75.0:
            dash_length, gap_length = 60.0, 15.0
            cycle = dash_length + gap_length
        if gap_length <= 1.0:
            dash_length, gap_length = 60.0, 15.0
            cycle = dash_length + gap_length

        runway_width = self.parameters['runway']['width']
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        start, end, direction, perpendicular, length = self._get_runway_direction(runway_coords)

        # Keep centerline between designators (match _draw_runway_designators)
        distance_from_threshold = 90.0
        line_spacing = 24.0
        digit_height = 22.0
        designator_clear = distance_from_threshold + line_spacing / 2.0 + digit_height / 2.0 + 5.0
        start_offset = designator_clear
        end_offset = designator_clear

        if length <= start_offset + end_offset:
            print("     Centerline: runway too short, skipped")
            return

        def rect(center, along_dir, perp_dir, L, W):
            ax, ay = along_dir
            px, py = perp_dir
            cx, cy = center
            p1 = (cx - ax * L / 2 - px * W / 2, cy - ay * L / 2 - py * W / 2)
            p2 = (cx + ax * L / 2 - px * W / 2, cy + ay * L / 2 - py * W / 2)
            p3 = (cx + ax * L / 2 + px * W / 2, cy + ay * L / 2 + py * W / 2)
            p4 = (cx - ax * L / 2 + px * W / 2, cy - ay * L / 2 + py * W / 2)
            return [p1, p2, p3, p4, p1]

        distance = start_offset
        seg_count = 0
        first_block_distance = None
        while distance < length - end_offset:
            block_len = min(dash_length, length - end_offset - distance)
            if block_len <= 0.0:
                break
            center = self._point_along_runway(start, direction, distance + block_len / 2.0)
            poly = rect(center, direction, perpendicular, block_len, block_width)
            clipped = self._clip_poly_to_runway(poly, runway_ref)
            if clipped:
                self._add_mark_poly(clipped, 'MARK_RWY', 7)
                seg_count += 1
                if first_block_distance is None:
                    first_block_distance = distance
            distance += dash_length + gap_length

        self._qa['centerline'] = {
            'dash': dash_length,
            'gap': gap_length,
            'cycle': cycle,
            'segments': seg_count,
            'start_offset': start_offset,
            'end_offset': end_offset,
            'block_width': block_width,
            'first_block_distance': first_block_distance,
        }
        print(
            f"     Centerline: dash={dash_length:.1f}m, gap={gap_length:.1f}m, "
            f"cycle={cycle:.1f}m, segments={seg_count}, "
            f"start_offset={start_offset:.1f}m, end_offset={end_offset:.1f}m"
        )
    
    def _draw_threshold_markings(self, runway_coords, runway_width, params, at_start=True):
        """Threshold Markings: 50m runway, 12 stripes (6 per side), symmetric and in-bounds."""

        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        start, end, direction, perpendicular, runway_length = self._get_runway_direction(runway_coords)

        # Choose threshold and inward direction
        if at_start:
            thr = start
            in_dir = direction
            perp = perpendicular
        else:
            thr = end
            in_dir = (-direction[0], -direction[1])
            perp = perpendicular

        stripes_per_side = 6
        stripe_width = 1.8
        stripe_length = 45.0
        margin = 2.0
        inner_clearance = 3.0

        # Max half-width available, subtract half stripe width to avoid edge overrun
        half = runway_width / 2 - margin - stripe_width / 2
        if half <= inner_clearance:
            inner_clearance = max(0.0, half * 0.5)

        # Offsets from inner_clearance to half, evenly spaced
        if stripes_per_side == 1:
            offsets = [inner_clearance]
        else:
            step = (half - inner_clearance) / (stripes_per_side - 1)
            offsets = [inner_clearance + i * step for i in range(stripes_per_side)]

        # Place stripes inside threshold to avoid overrun
        base = self._point_along_runway(thr, in_dir, stripe_length / 2 + 6.0)

        def rect(center, along_dir, perp_dir, L, W):
            ax, ay = along_dir
            px, py = perp_dir
            cx, cy = center
            p1 = (cx - ax*L/2 - px*W/2, cy - ay*L/2 - py*W/2)
            p2 = (cx + ax*L/2 - px*W/2, cy + ay*L/2 - py*W/2)
            p3 = (cx + ax*L/2 + px*W/2, cy + ay*L/2 + py*W/2)
            p4 = (cx - ax*L/2 + px*W/2, cy - ay*L/2 + py*W/2)
            return [p1, p2, p3, p4, p1]

        # Symmetric left/right stripes
        for sgn in (-1, 1):
            for off in offsets:
                c = self._point_perpendicular(base, perp, sgn * off)
                poly = rect(c, in_dir, perp, stripe_length, stripe_width)
                clipped = self._clip_poly_to_runway(poly, runway_ref)
                if clipped:
                    self._add_mark_poly(clipped, 'MARK_RWY', 7)

    def _draw_tdz_markings(self, runway_coords, runway_width, params, at_start=True):
        """Draw TDZ markings as grouped bars aligned with runway direction."""
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        direction = runway_ref['direction']
        perpendicular = runway_ref['perpendicular']
        start = runway_ref['start']
        end = runway_ref['end']

        if at_start:
            thr = start
            in_dir = direction
        else:
            thr = end
            in_dir = (-direction[0], -direction[1])

        defaults = self.standard_defaults['tdz']
        bar_length = float(params.get('bar_length', defaults['bar_length']))
        bar_width = float(params.get('bar_width', defaults['bar_width']))
        bars_per_side = int(params.get('bars_per_side', defaults['bars_per_side']))
        group_start = float(params.get('group_start', defaults['group_start']))
        group_spacing = float(params.get('group_spacing', defaults['group_spacing']))
        group_count = int(params.get('group_count', defaults['group_count']))
        inner_clearance = float(params.get('inner_clearance', defaults['inner_clearance']))
        bar_spacing = float(params.get('bar_spacing', defaults['bar_spacing']))
        aiming_distance = self._get_aiming_distance()
        tdz_positions = [group_start + i * group_spacing for i in range(group_count)]

        margin = 3.0
        half = runway_width / 2 - margin - bar_width / 2
        if half <= 0.0:
            return
        inner_clearance = max(0.0, min(inner_clearance, half))
        if bars_per_side <= 1:
            offsets = [inner_clearance]
        else:
            max_span = max(0.0, half - inner_clearance)
            if max_span <= 1e-6:
                offsets = [inner_clearance]
            else:
                max_step = max_span / (bars_per_side - 1)
                step = bar_spacing if bar_spacing <= max_step else max_step
                offsets = [inner_clearance + i * step for i in range(bars_per_side)]

        def rect(center, along_dir, perp_dir, L, W):
            ax, ay = along_dir
            px, py = perp_dir
            cx, cy = center
            p1 = (cx - ax * L / 2 - px * W / 2, cy - ay * L / 2 - py * W / 2)
            p2 = (cx + ax * L / 2 - px * W / 2, cy + ay * L / 2 - py * W / 2)
            p3 = (cx + ax * L / 2 + px * W / 2, cy + ay * L / 2 + py * W / 2)
            p4 = (cx - ax * L / 2 + px * W / 2, cy - ay * L / 2 + py * W / 2)
            return [p1, p2, p3, p4, p1]

        angle = math.degrees(math.atan2(in_dir[1], in_dir[0]))
        used_positions = []
        groups_drawn = 0
        stripes_per_group_total = bars_per_side * 2
        for distance in tdz_positions:
            if abs(distance - aiming_distance) <= 50.0:
                continue
            group_center = self._point_along_runway(thr, in_dir, distance)
            for side in (-1, 1):
                for off in offsets:
                    center = self._point_perpendicular(group_center, perpendicular, side * off)
                    poly = rect(center, in_dir, perpendicular, bar_length, bar_width)
                    clipped = self._clip_poly_to_runway(poly, runway_ref)
                    if clipped:
                        self._add_mark_poly(clipped, 'MARK_RWY', 7)
            used_positions.append(distance)
            groups_drawn += 1
            print(
                f"     TDZ group {('start' if at_start else 'end')} @ {distance}m: "
                f"bars/side={bars_per_side}, L={bar_length}, W={bar_width}, angle={angle:.1f}deg"
            )

        label = "start" if at_start else "end"
        self._qa['tdz'][label] = {
            'bars_per_side': bars_per_side,
            'bar_length': bar_length,
            'bar_width': bar_width,
            'positions': used_positions,
            'angle': angle,
            'inner_clearance': inner_clearance,
            'bar_spacing': bar_spacing,
        }
        if used_positions:
            print(
                f"     TDZ {label}: groups={groups_drawn}, stripes/group={stripes_per_group_total}, "
                f"range={min(used_positions):.0f}-{max(used_positions):.0f}m"
            )
        else:
            print(f"     TDZ {label}: groups=0")

    def _draw_aiming_point(self, runway_coords, runway_width, params, at_start=True):
        """Draw aiming point markings."""
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        bar_width = 6.0
        bar_length = 45.0
        center_offset = 13.0
        distance_from_threshold = self._get_aiming_distance()
        label = "start" if at_start else "end"
        print(f"     Aiming point {label}: center offset ±{center_offset}m")
        self._qa['aiming'] = {
            'bar_width': bar_width,
            'bar_length': bar_length,
            'center_offset': center_offset,
            'distance': distance_from_threshold,
        }

        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)

        if at_start:
            base = start
            aim_dir = direction
        else:
            base = end
            aim_dir = (-direction[0], -direction[1])

        aim_center = self._point_along_runway(base, aim_dir, distance_from_threshold)

        for side in [-1, 1]:
            aim_pos = self._point_perpendicular(aim_center, perpendicular, side * center_offset)

            p1 = (aim_pos[0] - aim_dir[0]*bar_length/2 - perpendicular[0]*bar_width/2,
                aim_pos[1] - aim_dir[1]*bar_length/2 - perpendicular[1]*bar_width/2)
            p2 = (aim_pos[0] + aim_dir[0]*bar_length/2 - perpendicular[0]*bar_width/2,
                aim_pos[1] + aim_dir[1]*bar_length/2 - perpendicular[1]*bar_width/2)
            p3 = (aim_pos[0] + aim_dir[0]*bar_length/2 + perpendicular[0]*bar_width/2,
                aim_pos[1] + aim_dir[1]*bar_length/2 + perpendicular[1]*bar_width/2)
            p4 = (aim_pos[0] - aim_dir[0]*bar_length/2 + perpendicular[0]*bar_width/2,
                aim_pos[1] - aim_dir[1]*bar_length/2 + perpendicular[1]*bar_width/2)

            aiming = [p1, p2, p3, p4, p1]
            clipped = self._clip_poly_to_runway(aiming, runway_ref)
            if clipped:
                self._add_mark_poly(clipped, 'MARK_RWY', 7)

    def _draw_runway_designators(self, runway_coords):
        """Draw runway designators."""
        runway_width = self.parameters['runway']['width']
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        distance_from_threshold = 90.0
        line_spacing = 24.0
        digit_height = 22.0
        digit_width = 11.0
        digit_thickness = 2.0
        letter_height = 14.0
        letter_width = 7.0
        letter_thickness = 2.0
        char_spacing = 4.0

        thr18, in_dir18, thr36, in_dir36 = self._map_runway_ends(runway_coords, runway_width)

        def rect(center, along_dir, perp_dir, L, W):
            ax, ay = along_dir
            px, py = perp_dir
            cx, cy = center
            p1 = (cx - ax * L / 2 - px * W / 2, cy - ay * L / 2 - py * W / 2)
            p2 = (cx + ax * L / 2 - px * W / 2, cy + ay * L / 2 - py * W / 2)
            p3 = (cx + ax * L / 2 + px * W / 2, cy + ay * L / 2 + py * W / 2)
            p4 = (cx - ax * L / 2 + px * W / 2, cy - ay * L / 2 + py * W / 2)
            return [p1, p2, p3, p4, p1]

        def build_segments(char_height, char_width, thickness):
            return {
                'A': (char_height / 2 - thickness / 2, 0.0, 'h'),
                'G': (0.0, 0.0, 'h'),
                'D': (-char_height / 2 + thickness / 2, 0.0, 'h'),
                'F': (char_height / 4, -char_width / 2 + thickness / 2, 'v'),
                'B': (char_height / 4, char_width / 2 - thickness / 2, 'v'),
                'E': (-char_height / 4, -char_width / 2 + thickness / 2, 'v'),
                'C': (-char_height / 4, char_width / 2 - thickness / 2, 'v'),
            }

        digit_map = {
            '0': ['A', 'B', 'C', 'D', 'E', 'F'],
            '1': ['B', 'C'],
            '2': ['A', 'B', 'G', 'E', 'D'],
            '3': ['A', 'B', 'G', 'C', 'D'],
            '4': ['F', 'G', 'B', 'C'],
            '5': ['A', 'F', 'G', 'C', 'D'],
            '6': ['A', 'F', 'G', 'E', 'C', 'D'],
            '7': ['A', 'B', 'C'],
            '8': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
            '9': ['A', 'B', 'C', 'D', 'F', 'G'],
            'L': ['F', 'E', 'D'],
            'R': ['A', 'B', 'C', 'E', 'F', 'G'],
        }

        def draw_char(char, center, along_dir, perp_dir, char_height, char_width, thickness):
            segs = digit_map.get(char)
            if not segs:
                return
            segments = build_segments(char_height, char_width, thickness)
            for key in segs:
                du, dv, orientation = segments[key]
                seg_center = (
                    center[0] + along_dir[0] * du + perp_dir[0] * dv,
                    center[1] + along_dir[1] * du + perp_dir[1] * dv,
                )
                if orientation == 'h':
                    poly = rect(seg_center, perp_dir, along_dir, char_width, thickness)
                else:
                    poly = rect(seg_center, along_dir, perp_dir, char_height / 2 - thickness, thickness)
                clipped = self._clip_poly_to_runway(poly, runway_ref)
                if clipped:
                    self._add_mark_poly(clipped, 'MARK_RWY', 7)

        def draw_string(text, base_center, along_dir, perp_dir, char_height, char_width, thickness):
            total_width = len(text) * char_width + (len(text) - 1) * char_spacing
            offset = -total_width / 2 + char_width / 2
            for ch in text:
                center = self._point_perpendicular(base_center, perp_dir, offset)
                draw_char(ch, center, along_dir, perp_dir, char_height, char_width, thickness)
                offset += char_width + char_spacing

        def draw_designator(thr, in_dir, top_text, bottom_text, label):
            perp_dir = self._perp_from_dir(in_dir)
            right_perp = (-perp_dir[0], -perp_dir[1])
            base_center = self._point_along_runway(thr, in_dir, distance_from_threshold)
            top_center = self._point_along_runway(base_center, in_dir, line_spacing / 2)
            bottom_center = self._point_along_runway(base_center, in_dir, -line_spacing / 2)

            if self.enable_text:
                angle = math.degrees(math.atan2(right_perp[1], right_perp[0]))
                self.msp.add_text(
                    top_text,
                    dxfattribs={'layer': 'TEXT', 'height': digit_height, 'rotation': angle, 'color': 7}
                ).set_placement(top_center, align=TextEntityAlignment.CENTER)
                self.msp.add_text(
                    bottom_text,
                    dxfattribs={'layer': 'TEXT', 'height': letter_height, 'rotation': angle, 'color': 7}
                ).set_placement(bottom_center, align=TextEntityAlignment.CENTER)
            else:
                draw_string(top_text, top_center, in_dir, right_perp, digit_height, digit_width, digit_thickness)
                draw_string(bottom_text, bottom_center, in_dir, right_perp, letter_height, letter_width, letter_thickness)

            angle = math.degrees(math.atan2(right_perp[1], right_perp[0]))
            print(f"     Designator {label}: base=({base_center[0]:.2f}, {base_center[1]:.2f}), rotation={angle:.1f}°")

        draw_designator(thr36, in_dir36, "36", "L", "36L")
        draw_designator(thr18, in_dir18, "18", "R", "18R")

    def _draw_runway_edge_lines(self, runway_coords, runway_width):
        """Draw runway edge lines (solid)."""
        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)

        # Sample along centerline
        left_coords = []
        right_coords = []

        # Sample along centerline
        num_points = len(runway_coords)

        for i, center_point in enumerate(runway_coords):
            # Compute left/right points
            if i == 0:
                local_dir = direction
            elif i == len(runway_coords) - 1:
                local_dir = direction
            else:
                # Use local direction
                dx = runway_coords[i+1][0] - runway_coords[i-1][0]
                dy = runway_coords[i+1][1] - runway_coords[i-1][1]
                length = math.sqrt(dx**2 + dy**2)
                if length > 1e-6:
                    local_dir = (dx/length, dy/length)
                else:
                    local_dir = direction

            local_perp = (-local_dir[1], local_dir[0])

            left_point = self._point_perpendicular(center_point, local_perp, -runway_width/2)
            right_point = self._point_perpendicular(center_point, local_perp, runway_width/2)

            left_coords.append(self.clamp_point_to_runway(left_point, runway_ref))
            right_coords.append(self.clamp_point_to_runway(right_point, runway_ref))

        # Draw left edge line
        self.msp.add_lwpolyline(left_coords,
                            dxfattribs={'layer': 'MARK_RWY',
                                        'color': 7,
                                        'lineweight': 25,
                                        'const_width': 0.9})

        # Draw right edge line
        self.msp.add_lwpolyline(right_coords,
                            dxfattribs={'layer': 'MARK_RWY',
                                        'color': 7,
                                        'lineweight': 25,
                                        'const_width': 0.9})

    def draw_holding_position_markings(self, runway_coords):
        """绘制跑道等待位置标志(智能版 - 只在垂直交叉处)"""
        print("   Drawing holding position markings...")
        
        taxiways = self.real_geometry['taxiways']
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        # 只为这些滑行道绘制等待位置
        target_taxiways = ['P0', 'P1', 'P2', 'P3', 'P6', 'P7', 'P8', 'P9']
        
        holding_count = 0
        
        for tw in taxiways: 
            ref = tw['ref']
            
            #  关键修复: 只处理目标滑行道,跳过C系列(平行滑行道)
            if ref not in target_taxiways: 
                continue
            
            coords = tw['geometry']['local_coordinates']
            
            if len(coords) < 2:
                continue
            
            # 计算滑行道方向
            tw_start = coords[0]
            tw_end = coords[-1]
            tw_dx = tw_end[0] - tw_start[0]
            tw_dy = tw_end[1] - tw_start[1]
            tw_length = math.sqrt(tw_dx**2 + tw_dy**2)
            
            if tw_length < 1e-6:
                continue
            
            tw_dir_x = tw_dx / tw_length
            tw_dir_y = tw_dy / tw_length
            
            #  关键修复: 检查是否与跑道垂直交叉
            # 点积接近0表示垂直,接近1表示平行
            dot_product = abs(tw_dir_x * direction[0] + tw_dir_y * direction[1])
            
            if dot_product > 0.5:  # 如果接近平行(角度<60°),跳过
                print(f"    ⊗ Skipping {ref} (parallel, dot={dot_product:.2f})")
                continue
            
            # 找到滑行道与跑道的交点
            for point in coords:
                dist, closest = self._find_closest_point_on_line(point, runway_coords)
                
                if dist < 30:  # 距离<30m认为是交叉点
                    # 绘制等待位置标志
                    line_length = 60
                    
                    p1 = self._point_perpendicular(closest, perpendicular, -line_length/2)
                    p2 = self._point_perpendicular(closest, perpendicular, line_length/2)
                    
                    # 第一条线
                    self.msp.add_line(p1, p2, dxfattribs={'layer': 'MARK_TWY', 'color': 2, 'lineweight': 50})
                    
                    # 第二条线(向滑行道方向偏移3m)
                    to_start = math.sqrt((closest[0]-start[0])**2 + (closest[1]-start[1])**2)
                    to_end = math.sqrt((closest[0]-end[0])**2 + (closest[1]-end[1])**2)
                    
                    if to_start < to_end:
                        offset_point = self._point_along_runway(closest, direction, -3)
                    else:
                        offset_point = self._point_along_runway(closest, direction, 3)
                    
                    p3 = self._point_perpendicular(offset_point, perpendicular, -line_length/2)
                    p4 = self._point_perpendicular(offset_point, perpendicular, line_length/2)
                    
                    self.msp.add_line(p3, p4, dxfattribs={'layer': 'MARK_TWY', 'color': 2, 'lineweight': 50})

                    # Stop bar lights on the holding line
                    light_count = 5
                    for i in range(light_count):
                        t = (i + 1) / (light_count + 1)
                        pos = (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
                        self._add_light_circle(pos, 0.6, 1, 'LGT_STOP_RED')
                    
                    holding_count += 1
                    print(f"     Drew holding position for {ref}")
                    break  # 每条滑行道只画一次
        
        print(f"     Holding positions:  {holding_count} locations")
    
    def draw_lighting_systems(self, runway_coords, runway_width):
        """Draw lighting system (table-driven)."""
        print("  Drawing lighting systems...")

        runway_ref = self._get_runway_reference(runway_coords, runway_width)
        thr18, in_dir18, thr36, in_dir36 = self._map_runway_ends(runway_coords, runway_width)

        light_radius = 1.0
        params_18r = dict(self.lighting_params.get('18R', {}))
        params_36l = dict(self.lighting_params.get('36L', {}))
        params_18r['label'] = '18R'
        params_36l['label'] = '36L'
        params_18r['apch_cat'] = 'CAT I'
        params_36l['apch_cat'] = 'CAT I'

        # Threshold/approach lighting
        stats_18 = self._draw_end_lighting(thr18, in_dir18, runway_ref, runway_width, light_radius, params_18r)
        stats_36 = self._draw_end_lighting(thr36, in_dir36, runway_ref, runway_width, light_radius, params_36l)

        # Centerline + edge lights
        rwy_stats = self._draw_runway_centerline_and_edge_lights(runway_ref, runway_width, light_radius, params_18r, params_36l)

        # TDZ lights (36L only)
        tdzl_len = params_36l.get('tdzl_len')
        if tdzl_len:
            self._draw_tdz_lights(thr36, in_dir36, runway_ref, runway_width, light_radius, tdzl_len)

        self._qa['lights'] = {
            'als_18': stats_18,
            'als_36': stats_36,
            'rwy': rwy_stats,
        }

        # Taxiway lights (blue, sparse demo)
        taxiways = self.real_geometry['taxiways']
        tw_light_count = 0

        for tw in taxiways[:5]:
            coords = tw['geometry']['local_coordinates']
            if len(coords) < 2:
                continue
            for i in range(min(3, len(coords))):
                point = coords[i]
                self._add_light_circle(point, light_radius * 0.9, 5, 'LGT_TWY_BLUE')
                tw_light_count += 1

        def fmt_range(minv, maxv):
            if minv is None or maxv is None:
                return "n/a"
            return f"{minv:.0f}-{maxv:.0f}m"

        print("    Lighting audit:")
        print(
            f"      ALS 18R: center={stats_18['als_center']} range={fmt_range(stats_18['als_center_min'], stats_18['als_center_max'])}, "
            f"barrettes={stats_18['als_barrette_groups']} groups, points={stats_18['als_barrette_points']} "
            f"lat={stats_18['als_barrette_lateral']}, "
            f"crossbar={stats_18['als_crossbar_present']} pts={stats_18['als_crossbar_points']} "
            f"total={stats_18['als_total']}, dupes={stats_18['als_dupe']}, inside_runway={stats_18['als_inside_runway']}, "
            f"pos={stats_18['als_bar_positions']} offsets={stats_18['als_crossbar_offsets']}"
        )
        print(
            f"      ALS 36L: center={stats_36['als_center']} range={fmt_range(stats_36['als_center_min'], stats_36['als_center_max'])}, "
            f"barrettes={stats_36['als_barrette_groups']} groups, points={stats_36['als_barrette_points']} "
            f"lat={stats_36['als_barrette_lateral']}, "
            f"crossbar={stats_36['als_crossbar_present']} pts={stats_36['als_crossbar_points']} "
            f"total={stats_36['als_total']}, dupes={stats_36['als_dupe']}, inside_runway={stats_36['als_inside_runway']}, "
            f"pos={stats_36['als_bar_positions']} offsets={stats_36['als_crossbar_offsets']}"
        )
        print(
            f"      ALS red side: 18R={stats_18['als_red_side']} range={fmt_range(stats_18['als_red_min'], stats_18['als_red_max'])}, "
            f"36L={stats_36['als_red_side']} range={fmt_range(stats_36['als_red_min'], stats_36['als_red_max'])}"
        )
        print(
            f"      THR lights: 18R={stats_18['thr']} offsets=({stats_18['thr_offset_min']:.1f},{stats_18['thr_offset_max']:.1f}), "
            f"36L={stats_36['thr']} offsets=({stats_36['thr_offset_min']:.1f},{stats_36['thr_offset_max']:.1f})"
        )
        print(
            f"      END lights: 18R={stats_18['end']}, 36L={stats_36['end']} "
            f"(red via bicolor inner halves)"
        )
        print(
            f"      EDGE lights: {rwy_stats['edge']} range={fmt_range(rwy_stats['edge_min'], rwy_stats['edge_max'])}, "
            f"offset=±{rwy_stats['edge_offset']:.1f}m, white={rwy_stats['edge_white']}, "
            f"yellow={rwy_stats['edge_yellow']}, outside={rwy_stats['edge_outside']}, dupe={rwy_stats['edge_dupe']}; "
            f"RCL lights: {rwy_stats['rcl']} range={fmt_range(rwy_stats['rcl_min'], rwy_stats['rcl_max'])}, "
            f"red={rwy_stats['rcl_red']}, white={rwy_stats['rcl_white']}, outside={rwy_stats['rcl_outside']}, "
            f"dupe={rwy_stats['rcl_dupe']}"
        )
        papi18 = stats_18['papi_base']
        papi36 = stats_36['papi_base']
        if papi18:
            print(
                f"      PAPI 18R: count={stats_18['papi']}, base=({papi18[0]:.2f}, {papi18[1]:.2f}), "
                f"lateral={stats_18['papi_lateral']:.1f}m, spacing={stats_18['papi_spacing']:.1f}m"
            )
        if papi36:
            print(
                f"      PAPI 36L: count={stats_36['papi']}, base=({papi36[0]:.2f}, {papi36[1]:.2f}), "
                f"lateral={stats_36['papi_lateral']:.1f}m, spacing={stats_36['papi_spacing']:.1f}m"
            )
        print(f"      Taxiway Lights: ~{tw_light_count} lights (blue dots, sparse demo)")
        print(f"    Total: Runway lights + threshold/end bicolor + taxiway lights")

    def _print_qa_summary(self, runway_width):
        print("\n QA summary:")
        width_ok = abs(runway_width - 50.0) <= 0.1
        print(f"  Runway width: {runway_width:.1f}m ({'OK' if width_ok else 'CHECK'})")

        aim = self._qa.get('aiming') or {}
        if aim:
            aim_ok = (
                abs(aim.get('bar_width', 0.0) - 6.0) < 1e-3
                and abs(aim.get('bar_length', 0.0) - 45.0) < 1e-3
                and abs(aim.get('center_offset', 0.0) - 13.0) < 1e-3
            )
            print(
                f"  Aiming point: {aim.get('bar_width', 0):.1f}x{aim.get('bar_length', 0):.1f}m, "
                f"offset={aim.get('center_offset', 0):.1f}m ({'OK' if aim_ok else 'CHECK'})"
            )

        cl = self._qa.get('centerline') or {}
        if cl:
            print(
                f"  Centerline: dash={cl.get('dash', 0):.1f} gap={cl.get('gap', 0):.1f} "
                f"cycle={cl.get('cycle', 0):.1f} segments={cl.get('segments', 0)}, "
                f"first={cl.get('first_block_distance', 0):.1f}m width={cl.get('block_width', 0):.1f}m"
            )

        tdz = self._qa.get('tdz') or {}
        for label in ('start', 'end'):
            info = tdz.get(label) or {}
            if info:
                positions = info.get('positions', [])
                if positions:
                    pos_range = f"{min(positions):.0f}-{max(positions):.0f}m"
                else:
                    pos_range = "n/a"
                print(
                    f"  TDZ {label}: groups={len(positions)}, bars/side={info.get('bars_per_side', 0)}, "
                    f"L={info.get('bar_length', 0):.1f} W={info.get('bar_width', 0):.1f}, "
                    f"range={pos_range}"
                )

        lights = self._qa.get('lights') or {}
        if lights:
            als_18 = lights.get('als_18') or {}
            als_36 = lights.get('als_36') or {}
            rwy = lights.get('rwy') or {}
            print(
                f"  APCH 18R: center={als_18.get('als_center', 0)}, barrettes={als_18.get('als_barrette_groups', 0)}, "
                f"crossbar={als_18.get('als_crossbar_present', False)}, dupes={als_18.get('als_dupe', 0)}"
            )
            print(
                f"  APCH 36L: center={als_36.get('als_center', 0)}, barrettes={als_36.get('als_barrette_groups', 0)}, "
                f"crossbar={als_36.get('als_crossbar_present', False)}, dupes={als_36.get('als_dupe', 0)}"
            )
            print(
                f"  ALS inside runway: 18R={als_18.get('als_inside_runway', 0)}, "
                f"36L={als_36.get('als_inside_runway', 0)}"
            )
            print(
                f"  RCL: red={rwy.get('rcl_red', 0)} "
                f"range={rwy.get('rcl_red_min', 0):.0f}-{rwy.get('rcl_red_max', 0):.0f}m; "
                f"white={rwy.get('rcl_white', 0)} "
                f"range={rwy.get('rcl_white_min', 0):.0f}-{rwy.get('rcl_white_max', 0):.0f}m; "
                f"all={rwy.get('rcl_min', 0):.0f}-{rwy.get('rcl_max', 0):.0f}m, "
                f"outside={rwy.get('rcl_outside', 0)}, dupe={rwy.get('rcl_dupe', 0)}"
            )
            print(
                f"  EDGE: yellow={rwy.get('edge_yellow', 0)} "
                f"range={rwy.get('edge_yellow_min', 0):.0f}-{rwy.get('edge_yellow_max', 0):.0f}m; "
                f"white={rwy.get('edge_white', 0)} "
                f"range={rwy.get('edge_white_min', 0):.0f}-{rwy.get('edge_white_max', 0):.0f}m; "
                f"all={rwy.get('edge_min', 0):.0f}-{rwy.get('edge_max', 0):.0f}m, "
                f"outside={rwy.get('edge_outside', 0)}, dupe={rwy.get('edge_dupe', 0)}"
            )
            if als_18.get('als_inside_runway', 0) > 0 or als_36.get('als_inside_runway', 0) > 0:
                print("  WARNING: ALS lights inside runway area detected")
            if rwy.get('rcl_outside', 0) > 0 or rwy.get('edge_outside', 0) > 0:
                print("  WARNING: Runway lights outside runway area detected")

        twy_edge = self._qa.get('twy_edge') or {}
        if twy_edge:
            print(
                f"  TWY edge: len={twy_edge.get('length_pre', 0):.1f}->{twy_edge.get('length_post', 0):.1f}m, "
                f"inside_pts={twy_edge.get('inside_points', 0)}"
            )
        twy_center = self._qa.get('twy_center') or {}
        if twy_center:
            print(
                f"  TWY center: len={twy_center.get('length_pre', 0):.1f}->{twy_center.get('length_post', 0):.1f}m, "
                f"inside_pts={twy_center.get('inside_points', 0)}, "
                f"merges={twy_center.get('merges', 0)}, snaps={twy_center.get('snaps', 0)}"
            )

    def add_title_block(self):
        """添加图框"""
        print("\n Adding title block...")
        
        """info_texts = [
            ("Beijing Capital International Airport", (-500, -500), 25),
            ("Runway 18R/36L - 课程设计CAD图纸", (-500, -550), 20),
            ("符合课件要求：跑道系统 + 滑行道系统 + 标志 + 灯光", (-500, -590), 15),
            ("Generated by IntegratedAirportCAD", (-500, -620), 12),
        ]
        
        for text, pos, height in info_texts:
            self.msp.add_text(
                text,
                dxfattribs={'layer': 'TITLE_BLOCK', 'height': height, 'color': 7}
            ).set_placement(pos, align=TextEntityAlignment. LEFT)"""
        
        print(f"   Title block added")
    
    def build(self):
        """构建完整图纸"""
        print("="*70)
        print("  BUILDING ZBAA 18R/36L CAD - 课件完全符合版")
        print("="*70)
        
        self.load_data()
        
        # 阶段1：基础几何
        print("\n" + "="*70)
        print(" STAGE 1: Real Geometry (课件标准)")
        print("="*70)
        
        runway_coords, runway_width = self.draw_runway_from_real_geometry()
        self.draw_taxiway_pavement(runway_coords)
        
        # 阶段2：跑道系统细节
        print("\n" + "="*70)
        print(" STAGE 2: Runway System Details (课件要求)")
        print("="*70)
        
        self.draw_runway_shoulder(runway_coords, runway_width)
        self.draw_runway_strip(runway_coords, runway_width)
        self.draw_resa(runway_coords, runway_width)
        self.draw_taxiway_edges(runway_coords)
        self.draw_taxiway_centerlines(runway_coords)
        self.draw_holding_position_markings(runway_coords)
        self.draw_runway_markings(runway_coords, runway_width)
        
        # 阶段3：灯光系统
        print("\n" + "="*70)
        print(" STAGE 3: Lighting Systems (课件要求)")
        print("="*70)
        
        self.draw_taxiway_signs(runway_coords, runway_width)
        self.draw_lighting_systems(runway_coords, runway_width)
        self._print_qa_summary(runway_width)
        
        self.add_title_block()
        
        print("\n" + "="*70)
        print(" BUILD COMPLETED - 课件完全符合版")
        print("="*70)
    
    def save(self, output_path:  str):
        """保存DXF文件"""
        print(f"\n Saving DXF...")
        
        os.makedirs(os.path. dirname(output_path), exist_ok=True)
        self. doc.saveas(output_path)
        
        file_size = os.path.getsize(output_path) / 1024
        
        print(f"   Saved to: {output_path}")
        print(f"   File size: {file_size:.1f} KB")
        
        # 图层统计
        print(f"\n CAD Statistics:")
        print(f"  Layers: {len(list(self.doc.layers))}")
        print(f"  Entities: ~{len(list(self.msp))}")


def main():
    """主函数"""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    print("\n" + "="*70)
    print(" ZBAA 18R/36L CAD GENERATOR - 课件完全符合版")
    print("="*70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_file = os.path.join(base_dir, 'runway_geometry.json')
    tables_file = os.path.join(base_dir, 'ZBAA_tables.json')
    output_dir = os.path.join(base_dir, 'output')
    output_file = os.path.join(output_dir, 'ZBAA_18R_36L_Final_CATI_v4.dxf')
    
    gen = IntegratedAirportCAD(geojson_file, tables_file)
    gen.build()
    gen.save(output_file)
    
    print("\n" + "="*70)
    print(" SUCCESS - 课件完全符合版生成完成!")
    print("="*70)
    print(f"\n 完成内容：")
    print(f"  • 跑道系统：50m道面 + 道肩 + 300m升降带(延伸60m) + RESA")
    print(f"  • 滑行道系统：C + P0-P9，P2-P7标注RET")
    print(f"  • 道面标志：编号 + 中心线 + TDZ + 瞄准点 + 等待位置")
    print(f"  • 灯光系统：PAPI + ALS + 说明文字")
    print(f"  • 图层：RWY/TWY/RET/STRIP/RESA/MARK/LIGHT/TEXT")
    print(f"\n Output:  {output_file}")
    print(f"\n Next:  Open in AutoCAD and verify all requirements!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
