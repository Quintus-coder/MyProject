# -*- coding: utf-8 -*-
"""
locate_zbaa_data.py
精确定位ZBAA_tables.json中18R的数据位置
"""

import json
import os
import re

def locate_runway_data(file_path='ZBAA_tables.json'):
    """定位跑道数据"""
    print("="*70)
    print("🔍 LOCATING 18R/36L DATA IN ZBAA_TABLES.JSON")
    print("="*70)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. 查找跑道尺寸表格
    print("\n📐 Looking for runway dimensions table...")
    for i, entry in enumerate(data):
        if 'data' not in entry:
            continue
        
        for row_idx, row in enumerate(entry['data']):
            if not isinstance(row, list):
                continue
            
            row_text = ' '.join(str(cell) for cell in row if cell)
            
            # 搜索包含"dimension"或"尺寸"的行
            if any(kw in row_text. lower() for kw in ['dimension', '尺寸', 'physical', '物理特性']):
                if '18r' in row_text. lower() or 'runway' in row_text.lower():
                    print(f"\n  ✓ Found at Entry[{i}], Row[{row_idx}]:")
                    print(f"    Page: {entry. get('page', '?')}")
                    print(f"    Row: {row}")
    
    # 2. 查找公布距离表格
    print("\n📏 Looking for declared distances (TORA/TODA/ASDA/LDA)...")
    for i, entry in enumerate(data):
        if 'data' not in entry:
            continue
        
        for row_idx, row in enumerate(entry['data']):
            if not isinstance(row, list):
                continue
            
            row_text = ' '.join(str(cell) for cell in row if cell)
            
            # 搜索包含TORA等的行
            if any(kw in row_text.upper() for kw in ['TORA', 'TODA', 'ASDA', 'LDA']):
                if '18r' in row_text. lower():
                    print(f"\n  ✓ Found at Entry[{i}], Row[{row_idx}]:")
                    print(f"    Page:  {entry.get('page', '?')}")
                    print(f"    Row: {row}")
    
    # 3. 查找RESA表格
    print("\n🚨 Looking for RESA...")
    for i, entry in enumerate(data):
        if 'data' not in entry:
            continue
        
        for row_idx, row in enumerate(entry['data']):
            if not isinstance(row, list):
                continue
            
            row_text = ' '.join(str(cell) for cell in row if cell)
            
            # 搜索RESA
            if 'resa' in row_text.lower() or '跑道端安全区' in row_text: 
                if '18r' in row_text.lower() or '240' in row_text or '90' in row_text:
                    print(f"\n  ✓ Found at Entry[{i}], Row[{row_idx}]:")
                    print(f"    Page: {entry.get('page', '?')}")
                    print(f"    Row: {row}")
    
    # 4. 查找所有包含18R和数字的表格（可能是尺寸）
    print("\n🔢 Looking for any 18R rows with numbers...")
    for i, entry in enumerate(data):
        if 'data' not in entry: 
            continue
        
        for row_idx, row in enumerate(entry['data']):
            if not isinstance(row, list):
                continue
            
            row_text = ' '.join(str(cell) for cell in row if cell)
            
            # 必须包含18R和至少一个3-4位数字
            if '18r' in row_text. lower() and re.search(r'\d{3,4}', row_text):
                # 排除已经显示过的
                if 'dimension' not in row_text.lower() and 'tora' not in row_text. lower():
                    print(f"\n  Entry[{i}], Row[{row_idx}]:")
                    print(f"    Page: {entry.get('page', '?')}")
                    print(f"    Content: {row_text[: 200]}")
    
    print("\n" + "="*70)
    print("✅ LOCATION SEARCH COMPLETED")
    print("="*70)


if __name__ == '__main__':
    locate_runway_data(os.path.join(os.path.dirname(__file__), 'ZBAA_tables.json'))