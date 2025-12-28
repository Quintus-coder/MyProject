"""
CAD Drawing Module for Airport Runway Design
Generates DXF files using ezdxf for various runway components
Updated: 2025-12-28 13:35:44 UTC
"""

import ezdxf
from ezdxf.addons import DxfAttrib
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class LightingType(Enum):
    """Enumeration for lighting system types"""
    APPROACH = "Approach Lighting System"
    END = "End Lights"
    SIDE = "Side Stripes"
    PAPI = "PAPI (Precision Approach Path Indicator)"


@dataclass
class Point:
    """3D Point representation"""
    x: float
    y: float
    z: float = 0.0


@dataclass
class RunwayConfig:
    """Configuration for runway dimensions and properties"""
    length: float
    width: float
    threshold_elevation: float
    far_end_elevation: float


class DXFGenerator:
    """Base class for DXF file generation"""
    
    def __init__(self, filename: str):
        """Initialize DXF document"""
        self.filename = filename
        self.doc = ezdxf.new('R2010')
        self.msp = self.doc.modelspace()
        self.setup_layers()
    
    def setup_layers(self):
        """Create standard layers for drawing"""
        layers = [
            ('Runway', 7),  # White
            ('Approach_Lighting', 1),  # Red
            ('End_Lights', 5),  # Magenta
            ('Side_Stripes', 3),  # Green
            ('PAPI', 6),  # Yellow
            ('Markings', 7),  # White
            ('Elevation_Data', 4),  # Cyan
        ]
        
        for layer_name, color in layers:
            if layer_name not in self.doc.layers:
                self.doc.layers.new(name=layer_name, dxfattribs={'color': color})
    
    def save(self):
        """Save the DXF document to file"""
        self.doc.saveas(self.filename)
        print(f"DXF file saved: {self.filename}")


class RunwayDrawer(DXFGenerator):
    """Generates runway layout and basic structure"""
    
    def __init__(self, filename: str, config: RunwayConfig):
        super().__init__(filename)
        self.config = config
    
    def draw_runway_outline(self):
        """Draw the runway boundary"""
        length = self.config.length
        width = self.config.width
        
        # Define runway corners
        corners = [
            (0, 0),
            (length, 0),
            (length, width),
            (0, width),
            (0, 0)
        ]
        
        # Draw runway outline
        points = [Point(x, y) for x, y in corners]
        self.msp.add_lwpolyline(
            [(p.x, p.y) for p in points],
            dxfattribs={'layer': 'Runway', 'lineweight': 50}
        )
    
    def draw_centerline(self):
        """Draw runway centerline"""
        length = self.config.length
        width = self.config.width
        center_y = width / 2
        
        self.msp.add_line(
            (0, center_y),
            (length, center_y),
            dxfattribs={
                'layer': 'Markings',
                'linetype': 'DASHED',
                'lineweight': 25
            }
        )
    
    def draw_threshold_markings(self):
        """Draw threshold and touchdown zone markings"""
        width = self.config.width
        
        # Threshold bar
        self.msp.add_line(
            (0, 0),
            (0, width),
            dxfattribs={'layer': 'Markings', 'lineweight': 35}
        )
        
        # Touchdown zone markings (dashed lines)
        for i in range(1, 6):
            offset = 150 * i
            self.msp.add_line(
                (offset, 0),
                (offset, width),
                dxfattribs={
                    'layer': 'Markings',
                    'linetype': 'DASHED',
                    'lineweight': 20
                }
            )


