"""
JSON Converter: ZBAA_tables.json to runway_geometry.json
Converts ZBAA airport table data to runway geometry format with validation.
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RunwayGeometry:
    """Data class representing runway geometry information."""
    runway_id: str
    runway_name: str
    latitude: float
    longitude: float
    elevation: float
    heading: float
    length: float
    width: float
    surface_type: str
    isClosed: bool = False
    lighting_type: Optional[str] = None
    remarks: Optional[str] = None


class JSONValidator:
    """Validates JSON data structure and content."""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that all required fields are present.
        
        Args:
            data: Dictionary to validate
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        missing_fields = [field for field in required_fields if field not in data]
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def validate_numeric_field(value: Any, field_name: str, min_val: Optional[float] = None,
                               max_val: Optional[float] = None) -> Tuple[bool, str]:
        """
        Validate numeric field with optional range checking.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_val: Minimum acceptable value
            max_val: Maximum acceptable value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            numeric_val = float(value)
            if min_val is not None and numeric_val < min_val:
                return False, f"{field_name} is below minimum value ({min_val})"
            if max_val is not None and numeric_val > max_val:
                return False, f"{field_name} exceeds maximum value ({max_val})"
            return True, ""
        except (TypeError, ValueError):
            return False, f"{field_name} must be numeric"
    
    @staticmethod
    def validate_runway_data(runway_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate runway data structure and content.
        
        Args:
            runway_data: Runway data dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_fields = ['runway_id', 'runway_name', 'latitude', 'longitude',
                          'elevation', 'heading', 'length', 'width', 'surface_type']
        
        is_valid, missing = JSONValidator.validate_required_fields(runway_data, required_fields)
        if not is_valid:
            errors.append(f"Missing required fields: {', '.join(missing)}")
        
        # Validate numeric fields
        numeric_validations = {
            'latitude': (-90, 90),
            'longitude': (-180, 180),
            'elevation': (-500, 10000),
            'heading': (0, 360),
            'length': (1000, 5000),
            'width': (30, 150)
        }
        
        for field, (min_val, max_val) in numeric_validations.items():
            if field in runway_data:
                is_valid, error_msg = JSONValidator.validate_numeric_field(
                    runway_data[field], field, min_val, max_val
                )
                if not is_valid:
                    errors.append(error_msg)
        
        # Validate string fields
        if 'runway_id' in runway_data and not isinstance(runway_data['runway_id'], str):
            errors.append("runway_id must be a string")
        if 'surface_type' in runway_data and runway_data['surface_type'] not in \
                ['asphalt', 'concrete', 'gravel', 'grass']:
            errors.append(f"Invalid surface_type: {runway_data['surface_type']}")
        
        return len(errors) == 0, errors


class JSONConverter:
    """Converts ZBAA_tables.json to runway_geometry.json format."""
    
    def __init__(self, input_file: str, output_file: str):
        """
        Initialize converter with input and output file paths.
        
        Args:
            input_file: Path to ZBAA_tables.json
            output_file: Path to output runway_geometry.json
        """
        self.input_file = input_file
        self.output_file = output_file
        self.validator = JSONValidator()
        self.conversion_stats = {
            'total_runways': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'validation_errors': []
        }
    
    def load_json(self, file_path: str) -> Optional[Dict]:
        """
        Load and parse JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data or None if error
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return None
        except IOError as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            return None
    
    def extract_runway_data(self, zbaa_data: Dict) -> List[Dict]:
        """
        Extract runway data from ZBAA_tables.json structure.
        
        Args:
            zbaa_data: Data from ZBAA_tables.json
            
        Returns:
            List of extracted runway data dictionaries
        """
        runways = []
        
        # Handle different possible data structures
        if 'runways' in zbaa_data:
            runways = zbaa_data['runways']
        elif 'data' in zbaa_data and isinstance(zbaa_data['data'], list):
            runways = zbaa_data['data']
        elif isinstance(zbaa_data, list):
            runways = zbaa_data
        else:
            # Try to find runway information in nested structure
            for key, value in zbaa_data.items():
                if isinstance(value, list) and key.lower().endswith('runways'):
                    runways = value
                    break
        
        return runways if isinstance(runways, list) else []
    
    def convert_runway(self, runway_data: Dict) -> Optional[RunwayGeometry]:
        """
        Convert single runway data to RunwayGeometry object.
        
        Args:
            runway_data: Raw runway data from source
            
        Returns:
            RunwayGeometry object or None if conversion fails
        """
        is_valid, errors = self.validator.validate_runway_data(runway_data)
        
        if not is_valid:
            error_msg = f"Validation failed for runway: {errors}"
            logger.warning(error_msg)
            self.conversion_stats['validation_errors'].append(error_msg)
            return None
        
        try:
            runway = RunwayGeometry(
                runway_id=str(runway_data.get('runway_id', '')),
                runway_name=str(runway_data.get('runway_name', '')),
                latitude=float(runway_data.get('latitude', 0.0)),
                longitude=float(runway_data.get('longitude', 0.0)),
                elevation=float(runway_data.get('elevation', 0.0)),
                heading=float(runway_data.get('heading', 0.0)),
                length=float(runway_data.get('length', 0.0)),
                width=float(runway_data.get('width', 0.0)),
                surface_type=str(runway_data.get('surface_type', 'asphalt')).lower(),
                isClosed=bool(runway_data.get('isClosed', False)),
                lighting_type=runway_data.get('lighting_type'),
                remarks=runway_data.get('remarks')
            )
            self.conversion_stats['successful_conversions'] += 1
            return runway
        except Exception as e:
            error_msg = f"Error converting runway: {str(e)}"
            logger.error(error_msg)
            self.conversion_stats['validation_errors'].append(error_msg)
            self.conversion_stats['failed_conversions'] += 1
            return None
    
    def convert(self) -> bool:
        """
        Execute the conversion process.
        
        Returns:
            True if conversion successful, False otherwise
        """
        logger.info(f"Starting conversion from {self.input_file} to {self.output_file}")
        
        # Load source data
        zbaa_data = self.load_json(self.input_file)
        if zbaa_data is None:
            logger.error("Failed to load source data")
            return False
        
        # Extract runway data
        runway_list = self.extract_runway_data(zbaa_data)
        if not runway_list:
            logger.error("No runway data found in source file")
            return False
        
        self.conversion_stats['total_runways'] = len(runway_list)
        logger.info(f"Found {len(runway_list)} runways to convert")
        
        # Convert each runway
        converted_runways = []
        for runway_data in runway_list:
            converted = self.convert_runway(runway_data)
            if converted:
                converted_runways.append(asdict(converted))
        
        # Prepare output
        output_data = {
            'airport_code': 'ZBAA',
            'airport_name': 'Beijing Capital International Airport',
            'conversion_timestamp': datetime.utcnow().isoformat(),
            'runway_count': len(converted_runways),
            'runways': converted_runways,
            'conversion_stats': self.conversion_stats
        }
        
        # Write output file
        try:
            output_dir = os.path.dirname(self.output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully wrote converted data to {self.output_file}")
            logger.info(f"Conversion stats: {self.conversion_stats}")
            return True
        except IOError as e:
            logger.error(f"Error writing output file: {str(e)}")
            return False


def main():
    """Main entry point for the converter."""
    if len(sys.argv) < 3:
        input_file = 'ZBAA_tables.json'
        output_file = 'runway_geometry.json'
        logger.info(f"Using default paths: {input_file} -> {output_file}")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    
    converter = JSONConverter(input_file, output_file)
    success = converter.convert()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
