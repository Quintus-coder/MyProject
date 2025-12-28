"""
Airport Runway System CAD Generator
Generates comprehensive CAD drawings of airport runway systems including:
- Safety zones
- All 5 taxiways
- Aprons
- Detailed runway markings
- Lighting systems
Based on runway_geometry.json data
"""

import json
import math
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime


@dataclass
class Point:
    """Represents a 2D point in CAD space"""
    x: float
    y: float
    
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    
    def rotate(self, angle_deg: float, origin: 'Point' = None) -> 'Point':
        """Rotate point around origin by angle in degrees"""
        if origin is None:
            origin = Point(0, 0)
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        x = self.x - origin.x
        y = self.y - origin.y
        
        new_x = x * cos_a - y * sin_a + origin.x
        new_y = x * sin_a + y * cos_a + origin.y
        
        return Point(new_x, new_y)


@dataclass
class Rectangle:
    """Represents a rectangular region"""
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0  # degrees
    
    def corners(self) -> List[Point]:
        """Get corners of rectangle"""
        center = Point(self.x + self.width / 2, self.y + self.height / 2)
        corners = [
            Point(self.x, self.y),
            Point(self.x + self.width, self.y),
            Point(self.x + self.width, self.y + self.height),
            Point(self.x, self.y + self.height),
        ]
        if self.rotation != 0:
            corners = [c.rotate(self.rotation, center) for c in corners]
        return corners


class RunwayLighting:
    """Generates lighting system data"""
    
    def __init__(self, runway_length: float, runway_width: float):
        self.runway_length = runway_length
        self.runway_width = runway_width
    
    def generate_edge_lights(self, spacing: float = 60) -> List[Dict]:
        """Generate runway edge lighting"""
        lights = []
        half_width = self.runway_width / 2
        
        for i in range(int(self.runway_length / spacing)):
            y = i * spacing
            # Left edge lights
            lights.append({
                'type': 'edge',
                'position': {'x': -half_width, 'y': y},
                'color': 'white'
            })
            # Right edge lights
            lights.append({
                'type': 'edge',
                'position': {'x': half_width, 'y': y},
                'color': 'white'
            })
        
        return lights
    
    def generate_threshold_lights(self) -> List[Dict]:
        """Generate runway threshold lighting"""
        lights = []
        half_width = self.runway_width / 2
        
        # Threshold lights at start
        for i in range(6):
            offset = (i - 2.5) * (self.runway_width / 5)
            lights.append({
                'type': 'threshold',
                'position': {'x': offset, 'y': -50},
                'color': 'green'
            })
        
        # End lights
        for i in range(6):
            offset = (i - 2.5) * (self.runway_width / 5)
            lights.append({
                'type': 'end',
                'position': {'x': offset, 'y': self.runway_length + 50},
                'color': 'red'
            })
        
        return lights
    
    def generate_touchdown_lights(self) -> List[Dict]:
        """Generate touchdown zone lighting"""
        lights = []
        half_width = self.runway_width / 2
        td_start = self.runway_length * 0.25
        td_length = self.runway_length * 0.5
        
        for i in range(int(td_length / 150)):
            y = td_start + i * 150
            for j in range(3):
                offset = (j - 1) * (self.runway_width / 3)
                lights.append({
                    'type': 'touchdown',
                    'position': {'x': offset, 'y': y},
                    'color': 'white'
                })
        
        return lights


class RunwayMarkings:
    """Generates detailed runway markings"""
    
    @staticmethod
    def generate_centerline(length: float, spacing: float = 60) -> List[Dict]:
        """Generate runway centerline markings"""
        markings = []
        dash_length = 36
        gap = spacing - dash_length
        
        for i in range(int(length / spacing)):
            start_y = i * spacing
            markings.append({
                'type': 'centerline',
                'start': {'x': 0, 'y': start_y},
                'end': {'x': 0, 'y': start_y + dash_length},
                'width': 0.6
            })
        
        return markings
    
    @staticmethod
    def generate_threshold_markings(width: float) -> List[Dict]:
        """Generate runway threshold markings"""
        markings = []
        bar_count = int(width / 3)
        
        for i in range(bar_count):
            x = (i - bar_count / 2 + 0.5) * 3
            markings.append({
                'type': 'threshold_bar',
                'x': x,
                'y': -30,
                'length': 3
            })
        
        return markings
    
    @staticmethod
    def generate_touchdown_markings(length: float, width: float) -> List[Dict]:
        """Generate touchdown zone markings"""
        markings = []
        td_start = length * 0.25
        td_length = length * 0.5
        
        for zone in range(3):
            y = td_start + zone * (td_length / 3)
            for side in [-1, 1]:
                x = side * (width / 3)
                markings.append({
                    'type': 'touchdown_mark',
                    'position': {'x': x, 'y': y},
                    'size': 9
                })
        
        return markings


