"""
CAD Generator - AutoCAD 2018 DXF (R2010) Compatible
"""

import json
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
        # 修正：从正确的JSON路径读取数据
        runway_dims = self.geometry_data.get('runwayDimensions', {})
        length_data = runway_dims.get('length', {})
        width_data = runway_dims.get('width', {})
        length = length_data.get('meters', 3800)
        width = width_data.get('meters', 60)
        
        runway = self.geometry_data.get('runway', {})
        designator = runway.get('designator', '18R/36L')
        
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
                'height': 30,
                'insert': (cx - 15, 100),  # 距入口100m
                'rotation': 0
            }
        )
        # 36L端编号（北端）
        self.msp.add_text(
            '36L',
            dxfattribs={
                'layer': 'RUNWAY_MARKINGS',
                'height': 30,
                'insert': (cx - 15, length - 150),  # 距入口100m
                'rotation': 180
            }
        )
        
        # 绘制侧边条纹（距边缘5m的连续白线）
        edge_offset = 5
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
        # 获取跑道尺寸
        runway_dims = self.geometry_data.get('runwayDimensions', {})
        length_data = runway_dims.get('length', {})
        width_data = runway_dims.get('width', {})
        l = length_data.get('meters', 3800)
        w = width_data.get('meters', 60)
        
        # 从JSON获取滑行道数据
        taxiways = self.geometry_data.get('taxiways', {})
        
        # 平行滑行道A（北侧）- 使用JSON中的准确宽度60m
        taxiway_a = taxiways.get('parallel_taxiway_north', {})
        tw_width = taxiway_a.get('width', 60)
        offset_a = 100  # 距跑道边缘100m
        pts_a = [(w + offset_a, 0), (w + offset_a + tw_width, 0), 
                 (w + offset_a + tw_width, l), (w + offset_a, l)]
        pline_a = self.msp.add_lwpolyline(pts_a, dxfattribs={'layer': 'TAXIWAYS'})
        pline_a.close()
        
        # 平行滑行道B（南侧）- 使用JSON中的准确宽度60m
        taxiway_b = taxiways.get('parallel_taxiway_south', {})
        tw_width = taxiway_b.get('width', 60)
        offset_b = 100  # 距跑道边缘100m
        pts_b = [(-offset_b - tw_width, 0), (-offset_b, 0), 
                 (-offset_b, l), (-offset_b - tw_width, l)]
        pline_b = self.msp.add_lwpolyline(pts_b, dxfattribs={'layer': 'TAXIWAYS'})
        pline_b.close()
        
        # 快速出口滑行道（C, D, E）- 使用JSON中的数据
        intermediate = taxiways.get('intermediate_taxiways', [])
        exit_count = 0
        
        for taxiway in intermediate:
            designator = taxiway.get('designator', '')
            if designator in ['C', 'D', 'E']:
                # 解析起点位置（例如："1200m from 18R"）
                start_str = taxiway.get('startPoint_along_runway', '')
                if 'from 18R' in start_str:
                    distance = int(start_str.split('m')[0])
                else:
                    continue
                
                angle = taxiway.get('angle', 45)
                width = taxiway.get('width', 45)
                radius = taxiway.get('radius', 550)
                
                # 绘制快速出口滑行道（简化为直线，实际应该是曲线）
                # 从跑道右侧边缘开始，45度角向外
                import math
                start_x = w
                start_y = distance
                
                # 计算45度角延伸的终点（简化版本）
                length_exit = 400  # 延伸400m到停机坪
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
        
        print(f"  ✓ Taxiways A, B + {exit_count} rapid exits (C, D, E)")
    
    def _draw_markings(self):
        """Draw runway markings - 绘制跑道标记系统"""
        # 获取跑道尺寸
        runway_dims = self.geometry_data.get('runwayDimensions', {})
        length_data = runway_dims.get('length', {})
        width_data = runway_dims.get('width', {})
        l = length_data.get('meters', 3800)
        w = width_data.get('meters', 60)
        
        # 从JSON获取标记数据
        markings = self.geometry_data.get('runwayMarkings', {})
        
        cx = w / 2  # 跑道中心线X坐标
        
        # 1. 入口标记（钢琴键图案）- Piano Key Pattern
        threshold = markings.get('threshold_markings', {})
        threshold_width = threshold.get('length_18R', 60)
        stripe_width = threshold.get('dimensions', {}).get('width', 3)
        stripe_spacing = threshold.get('dimensions', {}).get('spacing', 3)
        
        # 18R端入口标记（0m位置）
        num_stripes = 10
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
        
        # 2. 中心线标记 - Centerline Markings（改进版本）
        centerline = markings.get('centerline_marking', {})
        dash_length = centerline.get('dashLength', 30)
        gap_length = centerline.get('gapLength', 20)
        line_width = centerline.get('width', 0.45)
        
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
        tdz = markings.get('touchdown_zone_markings', {})
        zones = tdz.get('zones', 6)
        spacing = tdz.get('spacing', 150)
        start_dist = tdz.get('start_distance_from_threshold', 300)
        zone_width = tdz.get('width_per_zone', 45)
        zone_length = tdz.get('length_per_zone', 150)
        
        # 从18R端开始的接地区
        for i in range(zones):
            y_pos = start_dist + i * spacing
            if y_pos + zone_length <= l:
                # 左侧标记
                x_left = cx - zone_width / 2 - 10
                pts_left = [(x_left - 3, y_pos), (x_left, y_pos),
                           (x_left, y_pos + zone_length), (x_left - 3, y_pos + zone_length)]
                pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
                
                # 右侧标记
                x_right = cx + zone_width / 2 + 10
                pts_right = [(x_right, y_pos), (x_right + 3, y_pos),
                            (x_right + 3, y_pos + zone_length), (x_right, y_pos + zone_length)]
                pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
        
        # 从36L端开始的接地区
        for i in range(zones):
            y_pos = l - start_dist - zone_length - i * spacing
            if y_pos >= 0:
                # 左侧标记
                x_left = cx - zone_width / 2 - 10
                pts_left = [(x_left - 3, y_pos), (x_left, y_pos),
                           (x_left, y_pos + zone_length), (x_left - 3, y_pos + zone_length)]
                pline = self.msp.add_lwpolyline(pts_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
                
                # 右侧标记
                x_right = cx + zone_width / 2 + 10
                pts_right = [(x_right, y_pos), (x_right + 3, y_pos),
                            (x_right + 3, y_pos + zone_length), (x_right, y_pos + zone_length)]
                pline = self.msp.add_lwpolyline(pts_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
                pline.close()
        
        # 4. 瞄准点标记 - Aiming Point Markings
        aiming = markings.get('aiming_point', {})
        aim_dist = aiming.get('distance_from_threshold', 300)
        aim_width = aiming.get('width', 45)
        aim_length = aiming.get('length', 180)
        
        # 18R端瞄准点
        x_left = cx - aim_width / 2 - 5
        x_right = cx + aim_width / 2 + 5
        # 左侧矩形
        pts_aim_left = [(x_left - 10, aim_dist), (x_left, aim_dist),
                       (x_left, aim_dist + aim_length), (x_left - 10, aim_dist + aim_length)]
        pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
        pline.close()
        # 右侧矩形
        pts_aim_right = [(x_right, aim_dist), (x_right + 10, aim_dist),
                        (x_right + 10, aim_dist + aim_length), (x_right, aim_dist + aim_length)]
        pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
        pline.close()
        
        # 36L端瞄准点
        y_pos = l - aim_dist - aim_length
        # 左侧矩形
        pts_aim_left = [(x_left - 10, y_pos), (x_left, y_pos),
                       (x_left, y_pos + aim_length), (x_left - 10, y_pos + aim_length)]
        pline = self.msp.add_lwpolyline(pts_aim_left, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
        pline.close()
        # 右侧矩形
        pts_aim_right = [(x_right, y_pos), (x_right + 10, y_pos),
                        (x_right + 10, y_pos + aim_length), (x_right, y_pos + aim_length)]
        pline = self.msp.add_lwpolyline(pts_aim_right, dxfattribs={'layer': 'RUNWAY_MARKINGS'})
        pline.close()
        
        print(f"  ✓ Markings: Threshold, Centerline, TDZ ({zones} zones), Aiming points")
    
    def _draw_lights(self):
        """Draw lighting systems - 绘制灯光系统"""
        # 获取跑道尺寸
        runway_dims = self.geometry_data.get('runwayDimensions', {})
        length_data = runway_dims.get('length', {})
        width_data = runway_dims.get('width', {})
        l = length_data.get('meters', 3800)
        w = width_data.get('meters', 60)
        
        # 从JSON获取灯光系统数据
        lights = self.geometry_data.get('lightingSystems', {})
        
        # 1. 跑道边灯 - Runway Edge Lights（修正为60m间距）
        edge_lights = lights.get('runway_edge_lights', {})
        edge_spacing = edge_lights.get('spacing', 60)
        
        y = 0
        edge_count = 0
        while y <= l:
            # 左侧边灯
            self.msp.add_circle((-10, y), 1.5, dxfattribs={'layer': 'LIGHTS'})
            # 右侧边灯
            self.msp.add_circle((w + 10, y), 1.5, dxfattribs={'layer': 'LIGHTS'})
            y += edge_spacing
            edge_count += 2
        
        # 2. 入口灯 - Threshold Lights（绿色）
        threshold_lights = lights.get('threshold_lights', {})
        th_rows = 2  # 2排
        th_cols = 6  # 每排6盏
        row_spacing = threshold_lights.get('rowSpacing', 6)
        light_spacing = threshold_lights.get('lightSpacing', 3)
        
        threshold_count = 0
        # 18R端入口灯（绿色）
        cx = w / 2
        start_x = cx - (th_cols - 1) * light_spacing / 2
        for row in range(th_rows):
            y_pos = -10 - row * row_spacing
            for col in range(th_cols):
                x_pos = start_x + col * light_spacing
                self.msp.add_circle((x_pos, y_pos), 1.0, 
                                   dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                threshold_count += 1
        
        # 36L端入口灯（绿色）
        for row in range(th_rows):
            y_pos = l + 10 + row * row_spacing
            for col in range(th_cols):
                x_pos = start_x + col * light_spacing
                self.msp.add_circle((x_pos, y_pos), 1.0,
                                   dxfattribs={'layer': 'THRESHOLD_LIGHTS'})
                threshold_count += 1
        
        # 3. 末端灯 - End Lights（红色）
        end_lights = lights.get('end_lights', {})
        end_rows = 2  # 2排
        end_cols = 6  # 每排6盏
        
        end_count = 0
        # 18R端末端灯（红色）- 在跑道外侧
        for row in range(end_rows):
            y_pos = 10 + row * row_spacing
            for col in range(end_cols):
                x_pos = start_x + col * light_spacing
                self.msp.add_circle((x_pos, y_pos), 1.0,
                                   dxfattribs={'layer': 'END_LIGHTS'})
                end_count += 1
        
        # 36L端末端灯（红色）
        for row in range(end_rows):
            y_pos = l - 10 - row * row_spacing
            for col in range(end_cols):
                x_pos = start_x + col * light_spacing
                self.msp.add_circle((x_pos, y_pos), 1.0,
                                   dxfattribs={'layer': 'END_LIGHTS'})
                end_count += 1
        
        # 4. 中心线灯 - Centerline Lights（白色嵌入式）
        centerline_lights = lights.get('centerline_lights', {})
        cl_spacing = centerline_lights.get('spacing', 15)
        
        y = 0
        centerline_count = 0
        while y <= l:
            self.msp.add_circle((cx, y), 0.8,
                               dxfattribs={'layer': 'CENTERLINE_LIGHTS'})
            y += cl_spacing
            centerline_count += 1
        
        total_lights = edge_count + threshold_count + end_count + centerline_count
        print(f"  ✓ Lights: Edge({edge_count}), Threshold({threshold_count}), End({end_count}), Centerline({centerline_count}) = Total({total_lights})")
    
    def _add_annotations(self):
        """Add annotations - 添加文字注释"""
        runway = self.geometry_data.get('runway', {})
        airport = self.geometry_data.get('airport', {})
        runway_dims = self.geometry_data.get('runwayDimensions', {})
        
        # 获取完整机场信息
        airport_name = airport.get('name', 'Airport')
        icao = airport.get('icao', '')
        iata = airport.get('iata', '')
        designator = runway.get('designator', '??')
        
        # 获取跑道尺寸
        length_data = runway_dims.get('length', {})
        width_data = runway_dims.get('width', {})
        length = length_data.get('meters', 3800)
        width = width_data.get('meters', 60)
        
        # 主标题 - 使用JSON中的完整机场名称
        self.msp.add_text(
            airport_name,
            dxfattribs={
                'layer': 'TEXT',
                'height': 25,
                'insert': (-300, length + 100)
            }
        )
        
        # ICAO和IATA代码
        self.msp.add_text(
            f"ICAO: {icao}  IATA: {iata}",
            dxfattribs={
                'layer': 'TEXT',
                'height': 15,
                'insert': (-300, length + 60)
            }
        )
        
        # 跑道编号
        self.msp.add_text(
            f"Runway {designator}",
            dxfattribs={
                'layer': 'TEXT',
                'height': 20,
                'insert': (-300, length + 20)
            }
        )
        
        # 跑道尺寸标注
        self.msp.add_text(
            f"Dimensions: {length}m × {width}m",
            dxfattribs={
                'layer': 'TEXT',
                'height': 12,
                'insert': (-300, length - 20)
            }
        )
        
        # 跑道长度（英尺）
        length_feet = length_data.get('feet', int(length * 3.28084))
        self.msp.add_text(
            f"Length: {length}m ({length_feet}ft)",
            dxfattribs={
                'layer': 'TEXT',
                'height': 10,
                'insert': (-300, length - 45)
            }
        )
        
        # 跑道宽度（英尺）
        width_feet = width_data.get('feet', int(width * 3.28084))
        self.msp.add_text(
            f"Width: {width}m ({width_feet}ft)",
            dxfattribs={
                'layer': 'TEXT',
                'height': 10,
                'insert': (-300, length - 65)
            }
        )
        
        # 图例
        self.msp.add_text(
            "Legend:",
            dxfattribs={
                'layer': 'TEXT',
                'height': 12,
                'insert': (width + 150, length - 100)
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
                    'insert': (width + 150, y_offset)
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