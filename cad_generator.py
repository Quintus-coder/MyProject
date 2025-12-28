"""
DXF-based CAD Generator for Runway Layouts
Generates AutoCAD-compatible DXF files with proper layer organization.
Uses ezdxf library for professional CAD file generation.
"""

import ezdxf
from ezdxf.entities import DXFEntity
from ezdxf.math import Vec2
from typing import List, Tuple, Optional
import os


class RunwayCADGenerator:
    """
    Professional CAD generator for runway layouts using DXF format.
    Supports runway geometry, markings, lights, and safety zones.
    """

    def __init__(self, filename: str = "runway_layout.dxf"):
        """
        Initialize the CAD generator.
        
        Args:
            filename: Output DXF filename
        """
        self.filename = filename
        self.doc = ezdxf.new()
        self.msp = self.doc.modelspace()
        self._setup_layers()

    def _setup_layers(self) -> None:
        """Setup DXF layers with appropriate colors and line styles."""
        layers_config = {
            "RUNWAY_BASE": {"color": 7, "linetype": "Continuous"},  # White
            "CENTERLINE": {"color": 3, "linetype": "DASHED"},  # Yellow
            "THRESHOLD": {"color": 1, "linetype": "Continuous"},  # Red
            "EDGE_LIGHTS": {"color": 5, "linetype": "Continuous"},  # Magenta
            "SAFETY_ZONES": {"color": 2, "linetype": "DASHED"},  # Green
            "DIMENSIONS": {"color": 4, "linetype": "Continuous"},  # Cyan
            "ANNOTATIONS": {"color": 8, "linetype": "Continuous"},  # Gray
        }

        for layer_name, config in layers_config.items():
            if layer_name not in self.doc.layers:
                self.doc.layers.new(
                    name=layer_name,
                    dxfattribs={"color": config["color"], "linetype": config["linetype"]}
                )

    def create_runway_base(
        self,
        length: float = 3000.0,
        width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0
    ) -> None:
        """
        Create the runway base rectangle.
        
        Args:
            length: Runway length in meters
            width: Runway width in meters
            start_point: Starting corner point (x, y)
            rotation: Rotation angle in degrees
        """
        x, y = start_point
        
        # Create runway perimeter
        points = [
            (x, y),
            (x + length, y),
            (x + length, y + width),
            (x, y + width),
            (x, y)  # Close the polygon
        ]

        # Apply rotation if specified
        if rotation != 0:
            center = Vec2(x + length / 2, y + width / 2)
            from math import radians, cos, sin
            rad = radians(rotation)
            rotated_points = []
            for px, py in points[:-1]:
                # Translate to origin
                px -= center.x
                py -= center.y
                # Rotate
                new_x = px * cos(rad) - py * sin(rad)
                new_y = px * sin(rad) + py * cos(rad)
                # Translate back
                rotated_points.append((new_x + center.x, new_y + center.y))
            rotated_points.append(rotated_points[0])  # Close polygon
            points = rotated_points

        # Draw runway outline
        self.msp.add_lwpolyline(points, dxfattribs={"layer": "RUNWAY_BASE", "lineweight": 35})

        # Fill runway surface with light color
        self.msp.add_lwpolyline(
            points[:-1],
            dxfattribs={"layer": "RUNWAY_BASE", "color": 7}
        )

    def create_centerline_markings(
        self,
        runway_length: float = 3000.0,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0),
        dash_length: float = 60.0,
        gap_length: float = 40.0
    ) -> None:
        """
        Create dashed centerline markings down the runway.
        
        Args:
            runway_length: Runway length
            runway_width: Runway width
            start_point: Runway starting corner
            dash_length: Length of each dash in meters
            gap_length: Gap between dashes in meters
        """
        x, y = start_point
        centerline_y = y + runway_width / 2

        # Create dashed centerline
        current_x = x
        while current_x < x + runway_length:
            dash_end_x = min(current_x + dash_length, x + runway_length)
            self.msp.add_line(
                (current_x, centerline_y),
                (dash_end_x, centerline_y),
                dxfattribs={"layer": "CENTERLINE", "lineweight": 25}
            )
            current_x = dash_end_x + gap_length

    def create_threshold_markings(
        self,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0),
        threshold_depth: float = 30.0
    ) -> None:
        """
        Create threshold markings at runway entrance and exit.
        
        Args:
            runway_width: Runway width
            start_point: Runway starting corner
            threshold_depth: Depth of threshold markings from runway edge
        """
        x, y = start_point

        # Threshold at start
        threshold_points = [
            (x, y),
            (x + threshold_depth, y),
            (x + threshold_depth, y + runway_width),
            (x, y + runway_width),
            (x, y)
        ]
        self.msp.add_lwpolyline(
            threshold_points,
            dxfattribs={"layer": "THRESHOLD", "lineweight": 20}
        )

        # Threshold at end
        threshold_points_end = [
            (x + 3000 - threshold_depth, y),
            (x + 3000, y),
            (x + 3000, y + runway_width),
            (x + 3000 - threshold_depth, y + runway_width),
            (x + 3000 - threshold_depth, y)
        ]
        self.msp.add_lwpolyline(
            threshold_points_end,
            dxfattribs={"layer": "THRESHOLD", "lineweight": 20}
        )

    def create_edge_lights(
        self,
        runway_length: float = 3000.0,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0),
        light_spacing: float = 150.0,
        light_offset: float = 5.0,
        light_size: float = 1.5
    ) -> None:
        """
        Create edge light markings along runway sides.
        
        Args:
            runway_length: Runway length
            runway_width: Runway width
            start_point: Runway starting corner
            light_spacing: Distance between lights in meters
            light_offset: Distance from runway edge in meters
            light_size: Size of light symbol in meters
        """
        x, y = start_point

        # Left edge lights
        for i in range(int(runway_length / light_spacing) + 1):
            light_x = x + i * light_spacing
            light_y = y - light_offset

            # Draw light symbol (circle)
            circle = self.msp.add_circle(
                (light_x, light_y),
                light_size,
                dxfattribs={"layer": "EDGE_LIGHTS"}
            )

            # Add text label
            self.msp.add_text(
                f"L{i}",
                dxfattribs={
                    "layer": "EDGE_LIGHTS",
                    "height": 1.0,
                    "halign": ezdxf.const.TextHorizontalAlignment.CENTER,
                }
            ).set_pos((light_x, light_y - 3))

        # Right edge lights
        for i in range(int(runway_length / light_spacing) + 1):
            light_x = x + i * light_spacing
            light_y = y + runway_width + light_offset

            # Draw light symbol (circle)
            circle = self.msp.add_circle(
                (light_x, light_y),
                light_size,
                dxfattribs={"layer": "EDGE_LIGHTS"}
            )

            # Add text label
            self.msp.add_text(
                f"R{i}",
                dxfattribs={
                    "layer": "EDGE_LIGHTS",
                    "height": 1.0,
                    "halign": ezdxf.const.TextHorizontalAlignment.CENTER,
                }
            ).set_pos((light_x, light_y + 3))

    def create_safety_zones(
        self,
        runway_length: float = 3000.0,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0),
        zone_width: float = 100.0
    ) -> None:
        """
        Create safety zones around runway perimeter.
        
        Args:
            runway_length: Runway length
            runway_width: Runway width
            start_point: Runway starting corner
            zone_width: Width of safety zone in meters
        """
        x, y = start_point

        # Outer boundary of safety zone
        outer_points = [
            (x - zone_width, y - zone_width),
            (x + runway_length + zone_width, y - zone_width),
            (x + runway_length + zone_width, y + runway_width + zone_width),
            (x - zone_width, y + runway_width + zone_width),
            (x - zone_width, y - zone_width)
        ]

        # Draw outer safety zone boundary
        self.msp.add_lwpolyline(
            outer_points,
            dxfattribs={"layer": "SAFETY_ZONES", "lineweight": 15}
        )

        # Add diagonal hatching pattern for safety zones (corners)
        corner_size = zone_width * 0.8

        # Top-left corner safety zone
        tl_points = [
            (x - zone_width, y - zone_width),
            (x - zone_width + corner_size, y - zone_width),
            (x - zone_width, y - zone_width + corner_size),
            (x - zone_width, y - zone_width)
        ]
        self.msp.add_lwpolyline(
            tl_points,
            dxfattribs={"layer": "SAFETY_ZONES", "lineweight": 10}
        )

        # Top-right corner safety zone
        tr_points = [
            (x + runway_length + zone_width, y - zone_width),
            (x + runway_length + zone_width - corner_size, y - zone_width),
            (x + runway_length + zone_width, y - zone_width + corner_size),
            (x + runway_length + zone_width, y - zone_width)
        ]
        self.msp.add_lwpolyline(
            tr_points,
            dxfattribs={"layer": "SAFETY_ZONES", "lineweight": 10}
        )

        # Bottom-left corner safety zone
        bl_points = [
            (x - zone_width, y + runway_width + zone_width),
            (x - zone_width + corner_size, y + runway_width + zone_width),
            (x - zone_width, y + runway_width + zone_width - corner_size),
            (x - zone_width, y + runway_width + zone_width)
        ]
        self.msp.add_lwpolyline(
            bl_points,
            dxfattribs={"layer": "SAFETY_ZONES", "lineweight": 10}
        )

        # Bottom-right corner safety zone
        br_points = [
            (x + runway_length + zone_width, y + runway_width + zone_width),
            (x + runway_length + zone_width - corner_size, y + runway_width + zone_width),
            (x + runway_length + zone_width, y + runway_width + zone_width - corner_size),
            (x + runway_length + zone_width, y + runway_width + zone_width)
        ]
        self.msp.add_lwpolyline(
            br_points,
            dxfattribs={"layer": "SAFETY_ZONES", "lineweight": 10}
        )

    def add_dimension_annotations(
        self,
        runway_length: float = 3000.0,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0)
    ) -> None:
        """
        Add dimension annotations to the runway layout.
        
        Args:
            runway_length: Runway length
            runway_width: Runway width
            start_point: Runway starting corner
        """
        x, y = start_point

        # Length dimension
        self.msp.add_linear_dim(
            base=(x, y - 20),
            p1=(x, y - 20),
            p2=(x + runway_length, y - 20),
            dxfattribs={"layer": "DIMENSIONS"}
        )

        # Width dimension (left side)
        self.msp.add_linear_dim(
            base=(x - 20, y),
            p1=(x - 20, y),
            p2=(x - 20, y + runway_width),
            dxfattribs={"layer": "DIMENSIONS"}
        )

        # Add text annotations
        self.msp.add_text(
            f"Runway Length: {runway_length}m",
            dxfattribs={
                "layer": "ANNOTATIONS",
                "height": 2.5,
            }
        ).set_pos((x + runway_length / 2, y - 35))

        self.msp.add_text(
            f"Runway Width: {runway_width}m",
            dxfattribs={
                "layer": "ANNOTATIONS",
                "height": 2.5,
            }
        ).set_pos((x - 50, y + runway_width / 2))

        # Title annotation
        self.msp.add_text(
            "RUNWAY LAYOUT",
            dxfattribs={
                "layer": "ANNOTATIONS",
                "height": 5.0,
                "bold": True,
            }
        ).set_pos((x + runway_length / 2, y + runway_width + 50))

    def generate_complete_layout(
        self,
        runway_length: float = 3000.0,
        runway_width: float = 60.0,
        start_point: Tuple[float, float] = (0.0, 0.0)
    ) -> None:
        """
        Generate a complete runway layout with all elements.
        
        Args:
            runway_length: Runway length in meters
            runway_width: Runway width in meters
            start_point: Starting corner point (x, y)
        """
        self.create_runway_base(runway_length, runway_width, start_point)
        self.create_centerline_markings(runway_length, runway_width, start_point)
        self.create_threshold_markings(runway_width, start_point)
        self.create_edge_lights(runway_length, runway_width, start_point)
        self.create_safety_zones(runway_length, runway_width, start_point)
        self.add_dimension_annotations(runway_length, runway_width, start_point)

    def save(self) -> None:
        """Save the DXF file to disk."""
        self.doc.saveas(self.filename)
        print(f"CAD file saved: {self.filename}")

    def get_file_path(self) -> str:
        """Get the absolute path of the generated DXF file."""
        return os.path.abspath(self.filename)


def main():
    """Main function to demonstrate CAD generator usage."""
    # Create generator instance
    generator = RunwayCADGenerator("runway_layout.dxf")

    # Generate complete runway layout with standard dimensions
    generator.generate_complete_layout(
        runway_length=3000.0,  # 3000 meters
        runway_width=60.0,     # 60 meters
        start_point=(0.0, 0.0)
    )

    # Save the DXF file
    generator.save()

    print("Runway CAD layout generated successfully!")
    print(f"Output file: {generator.get_file_path()}")


if __name__ == "__main__":
    main()
