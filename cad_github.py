"""
CAD Generator - AutoCAD 2018 DXF (R2010) Compatible
"""

import json
import math
import os
import re
from pathlib import Path
import ezdxf


class AirportRunwayDXFGenerator:
    """DXF generator for airport runway systems"""
    
    def __init__(self, geometry_file='runway_geometry.json'):
        self.geometry_file = geometry_file
        self.geometry_data = {}
        self.doc = None
        self.msp = None
        
        # ==================== 硬编码配置区域 ====================
        # 仅包含JSON中确实不存在的参数
        # 分类：CAD视觉参数、CAD布局参数、位置参数、几何辅助参数
        
        # --- CAD视觉参数（绘图效果）---
        self.EDGE_LIGHT_RADIUS = 1.5  # 跑道边灯绘图半径（米）
                                       # 用途：在CAD中显示边灯的圆圈大小
                                       # 原因：这是视觉表现参数，非实际物理尺寸，JSON中无此数据
        
        self.THRESHOLD_LIGHT_RADIUS = 1.0  # 入口灯绘图半径（米）
                                            # 用途：在CAD中显示入口灯的圆圈大小
                                            # 原因：视觉参数，比边灯略小便于区分，JSON中无此数据
        
        self.CENTERLINE_LIGHT_RADIUS = 0.8  # 中心线灯绘图半径（米）
                                             # 用途：在CAD中显示嵌入式灯光的圆圈大小
                                             # 原因：视觉参数，最小的圆圈便于区分，JSON中无此数据
        
        self.RUNWAY_NUMBER_HEIGHT = 30  # 跑道编号字体高度（米）
                                         # 用途：控制跑道上大号编号的显示大小
                                         # 原因：CAD文字显示参数，非实际标记尺寸，JSON中无此数据
        
        self.ANNOTATION_TITLE_HEIGHT = 25  # 标题文字高度（米）
                                            # 用途：控制图纸主标题的文字大小
                                            # 原因：CAD图纸排版参数，JSON中无此数据
        
        self.ANNOTATION_SUBTITLE_HEIGHT = 20  # 副标题文字高度（米）
                                               # 用途：控制跑道编号等副标题的文字大小
                                               # 原因：CAD图纸排版参数，JSON中无此数据
        
        self.ANNOTATION_TEXT_HEIGHT = 12  # 普通文字高度（米）
                                           # 用途：控制尺寸标注等普通信息的文字大小
                                           # 原因：CAD图纸排版参数，JSON中无此数据
        
        self.ANNOTATION_SMALL_TEXT_HEIGHT = 10  # 小号文字高度（米）
                                                 # 用途：控制详细信息的文字大小
                                                 # 原因：CAD图纸排版参数，JSON中无此数据
        
        self.LEGEND_TEXT_HEIGHT = 8  # 图例文字高度（米）
                                      # 用途：控制图例说明的文字大小
                                      # 原因：CAD图纸排版参数，最小的文字，JSON中无此数据
        
        # --- CAD布局参数（图纸排版）---
        self.ANNOTATION_X_OFFSET = -300  # 注释文字横向偏移（米）
                                          # 用途：将文字放置在跑道左侧区域
                                          # 原因：图纸布局需求，避免遮挡主图，JSON中无此数据
        
        self.ANNOTATION_Y_BASE = 100  # 注释文字纵向基准偏移（米）
                                       # 用途：控制注释区域相对跑道端的起始位置
                                       # 原因：图纸布局需求，JSON中无此数据
        
        self.LEGEND_X_OFFSET = 150  # 图例横向偏移（米）
                                     # 用途：将图例放置在跑道右侧区域
                                     # 原因：图纸布局需求，与注释对称分布，JSON中无此数据
        
        self.LEGEND_Y_START_OFFSET = -100  # 图例起始纵向偏移（米）
                                            # 用途：控制图例区域的起始纵向位置
                                            # 原因：图纸布局需求，JSON中无此数据
        
        self.LEGEND_LINE_SPACING = 25  # 图例行间距（米）
                                        # 用途：控制图例各项之间的垂直间距
                                        # 原因：图纸布局需求，确保可读性，JSON中无此数据
        
        # --- 位置参数（JSON中缺失的关键尺寸）---
        self.EDGE_LIGHT_OFFSET = 10  # 边灯距跑道边缘横向距离（米）
                                      # 用途：控制边灯的横向位置
                                      # 原因：JSON中未提供边灯偏移量，基于ICAO标准
        
        self.THRESHOLD_LIGHT_Y_OFFSET = 10  # 入口灯距跑道端纵向距离（米）
                                             # 用途：控制入口灯距离入口的位置
                                             # 原因：JSON中未提供此具体距离，基于ICAO标准
        
        self.RUNWAY_NUMBER_DISTANCE = 100  # 跑道编号距入口距离（米）
                                            # 用途：控制跑道编号在跑道上的纵向位置
                                            # 原因：JSON中未提供此距离，基于ICAO标准
        
        self.TDZ_MARKING_OFFSET = 10  # 接地区标记额外横向偏移（米）
                                       # 用途：控制接地区标记相对中心线的横向位置
                                       # 原因：JSON中仅提供宽度，未提供偏移量
        
        self.AIMING_POINT_OFFSET = 5  # 瞄准点额外横向偏移（米）
                                       # 用途：控制瞄准点矩形相对中心线的横向位置
                                       # 原因：JSON中仅提供宽度，未提供偏移量
        
        # --- 几何辅助参数 ---
        self.TAXIWAY_OFFSET_FALLBACK = 100  # 滑行道距跑道边缘的备用偏移（米）
                                             # 用途：当GPS坐标缺失或计算失败时使用
                                             # 原因：正常情况下从坐标精确计算，此值作为安全fallback
                                             # 注：基于GPS坐标反推，北京首都机场实际约100米
        
        self.AIMING_POINT_WIDTH = 10  # 瞄准点矩形宽度（米）
                                       # 用途：控制瞄准点矩形的实际绘制宽度
                                       # 原因：JSON中未提供此具体宽度参数
        
        self.RUNWAY_NUMBER_X_OFFSET = 15  # 跑道编号横向偏移（米）
                                           # 用途：控制跑道编号相对中心线的横向位置调整
                                           # 原因：用于居中对齐跑道编号文字，JSON中无此数据
        
        self.RUNWAY_NUMBER_36L_Y_ADJUSTMENT = 50  # 36L端跑道编号额外纵向调整（米）
                                                   # 用途：36L端编号需要额外向内调整以避免过于靠近边缘
                                                   # 原因：确保编号在合适位置，JSON中无此数据
        
        self.ANNOTATION_HEIGHT_ADJUSTMENT = 5  # 注释文字高度微调（米）
                                                # 用途：用于某些文字高度的微调以保持视觉和谐
                                                # 原因：CAD排版细节调整，JSON中无此数据
        
        # ==================== 硬编码配置区域结束 ====================
    
    def load_geometry(self):
        """Load geometry"""
        try:
            if Path(self.geometry_file).exists():
                with open(self.geometry_file, 'r', encoding='utf-8') as f:
                    self.geometry_data = json.load(f)
                print(f"✓ Loaded:  {self.geometry_file}")
                return True
            else:
                print(f"⚠ Using default configuration...")
                self._set_defaults()
                return True
        except Exception as e:
            print(f"✗ Error:  {e}")
            self._set_defaults()
            return False
    
    def _set_defaults(self):
        """Default config"""
        self.geometry_data = {
            'airport':  {'name': ''},
            'runway': {'designator': '18R/36L', 'length': 3800, 'width': 60}
        }
    
    def create_dxf(self):
        """Create DXF using R2010 format (best compatibility)"""
        print(f"\n📄 Creating DXF (R2010 - AutoCAD 2010+)...")
        
        try:
            # Use R2010 for best compatibility with AutoCAD 2018
            self.doc = ezdxf.new('R2010', setup=True)
            self.doc.header['$INSUNITS'] = 6  # meters
            self.msp = self.doc.modelspace()
            
            self._setup_layers()
            self._draw_runway()
            self._draw_taxiways()
            self._draw_markings()
            self._draw_lights()
            self._add_annotations()
            
            print("  ✓ DXF created")
            return True
            
        except Exception as e:
            print(f"✗ Error:  {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _setup_layers(self):
        """Setup layers"""
        layers = {
            'RUNWAY': 7,
            'TAXIWAYS': 7,
            'MARKINGS':  1,
            'RUNWAY_MARKINGS': 1,  # 跑道标记专用图层（白色）
            'LIGHTS': 3,
            'THRESHOLD_LIGHTS': 3,  # 入口灯（绿色）
            'END_LIGHTS': 1,  # 末端灯（红色）
            'CENTERLINE_LIGHTS': 2,  # 中心线灯（黄色）
            'RAPID_EXIT': 5,  # 快速出口滑行道（蓝色）
            'TEXT': 4
        }
        
        for name, color in layers.items():
            try:
                self.doc.layers.new(name=name, dxfattribs={'color': color})
            except: 
                pass  # Layer already exists
    
    def _draw_runway(self):
        """Draw runway - 绘制跑道主体"""
        try:
            # 直接从JSON读取数据，不使用默认值
            runway_dims = self.geometry_data['runwayDimensions']
            length = runway_dims['length']['meters']
            width = runway_dims['width']['meters']
            
            runway = self.geometry_data['runway']
            designator = runway['designator']
            
            # 从JSON读取侧边条纹偏移量
            side_stripes = self.geometry_data['runwayMarkings']['side_stripes']
            edge_offset = side_stripes['distance_from_edge']
            
            # 绘制跑道主体矩形
            points = [(0, 0), (width, 0), (width, length), (0, length)]
            pline = self.msp.add_lwpolyline(points, dxfattribs={'layer': 'RUNWAY'})
            pline.close()
            
            # 绘制跑道编号标记（18R和36L大字）
            cx = width / 2
            # 18R端编号（南端）
            self.msp.add_text(
                '18R',
                dxfattribs={
                    'layer': 'RUNWAY_MARKINGS',
                    'height': self.RUNWAY_NUMBER_HEIGHT,
                    'insert': (cx - self.RUNWAY_NUMBER_X_OFFSET, self.RUNWAY_NUMBER_DISTANCE),
                    'rotation': 0
                }
            )
            # 36L端编号（北端）
            self.msp.add_text(
                '36L',
                dxfattribs={
                    'layer': 'RUNWAY_MARKINGS',
                    'height': self.RUNWAY_NUMBER_HEIGHT,
                    'insert': (cx - self.RUNWAY_NUMBER_X_OFFSET, length - self.RUNWAY_NUMBER_DISTANCE - self.RUNWAY_NUMBER_36L_Y_ADJUSTMENT),
                    'rotation': 180
                }
            )
            
            # 绘制侧边条纹（使用JSON中的distance_from_edge值）
            # 左侧边条纹
            self.msp.add_line(
                (edge_offset, 0),
                (edge_offset, length),
                dxfattribs={'layer': 'RUNWAY_MARKINGS'}
            )
            # 右侧边条纹
            self.msp.add_line(
                (width - edge_offset, 0),
                (width - edge_offset, length),
                dxfattribs={'layer': 'RUNWAY_MARKINGS'}
            )
            
            print(f"  ✓ Runway: {length}m × {width}m ({designator})")
            
        except KeyError as e:
            print(f"  ✗ Error drawing runway: Missing required data - {e}")
            print(f"     Please check runway_geometry.json for required fields:")
            print(f"     - runwayDimensions.length.meters")
            print(f"     - runwayDimensions.width.meters")
            print(f"     - runway.designator")
            print(f"     - runwayMarkings.side_stripes.distance_from_edge")
            return
        except Exception as e:
            print(f"  ✗ Unexpected error in _draw_runway: {e}")
            return
    
    def _calculate_taxiway_offset_from_coordinates(self):
        """
        从GPS坐标精确计算滑行道与跑道的间距
        
        Returns:
            tuple: (offset_north, offset_south) 北侧和南侧滑行道的偏移距离（米）
                   如果计算失败，返回 (None, None)
        """
        try:
            # 读取跑道中心线坐标（使用18R端作为参考）
            runway_coords = self.geometry_data['runwayGeometry']['coordinates']['threshold_18R']
            runway_lat = runway_coords['latitude']
            
            # 读取滑行道A（北侧）坐标
            taxiway_north_coords = self.geometry_data['taxiways']['parallel_taxiway_north']['coordinates']['start']
            taxiway_north_lat = taxiway_north_coords['latitude']
            
            # 读取滑行道B（南侧）坐标
            taxiway_south_coords = self.geometry_data['taxiways']['parallel_taxiway_south']['coordinates']['start']
            taxiway_south_lat = taxiway_south_coords['latitude']
            
            # 计算纬度差（度）
            lat_diff_north = abs(taxiway_north_lat - runway_lat)
            lat_diff_south = abs(runway_lat - taxiway_south_lat)
            
            # 转换为米
            # 简化计算：1度纬度 ≈ 111,000米（在北京附近纬度40°时较准确）
            # 更精确的计算需要考虑地球椭球体，但对于机场尺度，这个精度足够
            METERS_PER_DEGREE_LAT = 111000
            
            offset_north = lat_diff_north * METERS_PER_DEGREE_LAT
            offset_south = lat_diff_south * METERS_PER_DEGREE_LAT
            
            print(f"  ℹ Calculated taxiway offsets from GPS coordinates:")
            print(f"     North (A): {offset_north:.1f}m")
            print(f"     South (B): {offset_south:.1f}m")
            
            return (offset_north, offset_south)
            
        except KeyError as e:
            print(f"  ⚠ Warning: Cannot calculate taxiway offset from coordinates - {e}")
            print(f"     Using fallback value: {self.TAXIWAY_OFFSET_FALLBACK}m")
            return (None, None)
        except Exception as e:
            print(f"  ⚠ Warning: Unexpected error calculating taxiway offset - {e}")
            return (None, None)
    
    def _draw_taxiways(self):
        """Draw taxiways - 绘制滑行道系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取滑行道数据
            taxiways = self.geometry_data['taxiways']
            
            # 从GPS坐标计算间距
            offset_north, offset_south = self._calculate_taxiway_offset_from_coordinates()
            
            # 如果计算失败，使用备用值
            if offset_north is None:
                offset_north = self.TAXIWAY_OFFSET_FALLBACK
                offset_south = self.TAXIWAY_OFFSET_FALLBACK
            
            # 平行滑行道A（北侧）- 使用计算出的偏移
            taxiway_a = taxiways['parallel_taxiway_north']
            tw_width = taxiway_a['width']
            
            # 计算滑行道A的中心线位置（用于快速出口连接）
            taxiway_a_center_x = w + offset_north + tw_width / 2
            
            pts_a = [(w + offset_north, 0), (w + offset_north + tw_width, 0), 
                     (w + offset_north + tw_width, l), (w + offset_north, l)]
            pline_a = self.msp.add_lwpolyline(pts_a, dxfattribs={'layer': 'TAXIWAYS'})
            pline_a.close()
            
            # 平行滑行道B（南侧）- 使用计算出的偏移
            taxiway_b = taxiways['parallel_taxiway_south']
            tw_width = taxiway_b['width']
            pts_b = [(-offset_south - tw_width, 0), (-offset_south, 0), 
                     (-offset_south, l), (-offset_south - tw_width, l)]
            pline_b = self.msp.add_lwpolyline(pts_b, dxfattribs={'layer': 'TAXIWAYS'})
            pline_b.close()
            
            # 快速出口滑行道（C, D, E）- 连接到平行滑行道A
            intermediate = taxiways['intermediate_taxiways']
            exit_count = 0
            
            for taxiway in intermediate:
                designator = taxiway['designator']
                if designator in ['C', 'D', 'E']:
                    # 解析起点位置（例如："1200m from 18R"）
                    start_str = taxiway['startPoint_along_runway']
                    if 'from 18R' in start_str:
                        distance = int(start_str.split('m')[0])
                    else:
                        continue
                    
                    angle = taxiway['angle']
                    width = taxiway['width']
                    
                    # 快速出口起点：跑道右侧边缘
                    start_x = w
                    start_y = distance
                    
                    # ✅ 新增：计算到滑行道A中心线的实际距离
                    distance_to_taxiway_center = taxiway_a_center_x - start_x
                    
                    # ✅ 新增：计算快速出口延伸到滑行道A的实际长度
                    # 实际长度 = 水平距离 / cos(angle)，适用于任意角度的快速出口
                    length_to_taxiway = distance_to_taxiway_center / math.cos(math.radians(angle))
                    
                    # ✅ 新增：使用JSON中的lengthToApron来决定是否继续延伸
                    # 从JSON读取每个滑行道的实际长度到停机坪
                    length_exit_original = taxiway['lengthToApron']  # C=400, D=450, E=500
                    
                    # 如果JSON中的长度大于到滑行道的距离，则继续延伸
                    if length_exit_original > length_to_taxiway:
                        # 延伸到JSON指定的长度（穿过滑行道A到停机坪）
                        length_exit = length_exit_original
                    else:
                        # 只延伸到滑行道A
                        length_exit = length_to_taxiway
                    
                    # 计算终点
                    end_x = start_x + length_exit * math.cos(math.radians(angle))
                    end_y = start_y + length_exit * math.sin(math.radians(angle))
                    
                    # 绘制快速出口滑行道的中心线区域（简化为平行四边形）
                    half_width = width / 2
                    dx = -half_width * math.sin(math.radians(angle))
                    dy = half_width * math.cos(math.radians(angle))
                    
                    pts_exit = [
                        (start_x + dx, start_y + dy),
                        (start_x - dx, start_y - dy),
                        (end_x - dx, end_y - dy),
                        (end_x + dx, end_y + dy)
                    ]
                    pline_exit = self.msp.add_lwpolyline(pts_exit, dxfattribs={'layer': 'RAPID_EXIT'})
                    pline_exit.close()
                    
                    # ✅ 新增：输出快速出口信息（用于验证连接正确性）
                    print(f"    - Exit {designator}: {distance}m, length={length_exit:.1f}m, reaches x={end_x:.1f}m")
                    
                    exit_count += 1
            
            print(f"  ✓ Taxiways A(offset:{offset_north:.1f}m), B(offset:{offset_south:.1f}m) + {exit_count} rapid exits")
            
        except KeyError as e:
            print(f"  ✗ Error drawing taxiways: Missing required data - {e}")
            print(f"     Please check runway_geometry.json for required fields:")
            print(f"     - taxiways.parallel_taxiway_north.width")
            print(f"     - taxiways.parallel_taxiway_south.width")
            print(f"     - taxiways.intermediate_taxiways[].lengthToApron")
            return
        except Exception as e:
            print(f"  ✗ Unexpected error in _draw_taxiways: {e}")
            return
    
    def _draw_markings(self):
        """Draw runway markings - 绘制跑道标记系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取标记数据
            markings = self.geometry_data['runwayMarkings']
            
            cx = w / 2  # 跑道中心线X坐标
            
            # 1. 入口标记（钢琴键图案）- Piano Key Pattern
            threshold = markings['threshold_markings']
            threshold_width = threshold['length_18R']
            stripe_width = threshold['dimensions']['width']
            stripe_spacing = threshold['dimensions']['spacing']
            
            # 计算条纹数量：跑道宽度 / (条纹宽度 + 间距)
            num_stripes = int(w / (stripe_width + stripe_spacing))
            
            # 18R端入口标记（0m位置）
            total_width = num_stripes * (stripe_width + stripe_spacing)
            start_x = cx - total_width / 2
            for i in range(num_stripes):
                x = start_x + i * (stripe_width + stripe_spacing)
                pts = [(x, 0), (x + stripe_width, 0), 
                       (x + stripe_width, threshold_width), (x, threshold_width)]
                pline = self.msp.add_lwpolyline(pts, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
            
            # 36L端入口标记（l位置）
            for i in range(num_stripes):
                x = start_x + i * (stripe_width + stripe_spacing)
                pts = [(x, l - threshold_width), (x + stripe_width, l - threshold_width), 
                       (x + stripe_width, l), (x, l)]
                pline = self.msp.add_lwpolyline(pts, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
            
            # 2. 中心线标记 - Centerline Markings
            centerline = markings['centerline_marking']
            dash_length = centerline['dashLength']
            gap_length = centerline['gapLength']
            
            y = 0
            while y < l:
                end_y = min(y + dash_length, l)
                self.msp.add_line(
                    (cx, y),
                    (cx, end_y),
                    dxfattribs={'layer': 'RUNWAY_MARKINGS'}
                )
                y = end_y + gap_length
            
            # 3. 接地区标记 - Touchdown Zone Markings
            tdz = markings['touchdown_zone_markings']
            zones = tdz['zones']
            spacing = tdz['spacing']
            start_dist = tdz['start_distance_from_threshold']
            zone_width = tdz['width_per_zone']
            zone_length = tdz['length_per_zone']
            
            # 使用之前获取的stripe_width作为标记宽度（即threshold标记的宽度）
            
            # 从18R端开始的接地区
            for i in range(zones):
                y_pos = start_dist + i * spacing
                if y_pos + zone_length <= l:
                    # 左侧标记
                    x_left = cx - zone_width / 2 - self.TDZ_MARKING_OFFSET
                    pts_left = [(x_left - stripe_width, y_pos), (x_left, y_pos),
                               (x_left, y_pos + zone_length), (x_left - stripe_width, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
                    
                    # 右侧标记
                    x_right = cx + zone_width / 2 + self.TDZ_MARKING_OFFSET
                    pts_right = [(x_right, y_pos), (x_right + stripe_width, y_pos),
                                (x_right + stripe_width, y_pos + zone_length), (x_right, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
            
            # 从36L端开始的接地区
            for i in range(zones):
                y_pos = l - start_dist - zone_length - i * spacing
                if y_pos >= 0:
                    # 左侧标记
                    x_left = cx - zone_width / 2 - self.TDZ_MARKING_OFFSET
                    pts_left = [(x_left - stripe_width, y_pos), (x_left, y_pos),
                               (x_left, y_pos + zone_length), (x_left - stripe_width, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
                    
                    # 右侧标记
                    x_right = cx + zone_width / 2 + self.TDZ_MARKING_OFFSET
                    pts_right = [(x_right, y_pos), (x_right + stripe_width, y_pos),
                                (x_right + stripe_width, y_pos + zone_length), (x_right, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
            
            # 4. 瞄准点标记 - Aiming Point Markings
            aiming = markings['aiming_point']
            aim_dist = aiming['distance_from_threshold']
            aim_width = aiming['width']
            aim_length = aiming['length']
            
            # 18R端瞄准点
            x_left = cx - aim_width / 2 - self.AIMING_POINT_OFFSET
            x_right = cx + aim_width / 2 + self.AIMING_POINT_OFFSET
            # 左侧矩形
            pts_aim_left = [(x_left - self.AIMING_POINT_WIDTH, aim_dist), (x_left, aim_dist),
                           (x_left, aim_dist + aim_length), (x_left - self.AIMING_POINT_WIDTH, aim_dist + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            # 右侧矩形
            pts_aim_right = [(x_right, aim_dist), (x_right + self.AIMING_POINT_WIDTH, aim_dist),
                            (x_right + self.AIMING_POINT_WIDTH, aim_dist + aim_length), (x_right, aim_dist + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            
            # 36L端瞄准点
            y_pos = l - aim_dist - aim_length
            # 左侧矩形
            pts_aim_left = [(x_left - self.AIMING_POINT_WIDTH, y_pos), (x_left, y_pos),
                           (x_left, y_pos + aim_length), (x_left - self.AIMING_POINT_WIDTH, y_pos + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            # 右侧矩形
            pts_aim_right = [(x_right, y_pos), (x_right + self.AIMING_POINT_WIDTH, y_pos),
                            (x_right + self.AIMING_POINT_WIDTH, y_pos + aim_length), (x_right, y_pos + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            
            print(f"  ✓ Markings: Threshold({num_stripes} stripes), Centerline, TDZ({zones} zones), Aiming points")
            
        except KeyError as e:
            print(f"  ✗ Error drawing markings: Missing required data - {e}")
            print(f"     Please check runway_geometry.json for required fields:")
            print(f"     - runwayMarkings.threshold_markings.dimensions.width")
            print(f"     - runwayMarkings.threshold_markings.dimensions.spacing")
            print(f"     - runwayMarkings.centerline_marking")
            print(f"     - runwayMarkings.touchdown_zone_markings")
            print(f"     - runwayMarkings.aiming_point")
            return
        except Exception as e:
            print(f"  ✗ Unexpected error in _draw_markings: {e}")
            return
    
    def _draw_lights(self):
        """Draw lighting systems - 绘制灯光系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取灯光系统数据
            lights = self.geometry_data['lightingSystems']
            
            # 1. 跑道边灯 - Runway Edge Lights
            edge_lights = lights['runway_edge_lights']
            edge_spacing = edge_lights['spacing']
            
            y = 0
            edge_count = 0
            while y <= l:
                # 左侧边灯
                self.msp.add_circle((-self.EDGE_LIGHT_OFFSET, y), self.EDGE_LIGHT_RADIUS, 
                                   dxfattribs={'layer': 'LIGHTS'})
                # 右侧边灯
                self.msp.add_circle((w + self.EDGE_LIGHT_OFFSET, y), self.EDGE_LIGHT_RADIUS, 
                                   dxfattribs={'layer': 'LIGHTS'})
                y += edge_spacing
                edge_count += 2
            
            # 2. 入口灯 - Threshold Lights（绿色）
            threshold_lights = lights['threshold_lights']
            th_rows = 2  # 2排
            th_cols = 6  # 每排6盏
            row_spacing = threshold_lights['rowSpacing']
            light_spacing = threshold_lights['lightSpacing']
            
            threshold_count = 0
            # 18R端入口灯（绿色）
            cx = w / 2
            start_x = cx - (th_cols - 1) * light_spacing / 2
            for row in range(th_rows):
                y_pos = -self.THRESHOLD_LIGHT_Y_OFFSET - row * row_spacing
                for col in range(th_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), self.THRESHOLD_LIGHT_RADIUS, 
                                       dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                    threshold_count += 1
            
            # 36L端入口灯（绿色）
            for row in range(th_rows):
                y_pos = l + self.THRESHOLD_LIGHT_Y_OFFSET + row * row_spacing
                for col in range(th_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), self.THRESHOLD_LIGHT_RADIUS,
                                       dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                    threshold_count += 1
            
            # 3. 末端灯 - End Lights（红色）
            end_lights = lights['end_lights']
            end_rows = 2  # 2排
            end_cols = 6  # 每排6盏
            
            end_count = 0
            # 18R端末端灯（红色）- 在跑道外侧
            for row in range(end_rows):
                y_pos = self.THRESHOLD_LIGHT_Y_OFFSET + row * row_spacing
                for col in range(end_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), self.THRESHOLD_LIGHT_RADIUS,
                                       dxfattribs={'layer': 'END_LIGHTS'})
                    end_count += 1
            
            # 36L端末端灯（红色）
            for row in range(end_rows):
                y_pos = l - self.THRESHOLD_LIGHT_Y_OFFSET - row * row_spacing
                for col in range(end_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), self.THRESHOLD_LIGHT_RADIUS,
                                       dxfattribs={'layer': 'END_LIGHTS'})
                    end_count += 1
            
            # 4. 中心线灯 - Centerline Lights（白色嵌入式）
            centerline_lights = lights['centerline_lights']
            cl_spacing = centerline_lights['spacing']
            
            y = 0
            centerline_count = 0
            while y <= l:
                self.msp.add_circle((cx, y), self.CENTERLINE_LIGHT_RADIUS,
                                   dxfattribs={'layer': 'CENTERLINE_LIGHTS'})
                y += cl_spacing
                centerline_count += 1
            
            total_lights = edge_count + threshold_count + end_count + centerline_count
            print(f"  ✓ Lights: Edge({edge_count}), Threshold({threshold_count}), End({end_count}), Centerline({centerline_count}) = Total({total_lights})")
            
        except KeyError as e:
            print(f"  ✗ Error drawing lights: Missing required data - {e}")
            print(f"     Please check runway_geometry.json for required fields:")
            print(f"     - lightingSystems.runway_edge_lights.spacing")
            print(f"     - lightingSystems.threshold_lights")
            print(f"     - lightingSystems.centerline_lights.spacing")
            return
        except Exception as e:
            print(f"  ✗ Unexpected error in _draw_lights: {e}")
            return
    
    def _add_annotations(self):
        """Add annotations - 添加文字注释"""
        try:
            runway = self.geometry_data['runway']
            airport = self.geometry_data['airport']
            runway_dims = self.geometry_data['runwayDimensions']
            
            # 获取完整机场信息
            airport_name = airport['name']
            icao = airport['icao']
            iata = airport['iata']
            designator = runway['designator']
            
            # 获取跑道尺寸
            length = runway_dims['length']['meters']
            width = runway_dims['width']['meters']
            length_feet = runway_dims['length']['feet']
            width_feet = runway_dims['width']['feet']
            
            # 主标题 - 使用JSON中的完整机场名称
            self.msp.add_text(
                airport_name,
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_TITLE_HEIGHT,
                    'insert': (self.ANNOTATION_X_OFFSET, length + self.ANNOTATION_Y_BASE)
                }
            )
            
            # ICAO和IATA代码
            self.msp.add_text(
                f"ICAO: {icao}  IATA: {iata}",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_SUBTITLE_HEIGHT - self.ANNOTATION_HEIGHT_ADJUSTMENT,
                    'insert': (self.ANNOTATION_X_OFFSET, length + self.ANNOTATION_Y_BASE - 40)
                }
            )
            
            # 跑道编号
            self.msp.add_text(
                f"Runway {designator}",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_SUBTITLE_HEIGHT,
                    'insert': (self.ANNOTATION_X_OFFSET, length + self.ANNOTATION_Y_BASE - 80)
                }
            )
            
            # 跑道尺寸标注
            self.msp.add_text(
                f"Dimensions: {length}m × {width}m",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_TEXT_HEIGHT,
                    'insert': (self.ANNOTATION_X_OFFSET, length - 20)
                }
            )
            
            # 跑道长度（英尺）
            self.msp.add_text(
                f"Length: {length}m ({length_feet}ft)",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_SMALL_TEXT_HEIGHT,
                    'insert': (self.ANNOTATION_X_OFFSET, length - 45)
                }
            )
            
            # 跑道宽度（英尺）
            self.msp.add_text(
                f"Width: {width}m ({width_feet}ft)",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_SMALL_TEXT_HEIGHT,
                    'insert': (self.ANNOTATION_X_OFFSET, length - 65)
                }
            )
            
            # 图例
            self.msp.add_text(
                "Legend:",
                dxfattribs={
                    'layer': 'TEXT',
                    'height': self.ANNOTATION_TEXT_HEIGHT,
                    'insert': (width + self.LEGEND_X_OFFSET, length + self.LEGEND_Y_START_OFFSET)
                }
            )
            
            legend_items = [
                "- Gray: Runway & Taxiways",
                "- White: Markings",
                "- Green: Threshold Lights",
                "- Red: End Lights",
                "- Yellow: Centerline Lights",
                "- Blue: Rapid Exit Taxiways"
            ]
            
            y_offset = length + self.LEGEND_Y_START_OFFSET - 30
            for item in legend_items:
                self.msp.add_text(
                    item,
                    dxfattribs={
                        'layer': 'TEXT',
                        'height': self.LEGEND_TEXT_HEIGHT,
                        'insert': (width + self.LEGEND_X_OFFSET, y_offset)
                    }
                )
                y_offset -= self.LEGEND_LINE_SPACING
            
            print(f"  ✓ Annotations: {airport_name} ({icao}/{iata})")
            
        except KeyError as e:
            print(f"  ✗ Error adding annotations: Missing required data - {e}")
            print(f"     Please check runway_geometry.json for required fields:")
            print(f"     - airport.name, airport.icao, airport.iata")
            print(f"     - runway.designator")
            print(f"     - runwayDimensions.length, runwayDimensions.width")
            return
        except Exception as e:
            print(f"  ✗ Unexpected error in _add_annotations: {e}")
            return
    
    def _normalize_output_name(self, filename):
        """Normalize and enforce .dxf extension for output filenames."""
        name = filename.strip()
        name = re.sub(r'\.\s+', '.', name)
        if not name:
            name = 'airport_runway_system_R2010.dxf'
        base, ext = os.path.splitext(name)
        if not ext:
            name = f"{base}.dxf"
        elif ext.lower() != '.dxf':
            if ext.lower() == '.dwg':
                print("⚠ DWG not supported, saving as DXF instead.")
            else:
                print("⚠ Non-DXF extension detected, saving as DXF instead.")
            name = f"{base}.dxf"
        while name.lower().endswith('.dxf.dxf'):
            name = name[:-4]
        return name

    def save_dxf(self, filename):
        """Save DXF file"""
        try:
            print(f"\n💾 Saving DXF...")
            self.doc.saveas(filename)
            
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"  ✓ Filename: {filename}")
                print(f"  ✓ Size: {size:,} bytes")
                print(f"  ✓ Format: DXF (R2010)")
                return True
            
            return False
        except Exception as e:
            print(f"✗ Error:  {e}")
            return False
    
    def generate(self, output):
        """Generate complete DXF"""
        output = self._normalize_output_name(output)
        print("\n" + "="*70)
        print("🏢 AIRPORT RUNWAY SYSTEM - DXF GENERATOR")
        print("="*70)
        print(f"📄 Format: DXF (R2010 - Best Compatibility)")
        print(f"🎯 AutoCAD 2010+")
        
        print("\n📂 Loading geometry...")
        self.load_geometry()
        
        print("\n🔨 Creating DXF...")
        if not self.create_dxf():
            return False
        
        print("\n💾 Saving file...")
        if not self.save_dxf(output):
            return False
        
        print("\n" + "="*70)
        print("✅ SUCCESS!")
        print("="*70)
        print(f"\n📁 File:  {output}")
        print(f"✓ Now try opening in AutoCAD 2018!\n")
        
        return True


def main():
    """Main entry point"""
    import sys

    base_path = os.path.dirname(__file__)
    geometry = os.path.join(base_path, 'runway_geometry.json')
    
    output = os.path.join(base_path, "output", "airport_runway_system_R2010.dxf")
    gen = AirportRunwayDXFGenerator(geometry)

    return 0 if gen.generate(output) else 1


if __name__ == '__main__':
    exit(main())