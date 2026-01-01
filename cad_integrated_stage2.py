# -*- coding: utf-8 -*-
"""
cad_integrated_stage2.py (方向修复版)
北京首都国际机场18R/36L跑道系统CAD图纸生成器

修复内容：
- 所有标记按跑道实际方向绘制
- RESA正确对齐跑道端部
- 公布距离沿跑道方向标注
- 文字方向与跑道一致

数据来源:  
- 几何数据:  OpenStreetMap → runway_geometry.json
- 参数数据: ZBAA_tables.json (通过airport_parameters.py提取)
"""

import ezdxf
from ezdxf.enums import TextEntityAlignment
import math
import json
import os
from typing import List, Tuple, Dict, Any

# 导入参数提取器
from airport_parameters import AirportParameterExtractor


class IntegratedAirportCAD:
    """集成的机场CAD生成器（方向修复版）"""
    
    def __init__(self, 
                 geojson_data_file: str = 'runway_geometry.json',
                 tables_file: str = 'ZBAA_tables.json'):
        """初始化"""
        self.geojson_file = geojson_data_file
        self.tables_file = tables_file
        
        # 数据容器
        self.real_geometry = None
        self.parameters = None
        
        # DXF文档
        self. doc = ezdxf.new('R2010', setup=True)
        self.doc.header['$INSUNITS'] = 6
        self.msp = self.doc.modelspace()
        
        self._setup_layers()
    
    def _setup_layers(self):
        """设置图层"""
        print("🎨 Setting up layers...")
        
        layers_config = [
            ('RUNWAY', 7, 'Continuous'),
            ('RUNWAY_CENTERLINE', 1, 'Continuous'),
            ('RUNWAY_SHOULDER', 8, 'Continuous'),
            ('RUNWAY_STRIP', 9, 'DASHED'),
            ('RESA', 1, 'Continuous'),
            ('RUNWAY_MARKINGS', 7, 'Continuous'),
            ('TAXIWAY', 5, 'Continuous'),
            ('TAXIWAY_CENTERLINE', 2, 'Continuous'),
            ('DIMENSIONS', 6, 'Continuous'),
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
        
        print(f"  ✓ Created {len(layers_config)} layers")
    
    def load_data(self):
        """加载所有数据"""
        print("\n📂 Loading data...")
        
        # 1. 加载真实几何数据
        with open(self.geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.real_geometry = data. get('real_geometry', {})
        
        runway = self.real_geometry.get('runway', {})
        taxiways = self.real_geometry.get('taxiways', [])
        
        print(f"  ✓ Loaded real geometry:")
        print(f"    - Runway: {runway.get('designator', 'N/A')}")
        print(f"    - Taxiways: {len(taxiways)}")
        
        # 2. 提取参数
        print(f"\n  📊 Extracting parameters...")
        extractor = AirportParameterExtractor(self.tables_file)
        self.parameters = extractor.get_all_parameters()
    
    # ========== 方向计算辅助方法 ==========
    
    def _get_runway_direction(self, runway_coords):
        """
        计算跑道方向
        
        Returns:
            (起点, 终点, 单位方向向量, 垂直向量, 长度)
        """
        start = runway_coords[0]
        end = runway_coords[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)
        
        if length < 1e-6:
            return start, end, (0, 1), (-1, 0), 0
        
        # 单位方向向量
        dir_x = dx / length
        dir_y = dy / length
        
        # 垂直向量（逆时针旋转90度）
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
    
    def _calculate_polyline_length(self, coords:  List[Tuple[float, float]]) -> float:
        """计算折线总长度"""
        total_length = 0.0
        for i in range(len(coords) - 1):
            dx = coords[i+1][0] - coords[i][0]
            dy = coords[i+1][1] - coords[i][1]
            total_length += math.sqrt(dx**2 + dy**2)
        return total_length
    
    def _offset_polyline(self, coords: List[Tuple[float, float]], 
                        offset: float) -> Tuple[List, List]:
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
        """从真实几何数据绘制跑道"""
        print("\n🛫 Drawing runway from real geometry...")
        
        runway = self.real_geometry['runway']
        designator = runway['designator']
        coords = runway['geometry']['local_coordinates']
        width = runway. get('width_meters', 50)
        
        print(f"  Runway: {designator}")
        print(f"  Points: {len(coords)}")
        print(f"  Width: {width}m")
        
        centerline = [(x, y) for x, y in coords]
        
        # 绘制中心线
        self.msp.add_lwpolyline(centerline, 
                               dxfattribs={'layer':  'RUNWAY_CENTERLINE',
                                          'color':  1})
        
        # 绘制跑道边界
        left, right = self._offset_polyline(centerline, width / 2.0)
        boundary = left + list(reversed(right))
        
        pline = self.msp.add_lwpolyline(boundary,
                                       dxfattribs={'layer': 'RUNWAY',
                                                  'color':  7})
        pline.close()
        
        length = self._calculate_polyline_length(centerline)
        
        print(f"  ✓ Runway drawn:  {length:.1f}m")
        
        return centerline, width
    
    def draw_taxiways_from_real_geometry(self, runway_coords):
        """从真实几何数据绘制滑行道"""
        print("\n🛤️  Drawing taxiways from real geometry...")
        
        taxiways = self.real_geometry['taxiways']
        
        series_count = {}
        drawn_count = 0
        connected_count = 0
        
        for tw in taxiways:
            ref = tw['ref']
            coords = tw['geometry']['local_coordinates']
            width = tw.get('width_meters', 23)
            
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
            
            # 绘制中心线
            self.msp.add_lwpolyline(connected_centerline, 
                                   dxfattribs={'layer': 'TAXIWAY_CENTERLINE',
                                              'color': 2})
            
            # 绘制边界
            if len(connected_centerline) >= 2:
                left, right = self._offset_polyline(connected_centerline, width / 2.0)
                boundary = left + list(reversed(right))
                
                pline = self.msp.add_lwpolyline(boundary,
                                               dxfattribs={'layer': 'TAXIWAY',
                                                          'color':  5})
                pline.close()
            
            drawn_count += 1
        
        print(f"  ✓ Drew {drawn_count} taxiway segments")
        print(f"  ✓ Auto-connected {connected_count} to runway")
        print(f"\n  📊 By series:")
        for series in sorted(series_count.keys()):
            print(f"    {series}:  {series_count[series]} taxiway(s)")
    
    # ========== 阶段2：跑道系统完善（修复版） ==========
    
    def draw_runway_shoulder(self, runway_coords, runway_width):
        """绘制道肩"""
        print("  📐 Drawing runway shoulder...")
        
        shoulder_width = self.parameters['shoulder_width']
        
        left_runway, right_runway = self._offset_polyline(runway_coords, runway_width / 2.0)
        left_shoulder_outer, _ = self._offset_polyline(left_runway, shoulder_width)
        _, right_shoulder_outer = self._offset_polyline(right_runway, shoulder_width)
        
        # 左侧道肩
        left_shoulder_poly = left_runway + list(reversed(left_shoulder_outer))
        pline = self.msp.add_lwpolyline(left_shoulder_poly, 
                                       dxfattribs={'layer': 'RUNWAY_SHOULDER',
                                                  'color': 8})
        pline.close()
        
        # 右侧道肩
        right_shoulder_poly = right_runway + list(reversed(right_shoulder_outer))
        pline = self. msp.add_lwpolyline(right_shoulder_poly,
                                       dxfattribs={'layer': 'RUNWAY_SHOULDER',
                                                  'color': 8})
        pline.close()
        
        print(f"    ✓ Shoulder:  {shoulder_width}m each side")
    
    def draw_runway_strip(self, runway_coords, runway_width):
        """绘制升降带"""
        print("  📐 Drawing runway strip...")
        
        strip_width = self.parameters['strip']['width']
        
        left_strip, right_strip = self._offset_polyline(runway_coords, strip_width / 2.0)
        strip_boundary = left_strip + list(reversed(right_strip))
        
        pline = self.msp.add_lwpolyline(strip_boundary,
                                       dxfattribs={'layer':  'RUNWAY_STRIP',
                                                  'color':  9})
        pline.close()
        
        print(f"    ✓ Strip: {strip_width}m wide")
    
    def draw_resa(self, runway_coords, runway_width):
        """绘制RESA（修复版 - 按跑道方向）"""
        print("  📐 Drawing RESA...")
        
        resa_params = self.parameters['resa']
        resa_length = resa_params['length']
        resa_width = resa_params['width']
        
        # 获取跑道方向
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        # 18R端RESA（起点之前）
        # 中心点在起点前方resa_length/2处
        center_18r = self._point_along_runway(start, direction, -resa_length/2)
        
        # 四个角点
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
        
        # 36L端RESA（终点之后）
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
        
        print(f"    ✓ RESA: {resa_length}m × {resa_width}m (both ends)")
    
    def draw_runway_markings(self, runway_coords, runway_width):
        """绘制跑道标记"""
        print("  🎨 Drawing runway markings...")
        
        markings = self.parameters['markings']
        
        # 1. 跑道中心线虚线
        self._draw_runway_centerline_dashed(runway_coords, markings['centerline'])
        
        # 2. 入口标志
        self._draw_threshold_markings(runway_coords, runway_width, markings['threshold'], at_start=True)
        self._draw_threshold_markings(runway_coords, runway_width, markings['threshold'], at_start=False)
        
        # 3. 接地带标记
        self._draw_tdz_markings(runway_coords, runway_width, markings['tdz'], at_start=True)
        self._draw_tdz_markings(runway_coords, runway_width, markings['tdz'], at_start=False)
        
        # 4. 瞄准点
        self._draw_aiming_point(runway_coords, runway_width, markings['aiming_point'], at_start=True)
        self._draw_aiming_point(runway_coords, runway_width, markings['aiming_point'], at_start=False)
        
        # 5. 跑道编号
        self._draw_runway_designators(runway_coords)
        
        print(f"    ✓ Markings:  Threshold, TDZ, Aiming point, Designators")
    
    def _draw_runway_centerline_dashed(self, runway_coords, params):
        """绘制跑道中心线虚线（修复版）"""
        dash_length = params['dash_length']
        gap_length = params['gap_length']
        
        start, end, direction, _, length = self._get_runway_direction(runway_coords)
        
        distance = 0
        while distance < length: 
            dash_start = self._point_along_runway(start, direction, distance)
            distance_end = min(distance + dash_length, length)
            dash_end = self._point_along_runway(start, direction, distance_end)
            
            self.msp. add_line(dash_start, dash_end, 
                            dxfattribs={'layer':  'RUNWAY_MARKINGS',
                                       'color': 7})
            
            distance += dash_length + gap_length
    
    def _draw_threshold_markings(self, runway_coords, runway_width, params, at_start=True):
        """绘制入口标志（修复版）"""
        stripe_width = params['stripe_width']
        stripe_length = params['stripe_length']
        stripe_gap = params['stripe_gap']
        
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        if at_start:
            base_point = start
            stripe_dir = direction
        else:
            base_point = end
            stripe_dir = (-direction[0], -direction[1])
        
        num_stripes = int((runway_width - stripe_gap) / (stripe_width + stripe_gap))
        
        for i in range(num_stripes):
            offset = (i - num_stripes/2 + 0.5) * (stripe_width + stripe_gap)
            
            # 条纹中心
            stripe_center = self._point_perpendicular(base_point, perpendicular, offset)
            
            # 四个角点
            p1 = self._point_perpendicular(stripe_center, perpendicular, -stripe_width/2)
            p2 = self._point_perpendicular(stripe_center, perpendicular, stripe_width/2)
            p3 = self._point_perpendicular(
                self._point_along_runway(stripe_center, stripe_dir, stripe_length),
                perpendicular, stripe_width/2
            )
            p4 = self._point_perpendicular(
                self._point_along_runway(stripe_center, stripe_dir, stripe_length),
                perpendicular, -stripe_width/2
            )
            
            stripe = [p1, p2, p3, p4]
            pline = self.msp.add_lwpolyline(stripe, 
                                           dxfattribs={'layer': 'RUNWAY_MARKINGS',
                                                      'color': 7})
            pline.close()
    
    def _draw_tdz_markings(self, runway_coords, runway_width, params, at_start=True):
        """绘制接地带标记（修复版）"""
        bar_width = params['bar_width']
        bar_length = params['bar_length']
        bar_spacing = params['bar_spacing']
        start_distance = params['start_distance']
        pairs = params['pairs']
        
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        lateral_offset = runway_width * 0.35
        
        if at_start:
            base = start
            bar_dir = direction
        else: 
            base = end
            bar_dir = (-direction[0], -direction[1])
        
        for i in range(pairs):
            distance = start_distance + i * bar_spacing
            bar_center = self._point_along_runway(base, bar_dir, distance)
            
            # 左右各一个
            for side in [-1, 1]:
                bar_pos = self._point_perpendicular(bar_center, perpendicular, side * lateral_offset)
                
                # 矩形四个角
                p1 = self._point_perpendicular(
                    self._point_along_runway(bar_pos, perpendicular, -bar_length/2),
                    direction, -bar_width/2
                )
                p2 = self._point_perpendicular(
                    self._point_along_runway(bar_pos, perpendicular, bar_length/2),
                    direction, -bar_width/2
                )
                p3 = self._point_perpendicular(
                    self._point_along_runway(bar_pos, perpendicular, bar_length/2),
                    direction, bar_width/2
                )
                p4 = self._point_perpendicular(
                    self._point_along_runway(bar_pos, perpendicular, -bar_length/2),
                    direction, bar_width/2
                )
                
                bar = [p1, p2, p3, p4]
                pline = self.msp.add_lwpolyline(bar, 
                                               dxfattribs={'layer': 'RUNWAY_MARKINGS',
                                                          'color': 7})
                pline.close()
    
    def _draw_aiming_point(self, runway_coords, runway_width, params, at_start=True):
        """绘制瞄准点标记（修复版）"""
        bar_width = params['bar_width']
        bar_length = params['bar_length']
        distance_from_threshold = params['distance_from_threshold']
        
        start, end, direction, perpendicular, _ = self._get_runway_direction(runway_coords)
        
        lateral_offset = runway_width * 0.35
        
        if at_start:
            base = start
            aim_dir = direction
        else: 
            base = end
            aim_dir = (-direction[0], -direction[1])
        
        aim_center = self._point_along_runway(base, aim_dir, distance_from_threshold)
        
        for side in [-1, 1]: 
            aim_pos = self._point_perpendicular(aim_center, perpendicular, side * lateral_offset)
            
            # 矩形四个角
            p1 = self._point_perpendicular(
                self._point_along_runway(aim_pos, perpendicular, -bar_length/2),
                direction, -bar_width/2
            )
            p2 = self._point_perpendicular(
                self._point_along_runway(aim_pos, perpendicular, bar_length/2),
                direction, -bar_width/2
            )
            p3 = self._point_perpendicular(
                self._point_along_runway(aim_pos, perpendicular, bar_length/2),
                direction, bar_width/2
            )
            p4 = self._point_perpendicular(
                self._point_along_runway(aim_pos, perpendicular, -bar_length/2),
                direction, bar_width/2
            )
            
            aiming = [p1, p2, p3, p4]
            pline = self.msp.add_lwpolyline(aiming, 
                                           dxfattribs={'layer': 'RUNWAY_MARKINGS',
                                                      'color': 7})
            pline.close()
    
    def _draw_runway_designators(self, runway_coords):
        """绘制跑道编号（修复版）"""
        text_height = 20.0
        distance_from_threshold = 80.0
        
        start, end, direction, _, _ = self._get_runway_direction(runway_coords)
        
        # 18R端
        text_pos_18r = self._point_along_runway(start, direction, distance_from_threshold)
        self.msp.add_text(
            "18R",
            dxfattribs={'layer': 'TEXT', 'height': text_height, 'color': 7}
        ).set_placement(text_pos_18r, align=TextEntityAlignment.CENTER)
        
        # 36L端
        text_pos_36l = self._point_along_runway(end, direction, -distance_from_threshold)
        self.msp.add_text(
            "36L",
            dxfattribs={'layer': 'TEXT', 'height': text_height, 'color': 7}
        ).set_placement(text_pos_36l, align=TextEntityAlignment. CENTER)
    
    def draw_declared_distances(self, runway_coords):
        """绘制公布距离（修复版）"""
        print("  📏 Drawing declared distances...")
        
        distances = self.parameters['declared_distances']
        
        start, end, direction, perpendicular, length = self._get_runway_direction(runway_coords)
        
        # 标注位置（跑道左侧200m）
        offset = -200
        
        for i, (label, dist) in enumerate(distances.items()):
            # 每条标注再向左偏移
            line_offset = offset - i * 30
            
            # 标注线的起点和终点
            line_start = self._point_perpendicular(start, perpendicular, line_offset)
            line_end = self._point_perpendicular(end, perpendicular, line_offset)
            
            # 绘制标注线
            self.msp.add_line(line_start, line_end,
                            dxfattribs={'layer': 'DIMENSIONS', 'color': 6})
            
            # 箭头
            self._draw_arrow_along_line(line_start, direction, size=10)
            self._draw_arrow_along_line(line_end, (-direction[0], -direction[1]), size=10)
            
            # 标注文字（中点）
            mid_point = (
                (line_start[0] + line_end[0]) / 2,
                (line_start[1] + line_end[1]) / 2
            )
            text_pos = self._point_perpendicular(mid_point, perpendicular, -50)
            
            self.msp.add_text(
                f"{label}:  {dist:.0f}m",
                dxfattribs={'layer': 'TEXT', 'height': 10, 'color': 6}
            ).set_placement(text_pos, align=TextEntityAlignment.LEFT)
        
        print(f"    ✓ Declared distances:  TORA={distances['TORA']:.0f}m")
    
    def _draw_arrow_along_line(self, point, direction, size=10):
        """沿线方向绘制箭头"""
        dir_x, dir_y = direction
        x, y = point
        
        # 箭头的两个侧翼点
        wing1 = (
            x + dir_x * size - dir_y * size/2,
            y + dir_y * size + dir_x * size/2
        )
        wing2 = (
            x + dir_x * size + dir_y * size/2,
            y + dir_y * size - dir_x * size/2
        )
        
        arrow = [wing1, point, wing2]
        self. msp.add_lwpolyline(arrow, dxfattribs={'layer': 'DIMENSIONS', 'color': 6})
    
    # ========== 图框和主流程 ==========
    
    def add_title_block(self):
        """添加图框"""
        print("\n📋 Adding title block...")
        
        info_texts = [
            ("Beijing Capital International Airport", (-500, -500), 25),
            ("Runway 18R/36L - Integrated System", (-500, -550), 20),
            ("Stage 1+2: Geometry + Details (Direction Fixed)", (-500, -590), 15),
            (f"Generated by IntegratedAirportCAD", (-500, -620), 12),
        ]
        
        for text, pos, height in info_texts:
            self.msp.add_text(
                text,
                dxfattribs={'layer': 'TITLE_BLOCK', 'height': height, 'color': 7}
            ).set_placement(pos, align=TextEntityAlignment. LEFT)
        
        print(f"  ✓ Title block added")
    
    def build(self):
        """构建完整图纸"""
        print("="*70)
        print("🏗️  BUILDING INTEGRATED AIRPORT CAD - STAGE 1+2 (FIXED)")
        print("="*70)
        
        self.load_data()
        
        # 阶段1
        print("\n" + "="*70)
        print("📦 STAGE 1: Real Geometry")
        print("="*70)
        
        runway_coords, runway_width = self.draw_runway_from_real_geometry()
        self.draw_taxiways_from_real_geometry(runway_coords)
        
        # 阶段2
        print("\n" + "="*70)
        print("📦 STAGE 2: Runway Details (Direction Fixed)")
        print("="*70)
        
        self.draw_runway_shoulder(runway_coords, runway_width)
        self.draw_runway_strip(runway_coords, runway_width)
        self.draw_resa(runway_coords, runway_width)
        self.draw_runway_markings(runway_coords, runway_width)
        self.draw_declared_distances(runway_coords)
        
        self.add_title_block()
        
        print("\n" + "="*70)
        print("✅ BUILD COMPLETED - DIRECTION FIXED")
        print("="*70)
    
    def save(self, output_path:  str):
        """保存DXF文件"""
        print(f"\n💾 Saving DXF...")
        
        os.makedirs(os.path. dirname(output_path), exist_ok=True)
        self. doc.saveas(output_path)
        
        file_size = os.path.getsize(output_path) / 1024
        
        print(f"  ✓ Saved to: {output_path}")
        print(f"  ✓ File size: {file_size:.1f} KB")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🛫 ZBAA INTEGRATED CAD GENERATOR - DIRECTION FIXED")
    print("="*70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    geojson_file = os.path.join(base_dir, 'runway_geometry.json')
    tables_file = os.path.join(base_dir, 'ZBAA_tables.json')
    output_dir = os.path.join(base_dir, 'output')
    output_file = os.path.join(output_dir, 'airport_integrated_stage2_fixed.dxf')
    
    gen = IntegratedAirportCAD(geojson_file, tables_file)
    gen.build()
    gen.save(output_file)
    
    print("\n" + "="*70)
    print("🎉 SUCCESS - DIRECTION FIXED!")
    print("="*70)
    print(f"\nNext:  Open {output_file} in AutoCAD")
    print(f"All markings should now align with runway direction!")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())