"""
智能筛选GeoJSON数据
只保留与18R/36L跑道相关的命名滑行道
"""

import json
import math
from typing import List, Dict, Tuple

class TaxiwayFilter:
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.data = None
        
    def load_data(self):
        """加载JSON数据"""
        print(f"📂 Loading {self.json_file}...")
        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"  ✓ Loaded")
        
    def get_runway_bounds(self) -> Tuple[float, float, float, float]: 
        """获取18R/36L跑道的边界"""
        real_geom = self.data. get('real_geometry', {})
        runway = real_geom.get('runway', {})
        coords = runway.get('geometry', {}).get('local_coordinates', [])
        
        if not coords:
            raise ValueError("No runway coordinates found")
        
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        print(f"\n📏 Runway 18R/36L bounds:")
        print(f"  X: {min_x:.1f}m to {max_x:.1f}m")
        print(f"  Y: {min_y:.1f}m to {max_y:.1f}m")
        print(f"  Length: {max_y - min_y:.1f}m")
        print(f"  Width: {max_x - min_x:.1f}m")
        
        return (min_x, max_x, min_y, max_y)
        
    def calculate_distance_to_runway(self, taxiway_coords: List[List[float]], 
                                     runway_bounds: Tuple[float, float, float, float]) -> float:
        """计算滑行道到跑道的最小距离"""
        min_x, max_x, min_y, max_y = runway_bounds
        
        min_distance = float('inf')
        
        for x, y in taxiway_coords:
            # 计算点到跑道矩形的最小距离
            if min_x <= x <= max_x: 
                # 点在跑道X范围内，计算Y方向距离
                if y < min_y:
                    distance = min_y - y
                elif y > max_y:
                    distance = y - max_y
                else:
                    distance = 0  # 点在跑道内
            elif min_y <= y <= max_y:
                # 点在跑道Y范围内，计算X方向距离
                if x < min_x: 
                    distance = min_x - x
                else:
                    distance = x - max_x
            else:
                # 点在角落，计算到最近角点的距离
                corners = [
                    (min_x, min_y), (max_x, min_y),
                    (min_x, max_y), (max_x, max_y)
                ]
                distance = min(
                    math. sqrt((x - cx)**2 + (y - cy)**2)
                    for cx, cy in corners
                )
            
            min_distance = min(min_distance, distance)
            
        return min_distance
        
    def is_parallel_to_runway(self, taxiway_coords: List[List[float]], 
                             runway_bounds: Tuple[float, float, float, float]) -> bool:
        """判断滑行道是否平行于跑道"""
        if len(taxiway_coords) < 2:
            return False
        
        # 计算滑行道的主要方向
        start = taxiway_coords[0]
        end = taxiway_coords[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # 跑道是南北向（Y方向为主）
        # 平行滑行道也应该是Y方向为主
        if abs(dy) > abs(dx) * 3:  # Y方向变化 > 3倍X方向变化
            return True
        
        return False
        
    def get_taxiway_center(self, coords: List[List[float]]) -> Tuple[float, float]:
        """获取滑行道中心点"""
        avg_x = sum(c[0] for c in coords) / len(coords)
        avg_y = sum(c[1] for c in coords) / len(coords)
        return (avg_x, avg_y)
        
    def filter_taxiways(self, max_distance: float = 800) -> List[Dict]:
        """筛选滑行道"""
        print(f"\n🔍 Filtering taxiways (max distance: {max_distance}m)...")
        
        real_geom = self.data. get('real_geometry', {})
        all_taxiways = real_geom.get('taxiways', [])
        
        print(f"  Total taxiways: {len(all_taxiways)}")
        
        # 获取跑道边界
        runway_bounds = self.get_runway_bounds()
        min_x, max_x, min_y, max_y = runway_bounds
        
        filtered = []
        stats = {
            'total': len(all_taxiways),
            'unnamed': 0,
            'too_far': 0,
            'other_runway': 0,
            'kept': 0
        }
        
        print("\n  Analyzing each taxiway:")
        
        for tw in all_taxiways:
            ref = tw['ref']
            coords = tw['geometry']['local_coordinates']
            
            # 规则1：去除unnamed
            if ref == 'unnamed':
                stats['unnamed'] += 1
                continue
            
            # 规则2：计算距离
            distance = self.calculate_distance_to_runway(coords, runway_bounds)
            
            # 规则3：判断是否属于18R/36L
            center_x, center_y = self. get_taxiway_center(coords)
            is_parallel = self.is_parallel_to_runway(coords, runway_bounds)
            
            # 判断逻辑
            keep = False
            reason = ""
            
            if distance > max_distance:
                stats['too_far'] += 1
                reason = f"too far ({distance:. 0f}m)"
            elif distance < 50 and is_parallel:
                # 非常近且平行 -> 可能是平行滑行道
                keep = True
                reason = f"parallel ({distance:.0f}m)"
            elif distance < max_distance: 
                # 在合理距离内
                if abs(center_y - (min_y + max_y) / 2) < (max_y - min_y) / 2 + 500:
                    # Y坐标在跑道范围±500m内
                    keep = True
                    reason = f"nearby ({distance:.0f}m)"
                else:
                    stats['other_runway'] += 1
                    reason = f"other runway (y={center_y:.0f})"
            
            if keep: 
                filtered.append(tw)
                stats['kept'] += 1
                print(f"    ✓ {ref:<6s} - {reason}")
            else:
                print(f"    ✗ {ref:6s} - {reason}")
        
        return filtered, stats
        
    def categorize_taxiways(self, taxiways: List[Dict]) -> Dict[str, List[Dict]]: 
        """分类滑行道"""
        categories = {
            'parallel': [],      # 平行滑行道（W, E系列）
            'perimeter': [],     # 端部滑行道（Z系列）
            'connector': [],     # 连接滑行道（P, D, C, S系列）
            'other':  []
        }
        
        for tw in taxiways:
            ref = tw['ref']
            
            if ref. startswith('W') or ref.startswith('E'):
                categories['parallel'].append(tw)
            elif ref.startswith('Z'):
                categories['perimeter'].append(tw)
            elif ref.startswith(('P', 'D', 'C', 'S')):
                categories['connector'].append(tw)
            else:
                categories['other'].append(tw)
        
        return categories
        
    def save_filtered_data(self, filtered_taxiways: List[Dict]):
        """保存筛选后的数据"""
        print(f"\n💾 Saving filtered data...")
        
        real_geom = self.data. get('real_geometry', {})
        real_geom['taxiways'] = filtered_taxiways
        real_geom['taxiways_total'] = len(filtered_taxiways)
        real_geom['taxiways_filtered'] = True
        real_geom['filter_criteria'] = {
            'remove_unnamed': True,
            'runway':  '18R/36L',
            'max_distance_meters': 800
        }
        
        self.data['real_geometry'] = real_geom
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved to {self.json_file}")
        
    def process(self, max_distance: float = 800):
        """完整处理流程"""
        print("="*70)
        print("🔍 TAXIWAY FILTER - 18R/36L Runway")
        print("="*70)
        
        # 1. 加载数据
        self.load_data()
        
        # 2. 筛选滑行道
        filtered, stats = self.filter_taxiways(max_distance)
        
        # 3. 分类统计
        categories = self.categorize_taxiways(filtered)
        
        print("\n" + "="*70)
        print("📊 FILTERING RESULTS")
        print("="*70)
        
        print(f"\n  Total analyzed:      {stats['total']}")
        print(f"  ✗ Removed unnamed:    {stats['unnamed']}")
        print(f"  ✗ Removed too far:   {stats['too_far']}")
        print(f"  ✗ Other runway:      {stats['other_runway']}")
        print(f"  ✓ Kept (18R/36L):    {stats['kept']}")
        
        print(f"\n  📂 Taxiway categories:")
        print(f"    Parallel (W/E):    {len(categories['parallel'])}")
        print(f"    Perimeter (Z):     {len(categories['perimeter'])}")
        print(f"    Connector (P/D/C): {len(categories['connector'])}")
        print(f"    Other:              {len(categories['other'])}")
        
        # 4. 显示保留的滑行道列表
        print(f"\n  📋 Kept taxiways:")
        all_refs = sorted([tw['ref'] for tw in filtered])
        for i in range(0, len(all_refs), 10):
            print(f"    {', '.join(all_refs[i:i+10])}")
        
        # 5. 保存
        self.save_filtered_data(filtered)
        
        print("\n" + "="*70)
        print("✅ Filtering completed successfully!")
        print("="*70)


def main():
    """主函数"""
    import os
    
    # 获取脚本所在目录
    script_dir = os.path. dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'runway_geometry.json')
    
    # 创建筛选器
    filter = TaxiwayFilter(json_file)
    
    # 执行筛选（最大距离800米）
    filter.process(max_distance=800)


if __name__ == '__main__':
    main()