class ApproachLightingSystem(DXFGenerator):
    """MALS (Medium Intensity Approach Lighting System)"""
    
    def __init__(self, filename: str, runway_length: float, runway_width: float):
        super().__init__(filename)
        self.runway_length = runway_length
        self.runway_width = runway_width
    
    def draw_approach_lights(self):
        """Draw approach lighting system"""
        width = self.runway_width
        center_y = width / 2
        
        # Main approach light line (extends 2400-3000 ft before runway)
        approach_distance = 2400  # feet
        light_spacing = 200  # feet
        
        # Draw light positions
        for distance in range(light_spacing, approach_distance, light_spacing):
            x = -distance
            
            # Center light
            self.msp.add_circle(
                (x, center_y),
                radius=5,
                dxfattribs={'layer': 'Approach_Lighting', 'color': 1}
            )
            
            # Side lights (offset from centerline)
            side_offset = width / 3
            
            self.msp.add_circle(
                (x, center_y - side_offset),
                radius=4,
                dxfattribs={'layer': 'Approach_Lighting'}
            )
            
            self.msp.add_circle(
                (x, center_y + side_offset),
                radius=4,
                dxfattribs={'layer': 'Approach_Lighting'}
            )
        
        # Add text label
        self.msp.add_text(
            f'MALS - Medium Intensity Approach Lighting System',
            dxfattribs={'layer': 'Approach_Lighting', 'height': 50}
        ).set_pos((-approach_distance/2, center_y + 200))
    
    def draw_visual_glide_slope(self):
        """Draw VGSI (Visual Glide Slope Indicator) reference lines"""
        width = self.runway_width
        
        for angle in [2.5, 3.0, 3.5]:
            # Calculate line points for different glide slope angles
            rad = math.radians(angle)
            x_far = -1500
            y_at_far = width/2 + (x_far * math.tan(rad))
            
            self.msp.add_line(
                (x_far, y_at_far),
                (500, width/2),
                dxfattribs={
                    'layer': 'Approach_Lighting',
                    'linetype': 'DASHED',
                    'color': 1
                }
            )


class EndLights(DXFGenerator):
    """Runway End Identifier Lights (REIL)"""
    
    def __init__(self, filename: str, runway_length: float, runway_width: float):
        super().__init__(filename)
        self.runway_length = runway_length
        self.runway_width = runway_width
    
    def draw_end_lights(self):
        """Draw runway end identifier lights"""
        width = self.runway_width
        
        # Near end lights
        near_end_y_positions = [width * 0.25, width * 0.75]
        for y in near_end_y_positions:
            self.msp.add_circle(
                (-50, y),
                radius=6,
                dxfattribs={'layer': 'End_Lights', 'color': 5}
            )
        
        # Far end lights
        far_end_y_positions = [width * 0.25, width * 0.75]
        for y in far_end_y_positions:
            self.msp.add_circle(
                (self.runway_length + 50, y),
                radius=6,
                dxfattribs={'layer': 'End_Lights', 'color': 5}
            )
        
        # Add connecting lines
        self.msp.add_line(
            (-50, near_end_y_positions[0]),
            (-50, near_end_y_positions[1]),
            dxfattribs={'layer': 'End_Lights', 'color': 5}
        )
        
        self.msp.add_line(
            (self.runway_length + 50, far_end_y_positions[0]),
            (self.runway_length + 50, far_end_y_positions[1]),
            dxfattribs={'layer': 'End_Lights', 'color': 5}
        )
        
        # Add text label
        self.msp.add_text(
            'REIL - Runway End Identifier Lights',
            dxfattribs={'layer': 'End_Lights', 'height': 40}
        ).set_pos((self.runway_length/2 - 200, width + 100))
    
    def draw_threshold_lights(self):
        """Draw threshold and threshold bar lights"""
        width = self.runway_width
        spacing = 15  # feet between lights
        
        for i, y in enumerate([y for y in range(int(spacing), int(width), int(spacing*2))]):
            self.msp.add_circle(
                (0, y),
                radius=3,
                dxfattribs={'layer': 'End_Lights', 'color': 5}
            )


