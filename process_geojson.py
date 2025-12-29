"""
GeoJSON数据处理脚本
从export.geojson提取ZBAA 18R/36L跑道系统数据
转换为runway_geometry.json可用的格式
"""

import json
import math
import os
from typing import Dict, List, Tuple

class GeoJSONProcessor:
    def __init__(self, geojson_file: str):
        """初始化处理器"""
        self.geojson_file = geojson_file
        self.data = None
        self.runway_center = None  # 跑道中心点（用于坐标转换）
        
    def load_geojson(self):
        """加载GeoJSON文件"""
        print(f"📂 Loading {self.geojson_file}...")
        with open(self.geojson_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"  ✓ Loaded {len(self.data['features'])} features")
        
    def find_runway_18r_36l(self):
        """查找18R/36L跑道"""
        print("\n🔍 Searching for runway 18R/36L...")
        
        for feature in self.data['features']: 
            props = feature['properties']
            if props.get('aeroway') == 'runway':
                ref = props.get('ref', '')
                # 注意：GeoJSON中可能是18L/36R，我们需要找正确的那条
                print(f"  Found runway: {ref}")
                if '18R' in ref or '36L' in ref: 
                    print(f"  ✓ Found target runway: {ref}")
                    return feature
                    
        # 如果没有找到18R/36L，可能在OSM中标记为18L/36R
        # 需要手动确认
        print("  ⚠ Runway 18R/36L not found, checking alternatives...")
        return None
        
    def find_taxiways(self, runway_bounds: Tuple[float, float, float, float]) -> List[Dict]:
        """查找跑道附近的滑行道"""
        print("\n🔍 Searching for taxiways...")
        
        taxiways = []
        min_lon, min_lat, max_lon, max_lat = runway_bounds
        
        for feature in self.data['features']:
            props = feature['properties']
            if props. get('aeroway') == 'taxiway':
                ref = props.get('ref', 'unnamed')
                coords = feature['geometry']['coordinates']
                
                # 检查滑行道是否在跑道附近
                if self._is_near_runway(coords, runway_bounds):
                    taxiways.append(feature)
                    print(f"  ✓ Found taxiway: {ref}")
                    
        print(f"  Total:  {len(taxiways)} taxiways")
        return taxiways
        
    def _is_near_runway(self, coords: List[List[float]], 
                       bounds: Tuple[float, float, float, float]) -> bool:
        """判断滑行道是否在跑道附近"""
        min_lon, min_lat, max_lon, max_lat = bounds
        
        # 扩大边界（例如500m，约0.005度）
        buffer = 0.01
        
        for lon, lat in coords:
            if (min_lon - buffer <= lon <= max_lon + buffer and
                min_lat - buffer <= lat <= max_lat + buffer):
                return True
        return False
        
    def get_runway_bounds(self, runway_coords: List[List[float]]) -> Tuple[float, float, float, float]:
        """获取跑道边界"""
        lons = [c[0] for c in runway_coords]
        lats = [c[1] for c in runway_coords]
        return (min(lons), min(lats), max(lons), max(lats))
        
    def calculate_center(self, coords: List[List[float]]) -> Tuple[float, float]: 
        """计算中心点"""
        avg_lon = sum(c[0] for c in coords) / len(coords)
        avg_lat = sum(c[1] for c in coords) / len(coords)
        return (avg_lon, avg_lat)
        
    def gps_to_local(self, lon: float, lat: float) -> Tuple[float, float]: 
        """GPS坐标转本地平面坐标（以跑道中心为原点）"""
        if not self.runway_center:
            raise ValueError("Runway center not set")
            
        center_lon, center_lat = self.runway_center
        
        # 简化的平面投影（适用于小范围）
        # 1度纬度 ≈ 111000m
        # 1度经度 ≈ 111000m * cos(纬度)
        x = (lon - center_lon) * 111000 * math.cos(math.radians(center_lat))
        y = (lat - center_lat) * 111000
        
        return (x, y)
        
    def convert_linestring_to_local(self, coords: List[List[float]]) -> List[Tuple[float, float]]: 
        """转换LineString坐标列表"""
        return [self.gps_to_local(lon, lat) for lon, lat in coords]
        
    def calculate_length_and_width(self, coords:  List[Tuple[float, float]]) -> Tuple[float, float]: 
        """计算跑道长度和宽度"""
        # 长度：起点到终点的距离
        x1, y1 = coords[0]
        x2, y2 = coords[-1]
        length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # 宽度：从properties中读取或默认60m
        width = 60  # 默认值
        
        return (length, width)
        
    def generate_runway_json(self, runway_feature: Dict, taxiways: List[Dict]) -> Dict:
        """生成runway_geometry.json格式的数据"""
        print("\n📝 Generating runway_geometry data...")
        
        # 获取跑道坐标
        runway_coords = runway_feature['geometry']['coordinates']
        runway_props = runway_feature['properties']
        
        # 计算跑道中心（用于坐标转换）
        self.runway_center = self.calculate_center(runway_coords)
        center_lon, center_lat = self.runway_center

        print(f"  Runway center: {center_lat:.6f}°N, {center_lon:.6f}°E")
        
        # 转换跑道坐标到本地系统
        local_coords = self.convert_linestring_to_local(runway_coords)
        length, width = self.calculate_length_and_width(local_coords)
        
        print(f"  Runway dimensions: {length:.1f}m × {width}m")
        
        # 构建输出数据结构
        output = {
            "dataSource": "OpenStreetMap (OSM)",
            "processedFrom": "export.geojson",
            "coordinateSystem": {
                "origin": {
                    "latitude": center_lat,
                    "longitude": center_lon,
                    "description": "Runway center used as local coordinate system origin"
                },
                "projection": "Local planar approximation",
                "units": "meters"
            },
            "runway": {
                "designator":  runway_props. get('ref', '18R/36L'),
                "length_meters": round(length, 1),
                "width_meters": int(runway_props.get('width', 60)),
                "geometry": {
                    "type": "LineString",
                    "gps_coordinates": runway_coords,
                    "local_coordinates":  [[round(x, 2), round(y, 2)] for x, y in local_coords]
                }
            },
            "taxiways": []
        }
        
        # 处理每条滑行道
        print("\n  Processing taxiways:")
        for tw_feature in taxiways:
            tw_props = tw_feature['properties']
            tw_coords = tw_feature['geometry']['coordinates']
            tw_ref = tw_props.get('ref', 'unnamed')
            
            # 转换坐标
            local_tw_coords = self.convert_linestring_to_local(tw_coords)
            
            taxiway_data = {
                "ref": tw_ref,
                "type": "taxiway",
                "width_meters": int(tw_props.get('width', 23)),  # 默认23m
                "geometry": {
                    "type": "LineString",
                    "gps_coordinates": tw_coords,
                    "local_coordinates": [[round(x, 2), round(y, 2)] for x, y in local_tw_coords]
                }
            }
            
            output['taxiways'].append(taxiway_data)
            print(f"    ✓ {tw_ref}:  {len(tw_coords)} points")
            
        return output
        
    def merge_with_existing_json(self, new_data: Dict, existing_file: str = 'runway_geometry.json') -> Dict:
        """合并到现有的runway_geometry.json"""
        print(f"\n🔀 Merging with {existing_file}...")
        
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except FileNotFoundError:
            print(f"  ⚠ {existing_file} not found, will create new file")
            existing = {}
            
        # 更新字段
        existing['dataSource'] = f"{existing. get('dataSource', '')}, OpenStreetMap (OSM)"
        existing['geojson_data'] = new_data
        
        # 可以选择替换或保留原有的taxiways数据
        # 这里添加一个新字段来存储真实的几何数据
        existing['real_geometry'] = {
            "runway": new_data['runway'],
            "taxiways": new_data['taxiways']
        }
        
        print("  ✓ Merged successfully")
        return existing
        
    def save_json(self, data: Dict, output_file: str):
        """保存JSON文件"""
        print(f"\n💾 Saving to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved")
        
    def process(self, output_file: str):
        """完整处理流程"""
        print("="*70)
        print("🛫 ZBAA GeoJSON Data Processor")
        print("="*70)
        
        # 1. 加载GeoJSON
        self.load_geojson()
        
        # 2. 查找18R/36L跑道
        runway = self.find_runway_18r_36l()
        if not runway:
            print("\n❌ Error:  Runway 18R/36L not found")
            return
            
        # 3. 获取跑道范围
        runway_coords = runway['geometry']['coordinates']
        bounds = self.get_runway_bounds(runway_coords)
        
        # 4. 查找相关滑行道
        taxiways = self.find_taxiways(bounds)
        
        # 5. 生成数据
        new_data = self.generate_runway_json(runway, taxiways)
        
        # 6. 合并到现有JSON
        merged_data = self.merge_with_existing_json(new_data, output_file)
        
        # 7. 保存
        self.save_json(merged_data, output_file)
        
        print("\n" + "="*70)
        print("✅ Processing completed successfully!")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"  - Runway:  {runway['properties'].get('ref')}")
        print(f"  - Taxiways: {len(taxiways)}")
        print(f"  - Output:  {output_file}")


def main():
    """主函数"""

    base_path = os.path.dirname(__file__)
    processor = GeoJSONProcessor(os.path.join(base_path, 'export.geojson'))

    processor.process(os.path.join(base_path, 'runway_geometry.json'))


if __name__ == '__main__':
    main()