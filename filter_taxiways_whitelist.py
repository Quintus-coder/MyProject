"""
filter_taxiways_whitelist.py
白名单方式筛选滑行道 - 只保留C和P0-P9
"""

import json
import os

def filter_taxiways_by_whitelist(json_file='runway_geometry.json'):
    """使用白名单筛选滑行道"""
    print("="*70)
    print("🔍 TAXIWAY WHITELIST FILTER - 18R/36L")
    print("="*70)
    
    # 白名单：只要这些滑行道
    whitelist = {
        'C',   # 平行滑行道
        'C4', 'C5',      # 平行滑行道分段
        'P0', 'P1', 'P2', 'P3',  # 快速出口
        'P6', 'P7', 'P8', 'P9'   # 快速出口
    }
    
    print(f"\n📋 Whitelist: {sorted(whitelist)}")
    print(f"   Target: {len(whitelist)} taxiways")
    
    # 加载数据
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    real_geom = data. get('real_geometry', {})
    all_taxiways = real_geom.get('taxiways', [])
    
    print(f"\n📊 Current status:")
    print(f"   Total taxiways: {len(all_taxiways)}")
    
    # 筛选
    filtered = []
    found_refs = set()
    duplicate_count = {}
    
    for tw in all_taxiways:
        ref = tw['ref']
        
        if ref in whitelist:
            # 统计重复
            if ref in found_refs:
                duplicate_count[ref] = duplicate_count.get(ref, 1) + 1
                print(f"   ⚠️  Duplicate: {ref} (segment {duplicate_count[ref] + 1})")
            else:
                found_refs.add(ref)
                print(f"   ✓ Found: {ref}")
            
            filtered.append(tw)
    
    # 检查缺失
    missing = whitelist - found_refs
    if missing:
        print(f"\n   ⚠️  Missing taxiways: {sorted(missing)}")
    
    # 统计
    print(f"\n📊 Results:")
    print(f"   Found unique:  {len(found_refs)}/{len(whitelist)}")
    print(f"   Total segments: {len(filtered)}")
    print(f"   Removed:  {len(all_taxiways) - len(filtered)}")
    
    # 按系列分类
    print(f"\n📂 By type:")
    print(f"   C (parallel): {sum(1 for tw in filtered if tw['ref'] == 'C')} segment(s)")
    p_count = sum(1 for tw in filtered if tw['ref']. startswith('P'))
    print(f"   P0-P9 (exits): {p_count} segment(s)")
    
    # 详细列表
    print(f"\n📋 Detailed list:")
    for ref in sorted(found_refs):
        segments = [tw for tw in filtered if tw['ref'] == ref]
        total_points = sum(len(tw['geometry']['local_coordinates']) for tw in segments)
        print(f"   {ref:4s}: {len(segments)} segment(s), {total_points} points total")
    
    # 保存
    real_geom['taxiways'] = filtered
    real_geom['taxiways_total'] = len(found_refs)
    real_geom['taxiways_segments'] = len(filtered)
    real_geom['filter_method'] = 'whitelist'
    real_geom['filter_whitelist'] = sorted(list(whitelist))
    
    data['real_geometry'] = real_geom
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved to: {json_file}")
    
    print("\n" + "="*70)
    print("✅ FILTERING COMPLETED")
    print("="*70)
    
    return len(found_refs), len(filtered)


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(base_dir, 'runway_geometry.json')
    
    if not os.path.exists(json_file):
        print(f"❌ Error: {json_file} not found")
        return 1
    
    unique, segments = filter_taxiways_by_whitelist(json_file)
    
    print(f"\n✨ Summary:")
    print(f"   Unique taxiways: {unique}")
    print(f"   Total segments: {segments}")
    print(f"\nNext step: Run cad_integrated. py to generate DXF")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())