class SideStripes(DXFGenerator):
    """Runway Side Stripe Lighting"""
    
    def __init__(self, filename: str, runway_length: float, runway_width: float):
        super().__init__(filename)
        self.runway_length = runway_length
        self.runway_width = runway_width
    
    def draw_side_stripes(self):
        """Draw side stripe lights"""
        light_spacing = 200  # feet
        
        # Left side stripe
        for x in range(0, int(self.runway_length), int(light_spacing)):
            self.msp.add_circle(
                (x, 0),
                radius=3,
                dxfattribs={'layer': 'Side_Stripes', 'color': 3}
            )
        
        # Right side stripe
        for x in range(0, int(self.runway_length), int(light_spacing)):
            self.msp.add_circle(
                (x, self.runway_width),
                radius=3,
                dxfattribs={'layer': 'Side_Stripes', 'color': 3}
            )
        
        # Add connecting lines
        self.msp.add_line(
            (0, 0),
            (self.runway_length, 0),
            dxfattribs={
                'layer': 'Side_Stripes',
                'linetype': 'DASHED',
                'color': 3,
                'lineweight': 15
            }
        )
        
        self.msp.add_line(
            (0, self.runway_width),
            (self.runway_length, self.runway_width),
            dxfattribs={
                'layer': 'Side_Stripes',
                'linetype': 'DASHED',
                'color': 3,
                'lineweight': 15
            }
        )
        
        # Add text label
        self.msp.add_text(
            'Side Stripe Lights',
            dxfattribs={'layer': 'Side_Stripes', 'height': 40}
        ).set_pos((self.runway_length/2 - 150, -100))
    
    def draw_touchdown_zone_lights(self):
        """Draw touchdown zone lights along runway length"""
        width = self.runway_width
        center_y = width / 2
        light_spacing = 300  # feet
        
        for x in range(int(light_spacing), int(self.runway_length - light_spacing), int(light_spacing)):
            # Pair of lights on either side of centerline
            offset = width * 0.15
            
            self.msp.add_circle(
                (x, center_y - offset),
                radius=4,
                dxfattribs={'layer': 'Side_Stripes', 'color': 3}
            )
            
            self.msp.add_circle(
                (x, center_y + offset),
                radius=4,
                dxfattribs={'layer': 'Side_Stripes', 'color': 3}
            )


class PAPI(DXFGenerator):
    """PAPI - Precision Approach Path Indicator"""
    
    def __init__(self, filename: str, runway_length: float, runway_width: float):
        super().__init__(filename)
        self.runway_length = runway_length
        self.runway_width = runway_width
    
    def draw_papi_lights(self):
        """Draw PAPI light units"""
        width = self.runway_width
        
        # Typical PAPI installation: 4 lights offset to the side
        papi_x = 300  # Distance from threshold
        papi_y = width + 200  # Offset from runway edge
        light_spacing = 15  # feet between lights
        
        for i in range(4):
            light_y = papi_y + (i * light_spacing)
            
            # Draw PAPI light unit (box)
            self.msp.add_rectangle(
                (papi_x - 10, light_y - 5),
                20, 10,
                dxfattribs={'layer': 'PAPI', 'color': 6}
            )
            
            # Add indicator number
            self.msp.add_text(
                f'P{i+1}',
                dxfattribs={'layer': 'PAPI', 'height': 8, 'color': 6}
            ).set_pos((papi_x - 5, light_y))
        
        # Add PAPI information box
        self.msp.add_rectangle(
            (papi_x - 50, papi_y - 50),
            300, 150,
            dxfattribs={
                'layer': 'PAPI',
                'linetype': 'DASHED',
                'color': 6
            }
        )
        
        self.msp.add_text(
            'PAPI - Precision Approach Path Indicator\nGlide Slope: 3.0 degrees',
            dxfattribs={'layer': 'PAPI', 'height': 30, 'color': 6}
        ).set_pos((papi_x - 40, papi_y + 60))
    
    def draw_glide_slope_indicators(self):
        """Draw glide slope angle indicators"""
        width = self.runway_width
        center_y = width / 2
        
        # Target glide slope: 3.0 degrees
        target_angle = 3.0
        
        # Draw angle reference lines from PAPI position
        papi_x = 300
        
        angles = [2.5, 3.0, 3.5]
        colors = [1, 6, 5]  # Red, Yellow, Magenta
        
        for angle, color in zip(angles, colors):
            rad = math.radians(angle)
            x_far = papi_x - 1500
            y_at_far = center_y + (x_far * math.tan(rad))
            
            linetype = 'CONTINUOUS' if angle == target_angle else 'DASHED'
            
            self.msp.add_line(
                (x_far, y_at_far),
                (papi_x + 500, center_y),
                dxfattribs={
                    'layer': 'PAPI',
                    'linetype': linetype,
                    'color': color
                }
            )
    
    def draw_papi_reference_data(self):
        """Add PAPI reference data box"""
        info_text = """
PAPI CHARACTERISTICS:
- Glide Slope Angle: 3.0°
- Visual Range: 5-20 nautical miles
- Light Intensity: High
- Indication Colors:
  Above Path: White/Red
  On Path: Red/White
  Below Path: All Red
        """
        
        self.msp.add_text(
            info_text,
            dxfattribs={'layer': 'PAPI', 'height': 15}
        ).set_pos((-500, -300))


