# -*- coding: utf-8 -*-
"""
analyze_zbaa_tables.py
分析ZBAA_tables.json的内容结构
"""

import json
import os

def analyze_zbaa_tables(file_path='ZBAA_tables.json'):
    """分析JSON文件结构"""
    print("="*70)
    print("🔍 ANALYZING ZBAA_TABLES.JSON")
    print("="*70)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    print(f"\n📋 File structure:")
    print(f"  Type: {type(data)}")
    
    if isinstance(data, list):
        print(f"  Length: {len(data)} entries")
        print(f"\n📊 Entry types:")
        
        # 分析每个条目
        for i, entry in enumerate(data[: 5]):  # 只看前5个
            print(f"\n  Entry {i}:")
            print(f"    Type: {type(entry)}")
            
            if isinstance(entry, dict):
                print(f"    Keys: {list(entry.keys())}")
                
                # 显示每个key的内容片段
                for key, value in entry.items():
                    if isinstance(value, str):
                        preview = value[:100] if len(value) > 100 else value
                        print(f"      {key}: '{preview}...'")
                    elif isinstance(value, list):
                        print(f"      {key}: list with {len(value)} items")
                        if value and len(value) > 0:
                            print(f"        First item: {value[0]}")
                    else:
                        print(f"      {key}:  {value}")
        
        if len(data) > 5:
            print(f"\n  ... and {len(data) - 5} more entries")
    
    elif isinstance(data, dict):
        print(f"  Keys: {list(data.keys())}")
        
        for key, value in data.items():
            print(f"\n  {key}:")
            print(f"    Type: {type(value)}")
            if isinstance(value, list):
                print(f"    Length: {len(value)}")
            elif isinstance(value, str):
                preview = value[:200]
                print(f"    Content: {preview}...")
    
    # 搜索18R相关内容
    print("\n" + "="*70)
    print("🔎 SEARCHING FOR '18R' CONTENT")
    print("="*70)
    
    def search_recursive(obj, path="root"):
        """递归搜索18R"""
        results = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}"
                if '18r' in str(key).lower() or '18r' in str(value).lower():
                    results.append((new_path, key, value))
                results.extend(search_recursive(value, new_path))
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                if '18r' in str(item).lower():
                    results.append((new_path, i, item))
                results.extend(search_recursive(item, new_path))
        
        elif isinstance(obj, str):
            if '18r' in obj.lower():
                results.append((path, None, obj))
        
        return results
    
    results = search_recursive(data)
    
    if results: 
        print(f"\n✓ Found {len(results)} mentions of '18R':")
        for path, key, value in results[: 10]:  # 显示前10个
            print(f"\n  Location: {path}")
            if isinstance(value, str):
                preview = value[:150] if len(value) > 150 else value
                print(f"    Content: {preview}")
            elif isinstance(value, list):
                print(f"    List with {len(value)} items:")
                for item in value[:3]: 
                    print(f"      - {item}")
            else:
                print(f"    Value: {value}")
        
        if len(results) > 10:
            print(f"\n  ... and {len(results) - 10} more")
    else:
        print("\n⚠️  No '18R' found in the file")
    
    # 搜索常见关键词
    print("\n" + "="*70)
    print("🔎 SEARCHING FOR COMMON KEYWORDS")
    print("="*70)
    
    keywords = ['RESA', 'strip', 'shoulder', 'TORA', 'TODA', 'ASDA', 'LDA', 
                'dimension', 'width', 'length', 'runway']
    
    all_text = json.dumps(data, ensure_ascii=False).lower()
    
    found_keywords = []
    for keyword in keywords:
        if keyword. lower() in all_text:
            count = all_text.count(keyword.lower())
            found_keywords.append((keyword, count))
    
    if found_keywords:
        print(f"\n✓ Found keywords:")
        for keyword, count in sorted(found_keywords, key=lambda x: x[1], reverse=True):
            print(f"  {keyword}: {count} occurrences")
    else:
        print("\n⚠️  No common keywords found")
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETED")
    print("="*70)


if __name__ == '__main__':
    base_path = os.path.dirname(__file__)
    analyze_zbaa_tables(os.path.join(base_path, 'ZBAA_tables.json'))