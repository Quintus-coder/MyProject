"""
CAD Generator for Runway Geometry
Generates 3D CAD models from runway_geometry.json data with support for:
- Runway base surface
- Centerline markings
- Edge lights
- Threshold markings
- Touchdown zone lights
- Export to STEP format
"""

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class LightType(Enum):
    """Enumeration of light types used in runway"""
    EDGE = "edge"
    THRESHOLD = "threshold"
    TOUCHDOWN_ZONE = "touchdown_zone"


@dataclass
class Vector3D:
    """3D vector representation"""
    x: float
    y: float
    z: float

    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: 'Vector3D') -> float:
        """Calculate dot product"""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """Calculate cross product"""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def magnitude(self) -> float:
        """Calculate vector magnitude"""
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self) -> 'Vector3D':
        """Return normalized vector"""
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple"""
        return (self.x, self.y, self.z)


@dataclass
class Light:
    """3D light element"""
    position: Vector3D
    light_type: LightType
    radius: float = 0.05  # 50mm radius for light fixture
    height: float = 0.1    # 100mm height above surface

    def get_light_color(self) -> Tuple[int, int, int]:
        """Get RGB color based on light type"""
        colors = {
            LightType.EDGE: (255, 255, 255),           # White
            LightType.THRESHOLD: (0, 255, 0),          # Green
            LightType.TOUCHDOWN_ZONE: (255, 255, 255)  # White
        }
        return colors.get(self.light_type, (255, 255, 255))


@dataclass
class Marking:
    """2D marking element"""
    start_point: Vector3D
    end_point: Vector3D
    marking_type: str  # "centerline", "threshold", etc.
    width: float = 0.15  # 150mm standard width
    z_offset: float = 0.001  # Slight elevation above surface


class RunwayGeometry:
    """Represents runway geometry data"""

    def __init__(self, geometry_data: Dict):
        """Initialize from geometry dictionary"""
        rw_dims = geometry_data.get("runwayDimensions", {})
        rw_geom = geometry_data.get("runwayGeometry", {})
        rw_mark = geometry_data.get("runwayMarkings", {})

        self.name = geometry_data.get("name", geometry_data.get("runway", {}).get("runwayIdentifier", "Runway"))

        self.length = (
            rw_dims.get("length", {}).get("meters")
            or geometry_data.get("length", 3000.0)
        )
        self.width = (
            rw_dims.get("width", {}).get("meters")
            or geometry_data.get("width", 60.0)
        )

        self.heading = (
            rw_geom.get("magnetic_heading_18R", {}).get("trueHeading")
            or geometry_data.get("heading", 0.0)
        )

        self.elevation = (
            rw_geom.get("slope", {}).get("elevation_18R_meters")
            or geometry_data.get("elevation", 0.0)
        )

        origin_data = geometry_data.get("origin", {})
        self.origin = Vector3D(
            origin_data.get("x", 0.0),
            origin_data.get("y", 0.0),
            origin_data.get("z", 0.0)
        )

        self.surface_type = geometry_data.get("surface_type", "asphalt")

        start_dist = rw_mark.get("touchdown_zone_markings", {}).get("start_distance_from_threshold")
        end_dist = rw_mark.get("touchdown_zone_markings", {}).get("end_distance_from_threshold")
        self.threshold_distance = start_dist or geometry_data.get("threshold_distance", 300.0)
        self.touchdown_zone_length = (
            (end_dist - start_dist) if (start_dist is not None and end_dist is not None) else geometry_data.get("touchdown_zone_length", 900.0)
        )

    def get_runway_corners(self) -> List[Vector3D]:
        """Calculate 4 corners of runway base"""
        heading_rad = math.radians(self.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        # Length direction vector
        length_vec = Vector3D(cos_h * self.length, sin_h * self.length, 0)
        # Width direction vector (perpendicular)
        width_vec = Vector3D(-sin_h * self.width / 2, cos_h * self.width / 2, 0)

        corners = [
            self.origin - width_vec,  # Southwest
            self.origin + width_vec,  # Northwest
            self.origin + length_vec + width_vec,  # Northeast
            self.origin + length_vec - width_vec,  # Southeast
        ]
        return corners


class STEPExporter:
    """Exports 3D model to STEP (ISO 10303) format"""

    def __init__(self, filename: str):
        """Initialize STEP exporter"""
        self.filename = filename
        self.entities: List[str] = []
        self.entity_count = 1
        self.current_id = 1

    def _get_entity_id(self) -> int:
        """Get next entity ID"""
        entity_id = self.current_id
        self.current_id += 1
        return entity_id

    def add_cartesian_point(self, point: Vector3D) -> int:
        """Add a 3D point to STEP file"""
        entity_id = self._get_entity_id()
        coord_str = f"{point.x:.4f}, {point.y:.4f}, {point.z:.4f}"
        self.entities.append(f"#{entity_id} = CARTESIAN_POINT('Point_{entity_id}', ({coord_str}));")
        return entity_id

    def add_line(self, point1: Vector3D, point2: Vector3D) -> int:
        """Add a line segment"""
        p1_id = self.add_cartesian_point(point1)
        p2_id = self.add_cartesian_point(point2)
        entity_id = self._get_entity_id()
        self.entities.append(f"#{entity_id} = LINE('Line_{entity_id}', #{p1_id}, #{p2_id});")
        return entity_id

    def add_direction(self, vec: Vector3D, label: str) -> int:
        """Add a DIRECTION entity"""
        norm = vec.normalize()
        entity_id = self._get_entity_id()
        self.entities.append(
            f"#{entity_id} = DIRECTION('{label}', ({norm.x:.4f}, {norm.y:.4f}, {norm.z:.4f}));"
        )
        return entity_id

    def add_axis2_placement(self, center_id: int, axis_dir_id: int, ref_dir_id: int) -> int:
        """Add AXIS2_PLACEMENT_3D entity"""
        entity_id = self._get_entity_id()
        self.entities.append(
            f"#{entity_id} = AXIS2_PLACEMENT_3D('Axis_{entity_id}', #{center_id}, #{axis_dir_id}, #{ref_dir_id});"
        )
        return entity_id

    def add_circle(self, center: Vector3D, radius: float, normal: Vector3D) -> int:
        """Add a circle lying on plane defined by normal"""
        center_id = self.add_cartesian_point(center)

        axis_dir_id = self.add_direction(normal, f"AxisDir_{self.current_id}")

        # Choose a reference direction orthogonal to the normal
        normal_unit = normal.normalize()
        fallback = Vector3D(1, 0, 0) if abs(normal_unit.x) < 0.9 else Vector3D(0, 1, 0)
        ref_vec = fallback - normal_unit * normal_unit.dot(fallback)
        ref_dir_id = self.add_direction(ref_vec, f"RefDir_{self.current_id}")

        placement_id = self.add_axis2_placement(center_id, axis_dir_id, ref_dir_id)

        entity_id = self._get_entity_id()
        self.entities.append(
            f"#{entity_id} = CIRCLE('Circle_{entity_id}', #{placement_id}, {radius:.4f});"
        )
        return entity_id

    def add_plane(self, vertices: List[Vector3D]) -> int:
        """Add a plane (polygon)"""
        vertex_ids = [self.add_cartesian_point(v) for v in vertices]
        if vertex_ids and vertex_ids[0] != vertex_ids[-1]:
            vertex_ids.append(vertex_ids[0])
        entity_id = self._get_entity_id()
        vertex_refs = ", ".join([f"#{vid}" for vid in vertex_ids])
        self.entities.append(
            f"#{entity_id} = POLYLINE('Polygon_{entity_id}', ({vertex_refs}));"
        )
        return entity_id

    def write(self) -> str:
        """Generate and write STEP file content"""
        header = self._generate_header()
        data_section = self._generate_data_section()
        footer = "ENDSEC;\nEND-ISO-10303-21;"

        content = f"{header}\n{data_section}\n{footer}"

        with open(self.filename, 'w') as f:
            f.write(content)

        return self.filename

    def _generate_header(self) -> str:
        """Generate STEP file header"""
        timestamp = datetime.now().isoformat()
        return f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Runway CAD Model'), '2.0');
FILE_NAME('{os.path.basename(self.filename)}', '{timestamp}', ('CAD Generator'), (''),
  'CAD Generator v1.0', 'Generated', '');
FILE_SCHEMA(('AP203'));
ENDHDR;"""

    def _generate_data_section(self) -> str:
        """Generate data section with all entities"""
        return "DATA;\n" + "\n".join(self.entities)


