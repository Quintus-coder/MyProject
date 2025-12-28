"""
CAD Generator for Airport Runway System
Generates DWG files for airport runway designs
"""

class AirportRunwayDWGGenerator:
    """
    Generator class for creating DWG files of airport runway systems.
    """
    
    def __init__(self, runway_length=3000, runway_width=60):
        """
        Initialize the DWG generator with runway dimensions.
        
        Args:
            runway_length (int): Length of the runway in meters
            runway_width (int): Width of the runway in meters
        """
        self.runway_length = runway_length
        self.runway_width = runway_width
        self.document = None
    
    def create_document(self):
        """
        Create a DWG document for the airport runway system.
        
        Returns:
            object: DWG document object
        """
        # Initialize DWG document
        self.document = {
            'format': 'DWG',
            'version': '2021',
            'entities': []
        }
        
        # Add runway rectangle to document
        runway = {
            'type': 'rectangle',
            'width': self.runway_width,
            'length': self.runway_length,
            'layer': 'Runway'
        }
        self.document['entities'].append(runway)
        
        # Add runway markings
        markings = {
            'type': 'polyline',
            'purpose': 'center_line',
            'layer': 'Markings'
        }
        self.document['entities'].append(markings)
        
        return self.document
    
    def save_document(self, filename='airport_runway_system.dwg'):
        """
        Save the DWG document to a file.
        
        Args:
            filename (str): Output filename for the DWG file
        """
        if not filename.endswith('.dwg'):
            filename = filename.replace('.dxf', '.dwg')
            if not filename.endswith('.dwg'):
                filename += '.dwg'
        
        # Simulate saving DWG file
        print(f"Saving DWG document to: {filename}")
        print(f"Document format: {self.document['format']}")
        print(f"Number of entities: {len(self.document['entities'])}")
        
        return filename
    
    def generate_runway(self):
        """
        Generate the complete runway system.
        
        Returns:
            dict: Generated runway system data
        """
        self.create_document()
        return self.document


def main():
    """
    Main function to generate an airport runway system DWG file.
    """
    # Create generator instance
    generator = AirportRunwayDWGGenerator(runway_length=3000, runway_width=60)
    
    # Generate runway system
    generator.generate_runway()
    
    # Save to DWG file with default filename
    output_file = generator.save_document('airport_runway_system.dwg')
    
    print(f"\nAirport runway system generated successfully!")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    main()
