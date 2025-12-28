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
        # 以下参数未在JSON中提供，需要硬编码
        # 这些参数主要用于CAD图纸的视觉效果和布局
        
        # --- 滑行道布局参数 ---
        self.TAXIWAY_OFFSET = 100  # 平行滑行道距跑道边缘的距离（米）
                                    # 用途：控制滑行道A和B的横向位置
                                    # 原因：JSON中未提供滑行道与跑道的间距数据
        
        self.RAPID_EXIT_LENGTH = 400  # 快速出口滑行道延伸长度（米）
                                       # 用途：确定快速出口滑行道从跑道延伸到停机坪的长度
                                       # 原因：JSON中有lengthToApron字段(400-500m)，但为了统一使用固定值
        
        # --- 跑道标记布局参数 ---
        self.EDGE_STRIPE_OFFSET = 5  # 侧边条纹距跑道边缘的距离（米）
                                      # 用途：绘制跑道两侧的白色边界线
                                      # 原因：ICAO标准规定距边缘5米，JSON中未重复此标准值
        
        self.THRESHOLD_STRIPES_COUNT = 10  # 入口标记（钢琴键）的条纹数量
                                            # 用途：确定18R和36L端入口标记的条纹数
                                            # 原因：JSON中未明确指定条纹数量，使用ICAO标准值
        
        # --- 灯光布局参数 ---
        self.EDGE_LIGHT_OFFSET = 10  # 跑道边灯距跑道边缘的横向距离（米）
                                      # 用途：控制边灯的横向位置（跑道外侧）
                                      # 原因：JSON中未提供边灯的精确横向偏移量
        
        self.EDGE_LIGHT_RADIUS = 1.5  # 跑道边灯的绘图半径（米）
                                       # 用途：在CAD图纸中显示灯光的圆圈大小
                                       # 原因：这是CAD视觉表现参数，非实际物理尺寸
        
        self.THRESHOLD_LIGHT_RADIUS = 1.0  # 入口灯的绘图半径（米）
                                            # 用途：在CAD图纸中显示入口灯的圆圈大小
                                            # 原因：比边灯略小，便于区分
        
        self.CENTERLINE_LIGHT_RADIUS = 0.8  # 中心线灯的绘图半径（米）
                                             # 用途：在CAD图纸中显示中心线灯的圆圈大小
                                             # 原因：嵌入式灯光，绘制更小的圆圈
        
        self.THRESHOLD_LIGHT_Y_OFFSET = 10  # 入口灯距跑道入口的纵向偏移（米）
                                             # 用途：控制入口灯在跑道外的纵向位置
                                             # 原因：入口灯位于跑道端外侧，JSON未提供精确距离
        
        # --- 文字注释布局参数 ---
        self.ANNOTATION_X_OFFSET = -300  # 注释文字距跑道左侧的横向偏移（米）
                                          # 用途：将标题、机场信息等文字放置在跑道左侧
                                          # 原因：CAD图纸布局需求，避免遮挡跑道图形
        
        self.ANNOTATION_Y_BASE = 100  # 注释文字距跑道北端的基准纵向偏移（米）
                                       # 用途：控制标题文字的垂直位置（跑道上方）
                                       # 原因：CAD图纸布局需求
        
        self.LEGEND_X_OFFSET = 150  # 图例距跑道右侧的横向偏移（米）
                                     # 用途：将图例放置在跑道右侧
                                     # 原因：CAD图纸布局需求，图例应在明显位置
        
        # --- 跑道编号标记位置参数 ---
        self.RUNWAY_NUMBER_DISTANCE = 100  # 跑道编号文字距入口的距离（米）
                                            # 用途：控制"18R"和"36L"大字的位置
                                            # 原因：ICAO标准位置，JSON中未提供
        
        self.RUNWAY_NUMBER_HEIGHT = 30  # 跑道编号文字的高度（米）
                                         # 用途：控制跑道编号的字体大小
                                         # 原因：CAD视觉效果参数
        
        # --- 接地区标记布局参数 ---
        self.TDZ_MARKING_OFFSET = 10  # 接地区标记距中心线的横向偏移（米）
                                       # 用途：控制接地区矩形标记离中心线的距离
                                       # 原因：ICAO标准布局，JSON中未详细定义
        
        self.TDZ_MARKING_WIDTH = 3  # 接地区标记矩形的宽度（米）
                                     # 用途：控制接地区条纹的粗细
                                     # 原因：标准值，JSON中未提供
        
        # --- 瞄准点标记布局参数 ---
        self.AIMING_POINT_OFFSET = 5  # 瞄准点矩形距中心线的基准偏移（米）
                                       # 用途：控制瞄准点标记的横向位置
                                       # 原因：基于跑道宽度的标准布局
        
        self.AIMING_POINT_WIDTH = 10  # 瞄准点矩形的宽度（米）
                                       # 用途：控制瞄准点标记的粗细
                                       # 原因：ICAO标准值，JSON中未提供
        
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
            # 直接从JSON读取，不使用默认值
            runway_dims = self.geometry_data['runwayDimensions']
            length = runway_dims['length']['meters']
            width = runway_dims['width']['meters']
            runway = self.geometry_data['runway']
            designator = runway['designator']
        except KeyError as e:
            print(f"  ⚠ Warning: Missing required runway data - {e}")
            print(f"  ✗ Skipping runway drawing due to missing data")
            return
        
        # 绘制跑道主体矩形
        points = [(0, 0), (width, 0), (width, length), (0, length)]
        pline = self.msp.add_lwpolyline(points, dxfattribs={'layer': 'RUNWAY'})
        pline.close()
        
        # 绘制跑道编号标记（18R和36L大字）- 使用配置常量
        cx = width / 2
        # 18R端编号（南端）
        self.msp.add_text(
            '18R',
            dxfattribs={
                'layer': 'RUNWAY_MARKINGS',
                'height': self.RUNWAY_NUMBER_HEIGHT,
                'insert': (cx - 15, self.RUNWAY_NUMBER_DISTANCE),
                'rotation': 0
            }
        )
        # 36L端编号（北端）
        self.msp.add_text(
            '36L',
            dxfattribs={
                'layer': 'RUNWAY_MARKINGS',
                'height': self.RUNWAY_NUMBER_HEIGHT,
                'insert': (cx - 15, length - self.RUNWAY_NUMBER_DISTANCE - 50),
                'rotation': 180
            }
        )
        
        # 绘制侧边条纹（距边缘的连续白线）- 使用配置常量
        edge_offset = self.EDGE_STRIPE_OFFSET
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
    
    def _draw_taxiways(self):
        """Draw taxiways - 绘制滑行道系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取滑行道数据
            taxiways = self.geometry_data['taxiways']
        except KeyError as e:
            print(f"  ⚠ Warning: Missing taxiway data - {e}")
            print(f"  ✗ Skipping taxiways drawing")
            return
        
        # 平行滑行道A（北侧）- 使用配置常量和JSON数据
        try:
            taxiway_a = taxiways['parallel_taxiway_north']
            tw_width = taxiway_a['width']
            offset_a = self.TAXIWAY_OFFSET  # 使用配置常量
            pts_a = [(w + offset_a, 0), (w + offset_a + tw_width, 0), 
                     (w + offset_a + tw_width, l), (w + offset_a, l)]
            pline_a = self.msp.add_lwpolyline(pts_a, dxfattribs={'layer': 'TAXIWAYS'})
            pline_a.close()
        except KeyError as e:
            print(f"  ⚠ Warning: Missing parallel_taxiway_north data - {e}")
        
        # 平行滑行道B（南侧）- 使用配置常量和JSON数据
        try:
            taxiway_b = taxiways['parallel_taxiway_south']
            tw_width = taxiway_b['width']
            offset_b = self.TAXIWAY_OFFSET  # 使用配置常量
            pts_b = [(-offset_b - tw_width, 0), (-offset_b, 0), 
                     (-offset_b, l), (-offset_b - tw_width, l)]
            pline_b = self.msp.add_lwpolyline(pts_b, dxfattribs={'layer': 'TAXIWAYS'})
            pline_b.close()
        except KeyError as e:
            print(f"  ⚠ Warning: Missing parallel_taxiway_south data - {e}")
        
        # 快速出口滑行道（C, D, E）- 使用JSON中的数据和配置常量
        try:
            intermediate = taxiways['intermediate_taxiways']
            exit_count = 0
            
            for taxiway in intermediate:
                try:
                    designator = taxiway['designator']
                    if designator in ['C', 'D', 'E']:
                        # 解析起点位置
                        start_str = taxiway['startPoint_along_runway']
                        if 'from 18R' in start_str:
                            distance = int(start_str.split('m')[0])
                        else:
                            continue
                        
                        angle = taxiway['angle']
                        width = taxiway['width']
                        
                        # 绘制快速出口滑行道（简化为直线）
                        start_x = w
                        start_y = distance
                        
                        # 使用配置常量
                        length_exit = self.RAPID_EXIT_LENGTH
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
                        exit_count += 1
                except KeyError as e:
                    print(f"  ⚠ Warning: Missing data for taxiway {designator} - {e}")
                    continue
            
            print(f"  ✓ Taxiways A, B + {exit_count} rapid exits (C, D, E)")
        except KeyError as e:
            print(f"  ⚠ Warning: Missing intermediate_taxiways data - {e}")
            print(f"  ✓ Taxiways A, B drawn")
    
    def _draw_markings(self):
        """Draw runway markings - 绘制跑道标记系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取标记数据
            markings = self.geometry_data['runwayMarkings']
        except KeyError as e:
            print(f"  ⚠ Warning: Missing runway markings data - {e}")
            print(f"  ✗ Skipping markings drawing")
            return
        
        cx = w / 2  # 跑道中心线X坐标
        
        # 1. 入口标记（钢琴键图案）- Piano Key Pattern
        try:
            threshold = markings['threshold_markings']
            threshold_width = threshold['length_18R']
            stripe_width = threshold['dimensions']['width']
            stripe_spacing = threshold['dimensions']['spacing']
            
            # 使用配置常量
            num_stripes = self.THRESHOLD_STRIPES_COUNT
            total_width = num_stripes * (stripe_width + stripe_spacing)
            start_x = cx - total_width / 2
            
            # 18R端入口标记（0m位置）
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
        except KeyError as e:
            print(f"  ⚠ Warning: Missing threshold_markings data - {e}")
        
        # 2. 中心线标记 - Centerline Markings
        try:
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
        except KeyError as e:
            print(f"  ⚠ Warning: Missing centerline_marking data - {e}")
        
        # 3. 接地区标记 - Touchdown Zone Markings
        try:
            tdz = markings['touchdown_zone_markings']
            zones = tdz['zones']
            spacing = tdz['spacing']
            start_dist = tdz['start_distance_from_threshold']
            zone_width = tdz['width_per_zone']
            zone_length = tdz['length_per_zone']
            
            # 使用配置常量
            offset_from_center = self.TDZ_MARKING_OFFSET
            marking_width = self.TDZ_MARKING_WIDTH
            
            # 从18R端开始的接地区
            for i in range(zones):
                y_pos = start_dist + i * spacing
                if y_pos + zone_length <= l:
                    # 左侧标记
                    x_left = cx - zone_width / 2 - offset_from_center
                    pts_left = [(x_left - marking_width, y_pos), (x_left, y_pos),
                               (x_left, y_pos + zone_length), (x_left - marking_width, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
                    
                    # 右侧标记
                    x_right = cx + zone_width / 2 + offset_from_center
                    pts_right = [(x_right, y_pos), (x_right + marking_width, y_pos),
                                (x_right + marking_width, y_pos + zone_length), (x_right, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
            
            # 从36L端开始的接地区
            for i in range(zones):
                y_pos = l - start_dist - zone_length - i * spacing
                if y_pos >= 0:
                    # 左侧标记
                    x_left = cx - zone_width / 2 - offset_from_center
                    pts_left = [(x_left - marking_width, y_pos), (x_left, y_pos),
                               (x_left, y_pos + zone_length), (x_left - marking_width, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
                    
                    # 右侧标记
                    x_right = cx + zone_width / 2 + offset_from_center
                    pts_right = [(x_right, y_pos), (x_right + marking_width, y_pos),
                                (x_right + marking_width, y_pos + zone_length), (x_right, y_pos + zone_length)]
                    pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                    pline.close()
        except KeyError as e:
            print(f"  ⚠ Warning: Missing touchdown_zone_markings data - {e}")
        
        # 4. 瞄准点标记 - Aiming Point Markings
        try:
            aiming = markings['aiming_point']
            aim_dist = aiming['distance_from_threshold']
            aim_width = aiming['width']
            aim_length = aiming['length']
            
            # 使用配置常量
            offset_from_center = self.AIMING_POINT_OFFSET
            marking_width = self.AIMING_POINT_WIDTH
            
            # 18R端瞄准点
            x_left = cx - aim_width / 2 - offset_from_center
            x_right = cx + aim_width / 2 + offset_from_center
            # 左侧矩形
            pts_aim_left = [(x_left - marking_width, aim_dist), (x_left, aim_dist),
                           (x_left, aim_dist + aim_length), (x_left - marking_width, aim_dist + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            # 右侧矩形
            pts_aim_right = [(x_right, aim_dist), (x_right + marking_width, aim_dist),
                            (x_right + marking_width, aim_dist + aim_length), (x_right, aim_dist + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            
            # 36L端瞄准点
            y_pos = l - aim_dist - aim_length
            # 左侧矩形
            pts_aim_left = [(x_left - marking_width, y_pos), (x_left, y_pos),
                           (x_left, y_pos + aim_length), (x_left - marking_width, y_pos + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            # 右侧矩形
            pts_aim_right = [(x_right, y_pos), (x_right + marking_width, y_pos),
                            (x_right + marking_width, y_pos + aim_length), (x_right, y_pos + aim_length)]
            pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
            pline.close()
            
            print(f"  ✓ Markings: Threshold, Centerline, TDZ ({zones} zones), Aiming points")
        except KeyError as e:
            print(f"  ⚠ Warning: Missing aiming_point data - {e}")
            print(f"  ✓ Markings: Threshold, Centerline, TDZ (partial)")
    
    def _draw_lights(self):
        """Draw lighting systems - 绘制灯光系统"""
        try:
            # 获取跑道尺寸
            runway_dims = self.geometry_data['runwayDimensions']
            l = runway_dims['length']['meters']
            w = runway_dims['width']['meters']
            
            # 从JSON获取灯光系统数据
            lights = self.geometry_data['lightingSystems']
        except KeyError as e:
            print(f"  ⚠ Warning: Missing lighting systems data - {e}")
            print(f"  ✗ Skipping lights drawing")
            return
        
        cx = w / 2  # 跑道中心线X坐标
        
        # 1. 跑道边灯 - Runway Edge Lights
        try:
            edge_lights = lights['runway_edge_lights']
            edge_spacing = edge_lights['spacing']
            
            y = 0
            edge_count = 0
            # 使用配置常量
            light_offset = self.EDGE_LIGHT_OFFSET
            light_radius = self.EDGE_LIGHT_RADIUS
            
            while y <= l:
                # 左侧边灯
                self.msp.add_circle((-light_offset, y), light_radius, dxfattribs={'layer': 'LIGHTS'})
                # 右侧边灯
                self.msp.add_circle((w + light_offset, y), light_radius, dxfattribs={'layer': 'LIGHTS'})
                y += edge_spacing
                edge_count += 2
        except KeyError as e:
            print(f"  ⚠ Warning: Missing runway_edge_lights data - {e}")
            edge_count = 0
        
        # 2. 入口灯 - Threshold Lights（绿色）
        try:
            threshold_lights = lights['threshold_lights']
            row_spacing = threshold_lights['rowSpacing']
            light_spacing = threshold_lights['lightSpacing']
            
            # 使用配置常量
            th_radius = self.THRESHOLD_LIGHT_RADIUS
            th_offset = self.THRESHOLD_LIGHT_Y_OFFSET
            
            th_rows = 2  # 2排
            th_cols = 6  # 每排6盏
            
            threshold_count = 0
            # 18R端入口灯（绿色）
            start_x = cx - (th_cols - 1) * light_spacing / 2
            for row in range(th_rows):
                y_pos = -th_offset - row * row_spacing
                for col in range(th_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), th_radius, 
                                       dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                    threshold_count += 1
            
            # 36L端入口灯（绿色）
            for row in range(th_rows):
                y_pos = l + th_offset + row * row_spacing
                for col in range(th_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), th_radius,
                                       dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                    threshold_count += 1
        except KeyError as e:
            print(f"  ⚠ Warning: Missing threshold_lights data - {e}")
            threshold_count = 0
        
        # 3. 末端灯 - End Lights（红色）
        try:
            end_lights = lights['end_lights']
            row_spacing = end_lights['rowSpacing']
            light_spacing = end_lights['lightSpacing']
            
            # 使用配置常量
            end_radius = self.THRESHOLD_LIGHT_RADIUS
            end_offset = self.THRESHOLD_LIGHT_Y_OFFSET
            
            end_rows = 2  # 2排
            end_cols = 6  # 每排6盏
            
            end_count = 0
            # 18R端末端灯（红色）- 在跑道外侧
            start_x = cx - (end_cols - 1) * light_spacing / 2
            for row in range(end_rows):
                y_pos = end_offset + row * row_spacing
                for col in range(end_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), end_radius,
                                       dxfattribs={'layer': 'END_LIGHTS'})
                    end_count += 1
            
            # 36L端末端灯（红色）
            for row in range(end_rows):
                y_pos = l - end_offset - row * row_spacing
                for col in range(end_cols):
                    x_pos = start_x + col * light_spacing
                    self.msp.add_circle((x_pos, y_pos), end_radius,
                                       dxfattribs={'layer': 'END_LIGHTS'})
                    end_count += 1
        except KeyError as e:
            print(f"  ⚠ Warning: Missing end_lights data - {e}")
            end_count = 0
        
        # 4. 中心线灯 - Centerline Lights（白色嵌入式）
        try:
            centerline_lights = lights['centerline_lights']
            cl_spacing = centerline_lights['spacing']
            
            # 使用配置常量
            cl_radius = self.CENTERLINE_LIGHT_RADIUS
            
            y = 0
            centerline_count = 0
            while y <= l:
                self.msp.add_circle((cx, y), cl_radius,
                                   dxfattribs={'layer': 'CENTERLINE_LIGHTS'})
                y += cl_spacing
                centerline_count += 1
        except KeyError as e:
            print(f"  ⚠ Warning: Missing centerline_lights data - {e}")
            centerline_count = 0
        
        total_lights = edge_count + threshold_count + end_count + centerline_count
        if total_lights > 0:
            print(f"  ✓ Lights: Edge({edge_count}), Threshold({threshold_count}), End({end_count}), Centerline({centerline_count}) = Total({total_lights})")
        else:
            print(f"  ⚠ No lights drawn due to missing data")
    
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
        except KeyError as e:
            print(f"  ⚠ Warning: Missing annotation data - {e}")
            print(f"  ✗ Skipping annotations")
            return
        
        # 使用配置常量
        x_offset = self.ANNOTATION_X_OFFSET
        y_base = self.ANNOTATION_Y_BASE
        legend_x = self.LEGEND_X_OFFSET
        
        # 主标题 - 使用JSON中的完整机场名称
        self.msp.add_text(
            airport_name,
            dxfattribs={
                'layer': 'TEXT',
                'height': 25,
                'insert': (x_offset, length + y_base)
            }
        )
        
        # ICAO和IATA代码
        self.msp.add_text(
            f"ICAO: {icao}  IATA: {iata}",
            dxfattribs={
                'layer': 'TEXT',
                'height': 15,
                'insert': (x_offset, length + 60)
            }
        )
        
        # 跑道编号
        self.msp.add_text(
            f"Runway {designator}",
            dxfattribs={
                'layer': 'TEXT',
                'height': 20,
                'insert': (x_offset, length + 20)
            }
        )
        
        # 跑道尺寸标注
        self.msp.add_text(
            f"Dimensions: {length}m × {width}m",
            dxfattribs={
                'layer': 'TEXT',
                'height': 12,
                'insert': (x_offset, length - 20)
            }
        )
        
        # 跑道长度（英尺）
        self.msp.add_text(
            f"Length: {length}m ({length_feet}ft)",
            dxfattribs={
                'layer': 'TEXT',
                'height': 10,
                'insert': (x_offset, length - 45)
            }
        )
        
        # 跑道宽度（英尺）
        self.msp.add_text(
            f"Width: {width}m ({width_feet}ft)",
            dxfattribs={
                'layer': 'TEXT',
                'height': 10,
                'insert': (x_offset, length - 65)
            }
        )
        
        # 图例
        self.msp.add_text(
            "Legend:",
            dxfattribs={
                'layer': 'TEXT',
                'height': 12,
                'insert': (width + legend_x, length - 100)
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
        
        y_offset = length - 130
        for item in legend_items:
            self.msp.add_text(
                item,
                dxfattribs={
                    'layer': 'TEXT',
                    'height': 8,
                    'insert': (width + legend_x, y_offset)
                }
            )
            y_offset -= 25
        
        print(f"  ✓ Annotations: {airport_name} ({icao}/{iata})")
    
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
    
    geometry = sys.argv[1] if len(sys.argv) > 1 else 'runway_geometry.json'
    
    base_path = os.path.dirname(__file__)
    output = os.path.join(base_path, "output", "airport_runway_system_R2010.dxf")
    gen = AirportRunwayDXFGenerator(geometry)
    return 0 if gen.generate(output) else 1


if __name__ == '__main__':
    exit(main())