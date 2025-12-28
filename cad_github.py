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
            'airport':  {'name': 'Beijing Capital Airport'},
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
            'LIGHTS': 3,
            'TEXT': 4
        }
        
        for name, color in layers.items():
            try:
                self.doc.layers.new(name=name, dxfattribs={'color': color})
            except: 
                pass  # Layer already exists
    
    def _draw_runway(self):
        """Draw runway"""
        runway = self.geometry_data.get('runway', {})
        length = runway.get('length', 3800)
        width = runway.get('width', 60)
        
        # Draw rectangle
        points = [(0, 0), (width, 0), (width, length), (0, length)]
        pline = self.msp.add_lwpolyline(points, dxfattribs={'layer': 'RUNWAY'})
        pline.close()
        
        print(f"  ✓ Runway: {length}m × {width}m")
    
    def _draw_taxiways(self):
        """Draw taxiways"""
        runway = self.geometry_data.get('runway', {})
        w = runway.get('width', 60)
        l = runway.get('length', 3800)
        
        # Taxiway A
        pts_a = [(w+100, 0), (w+160, 0), (w+160, l), (w+100, l)]
        pline_a = self.msp.add_lwpolyline(pts_a, dxfattribs={'layer': 'TAXIWAYS'})
        pline_a.close()
        
        # Taxiway B
        pts_b = [(-160, 0), (-100, 0), (-100, l), (-160, l)]
        pline_b = self.msp.add_lwpolyline(pts_b, dxfattribs={'layer': 'TAXIWAYS'})
        pline_b.close()
        
        print(f"  ✓ Taxiways A, B")
    
    def _draw_markings(self):
        """Draw markings"""
        runway = self.geometry_data.get('runway', {})
        l = runway.get('length', 3800)
        w = runway.get('width', 60)
        
        cx = w / 2
        y = 0
        while y < l:
            self.msp.add_line(
                (cx, y),
                (cx, min(y + 30, l)),
                dxfattribs={'layer': 'MARKINGS'}
            )
            y += 50
        
        print(f"  ✓ Markings")
    
    def _draw_lights(self):
        """Draw lights"""
        runway = self.geometry_data.get('runway', {})
        l = runway.get('length', 3800)
        w = runway.get('width', 60)
        
        y = 0
        count = 0
        while y < l:
            self.msp.add_circle((-10, y), 1.5, dxfattribs={'layer': 'LIGHTS'})
            self.msp.add_circle((w + 10, y), 1.5, dxfattribs={'layer': 'LIGHTS'})
            y += 100
            count += 2
        
        print(f"  ✓ Lights ({count} total)")
    
    def _add_annotations(self):
        """Add annotations"""
        runway = self.geometry_data.get('runway', {})
        airport = self.geometry_data.get('airport', {})
        
        # Simple text without positioning
        self.msp.add_text(
            airport.get('name', 'Airport'),
            dxfattribs={'layer': 'TEXT', 'height': 20}
        )
        
        self.msp.add_text(
            f"RWY {runway.get('designator', '??')}",
            dxfattribs={'layer': 'TEXT', 'height': 15}
        )
        
        print(f"  ✓ Annotations")
    
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

    def save_dxf(self, filename='airport_runway_system_R2010.dxf'):
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
    
    def generate(self, output='airport_runway_system_R2010.dxf'):
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
    output = sys.argv[2] if len(sys.argv) > 2 else 'airport_runway_system_R2010.dxf'
    
    gen = AirportRunwayDXFGenerator(geometry)
    return 0 if gen.generate(output) else 1


if __name__ == '__main__':
    exit(main())