# -*- coding: utf-8 -*-
"""
airport_parameters.py (改进版 v2.0)
智能参数获取系统：从ZBAA_tables. json精确提取数据
根据定位结果，数据位于第16-17页
"""

import json
import os
import re
from typing import Dict, Any, Optional, Tuple


class AirportParameterExtractor:
    """机场参数提取器 - 精确适配ZBAA_tables.json格式"""
    
    def __init__(self, tables_file: str = 'ZBAA_tables.json'):
        self.tables_file = tables_file
        self. tables_data = None
        self.runway_designator = "18R"
        
        self._load_tables()
    
    def _load_tables(self):
        """加载ZBAA_tables.json"""
        try:
            with open(self.tables_file, 'r', encoding='utf-8') as f:
                self. tables_data = json.load(f)
            print(f"✓ Loaded {self.tables_file} ({len(self.tables_data)} entries)")
        except FileNotFoundError:
            print(f"⚠ {self.tables_file} not found, will use standards")
            self.tables_data = None
        except Exception as e:
            print(f"⚠ Error loading:  {e}")
            self.tables_data = None
    
    def _search_by_page_and_keywords(self, page_num: int, keywords: list) -> list:
        """
        精确搜索：指定页码和关键词
        
        Args:
            page_num: 页码
            keywords:  必须包含的关键词列表
        
        Returns:
            匹配的行列表
        """
        if not self.tables_data:
            return []
        
        results = []
        
        for entry in self.tables_data:
            # 检查页码
            if entry.get('page') != page_num:
                continue
            
            data_rows = entry.get('data', [])
            if not isinstance(data_rows, list):
                continue
            
            # 遍历该页的每一行
            for row_idx, row in enumerate(data_rows):
                if not isinstance(row, list):
                    continue
                
                # 将行转换为文本
                row_text = ' '.join(str(cell) for cell in row if cell is not None)
                
                # 检查是否包含所有关键词
                if all(kw. lower() in row_text.lower() for kw in keywords):
                    results.append({
                        'row_index': row_idx,
                        'row':  row,
                        'text':  row_text
                    })
        
        return results
    
    def _extract_dimensions(self, text: str) -> Optional[Tuple[float, float]]:
        """
        从文本中提取尺寸（如 "3200×50"）
        
        Returns:
            (长度, 宽度) 或 None
        """
        if not text:
            return None
        
        patterns = [
            r'(\d{2,5})\s*[×xX*]\s*(\d{2,4})',      # 3200×50
            r'(\d{2,5})\s*[mM]\s*[×xX]\s*(\d{2,4})', # 3200m×50
        ]
        
        for pattern in patterns:
            match = re. search(pattern, text)
            if match:
                return (float(match.group(1)), float(match.group(2)))
        
        return None
    
    def _extract_numbers(self, text: str, count: int = None) -> list:
        """
        提取文本中的所有数字
        
        Args:
            text: 文本
            count: 期望的数字数量
        
        Returns:
            数字列表
        """
        if not text:
            return []
        
        numbers = re. findall(r'\d{2,5}(?:\.\d+)?', text)
        numbers = [float(n) for n in numbers]
        
        if count: 
            return numbers[:count]
        return numbers
    
    # ========== 参数获取方法 ==========
    
    def get_runway_dimensions(self) -> Dict[str, float]:
        """
        获取跑道尺寸
        
        数据位置:  Page 16, Entry[23], Row[3]
        格式: "18R ...  3200×50 ..."
        
        Returns:
            {'length': 3200, 'width': 50}
        """
        print("\n🔍 Getting runway dimensions...")
        
        # 精确搜索：第16页，包含"18R"和"×"
        results = self._search_by_page_and_keywords(16, ['18R', '×'])
        
        for result in results:
            text = result['text']
            dims = self._extract_dimensions(text)
            
            if dims:
                # 验证是否是合理的跑道尺寸
                length, width = dims
                if 3000 <= length <= 4000 and 40 <= width <= 60:
                    print(f"  ✓ From ZBAA_tables (Page 16, Row {result['row_index']})")
                    print(f"    {length}m × {width}m")
                    return {'length':  length, 'width': width}
        
        # 备用方案：使用ICAO标准
        print(f"  ⚠ Not found in tables")
        print(f"  ✓ ICAO standard (Code 4E): 3200m × 50m")
        return {'length': 3200.0, 'width':  50.0}
    
    def get_shoulder_width(self) -> float:
        """
        获取道肩宽度
        
        注意:  通常不在表格中，使用ICAO标准
        
        Returns:
            宽度（米）
        """
        print("\n🔍 Getting shoulder width...")
        
        # 尝试搜索（通常找不到）
        results = self._search_by_page_and_keywords(16, ['18R', 'shoulder'])
        if not results:
            results = self._search_by_page_and_keywords(16, ['shoulder', '道肩'])
        
        for result in results:
            text = result['text']
            match = re.search(r'shoulder.*?(\d+\. ?\d*)\s*m', text, re.IGNORECASE)
            if match: 
                width = float(match.group(1))
                print(f"  ✓ From ZBAA_tables:  {width}m")
                return width
        
        # 使用ICAO标准
        print(f"  ⚠ Not found in tables")
        print(f"  ✓ ICAO Annex 14, Table 3-1 (Code 4E): 7.5m")
        return 7.5
    
    def get_strip_dimensions(self) -> Dict[str, float]:
        """
        获取升降带尺寸
        
        数据位置: Page 16, Entry[23], Row[11]
        格式: "18R Nil Nil 3320×280 240×100 ..."
        
        Returns:
            {'length':  3320, 'width':  280}
        """
        print("\n🔍 Getting strip dimensions...")
        
        # 精确搜索：第16页，包含"18R"和"3320"
        results = self._search_by_page_and_keywords(16, ['18R'])
        
        for result in results:
            text = result['text']
            
            # 查找 3320×280 格式
            match = re.search(r'(3\d{3})\s*[×xX]\s*(\d{3})', text)
            if match:
                length = float(match.group(1))
                width = float(match.group(2))
                
                # 验证是否是升降带尺寸（比跑道长且宽）
                if length > 3000 and width > 100:
                    print(f"  ✓ From ZBAA_tables (Page 16, Row {result['row_index']})")
                    print(f"    {length}m × {width}m")
                    return {'length': length, 'width': width}
        
        # 备用方案：使用ICAO标准
        print(f"  ⚠ Not found in tables")
        print(f"  ✓ ICAO Annex 14, Table 3-1 (Code 4, Precision): 150m width")
        
        runway_dims = self.get_runway_dimensions()
        return {
            'length': runway_dims['length'] + 120,  # 跑道长度 + 2×60m
            'width': 150.0
        }
    
    def get_resa_dimensions(self) -> Dict[str, float]: 
        """
        获取RESA尺寸
        
        数据位置: Page 16, Entry[23], Row[11]
        格式: "18R Nil Nil 3320×280 240×100 ..."
        
        Returns:
            {'length': 240, 'width': 100}
        """
        print("\n🔍 Getting RESA dimensions...")
        
        # 精确搜索：第16页，包含"18R"和"240"
        results = self._search_by_page_and_keywords(16, ['18R', '240'])
        
        for result in results:
            text = result['text']
            
            # 查找 240×数字 格式
            match = re.search(r'240\s*[×xX]\s*(\d{2,3})', text)
            if match:
                width = float(match.group(1))
                print(f"  ✓ From ZBAA_tables (Page 16, Row {result['row_index']})")
                print(f"    240m × {width}m")
                return {'length': 240.0, 'width': width}
        
        # 备用方案：使用ICAO标准
        print(f"  ⚠ Not found in tables")
        print(f"  ✓ ICAO Annex 14, 3. 5. 5 (Code 4, recommended): 240m × 90m")
        return {'length': 240.0, 'width': 90.0}
    
    def get_declared_distances(self) -> Dict[str, float]:
        """
        获取公布距离
        
        数据位置: Page 17, Entry[24], Row[14]
        格式: "18R 3200 3200 3200 3200 Nil"
        顺序:  TORA TODA ASDA LDA
        
        Returns:
            {'TORA': 3200, 'TODA': 3200, 'ASDA': 3200, 'LDA':  3200}
        """
        print("\n🔍 Getting declared distances...")
        
        # 精确搜索：第17页，包含"18R"
        results = self._search_by_page_and_keywords(17, ['18R'])
        
        for result in results:
            text = result['text']
            numbers = self._extract_numbers(text)
            
            # 查找包含四个相同或相近数字的行（TORA/TODA/ASDA/LDA）
            if len(numbers) >= 4:
                # 检查前四个数字是否都在3000-3500范围内
                if all(3000 <= n <= 3500 for n in numbers[: 4]):
                    distances = {
                        'TORA': numbers[0],
                        'TODA': numbers[1],
                        'ASDA': numbers[2],
                        'LDA': numbers[3]
                    }
                    print(f"  ✓ From ZBAA_tables (Page 17, Row {result['row_index']})")
                    for key, value in distances.items():
                        print(f"    {key}: {value}m")
                    return distances
        
        # 备用方案：使用跑道长度
        print(f"  ⚠ Not found in tables")
        runway_dims = self.get_runway_dimensions()
        default = runway_dims['length']
        
        distances = {
            'TORA': default,
            'TODA': default,
            'ASDA': default,
            'LDA': default
        }
        print(f"  ✓ Using runway length: {default}m")
        return distances
    
    def get_marking_dimensions(self) -> Dict[str, Any]:
        """
        获取跑道标记尺寸
        
        注意: 标记尺寸通常不在表格中，使用ICAO Annex 14标准
        
        Returns: 
            包含各种标记尺寸的字典
        """
        print("\n🔍 Getting marking dimensions...")
        print(f"  ⚠ Marking dimensions not in tables")
        print(f"  ✓ Using ICAO Annex 14, Chapter 5 standards")
        
        return {
            # 入口标志（钢琴键）
            'threshold': {
                'stripe_width': 3.0,     # ICAO:  1.8-5.7m
                'stripe_length': 45.0,   # ICAO: 30-50m (Code 4)
                'stripe_gap': 3.0,
                'source':  'ICAO Annex 14, Figure 5-7'
            },
            
            # 接地带标记（TDZ）
            'tdz': {
                'bar_width': 4.0,         # ICAO: 3m
                'bar_length': 22.5,       # ICAO: 22.5m
                'bar_spacing': 150.0,     # ICAO: 150m
                'start_distance': 150.0,  # ICAO: 150m from threshold
                'pairs': 3,               # CAT I: 3 pairs
                'source': 'ICAO Annex 14, Section 5.2. 3. 7'
            },
            
            # 瞄准点标记
            'aiming_point': {
                'bar_width': 6.0,
                'bar_length': 90.0,
                'distance_from_threshold': 300.0,  # ICAO: 250-400m
                'source': 'ICAO Annex 14, Section 5.2.3.5'
            },
            
            # 中心线虚线
            'centerline': {
                'dash_length': 30.0,      # ICAO: 30-50m
                'gap_length': 20.0,       # ICAO: 15-30m
                'source':  'ICAO Annex 14, Section 5.2.3.2'
            }
        }
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        获取所有参数
        
        Returns:
            完整的参数字典
        """
        print("\n" + "="*70)
        print("📊 EXTRACTING ZBAA 18R/36L PARAMETERS")
        print("="*70)
        
        params = {
            'runway':  self.get_runway_dimensions(),
            'shoulder_width': self.get_shoulder_width(),
            'strip': self.get_strip_dimensions(),
            'resa': self.get_resa_dimensions(),
            'declared_distances': self.get_declared_distances(),
            'markings': self.get_marking_dimensions()
        }
        
        print("\n" + "="*70)
        print("✅ PARAMETER EXTRACTION COMPLETED")
        print("="*70)
        
        return params
    
    def print_summary(self, params: Dict[str, Any]):
        """打印参数摘要"""
        print("\n" + "="*70)
        print("📋 PARAMETER SUMMARY - ZBAA 18R/36L")
        print("="*70)
        
        print(f"\n🛫 Runway:")
        print(f"  Length: {params['runway']['length']}m")
        print(f"  Width:   {params['runway']['width']}m")
        
        print(f"\n📏 Shoulders:")
        print(f"  Width:  {params['shoulder_width']}m (each side)")
        
        print(f"\n📐 Strip:")
        print(f"  Length: {params['strip']['length']}m")
        print(f"  Width:  {params['strip']['width']}m")
        
        print(f"\n🚨 RESA:")
        print(f"  Length: {params['resa']['length']}m")
        print(f"  Width:   {params['resa']['width']}m")
        
        print(f"\n📊 Declared Distances:")
        for key, value in params['declared_distances'].items():
            print(f"  {key}: {value}m")
        
        print(f"\n🎨 Markings:  ICAO Annex 14 standards")
        
        print("\n" + "="*70)


def test_extractor():
    """测试提取器"""
    base_path = os.path.dirname(__file__)
    extractor = AirportParameterExtractor(os.path.join(base_path, 'ZBAA_tables.json'))
    params = extractor.get_all_parameters()
    extractor.print_summary(params)
    
    return params


if __name__ == '__main__':
    test_extractor()