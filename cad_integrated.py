# -*- coding: utf-8 -*-
"""
cad_integrated.py - 阶段1
融合版CAD生成器 - 使用真实GeoJSON数据

阶段1功能：
- 绘制真实的跑道（来自export. geojson）
- 绘制47条真实滑行道（来自export.geojson）
- 基础图层结构
"""

import json
import math
import os
from typing import List, Tuple, Dict, Any
import ezdxf

class IntegratedAirportCAD:
    def __init__(self, 
                 geojson_data_file: str = 'runway_geometry.json',
                 tables_file: str = 'ZBAA_tables. json'):
        """初始化"""
        self.geojson_file = geojson_data_file
        self.tables_file = tables_file
        
        # 数据容器
        self.real_geometry = None
        self.tables_data = None
        
        # DXF文档
        self. doc = ezdxf.new('R2010', setup=True)
        self.doc.header['$INSUNITS'] = 6  # meters
        self.msp = self.doc.modelspace()
        
        self._setup_layers()
        
    def _setup_layers(self):
        """设置图层"""
        print("🎨 Setting up layers...")
        
        layers = {
            # 跑道系统
            'RUNWAY':  7,                    # 白色 - 跑道主体
            'RUNWAY_SHOULDER': 8,           # 深灰 - 道肩
            'RUNWAY_STRIP': 9,              # 浅灰 - 升降带
            'RESA':  1,                      # 红色 - 跑道端安全区
            'RUNWAY_MARKINGS': 1,           # 红色 - 跑道标记
            
            # 滑行道系统
            'TAXIWAY':  5,                   # 蓝色 - 滑行道主体
            'TAXIWAY_CENTERLINE': 2,        # 黄色 - 滑行道中心线
            'TAXIWAY_EDGE': 2,              # 黄色 - 滑行道边线
            'TAXIWAY_HOLD': 2,              # 黄色 - 等待位置
            
            # 灯光系统
            'RUNWAY_LIGHTS': 3,             # 绿色 - 跑道灯光
            'TAXIWAY_LIGHTS': 3,            # 绿色 - 滑行道灯光
            'APPROACH_LIGHTS': 4,           # 青色 - 进近灯光
            'PAPI': 1,                      # 红色 - PAPI灯光
            
            # 标志和文字
            'SIGNS': 30,                    # 橙色 - 标志牌
            'TEXT': 8,                      # 深灰 - 文字标注
            'DIMENSIONS': 6,                # 紫色 - 尺寸标注
        }
        
        for name, color in layers.items():
            try:
                self. doc.layers. new(name=name, dxfattribs={'color': color})
            except Exception as e:
                pass  # 图层可能已存在
        
        print(f"  ✓ Created {len(layers)} layers")
    
    def load_data(self):
        """加载所有数据"""
        print("\n📂 Loading data...")
        
        # 1. 加载真实几何数据
        try:
            with open(self. geojson_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.real_geometry = data. get('real_geometry', {})
            
            runway = self.real_geometry.get('runway', {})
            taxiways = self.real_geometry.get('taxiways', [])
            
            print(f"  ✓ Loaded real geometry:")
            print(f"    - Runway: {runway.get('designator', 'N/A')}")
            print(f"    - Runway length: {runway.get('length_meters', 0):.1f}m")
            print(f"    - Taxiways: {len(taxiways)}")
            
        except FileNotFoundError:
            print(f"  ✗ Error: {self.geojson_file} not found")
            raise
        except Exception as e:
            print(f"  ✗ Error loading geometry: {e}")
            raise
        
        # 2. 加载ZBAA表格数据（可选）
        try: 
            with open(self.tables_file, 'r', encoding='utf-8') as f:
                self.tables_data = json.load(f)
            print(f"  ✓ Loaded ZBAA tables")
        except: 
            print(f"  ⚠ ZBAA tables not available (optional)")
    
    # ========== 几何工具函数 ==========
    
    def _offset_polyline(self, points:  List[Tuple[float, float]], 
                        offset: float) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        计算折线的左右偏移
        返回：(left_points, right_points)
        """
        if len(points) < 2:
            return [], []
        
        left = []
        right = []
        
        for i, (x, y) in enumerate(points):
            if i == 0:
                # 第一个点：使用第一段的法向
                dx = points[1][0] - points[0][0]
                dy = points[1][1] - points[0][1]
            elif i == len(points) - 1:
                # 最后一个点：使用最后一段的法向
                dx = points[-1][0] - points[-2][0]
                dy = points[-1][1] - points[-2][1]
            else: 
                # 中间点：使用前后段的平均法向
                dx = points[i+1][0] - points[i-1][0]
                dy = points[i+1][1] - points[i-1][1]
            
            # 归一化并旋转90度得到法向量
            length = math.sqrt(dx**2 + dy**2)
            if length > 1e-6: 
                nx = -dy / length
                ny = dx / length
            else:
                nx, ny = 0, 1  # 默认向上
            
            left.append((x + nx * offset, y + ny * offset))
            right.append((x - nx * offset, y - ny * offset))
        
        return left, right
    
    def _calculate_polyline_length(self, points: List[Tuple[float, float]]) -> float:
        """计算折线总长度"""
        total = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            total += math.sqrt(dx**2 + dy**2)
        return total
    
    def _find_closest_point_on_line(self, 
                                    point: Tuple[float, float], 
                                    line_points: List[Tuple[float, float]]) -> Tuple[float, Tuple[float, float]]:
        """
        找到点到折线的最近点
        
        Args:
            point: 目标点坐标
            line_points: 折线的点列表
        
        Returns:
            (最小距离, 最近点坐标)
        
        算法：
        - 遍历折线的每一段
        - 计算点到线段的投影点
        - 投影点限制在线段范围内
        - 返回最小距离和对应的最近点
        """
        px, py = point
        min_dist = float('inf')
        closest_point = line_points[0]
        
        for i in range(len(line_points) - 1):
            x1, y1 = line_points[i]
            x2, y2 = line_points[i + 1]
            
            dx = x2 - x1
            dy = y2 - y1
            length_sq = dx * dx + dy * dy
            
            if length_sq < 1e-10:  # 线段退化为点
                closest = (x1, y1)
            else:
                # 计算投影参数 t，限制在 [0, 1]
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
                closest = (x1 + t * dx, y1 + t * dy)
            
            # 计算距离
            dist = math.sqrt((px - closest[0])**2 + (py - closest[1])**2)
            
            if dist < min_dist:
                min_dist = dist
                closest_point = closest
        
        return min_dist, closest_point
    
    def connect_taxiway_to_runway(self, 
                                  taxiway_coords: List[Tuple[float, float]], 
                                  runway_coords: List[Tuple[float, float]],
                                  threshold: float = 50.0) -> Tuple[List[Tuple[float, float]], bool]:
        """
        自动连接滑行道到跑道中心线
        
        Args:
            taxiway_coords: 滑行道中心线坐标
            runway_coords: 跑道中心线坐标
            threshold: 连接距离阈值（米），小于此值则自动连接
        
        Returns:
            (修正后的滑行道坐标, 是否进行了连接)
        
        逻辑：
        1. 检查滑行道起点和终点距离跑道的距离
        2. 如果距离 < threshold 且 > 0.01米（避免重复点）
        3. 在端点和跑道中心线最近点之间添加连接线段
        """
        if len(taxiway_coords) < 2 or len(runway_coords) < 2:
            return taxiway_coords, False
        
        start = taxiway_coords[0]
        end = taxiway_coords[-1]
        
        # 找到起点和终点到跑道的最近点
        start_dist, start_closest = self._find_closest_point_on_line(start, runway_coords)
        end_dist, end_closest = self._find_closest_point_on_line(end, runway_coords)
        
        new_coords = list(taxiway_coords)
        modified = False
        
        # 如果起点接近跑道，添加连接点
        if start_dist < threshold and start_dist > 0.01:
            new_coords.insert(0, start_closest)
            modified = True
        
        # 如果终点接近跑道，添加连接点
        if end_dist < threshold and end_dist > 0.01:
            new_coords.append(end_closest)
            modified = True
        
        return new_coords, modified
    
    # ========== 阶段1：绘制真实几何 ==========
    
    def draw_runway_from_real_geometry(self):
        """从真实几何数据绘制跑道"""
        print("\n🛫 Drawing runway from real geometry...")
        
        runway = self.real_geometry['runway']
        coords = runway['geometry']['local_coordinates']
        width = runway['width_meters']
        designator = runway['designator']
        
        # 转换坐标格式
        centerline_points = [(x, y) for x, y in coords]
        
        print(f"  Runway: {designator}")
        print(f"  Points: {len(centerline_points)}")
        print(f"  Width: {width}m")
        
        # 1. 绘制跑道中心线
        self. msp.add_lwpolyline(centerline_points, 
                               dxfattribs={'layer': 'RUNWAY_MARKINGS',
                                          'color': 1})
        
        # 2. 计算跑道边界
        left_edge, right_edge = self._offset_polyline(centerline_points, width / 2.0)
        
        # 3. 绘制跑道面（闭合多边形）
        runway_boundary = left_edge + list(reversed(right_edge))
        pline = self.msp.add_lwpolyline(runway_boundary, 
                                       dxfattribs={'layer': 'RUNWAY',
                                                  'color': 7})
        pline.close()
        
        # 4. 计算实际长度
        actual_length = self._calculate_polyline_length(centerline_points)
        
        print(f"  ✓ Runway drawn:")
        print(f"    - Calculated length: {actual_length:.1f}m")
        print(f"    - Centerline points: {len(centerline_points)}")
        print(f"    - Boundary closed: Yes")
        
        return centerline_points, width
    
    def draw_taxiways_from_real_geometry(self, runway_coords: List[Tuple[float, float]]):
        """从真实几何数据绘制滑行道（带自动连接）"""
        print("\n🛤️  Drawing taxiways from real geometry...")
        
        taxiways = self.real_geometry['taxiways']
        
        series_count = {}
        drawn_count = 0
        connected_count = 0
        
        for tw in taxiways:
            ref = tw['ref']
            coords = tw['geometry']['local_coordinates']
            width = tw.get('width_meters', 23)
            
            series = ref[0] if ref else '?'
            series_count[series] = series_count.get(series, 0) + 1
            
            centerline = [(x, y) for x, y in coords]
            
            if len(centerline) < 2:
                continue
            
            # ✨ 自动连接到跑道
            connected_centerline, was_connected = self.connect_taxiway_to_runway(
                centerline, 
                runway_coords, 
                threshold=100.0  # 100米以内自动连接（调整后以覆盖所有快速出口）
            )
            
            if was_connected:
                connected_count += 1
                print(f"      ✓ {ref}: Connected to runway")
            
            # 绘制中心线（使用修正后的坐标）
            self.msp.add_lwpolyline(connected_centerline, 
                                   dxfattribs={'layer': 'TAXIWAY_CENTERLINE',
                                              'color': 2})
            
            # 绘制边界
            if len(connected_centerline) >= 2:
                left, right = self._offset_polyline(connected_centerline, width / 2.0)
                boundary = left + list(reversed(right))
                
                pline = self.msp.add_lwpolyline(boundary,
                                               dxfattribs={'layer': 'TAXIWAY',
                                                          'color': 5})
                pline.close()
            
            drawn_count += 1
        
        print(f"  ✓ Drew {drawn_count} taxiways")
        print(f"  ✓ Auto-connected {connected_count} to runway")
        print(f"\n  📊 By series:")
        for series in sorted(series_count.keys()):
            count = series_count[series]
            print(f"    {series}: {count} taxiway(s)")
    
    def add_title_block(self):
        """添加图纸标题栏"""
        print("\n📋 Adding title block...")
        
        runway = self.real_geometry['runway']
        taxiways = self.real_geometry['taxiways']
        
        # 计算图纸范围
        all_coords = []
        all_coords.extend(runway['geometry']['local_coordinates'])
        for tw in taxiways:
            all_coords.extend(tw['geometry']['local_coordinates'])
        
        if all_coords:
            xs = [c[0] for c in all_coords]
            ys = [c[1] for c in all_coords]
            max_y = max(ys)
        else:
            max_y = 0
        
        # 标题信息
        title_text = f"""ZBAA RUNWAY {runway['designator']} - INTEGRATED CAD
Data Source: OpenStreetMap + Real Geometry
Runway:  {runway['length_meters']:.1f}m × {runway['width_meters']}m
Taxiways: {len(taxiways)} (Real positions from OSM)
Coordinate System: Local planar (meters)
DXF Version: R2010 (AutoCAD 2010+)

Stage 1: Basic Geometry (Runway + Taxiways)"""
        
        # 放置在图纸上方
        self.msp.add_mtext(
            title_text,
            dxfattribs={'layer': 'TEXT', 'char_height': 6.0}
        ).set_location((-400, max_y + 300))
        
        print(f"  ✓ Title block added")
    
    # ========== 构建和保存 ==========
    
    def build(self):
        """构建完整图纸 - 阶段1（修正版）"""
        print("="*70)
        print("🏗️  BUILDING INTEGRATED AIRPORT CAD - STAGE 1 (FIXED)")
        print("="*70)
        
        self.load_data()
        
        print("\n" + "="*70)
        print("📦 STAGE 1: Real Geometry (Runway + Taxiways)")
        print("="*70)
        
        # 先绘制跑道，获取中心线坐标
        runway_coords, runway_width = self.draw_runway_from_real_geometry()
        
        # 绘制滑行道（传入跑道坐标用于连接）
        self.draw_taxiways_from_real_geometry(runway_coords)
        
        self.add_title_block()
        
        print("\n" + "="*70)
        print("✅ BUILD COMPLETED - STAGE 1 (FIXED)")
        print("="*70)
        print("\n📊 Summary:")
        print(f"  - Runway:  {self.real_geometry['runway']['designator']}")
        print(f"  - Taxiways:  {len(self.real_geometry['taxiways'])}")
        print(f"  - Layers: 13")
        print(f"  - Entities: ~{len(self.real_geometry['taxiways']) * 2 + 3}")
    
    def save(self, output_path: str):
        """保存DXF文件"""
        print(f"\n💾 Saving DXF...")
        
        os.makedirs(os.path. dirname(output_path), exist_ok=True)
        self.doc.saveas(output_path)
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        
        print(f"  ✓ Saved to: {output_path}")
        print(f"  ✓ File size: {file_size:.1f} KB")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🛫 ZBAA INTEGRATED CAD GENERATOR - STAGE 1")
    print("="*70)
    
    # 获取脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 输入文件
    geojson_file = os.path.join(base_dir, 'runway_geometry.json')
    tables_file = os.path.join(base_dir, 'ZBAA_tables.json')
    
    # 输出文件
    output_dir = os.path.join(base_dir, 'output')
    output_file = os.path.join(output_dir, 'airport_integrated_stage1.dxf')
    
    # 检查输入文件
    if not os. path.exists(geojson_file):
        print(f"\n❌ Error: {geojson_file} not found")
        print("   Please run process_geojson.py first!")
        return 1
    
    # 创建生成器
    gen = IntegratedAirportCAD(
        geojson_data_file=geojson_file,
        tables_file=tables_file
    )
    
    # 构建和保存
    gen.build()
    gen.save(output_file)
    
    print("\n" + "="*70)
    print("🎉 SUCCESS!")
    print("="*70)
    print(f"\nNext steps:")
    print(f"  1. Open in AutoCAD:  {output_file}")
    print(f"  2. Command:  ZOOM → Extents")
    print(f"  3.  Verify:  Runway + 47 taxiways should be visible")
    print(f"  4. If OK:  Continue to Stage 2 (Runway system details)")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())