class ComprehensiveRunwayDXF(DXFGenerator):
    """Master class that integrates all drawing modules"""
    
    def __init__(self, filename: str, config: RunwayConfig):
        super().__init__(filename)
        self.config = config
    
    def generate_complete_drawing(self):
        """Generate complete runway with all systems"""
        
        # 1. Draw basic runway
        runway = RunwayDrawer(None, self.config)
        runway.doc = self.doc
        runway.msp = self.msp
        runway.draw_runway_outline()
        runway.draw_centerline()
        runway.draw_threshold_markings()
        
        # 2. Draw Approach Lighting System
        als = ApproachLightingSystem(None, self.config.length, self.config.width)
        als.doc = self.doc
        als.msp = self.msp
        als.draw_approach_lights()
        als.draw_visual_glide_slope()
        
        # 3. Draw End Lights
        el = EndLights(None, self.config.length, self.config.width)
        el.doc = self.doc
        el.msp = self.msp
        el.draw_end_lights()
        el.draw_threshold_lights()
        
        # 4. Draw Side Stripes
        ss = SideStripes(None, self.config.length, self.config.width)
        ss.doc = self.doc
        ss.msp = self.msp
        ss.draw_side_stripes()
        ss.draw_touchdown_zone_lights()
        
        # 5. Draw PAPI
        papi = PAPI(None, self.config.length, self.config.width)
        papi.doc = self.doc
        papi.msp = self.msp
        papi.draw_papi_lights()
        papi.draw_glide_slope_indicators()
        papi.draw_papi_reference_data()
        
        # Add title block
        self.add_title_block()
    
    def add_title_block(self):
        """Add title block with document information"""
        title_text = (
            f"AIRPORT RUNWAY DESIGN\n"
            f"Runway Length: {self.config.length} ft\n"
            f"Runway Width: {self.config.width} ft\n"
            f"Threshold Elev: {self.config.threshold_elevation} ft\n"
            f"Far End Elev: {self.config.far_end_elevation} ft\n"
            f"Generated: 2025-12-28 13:35:44 UTC"
        )
        
        self.msp.add_text(
            title_text,
            dxfattribs={'layer': 'Markings', 'height': 25}
        ).set_pos((-1000, -500))


def main():
    """Main execution function"""
    
    # Define runway configuration
    runway_config = RunwayConfig(
        length=12000.0,  # feet
        width=200.0,     # feet
        threshold_elevation=125.0,  # feet MSL
        far_end_elevation=128.5  # feet MSL
    )
    
    # Generate comprehensive drawing
    output_file = "airport_runway_complete.dxf"
    
    print("Generating comprehensive runway DXF drawing...")
    print(f"  - Runway Length: {runway_config.length} ft")
    print(f"  - Runway Width: {runway_config.width} ft")
    print("  - Including Systems:")
    print("    * Approach Lighting System (MALS)")
    print("    * End Lights (REIL)")
    print("    * Side Stripes & Touchdown Zone Lights")
    print("    * PAPI (Precision Approach Path Indicator)")
    
    generator = ComprehensiveRunwayDXF(output_file, runway_config)
    generator.generate_complete_drawing()
    generator.save()
    
    print(f"\nDXF generation completed successfully!")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    main()
