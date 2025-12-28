"""
Multi-Layer DXF Generator for Airport Runway Systems
Generates comprehensive CAD drawings with 6 specialized layers
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import ezdxf
from ezdxf.entities import DXFEntity
from ezdxf.addons import Hatch


class AirportRunwayDXFGenerator:
    """
    Comprehensive DXF generator for airport runway systems.
    Reads runway_geometry.json and generates multi-layer CAD drawings.
    """
    
    # Layer definitions
    LAYERS = {
        'runway_taxiways': {'color': 7, 'linetype': 'CONTINUOUS', 'description': 'Runway and Taxiways'},
        'runway_markings': {'color': 1, 'linetype': 'CONTINUOUS', 'description': 'Runway Markings'},
        'lighting_systems': {'color': 3, 'linetype': 'CONTINUOUS', 'description': 'Lighting Systems'},
        'safety_zones': {'color': 6, 'linetype': 'DASHED', 'description': 'Safety Zones'},
        'equipment_facilities': {'color': 5, 'linetype': 'CONTINUOUS', 'description': 'Equipment and Facilities'},
        'annotations': {'color': 2, 'linetype': 'CONTINUOUS', 'description': 'Annotations'}
    }
    
    def __init__(self, geometry_file: str = 'runway_geometry.json'):
        """
        Initialize the DXF generator.
        
        Args:
            geometry_file: Path to the runway geometry JSON file
        """
        self.geometry_file = geometry_file
        self.geometry_data = {}
        self.dxf = None
        self.msp = None
        
    def load_geometry(self) -> bool:
        """
        Load runway geometry from JSON file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if Path(self.geometry_file).exists():
                with open(self.geometry_file, 'r') as f:
                    self.geometry_data = json.load(f)
                print(f"✓ Loaded geometry from {self.geometry_file}")
                return True
            else:
                print(f"⚠ Geometry file not found: {self.geometry_file}")
                print("  Using default runway configuration")
                self.geometry_data = self._get_default_geometry()
                return True
        except Exception as e:
            print(f"✗ Error loading geometry: {e}")
            self.geometry_data = self._get_default_geometry()
            return False
    
    def _get_default_geometry(self) -> Dict:
        """
        Get default runway geometry configuration.
        
        Returns:
            dict: Default geometry configuration
        """
        return {
            'runway': {
                'length': 3660,
                'width': 60,
                'heading': 0,
                'position': [0, 0]
            },
            'taxiways': [
                {
                    'name': 'Taxiway A',
                    'width': 35,
                    'points': [[100, -500], [100, 3500], [150, 3660]]
                },
                {
                    'name': 'Taxiway B',
                    'width': 35,
                    'points': [[-100, 500], [-100, 3000], [-150, 3660]]
                }
            ],
            'runway_markings': {
                'centerline': True,
                'threshold_markings': True,
                'zone_markings': True
            },
            'lighting': [
                {'type': 'runway_lights', 'spacing': 100},
                {'type': 'taxiway_lights', 'spacing': 50}
            ],
            'safety_zones': {
                'fato': {'distance': 120},
                'resa': {'distance': 200}
            },
            'equipment': [
                {'type': 'PAPI', 'count': 2},
                {'type': 'Windsock', 'count': 1},
                {'type': 'Beacon', 'count': 1}
            ]
        }
    
    def create_document(self, output_file: str = 'airport_runway_system.dxf') -> bool:
        """
        Create the DXF document with all layers.
        
        Args:
            output_file: Output DXF filename
            
        Returns:
            bool: True if successful
        """
        try:
            # Create DXF document
            self.dxf = ezdxf.new('R2010')
            self.msp = self.dxf.modelspace()
            
            # Setup layers
            self._setup_layers()
            
            # Generate all layer content
            self._generate_runway_taxiways()
            self._generate_runway_markings()
            self._generate_lighting_systems()
            self._generate_safety_zones()
            self._generate_equipment_facilities()
            self._generate_annotations()
            
            # Save document
            self.dxf.saveas(output_file)
            print(f"✓ DXF document created: {output_file}")
            return True
            
        except Exception as e:
            print(f"✗ Error creating DXF document: {e}")
            return False
    
    def _setup_layers(self):
        """Setup all required layers in the DXF document."""
        for layer_name, layer_config in self.LAYERS.items():
            if layer_name not in self.dxf.layers:
                self.dxf.layers.new(
                    name=layer_name,
                    dxfattribs={
                        'color': layer_config['color'],
                        'linetype': layer_config['linetype']
                    }
                )
                print(f"  ✓ Created layer: {layer_name}")
    
    def _generate_runway_taxiways(self):
        """Generate runway and taxiway geometries on dedicated layer."""
        layer = 'runway_taxiways'
        runway = self.geometry_data.get('runway', {})
        
        # Draw runway
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        
        # Runway rectangle
        x, y = runway_pos
        runway_pts = [
            (x - runway_width/2, y),
            (x + runway_width/2, y),
            (x + runway_width/2, y + runway_length),
            (x - runway_width/2, y + runway_length)
        ]
        
        runway_lwp = self.msp.add_lwpolyline(
            runway_pts,
            dxfattribs={'layer': layer, 'color': 7}
        )
        runway_lwp.close()
        
        print(f"  ✓ Drew runway: {runway_length}m x {runway_width}m")
        
        # Draw taxiways
        taxiways = self.geometry_data.get('taxiways', [])
        for i, taxiway in enumerate(taxiways):
            if 'points' in taxiway:
                tw_lwp = self.msp.add_lwpolyline(
                    taxiway['points'],
                    dxfattribs={'layer': layer, 'color': 7}
                )
                print(f"  ✓ Drew {taxiway.get('name', f'Taxiway {i+1}')}")
    
    def _generate_runway_markings(self):
        """Generate runway centerline and threshold markings."""
        layer = 'runway_markings'
        runway = self.geometry_data.get('runway', {})
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        x, y = runway_pos
        
        markings_config = self.geometry_data.get('runway_markings', {})
        
        # Runway centerline
        if markings_config.get('centerline', True):
            centerline_spacing = 30
            dash_length = 20
            gap_length = 10
            
            current_y = y
            while current_y < y + runway_length:
                self.msp.add_line(
                    (x, current_y),
                    (x, current_y + dash_length),
                    dxfattribs={'layer': layer, 'color': 1, 'linetype': 'DASHED'}
                )
                current_y += dash_length + gap_length
            
            print(f"  ✓ Drew runway centerline")
        
        # Threshold markings
        if markings_config.get('threshold_markings', True):
            threshold_width = 8
            num_lines = 10
            spacing = runway_width / (num_lines + 1)
            
            for i in range(1, num_lines + 1):
                x_pos = x - runway_width/2 + spacing * i
                self.msp.add_line(
                    (x_pos, y),
                    (x_pos, y + threshold_width),
                    dxfattribs={'layer': layer, 'color': 1}
                )
                self.msp.add_line(
                    (x_pos, y + runway_length - threshold_width),
                    (x_pos, y + runway_length),
                    dxfattribs={'layer': layer, 'color': 1}
                )
            
            print(f"  ✓ Drew threshold markings")
        
        # Zone markings
        if markings_config.get('zone_markings', True):
            zone_markers = [
                ('Touchdown Zone', 400),
                ('Aiming Point', 1000),
                ('Mid Runway', runway_length / 2)
            ]
            
            for zone_name, zone_pos in zone_markers:
                self.msp.add_circle(
                    (x, y + zone_pos),
                    radius=2,
                    dxfattribs={'layer': layer, 'color': 1}
                )
            
            print(f"  ✓ Drew zone markings")
    
    def _generate_lighting_systems(self):
        """Generate runway and taxiway lighting systems."""
        layer = 'lighting_systems'
        runway = self.geometry_data.get('runway', {})
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        x, y = runway_pos
        
        lighting_configs = self.geometry_data.get('lighting', [])
        
        for lighting in lighting_configs:
            light_type = lighting.get('type', '')
            spacing = lighting.get('spacing', 100)
            
            if light_type == 'runway_lights':
                # Runway edge lights
                current_y = y
                while current_y < y + runway_length:
                    # Left edge
                    self.msp.add_circle(
                        (x - runway_width/2 - 5, current_y),
                        radius=1.5,
                        dxfattribs={'layer': layer, 'color': 3}
                    )
                    # Right edge
                    self.msp.add_circle(
                        (x + runway_width/2 + 5, current_y),
                        radius=1.5,
                        dxfattribs={'layer': layer, 'color': 3}
                    )
                    current_y += spacing
                
                print(f"  ✓ Drew runway edge lights (spacing: {spacing}m)")
            
            elif light_type == 'taxiway_lights':
                # Taxiway lights along taxiways
                taxiways = self.geometry_data.get('taxiways', [])
                for taxiway in taxiways:
                    if 'points' in taxiway:
                        for point in taxiway['points']:
                            self.msp.add_circle(
                                point,
                                radius=0.75,
                                dxfattribs={'layer': layer, 'color': 3}
                            )
                
                print(f"  ✓ Drew taxiway lights")
    
    def _generate_safety_zones(self):
        """Generate safety zones (FATO, RESA, clearance areas)."""
        layer = 'safety_zones'
        runway = self.geometry_data.get('runway', {})
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        x, y = runway_pos
        
        safety_zones_config = self.geometry_data.get('safety_zones', {})
        
        # FATO (Final Approach and Takeoff Area)
        fato_distance = safety_zones_config.get('fato', {}).get('distance', 120)
        fato_width = runway_width + (2 * fato_distance)
        fato_length = runway_length + (2 * fato_distance)
        
        fato_pts = [
            (x - fato_width/2, y - fato_distance),
            (x + fato_width/2, y - fato_distance),
            (x + fato_width/2, y + fato_length - fato_distance),
            (x - fato_width/2, y + fato_length - fato_distance)
        ]
        
        fato_lwp = self.msp.add_lwpolyline(
            fato_pts,
            dxfattribs={'layer': layer, 'color': 6, 'linetype': 'DASHED'}
        )
        fato_lwp.close()
        print(f"  ✓ Drew FATO (distance: {fato_distance}m)")
        
        # RESA (Runway End Safety Area)
        resa_distance = safety_zones_config.get('resa', {}).get('distance', 200)
        resa_width = runway_width
        
        # RESA at start
        resa_start_pts = [
            (x - resa_width/2, y - resa_distance),
            (x + resa_width/2, y - resa_distance),
            (x + resa_width/2, y),
            (x - resa_width/2, y)
        ]
        
        resa_start_lwp = self.msp.add_lwpolyline(
            resa_start_pts,
            dxfattribs={'layer': layer, 'color': 6, 'linetype': 'DASHED'}
        )
        resa_start_lwp.close()
        
        # RESA at end
        resa_end_pts = [
            (x - resa_width/2, y + runway_length),
            (x + resa_width/2, y + runway_length),
            (x + resa_width/2, y + runway_length + resa_distance),
            (x - resa_width/2, y + runway_length + resa_distance)
        ]
        
        resa_end_lwp = self.msp.add_lwpolyline(
            resa_end_pts,
            dxfattribs={'layer': layer, 'color': 6, 'linetype': 'DASHED'}
        )
        resa_end_lwp.close()
        print(f"  ✓ Drew RESA zones (distance: {resa_distance}m)")
    
    def _generate_equipment_facilities(self):
        """Generate equipment and facilities (PAPI, windsock, beacon, etc.)."""
        layer = 'equipment_facilities'
        runway = self.geometry_data.get('runway', {})
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        x, y = runway_pos
        
        equipment_list = self.geometry_data.get('equipment', [])
        
        equipment_positions = {
            'PAPI': [(x - 100, y + 500), (x - 100, y + runway_length - 500)],
            'Windsock': [(x + runway_width/2 + 50, y + runway_length/2)],
            'Beacon': [(x, y + runway_length/2 + 200)]
        }
        
        for equipment in equipment_list:
            equip_type = equipment.get('type', '')
            count = equipment.get('count', 1)
            
            if equip_type in equipment_positions:
                positions = equipment_positions[equip_type][:count]
                
                for pos in positions:
                    if equip_type == 'PAPI':
                        # Draw PAPI as rectangle
                        papi_size = 5
                        self.msp.add_lwpolyline(
                            [(pos[0]-papi_size, pos[1]-papi_size),
                             (pos[0]+papi_size, pos[1]-papi_size),
                             (pos[0]+papi_size, pos[1]+papi_size),
                             (pos[0]-papi_size, pos[1]+papi_size)],
                            dxfattribs={'layer': layer, 'color': 5}
                        )
                    
                    elif equip_type == 'Windsock':
                        # Draw windsock as circle
                        self.msp.add_circle(
                            pos,
                            radius=3,
                            dxfattribs={'layer': layer, 'color': 5}
                        )
                        self.msp.add_line(
                            pos,
                            (pos[0], pos[1] + 8),
                            dxfattribs={'layer': layer, 'color': 5}
                        )
                    
                    elif equip_type == 'Beacon':
                        # Draw beacon as star
                        self.msp.add_circle(
                            pos,
                            radius=2,
                            dxfattribs={'layer': layer, 'color': 5}
                        )
                
                print(f"  ✓ Drew {count} {equip_type} unit(s)")
    
    def _generate_annotations(self):
        """Generate text annotations and labels."""
        layer = 'annotations'
        runway = self.geometry_data.get('runway', {})
        runway_length = runway.get('length', 3660)
        runway_width = runway.get('width', 60)
        runway_pos = runway.get('position', [0, 0])
        x, y = runway_pos
        
        # Add title
        self.msp.add_text(
            'AIRPORT RUNWAY SYSTEM',
            dxfattribs={
                'layer': layer,
                'color': 2,
                'height': 30
            }
        ).set_pos((x - 300, y + runway_length + 100))
        
        # Add runway designation
        self.msp.add_text(
            f'Runway: {runway_length}m x {runway_width}m',
            dxfattribs={
                'layer': layer,
                'color': 2,
                'height': 15
            }
        ).set_pos((x, y - 150))
        
        # Add taxiway labels
        taxiways = self.geometry_data.get('taxiways', [])
        for i, taxiway in enumerate(taxiways):
            if 'points' in taxiway and len(taxiway['points']) > 0:
                label_pos = taxiway['points'][0]
                self.msp.add_text(
                    taxiway.get('name', f'Taxiway {i+1}'),
                    dxfattribs={
                        'layer': layer,
                        'color': 2,
                        'height': 8
                    }
                ).set_pos(label_pos)
        
        # Add dimension annotations
        self.msp.add_text(
            f'{runway_length}m',
            dxfattribs={
                'layer': layer,
                'color': 2,
                'height': 10
            }
        ).set_pos((x - 50, y + runway_length/2))
        
        # Add timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        self.msp.add_text(
            f'Generated: {timestamp}',
            dxfattribs={
                'layer': layer,
                'color': 2,
                'height': 8
            }
        ).set_pos((x - 200, y - 80))
        
        print(f"  ✓ Added text annotations and labels")
    
    def generate(self, output_file: str = 'airport_runway_system.dxf') -> bool:
        """
        Complete generation workflow.
        
        Args:
            output_file: Output DXF filename
            
        Returns:
            bool: True if successful
        """
        print("\n" + "="*60)
        print("AIRPORT RUNWAY SYSTEM - DXF GENERATOR")
        print("="*60 + "\n")
        
        # Load geometry
        print("Loading geometry data...")
        if not self.load_geometry():
            print("⚠ Using default geometry configuration\n")
        
        # Create document
        print("\nCreating DXF document...")
        print("Setting up layers...")
        if not self.create_document(output_file):
            return False
        
        print("\n" + "="*60)
        print("GENERATION COMPLETE")
        print("="*60 + "\n")
        print(f"Output file: {output_file}")
        print(f"Layers generated: {len(self.LAYERS)}")
        print("✓ Multi-layer airport runway system DXF created successfully!\n")
        
        return True


def main():
    """Main entry point for the DXF generator."""
    # Initialize generator
    generator = AirportRunwayDXFGenerator(geometry_file='runway_geometry.json')
    
    # Generate DXF with all layers
    success = generator.generate(output_file='airport_runway_system.dxf')
    
    return success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
