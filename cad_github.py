#!/usr/bin/env python3
"""
Extended DXF Generator for Airport Runway System
Supports 4 modules: Runway Markings, Safety Areas, Lighting Systems, and Taxiways
Reads from runway_geometry.json and generates R2010 format DXF files
Author: Quintus-coder
Date: 2025-12-28
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import math


class DXFGenerator:
    """Generate DXF (R2010 format) files for airport runway systems using 2D entities."""

    def __init__(self, filename: str = "airport_runway_system.dxf"):
        """
        Initialize DXF generator.
        
        Args:
            filename: Output DXF filename
        """
        self.filename = filename
        self.entities = []
        self.handles = {}
        self.next_handle = 256
        self.version = "AC1021"  # R2010 format
        self.layers = {
            "RUNWAY_MARKINGS": {"color": 1, "linetype": "CONTINUOUS"},
            "SAFETY_AREAS": {"color": 3, "linetype": "DASHED"},
            "LIGHTING_SYSTEMS": {"color": 5, "linetype": "CONTINUOUS"},
            "TAXIWAYS": {"color": 2, "linetype": "CONTINUOUS"},
            "TEXT_LABELS": {"color": 7, "linetype": "CONTINUOUS"},
        }
        self.current_entity_id = 0

    def get_handle(self) -> str:
        """Generate next handle in hexadecimal format."""
        handle = format(self.next_handle, 'X')
        self.next_handle += 1
        return handle

    def add_line(self, x1: float, y1: float, x2: float, y2: float, 
                 layer: str = "0", color: int = 256) -> None:
        """Add LINE entity to DXF."""
        handle = self.get_handle()
        self.entities.append({
            "type": "LINE",
            "handle": handle,
            "layer": layer,
            "color": color,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        })

    def add_lwpolyline(self, points: List[Tuple[float, float]], 
                       layer: str = "0", color: int = 256, closed: bool = False) -> None:
        """Add LWPOLYLINE entity to DXF."""
        handle = self.get_handle()
        self.entities.append({
            "type": "LWPOLYLINE",
            "handle": handle,
            "layer": layer,
            "color": color,
            "points": points,
            "closed": closed,
        })

    def add_point(self, x: float, y: float, 
                  layer: str = "0", color: int = 256) -> None:
        """Add POINT entity to DXF."""
        handle = self.get_handle()
        self.entities.append({
            "type": "POINT",
            "handle": handle,
            "layer": layer,
            "color": color,
            "x": x,
            "y": y,
        })

    def add_circle(self, cx: float, cy: float, radius: float, 
                   layer: str = "0", color: int = 256) -> None:
        """Add CIRCLE entity to DXF."""
        handle = self.get_handle()
        self.entities.append({
            "type": "CIRCLE",
            "handle": handle,
            "layer": layer,
            "color": color,
            "cx": cx,
            "cy": cy,
            "radius": radius,
        })

    def add_text(self, text: str, x: float, y: float, height: float = 1.0,
                 layer: str = "0", color: int = 256) -> None:
        """Add TEXT entity to DXF."""
        handle = self.get_handle()
        self.entities.append({
            "type": "TEXT",
            "handle": handle,
            "layer": layer,
            "color": color,
            "text": text,
            "x": x,
            "y": y,
            "height": height,
        })

    def generate_runway_markings(self, runway_data: Dict[str, Any]) -> None:
        """Generate runway marking entities."""
        if "runways" not in runway_data:
            return

        layer = "RUNWAY_MARKINGS"
        color = self.layers[layer]["color"]

        for runway in runway_data["runways"]:
            # Runway outline
            start_x = runway.get("start_x", 0)
            start_y = runway.get("start_y", 0)
            end_x = runway.get("end_x", 0)
            end_y = runway.get("end_y", 0)
            width = runway.get("width", 60)

            # Calculate perpendicular points for runway width
            direction_x = end_x - start_x
            direction_y = end_y - start_y
            length = math.sqrt(direction_x**2 + direction_y**2)
            
            if length > 0:
                perp_x = -direction_y / length * (width / 2)
                perp_y = direction_x / length * (width / 2)

                # Runway boundary points
                points = [
                    (start_x - perp_x, start_y - perp_y),
                    (end_x - perp_x, end_y - perp_y),
                    (end_x + perp_x, end_y + perp_y),
                    (start_x + perp_x, start_y + perp_y),
                ]
                
                # Draw runway outline
                self.add_lwpolyline(points, layer=layer, color=color, closed=True)

                # Center line
                self.add_line(start_x, start_y, end_x, end_y, layer=layer, color=color)

            # Runway designation
            runway_name = runway.get("name", "RWY")
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            self.add_text(runway_name, mid_x, mid_y, height=2.0, layer="TEXT_LABELS", color=color)

            # Threshold markings (dashed lines)
            threshold_offset = 30
            threshold_points = [
                (start_x - perp_x * 0.3, start_y - perp_y * 0.3),
                (start_x + perp_x * 0.3, start_y + perp_y * 0.3),
            ]
            
            for i in range(0, int(width), 10):
                frac = i / width
                px = start_x + (perp_x * 2 * frac - perp_x)
                py = start_y + (perp_y * 2 * frac - perp_y)
                self.add_point(px, py, layer=layer, color=color)

    def generate_safety_areas(self, runway_data: Dict[str, Any]) -> None:
        """Generate safety area entities (RESA, OFZ, etc.)."""
        if "runways" not in runway_data:
            return

        layer = "SAFETY_AREAS"
        color = self.layers[layer]["color"]

        for runway in runway_data["runways"]:
            start_x = runway.get("start_x", 0)
            start_y = runway.get("start_y", 0)
            end_x = runway.get("end_x", 0)
            end_y = runway.get("end_y", 0)
            width = runway.get("width", 60)
            resa_length = runway.get("resa_length", 240)

            # Calculate direction vectors
            direction_x = end_x - start_x
            direction_y = end_y - start_y
            length = math.sqrt(direction_x**2 + direction_y**2)
            
            if length > 0:
                unit_x = direction_x / length
                unit_y = direction_y / length
                perp_x = -unit_y * (width / 2)
                perp_y = unit_x * (width / 2)

                # RESA at start of runway
                resa_start_x = start_x - unit_x * resa_length
                resa_start_y = start_y - unit_y * resa_length
                
                resa_points = [
                    (resa_start_x - perp_x, resa_start_y - perp_y),
                    (start_x - perp_x, start_y - perp_y),
                    (start_x + perp_x, start_y + perp_y),
                    (resa_start_x + perp_x, resa_start_y + perp_y),
                ]
                self.add_lwpolyline(resa_points, layer=layer, color=color, closed=True)
                self.add_text("RESA", resa_start_x, resa_start_y - 50, height=2.0, 
                            layer="TEXT_LABELS", color=color)

                # RESA at end of runway
                resa_end_x = end_x + unit_x * resa_length
                resa_end_y = end_y + unit_y * resa_length
                
                resa_end_points = [
                    (end_x - perp_x, end_y - perp_y),
                    (resa_end_x - perp_x, resa_end_y - perp_y),
                    (resa_end_x + perp_x, resa_end_y + perp_y),
                    (end_x + perp_x, end_y + perp_y),
                ]
                self.add_lwpolyline(resa_end_points, layer=layer, color=color, closed=True)
                self.add_text("RESA", resa_end_x, resa_end_y + 50, height=2.0, 
                            layer="TEXT_LABELS", color=color)

    def generate_lighting_systems(self, runway_data: Dict[str, Any]) -> None:
        """Generate lighting system entities (approach lights, edge lights, etc.)."""
        if "runways" not in runway_data:
            return

        layer = "LIGHTING_SYSTEMS"
        color = self.layers[layer]["color"]

        for runway in runway_data["runways"]:
            start_x = runway.get("start_x", 0)
            start_y = runway.get("start_y", 0)
            end_x = runway.get("end_x", 0)
            end_y = runway.get("end_y", 0)
            width = runway.get("width", 60)
            light_spacing = runway.get("light_spacing", 30)

            # Calculate direction and perpendicular vectors
            direction_x = end_x - start_x
            direction_y = end_y - start_y
            length = math.sqrt(direction_x**2 + direction_y**2)
            
            if length > 0:
                unit_x = direction_x / length
                unit_y = direction_y / length
                perp_x = -unit_y
                perp_y = unit_x

                # Edge lighting along runway
                for i in range(int(length / light_spacing)):
                    t = (i * light_spacing) / length
                    px = start_x + unit_x * i * light_spacing
                    py = start_y + unit_y * i * light_spacing

                    # Left edge light
                    light_x = px - perp_x * (width / 2 + 5)
                    light_y = py - perp_y * (width / 2 + 5)
                    self.add_circle(light_x, light_y, radius=2.0, layer=layer, color=color)

                    # Right edge light
                    light_x = px + perp_x * (width / 2 + 5)
                    light_y = py + perp_y * (width / 2 + 5)
                    self.add_circle(light_x, light_y, radius=2.0, layer=layer, color=color)

                # Approach lighting system
                approach_length = runway.get("approach_length", 300)
                approach_spacing = 15
                
                for i in range(0, approach_length, approach_spacing):
                    # Left approach lights
                    approach_x = start_x - unit_x * i
                    approach_y = start_y - unit_y * i
                    light_x = approach_x - perp_x * (width / 2 + 15)
                    light_y = approach_y - perp_y * (width / 2 + 15)
                    self.add_point(light_x, light_y, layer=layer, color=color)

                    # Right approach lights
                    light_x = approach_x + perp_x * (width / 2 + 15)
                    light_y = approach_y + perp_y * (width / 2 + 15)
                    self.add_point(light_x, light_y, layer=layer, color=color)

    def generate_taxiways(self, runway_data: Dict[str, Any]) -> None:
        """Generate taxiway entities."""
        if "taxiways" not in runway_data:
            return

        layer = "TAXIWAYS"
        color = self.layers[layer]["color"]

        for taxiway in runway_data["taxiways"]:
            taxiway_name = taxiway.get("name", "TWY")
            start_x = taxiway.get("start_x", 0)
            start_y = taxiway.get("start_y", 0)
            end_x = taxiway.get("end_x", 0)
            end_y = taxiway.get("end_y", 0)
            width = taxiway.get("width", 30)

            # Calculate perpendicular points
            direction_x = end_x - start_x
            direction_y = end_y - start_y
            length = math.sqrt(direction_x**2 + direction_y**2)
            
            if length > 0:
                perp_x = -direction_y / length * (width / 2)
                perp_y = direction_x / length * (width / 2)

                # Taxiway outline
                points = [
                    (start_x - perp_x, start_y - perp_y),
                    (end_x - perp_x, end_y - perp_y),
                    (end_x + perp_x, end_y + perp_y),
                    (start_x + perp_x, start_y + perp_y),
                ]
                self.add_lwpolyline(points, layer=layer, color=color, closed=True)

                # Center line
                self.add_line(start_x, start_y, end_x, end_y, layer=layer, color=color)

                # Taxiway label
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                self.add_text(taxiway_name, mid_x, mid_y, height=1.5, 
                            layer="TEXT_LABELS", color=color)

    def load_runway_geometry(self, json_file: str) -> Dict[str, Any]:
        """Load runway geometry from JSON file."""
        if not os.path.exists(json_file):
            print(f"Warning: {json_file} not found. Using default geometry.")
            return self._get_default_geometry()
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            print(f"Successfully loaded runway geometry from {json_file}")
            return data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}. Using default geometry.")
            return self._get_default_geometry()

    def _get_default_geometry(self) -> Dict[str, Any]:
        """Return default airport geometry."""
        return {
            "airport_name": "Default Airport",
            "runways": [
                {
                    "name": "09/27",
                    "start_x": 0,
                    "start_y": 0,
                    "end_x": 4000,
                    "end_y": 0,
                    "width": 60,
                    "resa_length": 240,
                    "approach_length": 300,
                    "light_spacing": 30,
                },
            ],
            "taxiways": [
                {
                    "name": "A",
                    "start_x": 500,
                    "start_y": 100,
                    "end_x": 500,
                    "end_y": -100,
                    "width": 30,
                },
                {
                    "name": "B",
                    "start_x": 2000,
                    "start_y": 100,
                    "end_x": 2000,
                    "end_y": -100,
                    "width": 30,
                },
            ],
        }

    def generate_dxf_header(self) -> str:
        """Generate DXF header section."""
        header = "  0\nSECTION\n  2\nHEADER\n"
        header += "  9\n$ACADVER\n  1\nAC1021\n"  # R2010
        header += "  9\n$EXTMIN\n 10\n-500.0\n 20\n-500.0\n"
        header += "  9\n$EXTMAX\n 10\n5000.0\n 20\n500.0\n"
        header += "  0\nENDSEC\n"
        return header

    def generate_dxf_classes(self) -> str:
        """Generate DXF classes section."""
        return "  0\nSECTION\n  2\nCLASSES\n  0\nENDSEC\n"

    def generate_dxf_tables(self) -> str:
        """Generate DXF tables section with layer definitions."""
        tables = "  0\nSECTION\n  2\nTABLES\n"
        
        # LTYPE table
        tables += "  0\nTABLE\n  2\nLTYPE\n 70\n2\n"
        tables += "  0\nLTYPE\n  2\nCONTINUOUS\n 70\n0\n  3\nSolid line\n 72\n65\n 73\n0\n 40\n0.0\n"
        tables += "  0\nLTYPE\n  2\nDASHED\n 70\n0\n  3\nDashed line\n 72\n65\n 73\n2\n 40\n0.75\n 55\n0.5\n 55\n-0.25\n"
        tables += "  0\nENDTAB\n"
        
        # LAYER table
        tables += "  0\nTABLE\n  2\nLAYER\n 70\n6\n"
        
        for layer_name, layer_props in self.layers.items():
            tables += f"  0\nLAYER\n  2\n{layer_name}\n 70\n0\n"
            tables += f" 62\n{layer_props['color']}\n"
            tables += f"  6\n{layer_props['linetype']}\n"
            tables += " 370\n25\n"  # Line weight
        
        # Default layer
        tables += "  0\nLAYER\n  2\n0\n 70\n0\n 62\n7\n  6\nCONTINUOUS\n 370\n-1\n"
        
        tables += "  0\nENDTAB\n"
        
        # STYLE table
        tables += "  0\nTABLE\n  2\nSTYLE\n 70\n1\n"
        tables += "  0\nSTYLE\n  2\nSTANDARD\n 70\n0\n 40\n0.0\n 41\n1.0\n 50\n0.0\n 71\n0\n 42\n1.0\n  3\ntxt\n  4\n\n"
        tables += "  0\nENDTAB\n"
        
        tables += "  0\nENDSEC\n"
        return tables

    def generate_dxf_blocks(self) -> str:
        """Generate DXF blocks section."""
        return "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  8\n0\n  2\n*MODEL_SPACE\n 70\n0\n  0\nENDBLK\n  0\nENDSEC\n"

    def generate_dxf_entities(self) -> str:
        """Generate DXF entities section with all created entities."""
        entities = "  0\nSECTION\n  2\nENTITIES\n"
        
        for entity in self.entities:
            if entity["type"] == "LINE":
                entities += f"  0\nLINE\n"
                entities += f"  5\n{entity['handle']}\n"
                entities += f"  8\n{entity['layer']}\n"
                entities += f" 62\n{entity['color']}\n"
                entities += f" 10\n{entity['x1']}\n 20\n{entity['y1']}\n"
                entities += f" 11\n{entity['x2']}\n 21\n{entity['y2']}\n"
            
            elif entity["type"] == "LWPOLYLINE":
                entities += f"  0\nLWPOLYLINE\n"
                entities += f"  5\n{entity['handle']}\n"
                entities += f"  8\n{entity['layer']}\n"
                entities += f" 62\n{entity['color']}\n"
                entities += f" 90\n{len(entity['points'])}\n"
                entities += f" 70\n{'1' if entity['closed'] else '0'}\n"
                for point in entity["points"]:
                    entities += f" 10\n{point[0]}\n 20\n{point[1]}\n"
            
            elif entity["type"] == "POINT":
                entities += f"  0\nPOINT\n"
                entities += f"  5\n{entity['handle']}\n"
                entities += f"  8\n{entity['layer']}\n"
                entities += f" 62\n{entity['color']}\n"
                entities += f" 10\n{entity['x']}\n 20\n{entity['y']}\n"
            
            elif entity["type"] == "CIRCLE":
                entities += f"  0\nCIRCLE\n"
                entities += f"  5\n{entity['handle']}\n"
                entities += f"  8\n{entity['layer']}\n"
                entities += f" 62\n{entity['color']}\n"
                entities += f" 10\n{entity['cx']}\n 20\n{entity['cy']}\n"
                entities += f" 40\n{entity['radius']}\n"
            
            elif entity["type"] == "TEXT":
                entities += f"  0\nTEXT\n"
                entities += f"  5\n{entity['handle']}\n"
                entities += f"  8\n{entity['layer']}\n"
                entities += f" 62\n{entity['color']}\n"
                entities += f" 10\n{entity['x']}\n 20\n{entity['y']}\n"
                entities += f" 40\n{entity['height']}\n"
                entities += f"  1\n{entity['text']}\n"
        
        entities += "  0\nENDSEC\n"
        return entities

    def generate_dxf_objects(self) -> str:
        """Generate DXF objects section."""
        return "  0\nSECTION\n  2\nOBJECTS\n  0\nDICTIONARY\n  0\nENDSEC\n"

    def generate(self, json_file: str = "runway_geometry.json") -> None:
        """Generate complete DXF file from runway geometry JSON."""
        print(f"Generating DXF file: {self.filename}")
        
        # Load runway geometry
        runway_data = self.load_runway_geometry(json_file)
        
        # Generate all modules
        print("Generating runway markings...")
        self.generate_runway_markings(runway_data)
        
        print("Generating safety areas...")
        self.generate_safety_areas(runway_data)
        
        print("Generating lighting systems...")
        self.generate_lighting_systems(runway_data)
        
        print("Generating taxiways...")
        self.generate_taxiways(runway_data)
        
        # Write DXF file
        self._write_dxf_file()
        print(f"DXF file generated successfully: {self.filename}")

    def _write_dxf_file(self) -> None:
        """Write all sections to DXF file."""
        with open(self.filename, 'w') as f:
            f.write(self.generate_dxf_header())
            f.write(self.generate_dxf_classes())
            f.write(self.generate_dxf_tables())
            f.write(self.generate_dxf_blocks())
            f.write(self.generate_dxf_entities())
            f.write(self.generate_dxf_objects())
            f.write("  0\nEOF\n")


def main():
    """Main function to generate airport runway system DXF."""
    import sys
    
    output_file = "airport_runway_system.dxf"
    input_json = "runway_geometry.json"
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print("=" * 60)
    print("Extended Airport Runway System DXF Generator")
    print("=" * 60)
    print(f"Input JSON:  {input_json}")
    print(f"Output DXF:  {output_file}")
    print("Modules: Runway Markings, Safety Areas, Lighting Systems, Taxiways")
    print("Format: R2010 (AC1021)")
    print("=" * 60)
    
    generator = DXFGenerator(output_file)
    generator.generate(input_json)
    
    print("\nGeneration complete!")
    print(f"Output file: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