class CADGenerator:
    """Main CAD generation engine"""

    def __init__(self, geometry_file: str):
        """Initialize CAD generator from geometry file"""
        self.geometry_data = self._load_geometry(geometry_file)
        self.runway = RunwayGeometry(self.geometry_data)
        self.markings: List[Marking] = []
        self.lights: List[Light] = []
        self.exporter: Optional[STEPExporter] = None

    def _load_geometry(self, geometry_file: str) -> Dict:
        """Load runway geometry from JSON file"""
        if not os.path.exists(geometry_file):
            raise FileNotFoundError(f"Geometry file not found: {geometry_file}")

        with open(geometry_file, 'r') as f:
            return json.load(f)

    def generate_runway_base(self, exporter: STEPExporter) -> int:
        """Generate 3D runway base surface"""
        corners = self.runway.get_runway_corners()
        # Create runway as a plane
        return exporter.add_plane(corners)

    def generate_centerline_markings(self, exporter: STEPExporter) -> List[int]:
        """Generate centerline markings down the center of runway"""
        heading_rad = math.radians(self.runway.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        marking_ids = []
        line_length = 30.0  # 30m segments
        spacing = 60.0     # 60m between segments
        num_segments = int(self.runway.length / spacing)

        for i in range(num_segments):
            distance = i * spacing
            center_point = self.runway.origin + Vector3D(
                cos_h * distance, sin_h * distance, self.runway.elevation
            )
            start = center_point - Vector3D(cos_h * line_length / 2, sin_h * line_length / 2, 0)
            end = center_point + Vector3D(cos_h * line_length / 2, sin_h * line_length / 2, 0)

            marking = Marking(start, end, "centerline")
            self.markings.append(marking)
            marking_ids.append(exporter.add_line(start, end))

        return marking_ids

    def generate_edge_lights(self, exporter: STEPExporter, spacing: float = 50.0) -> List[int]:
        """Generate edge lights along runway edges"""
        heading_rad = math.radians(self.runway.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        # Width vectors for left and right edges
        width_vec = Vector3D(-sin_h, cos_h, 0) * (self.runway.width / 2)
        light_ids = []

        num_lights = int(self.runway.length / spacing)

        for i in range(num_lights):
            distance = i * spacing
            base_point = self.runway.origin + Vector3D(
                cos_h * distance, sin_h * distance, self.runway.elevation
            )

            # Left edge light
            left_pos = base_point + width_vec
            left_light = Light(left_pos, LightType.EDGE)
            self.lights.append(left_light)
            light_ids.append(exporter.add_circle(left_pos, left_light.radius, Vector3D(0, 0, 1)))

            # Right edge light
            right_pos = base_point - width_vec
            right_light = Light(right_pos, LightType.EDGE)
            self.lights.append(right_light)
            light_ids.append(exporter.add_circle(right_pos, right_light.radius, Vector3D(0, 0, 1)))

        return light_ids

    def generate_threshold_markings(self, exporter: STEPExporter) -> List[int]:
        """Generate threshold markings at runway start"""
        heading_rad = math.radians(self.runway.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        # Perpendicular to runway direction
        perp_vec = Vector3D(-sin_h, cos_h, 0) * (self.runway.width / 2)

        threshold_point = self.runway.origin + Vector3D(
            cos_h * self.runway.threshold_distance,
            sin_h * self.runway.threshold_distance,
            self.runway.elevation
        )
        start = threshold_point - perp_vec
        end = threshold_point + perp_vec

        marking = Marking(start, end, "threshold")
        self.markings.append(marking)

        marking_ids = []
        # Create dashed threshold line (3 segments)
        dash_length = self.runway.width / 4
        num_dashes = 4
        dash_spacing = self.runway.width / num_dashes

        for i in range(num_dashes):
            offset = i * dash_spacing - self.runway.width / 2 + dash_length / 2
            dash_start = threshold_point + Vector3D(-sin_h * offset, cos_h * offset, 0)
            dash_start -= Vector3D(cos_h * dash_length / 2, sin_h * dash_length / 2, 0)

            dash_end = dash_start + Vector3D(cos_h * dash_length, sin_h * dash_length, 0)

            marking_ids.append(exporter.add_line(dash_start, dash_end))

        return marking_ids

    def generate_threshold_lights(self, exporter: STEPExporter, lights_per_side: int = 6) -> List[int]:
        """Generate threshold lights on both sides"""
        heading_rad = math.radians(self.runway.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        perp_vec = Vector3D(-sin_h, cos_h, 0)
        light_ids = []

        threshold_point = self.runway.origin + Vector3D(
            cos_h * self.runway.threshold_distance,
            sin_h * self.runway.threshold_distance,
            self.runway.elevation
        )

        spacing = self.runway.width / (lights_per_side + 1)

        for i in range(1, lights_per_side + 1):
            offset = i * spacing - self.runway.width / 2

            # Left threshold light
            left_pos = threshold_point + perp_vec * offset
            left_light = Light(left_pos, LightType.THRESHOLD)
            self.lights.append(left_light)
            light_ids.append(exporter.add_circle(left_pos, left_light.radius, Vector3D(0, 0, 1)))

            # Right threshold light
            right_pos = threshold_point - perp_vec * offset
            right_light = Light(right_pos, LightType.THRESHOLD)
            self.lights.append(right_light)
            light_ids.append(exporter.add_circle(right_pos, right_light.radius, Vector3D(0, 0, 1)))

        return light_ids

    def generate_touchdown_zone_lights(self, exporter: STEPExporter, spacing: float = 75.0) -> List[int]:
        """Generate touchdown zone lights"""
        heading_rad = math.radians(self.runway.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)

        perp_vec = Vector3D(-sin_h, cos_h, 0) * (self.runway.width / 4)
        light_ids = []

        start_distance = self.runway.threshold_distance
        end_distance = start_distance + self.runway.touchdown_zone_length

        num_lights = int((end_distance - start_distance) / spacing)

        for i in range(num_lights):
            distance = start_distance + i * spacing
            base_point = self.runway.origin + Vector3D(
                cos_h * distance, sin_h * distance, self.runway.elevation
            )

            # Left touchdown zone light
            left_pos = base_point + perp_vec
            left_light = Light(left_pos, LightType.TOUCHDOWN_ZONE)
            self.lights.append(left_light)
            light_ids.append(exporter.add_circle(left_pos, left_light.radius, Vector3D(0, 0, 1)))

            # Right touchdown zone light
            right_pos = base_point - perp_vec
            right_light = Light(right_pos, LightType.TOUCHDOWN_ZONE)
            self.lights.append(right_light)
            light_ids.append(exporter.add_circle(right_pos, right_light.radius, Vector3D(0, 0, 1)))

        return light_ids

    def generate_complete_model(self, output_file: str = "runway_model.stp") -> str:
        """Generate complete runway CAD model and export to STEP format"""
        self.exporter = STEPExporter(output_file)

        print(f"Generating CAD model for: {self.runway.name}")
        print(f"  Runway dimensions: {self.runway.length}m x {self.runway.width}m")
        print(f"  Heading: {self.runway.heading} deg")
        print()

        # Generate all components
        print("Generating runway base...")
        self.generate_runway_base(self.exporter)

        print("Generating centerline markings...")
        self.generate_centerline_markings(self.exporter)

        print("Generating edge lights...")
        self.generate_edge_lights(self.exporter)

        print("Generating threshold markings...")
        self.generate_threshold_markings(self.exporter)

        print("Generating threshold lights...")
        self.generate_threshold_lights(self.exporter)

        print("Generating touchdown zone lights...")
        self.generate_touchdown_zone_lights(self.exporter)

        # Export to STEP
        print(f"\nExporting to STEP format: {output_file}")
        output_path = self.exporter.write()

        print(f"Model generation complete!")
        print(f"  Total markings: {len(self.markings)}")
        print(f"  Total lights: {len(self.lights)}")
        print(f"  Output file: {output_path}")

        return output_path

    def get_model_statistics(self) -> Dict:
        """Get statistics about the generated model"""
        return {
            "runway_name": self.runway.name,
            "runway_length": self.runway.length,
            "runway_width": self.runway.width,
            "heading": self.runway.heading,
            "elevation": self.runway.elevation,
            "total_markings": len(self.markings),
            "total_lights": len(self.lights),
            "edge_lights": sum(1 for l in self.lights if l.light_type == LightType.EDGE),
            "threshold_lights": sum(1 for l in self.lights if l.light_type == LightType.THRESHOLD),
            "touchdown_zone_lights": sum(1 for l in self.lights if l.light_type == LightType.TOUCHDOWN_ZONE),
        }


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cad_generator.py <geometry_file.json> [output_file.stp]")
        print("\nExample:")
        print("  python cad_generator.py runway_geometry.json runway_model.stp")
        sys.exit(1)

    geometry_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "runway_model.stp"

    try:
        generator = CADGenerator(geometry_file)
        output_path = generator.generate_complete_model(output_file)
        stats = generator.get_model_statistics()

        print("\nModel Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