class TaxiwaySystem:
    """Generates all 5 taxiways"""
    
    def __init__(self, runway_geometry: Dict):
        self.runway_geometry = runway_geometry
        self.runway_length = runway_geometry.get('length', 3000)
        self.runway_width = runway_geometry.get('width', 45)
    
    def generate_taxiways(self) -> List[Dict]:
        """Generate all 5 taxiways"""
        taxiways = []
        
        # Taxiway A (main parallel)
        taxiways.append(self._generate_taxiway_a())
        
        # Taxiway B (connecting)
        taxiways.append(self._generate_taxiway_b())
        
        # Taxiway C (connecting)
        taxiways.append(self._generate_taxiway_c())
        
        # Taxiway D (rapid exit)
        taxiways.append(self._generate_taxiway_d())
        
        # Taxiway E (rapid exit)
        taxiways.append(self._generate_taxiway_e())
        
        return taxiways
    
    def _generate_taxiway_a(self) -> Dict:
        """Main parallel taxiway A"""
        width = 35
        offset = self.runway_width / 2 + 100
        return {
            'name': 'Taxiway A',
            'type': 'main_parallel',
            'width': width,
            'length': self.runway_length,
            'position': {'x': offset, 'y': 0},
            'surface': 'asphalt'
        }
    
    def _generate_taxiway_b(self) -> Dict:
        """Connecting taxiway B"""
        return {
            'name': 'Taxiway B',
            'type': 'connecting',
            'width': 23,
            'start': {'x': 200, 'y': 0},
            'end': {'x': self.runway_width / 2 + 100, 'y': 200},
            'surface': 'asphalt'
        }
    
    def _generate_taxiway_c(self) -> Dict:
        """Connecting taxiway C"""
        return {
            'name': 'Taxiway C',
            'type': 'connecting',
            'width': 23,
            'start': {'x': 800, 'y': 0},
            'end': {'x': self.runway_width / 2 + 100, 'y': 300},
            'surface': 'asphalt'
        }
    
    def _generate_taxiway_d(self) -> Dict:
        """Rapid exit taxiway D"""
        return {
            'name': 'Taxiway D',
            'type': 'rapid_exit',
            'width': 25,
            'start': {'x': 0, 'y': self.runway_length * 0.5},
            'end': {'x': self.runway_width / 2 + 100, 'y': self.runway_length * 0.5 + 300},
            'surface': 'asphalt'
        }
    
    def _generate_taxiway_e(self) -> Dict:
        """Rapid exit taxiway E"""
        return {
            'name': 'Taxiway E',
            'type': 'rapid_exit',
            'width': 25,
            'start': {'x': 0, 'y': self.runway_length * 0.75},
            'end': {'x': self.runway_width / 2 + 100, 'y': self.runway_length * 0.75 + 250},
            'surface': 'asphalt'
        }


class SafetyZones:
    """Generates safety zone configurations"""
    
    def __init__(self, runway_geometry: Dict):
        self.runway_geometry = runway_geometry
        self.runway_length = runway_geometry.get('length', 3000)
        self.runway_width = runway_geometry.get('width', 45)
    
    def generate_zones(self) -> List[Dict]:
        """Generate all safety zones"""
        zones = []
        
        # Runway Safety Area (RSA)
        zones.append(self._generate_rsa())
        
        # Obstacle Free Zone (OFZ)
        zones.append(self._generate_ofz())
        
        # Runway Object Free Area (ROFA)
        zones.append(self._generate_rofa())
        
        # Blast Pad
        zones.append(self._generate_blast_pad())
        
        # Stopway
        zones.append(self._generate_stopway())
        
        return zones
    
    def _generate_rsa(self) -> Dict:
        """Runway Safety Area"""
        return {
            'name': 'Runway Safety Area',
            'type': 'RSA',
            'length': self.runway_length + 600,
            'width': self.runway_width + 150,
            'surface_type': 'clear',
            'purpose': 'Emergency recovery area'
        }
    
    def _generate_ofz(self) -> Dict:
        """Obstacle Free Zone"""
        return {
            'name': 'Obstacle Free Zone',
            'type': 'OFZ',
            'length': self.runway_length,
            'width': self.runway_width + 50,
            'height_limit': 35,
            'purpose': 'Aircraft clearance'
        }
    
    def _generate_rofa(self) -> Dict:
        """Runway Object Free Area"""
        return {
            'name': 'Runway Object Free Area',
            'type': 'ROFA',
            'width': self.runway_width + 80,
            'length': self.runway_length,
            'purpose': 'Object free surface'
        }
    
    def _generate_blast_pad(self) -> Dict:
        """Blast Pad for high-power aircraft"""
        return {
            'name': 'Blast Pad',
            'type': 'blast_pad',
            'length': 300,
            'width': self.runway_width + 150,
            'position': 'runway_end',
            'surface': 'reinforced_concrete'
        }
    
    def _generate_stopway(self) -> Dict:
        """Additional stopway for go-around"""
        return {
            'name': 'Stopway',
            'type': 'stopway',
            'length': 300,
            'width': self.runway_width,
            'position': 'runway_end',
            'surface': 'asphalt'
        }


