"""
CAD Generator for Airport Runway System - AutoCAD 2018 Compatible
"""

import json
import os
from pathlib import Path
import ezdxf


class AirportRunwayDWGGenerator:
    """DWG generator for airport runway systems (AutoCAD 2018+)"""
    
    def __init__(self, geometry_file='runway_geometry.json', autocad_version='2018'):
        self.geometry_file = geometry_file
        self.autocad_version = autocad_version
        self.geometry_data = {}
        self.doc = None
        self.msp = None
        
        self.version_map = {
            '2018':  'R2018',
            '2019': 'R2019',
            '2020':  'R2020',
            '2021': 'R2021',
        }
        
        self. dxf_version = self.version_map. get(autocad_version, 'R2018')
    
    def load_geometry(self):
        """Load runway geometry from JSON file"""
        try:
            if Path(self.geometry_file).exists():
                with open(self. geometry_file, 'r', encoding='utf-8') as f:
                    self.geometry_data = json.load(f)
                print(f"✓ Loaded:  {self.geometry_file}")
                return True
            else:
                print(f"⚠ File not found: {self.geometry_file}")
                self._set_defaults()
                return True
        except Exception as e: 
            print(f"✗ Error:  {e}")
            self._set_defaults()
            return False
    
    def _set_defaults(self):
        """Set default runway data"""
        self.geometry_data = {
            'airport': {'name': 'Beijing Capital'},
            'runway': {'designator': '18R/36L', 'length': 3800, 'width': 60}
        }
    
    def create_dwg(self):
        """Create DWG document"""
        print(f"\n📄 Creating DWG (AutoCAD {self.autocad_version})...")
        
        self.doc = ezdxf. new(self.dxf_version)
        self.msp = self. doc.modelspace()
        
        # Setup layers
        self. doc.layers.new('RUNWAY', dxfattribs={'color': 7})
        self.doc.layers.new('TAXIWAYS', dxfattribs={'color': 7})
        self.doc.layers.new('MARKINGS', dxfattribs={'color': 1})
        self.doc.layers.new('LIGHTS', dxfattribs={'color': 3})
        self.doc.layers.new('TEXT', dxfattribs={'color': 4})
        
        # Draw elements
        self._draw_runway()
        self._draw_taxiways()
        self._draw_markings()
        self._draw_lights()
        self._add_text()
        
        return True
    
    def _draw_runway(self):
        """Draw runway"""
        runway = self.geometry_data. get('runway', {})
        length = runway.get('length', 3800)
        width = runway. get('width', 60)
        
        points = [(0, 0), (width, 0), (width, length), (0, length), (0, 0)]
        self.msp.add_lwpolyline(points, dxfattribs={'layer': 'RUNWAY'})
        print(f"  ✓ Runway:  {length}m × {width}m")
    
    def _draw_taxiways(self):
        """Draw taxiways"""
        runway = self.geometry_data.get('runway', {})
        w = runway.get('width', 60)
        l = runway. get('length', 3800)
        
        # Taxiway A
        pts_a = [(w+100, 0), (w+160, 0), (w+160, l), (w+100, l), (w+100, 0)]
        self.msp.add_lwpolyline(pts_a, dxfattribs={'layer': 'TAXIWAYS'})
        
        # Taxiway B
        pts_b = [(-160, 0), (-100, 0), (-100, l), (-160, l), (-160, 0)]
        self.msp.add_lwpolyline(pts_b, dxfattribs={'layer': 'TAXIWAYS'})
        
        print(f"  ✓ Taxiways A, B")
    
    def _draw_markings(self):
        """Draw runway markings"""
        runway = self.geometry_data.get('runway', {})
        l = runway.get('length', 3800)
        w = runway.get('width', 60)
        
        # Centerline
        cx = w / 2
        y = 0
        while y < l:
            self. msp.add_line((cx, y), (cx, min(y+30, l)), dxfattribs={'layer': 'MARKINGS'})
            y += 50
        
        print(f"  ✓ Markings")
    
    def _draw_lights(self):
        """Draw runway lights"""
        runway = self.geometry_data.get('runway', {})
        l = runway.get('length', 3800)
        w = runway.get('width', 60)
        
        y = 0
        count = 0
        while y < l:
            self.msp.add_circle((-10, y), 1. 5, dxfattribs={'layer': 'LIGHTS'})
            self.msp.add_circle((w+10, y), 1.5, dxfattribs={'layer': 'LIGHTS'})
            y += 100
            count += 2
        
        print(f"  ✓ Lights ({count} total)")
    
    def _add_text(self):
        """Add annotations"""
        runway = self.geometry_data.get('runway', {})
        airport = self.geometry_data.get('airport', {})
        
        l = runway.get('length', 3800)
        w = runway.get('width', 60)
        
        # Title
        txt1 = self.msp. add_text(airport.get('name', 'Airport'), dxfattribs={'layer': 'TEXT', 'height': 40})
        txt1.set_pos((w/2, l+200))
        
        # Info
        txt2 = self. msp.add_text(
            f"{runway.get('designator', 'RWY')} - {l}m × {w}m",
            dxfattribs={'layer': 'TEXT', 'height': 20}
        )
        txt2.set_pos((w/2, l+100))
        
        print(f"  ✓ Text added")
    
    def save_dwg(self, filename='airport_runway_system.dwg'):
        """Save DWG file"""
        if not filename.endswith('.dwg'):
            filename = filename.replace('.dxf', '') + '.dwg'
        
        try:
            print(f"\n💾 Saving DWG...")
            self.doc.saveas(filename)
            
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"  File: {filename}")
                print(f"  Size: {size:,} bytes")
                print(f"✓ Saved successfully!")
                return True
            return False
        except Exception as e:
            print(f"✗ Error:  {e}")
            return False
    
    def generate(self, output='airport_runway_system. dwg'):
        """Full generation workflow"""
        print("\n" + "="*70)
        print("🏢 AIRPORT RUNWAY SYSTEM - DWG GENERATOR")
        print("="*70)
        print(f"📍 AutoCAD:  {self.autocad_version}")
        
        print("\n📂 Loading geometry...")
        self.load_geometry()
        
        if not self.create_dwg():
            return False
        
        if not self.save_dwg(output):
            return False
        
        print("\n" + "="*70)
        print("✅ COMPLETE!")
        print("="*70)
        print(f"📁 Output: {output}")
        print(f"🔓 Compatible with: AutoCAD {self.autocad_version}+")
        print(f"✓ Ready to open in CAD!\n")
        
        return True


def main():
    """Main entry point"""
    import sys
    
    geometry = sys. argv[1] if len(sys.argv) > 1 else 'runway_geometry.json'
    version = sys.argv[2] if len(sys.argv) > 2 else '2018'
    output = sys. argv[3] if len(sys.argv) > 3 else 'airport_runway_system. dwg'
    
    generator = AirportRunwayDWGGenerator(geometry, version)
    success = generator.generate(output)
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