class ApronSystem:
    """Generates apron configurations"""
    
    def __init__(self, runway_geometry: Dict):
        self.runway_geometry = runway_geometry
        self.runway_width = runway_geometry.get('width', 45)
    
    def generate_aprons(self) -> List[Dict]:
        """Generate apron areas"""
        aprons = []
        
        # Runway Apron
        aprons.append({
            'name': 'Runway Apron',
            'type': 'runway_apron',
            'length': 500,
            'width': self.runway_width + 200,
            'position': {'x': 0, 'y': 0},
            'surface': 'asphalt'
        })
        
        # Terminal Apron
        aprons.append({
            'name': 'Terminal Apron',
            'type': 'terminal_apron',
            'length': 400,
            'width': 600,
            'position': {'x': self.runway_width / 2 + 100, 'y': -400},
            'surface': 'asphalt',
            'gates': 6
        })
        
        # Cargo Apron
        aprons.append({
            'name': 'Cargo Apron',
            'type': 'cargo_apron',
            'length': 300,
            'width': 400,
            'position': {'x': self.runway_width / 2 + 100, 'y': 500},
            'surface': 'asphalt'
        })
        
        # Maintenance Apron
        aprons.append({
            'name': 'Maintenance Apron',
            'type': 'maintenance_apron',
            'length': 250,
            'width': 350,
            'position': {'x': self.runway_width / 2 + 550, 'y': 800},
            'surface': 'concrete'
        })
        
        return aprons


class AirportCADGenerator:
    """Main CAD generator for airport runway systems"""
    
    def __init__(self, runway_geometry_file: str = 'runway_geometry.json'):
        self.runway_geometry_file = runway_geometry_file
        self.runway_geometry = self._load_geometry()
        self.timestamp = datetime.utcnow().isoformat() + 'Z'
    
    def _load_geometry(self) -> Dict:
        """Load runway geometry from JSON file"""
        try:
            if os.path.exists(self.runway_geometry_file):
                with open(self.runway_geometry_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading geometry file: {e}")
        
        # Default geometry if file not found
        return {
            'length': 3000,
            'width': 45,
            'elevation': 100,
            'heading': 180,
            'surface_type': 'asphalt'
        }
    
    def generate_complete_cad(self) -> Dict:
        """Generate complete CAD data for airport"""
        cad_data = {
            'metadata': {
                'project': 'Airport Runway System CAD',
                'version': '2.0',
                'generated': self.timestamp,
                'generator': 'AirportCADGenerator',
                'runway_geometry_source': self.runway_geometry_file
            },
            'runway': {
                'geometry': self.runway_geometry,
                'markings': RunwayMarkings.generate_centerline(
                    self.runway_geometry.get('length', 3000)
                ) + RunwayMarkings.generate_threshold_markings(
                    self.runway_geometry.get('width', 45)
                ) + RunwayMarkings.generate_touchdown_markings(
                    self.runway_geometry.get('length', 3000),
                    self.runway_geometry.get('width', 45)
                )
            },
            'lighting': {
                'edge': RunwayLighting(
                    self.runway_geometry.get('length', 3000),
                    self.runway_geometry.get('width', 45)
                ).generate_edge_lights(),
                'threshold': RunwayLighting(
                    self.runway_geometry.get('length', 3000),
                    self.runway_geometry.get('width', 45)
                ).generate_threshold_lights(),
                'touchdown': RunwayLighting(
                    self.runway_geometry.get('length', 3000),
                    self.runway_geometry.get('width', 45)
                ).generate_touchdown_lights()
            },
            'safety_zones': SafetyZones(self.runway_geometry).generate_zones(),
            'taxiways': TaxiwaySystem(self.runway_geometry).generate_taxiways(),
            'aprons': ApronSystem(self.runway_geometry).generate_aprons()
        }
        
        return cad_data
    
    def export_to_json(self, output_file: str = 'airport_cad.json') -> str:
        """Export CAD data to JSON file"""
        cad_data = self.generate_complete_cad()
        with open(output_file, 'w') as f:
            json.dump(cad_data, f, indent=2)
        return output_file
    
    def export_to_dxf_format(self, output_file: str = 'airport_cad.dxf') -> str:
        """Export CAD data in DXF-compatible format"""
        cad_data = self.generate_complete_cad()
        
        dxf_content = self._generate_dxf_header()
        
        # Add runway
        dxf_content += self._add_dxf_rectangle(
            0, 0,
            self.runway_geometry.get('width', 45),
            self.runway_geometry.get('length', 3000),
            'RUNWAY', 'white'
        )
        
        # Add taxiways
        for taxiway in cad_data['taxiways']:
            if 'length' in taxiway:
                dxf_content += self._add_dxf_rectangle(
                    taxiway['position']['x'], taxiway['position']['y'],
                    taxiway['width'], taxiway['length'],
                    taxiway['name'], 'yellow'
                )
        
        # Add aprons
        for apron in cad_data['aprons']:
            dxf_content += self._add_dxf_rectangle(
                apron['position']['x'], apron['position']['y'],
                apron['width'], apron['length'],
                apron['name'], 'gray'
            )
        
        dxf_content += self._generate_dxf_footer()
        
        with open(output_file, 'w') as f:
            f.write(dxf_content)
        
        return output_file
    
    def _generate_dxf_header(self) -> str:
        """Generate DXF file header"""
        return """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1021
  9
$EXTMIN
 10
0
 20
0
  9
$EXTMAX
 10
5000
 20
5000
  0
ENDSEC
  0
SECTION
  2
TABLES
  0
TABLE
  2
LAYER
 70
10
  0
LAYER
  2
RUNWAY
 70
0
 62
7
  6
CONTINUOUS
  0
LAYER
  2
TAXIWAY
 70
0
 62
2
  6
CONTINUOUS
  0
LAYER
  2
APRON
 70
0
 62
8
  6
CONTINUOUS
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
ENDTAB
  0
SECTION
  2
BLOCKS
  0
ENDBLK
  0
ENDSEC
  0
SECTION
  2
ENTITIES
"""
    
    def _generate_dxf_footer(self) -> str:
        """Generate DXF file footer"""
        return """  0
ENDSEC
  0
EOF
"""
    
    def _add_dxf_rectangle(self, x: float, y: float, width: float, 
                          height: float, name: str, color: str) -> str:
        """Add a rectangle to DXF content"""
        color_code = {'white': 7, 'yellow': 2, 'gray': 8, 'green': 3, 'red': 1}[color]
        return f"""  0
LWPOLYLINE
  5
{id(name)}
330
1F
100
AcDbEntity
  8
{name}
 62
{color_code}
370
-1
100
AcDbLwPolyline
 90
4
 70
1
 43
0.0
 10
{x}
 20
{y}
 10
{x + width}
 20
{y}
 10
{x + width}
 20
{y + height}
 10
{x}
 20
{y + height}
"""


def main():
    """Main execution function"""
    print("Airport Runway System CAD Generator")
    print("=" * 50)
    
    # Initialize generator
    generator = AirportCADGenerator()
    
    # Generate JSON output
    print("Generating CAD data...")
    json_file = generator.export_to_json()
    print(f"✓ JSON export: {json_file}")
    
    # Generate DXF output
    dxf_file = generator.export_to_dxf_format()
    print(f"✓ DXF export: {dxf_file}")
    
    # Display summary
    cad_data = generator.generate_complete_cad()
    print("\nCAD System Summary:")
    print(f"  Runway Length: {cad_data['runway']['geometry'].get('length', 'N/A')} m")
    print(f"  Runway Width: {cad_data['runway']['geometry'].get('width', 'N/A')} m")
    print(f"  Runway Markings: {len(cad_data['runway']['markings'])} elements")
    print(f"  Safety Zones: {len(cad_data['safety_zones'])}")
    print(f"  Taxiways: {len(cad_data['taxiways'])}")
    print(f"  Aprons: {len(cad_data['aprons'])}")
    print(f"  Lighting Systems:")
    print(f"    - Edge Lights: {len(cad_data['lighting']['edge'])}")
    print(f"    - Threshold Lights: {len(cad_data['lighting']['threshold'])}")
    print(f"    - Touchdown Lights: {len(cad_data['lighting']['touchdown'])}")
    print("\n✓ CAD generation complete!")


if __name__ == '__main__':
    main()
