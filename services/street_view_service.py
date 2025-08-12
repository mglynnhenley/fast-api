import os
import requests
import math
from typing import Optional, List, Dict, Any, Tuple


class StreetViewService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Street View service.
        
        Args:
            api_key: Google Maps API key. If None, will use GOOGLE_MAPS_API_KEY environment variable
        """
        if api_key is None:
            api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        
        if not api_key:
            raise ValueError("Google Maps API key is required. Set GOOGLE_MAPS_API_KEY environment variable or pass api_key parameter.")
        
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/streetview"
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def get_street_view_at_degree(self, location: str, degree: int, size: str = '1024x768') -> Dict[str, Any]:
        """
        Get a Street View image at a specific degree/heading.
        
        Args:
            location: Address or coordinates
            degree: Camera heading in degrees (0-360)
            size: Image size (default: '1024x768')
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - imageBuffer: Bytes of the image (if successful)
                - url: The Street View URL (if successful)
                - error: Error message (if failed)
        """
        try:
            params = {
                'location': location,
                'size': size,
                'heading': degree,
                'pitch': 0,
                'fov': 90,
                'key': self.api_key
            }
            
            url = f"{self.base_url}?{self._build_query_string(params)}"
            
            response = requests.get(url)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
            
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return {
                    'success': False,
                    'error': f'Expected image response, got: {content_type}'
                }
            
            return {
                'success': True,
                'imageBuffer': response.content,
                'url': url,
                'degree': degree
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_street_view_at_degrees(self, location: str, degrees: List[int], size: str = '1024x768') -> List[Dict[str, Any]]:
        """
        Get Street View images at multiple degrees.
        
        Args:
            location: Address or coordinates
            degrees: List of camera headings in degrees (0-360)
            size: Image size (default: '1024x768')
        
        Returns:
            List of dictionaries, each containing:
                - success: Boolean indicating success
                - imageBuffer: Bytes of the image (if successful)
                - url: The Street View URL (if successful)
                - degree: The degree used
                - error: Error message (if failed)
        """
        results = []
        
        for degree in degrees:
            result = self.get_street_view_at_degree(location, degree, size)
            results.append(result)
        
        return results
    
    def get_coordinates(self, location: str) -> Tuple[float, float]:
        """
        Get coordinates (lat, lng) for a location string.
        
        Args:
            location: Address or coordinates string
        
        Returns:
            Tuple of (latitude, longitude)
        """
        # If location is already coordinates, parse them
        if ',' in location and all(c.isdigit() or c in '.-, ' for c in location):
            try:
                coords = location.replace(' ', '').split(',')
                return float(coords[0]), float(coords[1])
            except:
                pass
        
        # Otherwise, geocode the address
        params = {
            'address': location,
            'key': self.api_key
        }
        
        response = requests.get(self.geocoding_url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Geocoding failed: {response.status_code}")
        
        data = response.json()
        
        if data['status'] != 'OK' or not data['results']:
            raise Exception(f"Geocoding failed: {data['status']}")
        
        location_data = data['results'][0]['geometry']['location']
        return location_data['lat'], location_data['lng']
    
    def calculate_image_edges(self, lat: float, lng: float, heading: int, fov: int = 90, distance: float = 100) -> Dict[str, Tuple[float, float]]:
        """
        Calculate the coordinates of the edges of a Street View image.
        
        Args:
            lat: Latitude of the camera position
            lng: Longitude of the camera position
            heading: Camera heading in degrees (0-360)
            fov: Field of view in degrees (default: 90)
            distance: Distance in meters to project the edges (default: 100)
        
        Returns:
            Dictionary with edge coordinates:
                - 'top_left': (lat, lng)
                - 'top_right': (lat, lng)
                - 'bottom_left': (lat, lng)
                - 'bottom_right': (lat, lng)
                - 'center': (lat, lng) - center of the image
                - 'camera_position': (lat, lng)
        """
        # Convert heading and FOV to radians
        heading_rad = math.radians(heading)
        fov_rad = math.radians(fov)
        
        # Calculate the angles for each corner
        left_angle = heading_rad - fov_rad / 2
        right_angle = heading_rad + fov_rad / 2
        
        # Earth's radius in meters
        earth_radius = 6371000
        
        # Calculate the center point of the image
        center_lat = lat + (distance * math.cos(heading_rad)) / earth_radius * (180 / math.pi)
        center_lng = lng + (distance * math.sin(heading_rad)) / (earth_radius * math.cos(math.radians(lat))) * (180 / math.pi)
        
        # Calculate the left edge
        left_lat = lat + (distance * math.cos(left_angle)) / earth_radius * (180 / math.pi)
        left_lng = lng + (distance * math.sin(left_angle)) / (earth_radius * math.cos(math.radians(lat))) * (180 / math.pi)
        
        # Calculate the right edge
        right_lat = lat + (distance * math.cos(right_angle)) / earth_radius * (180 / math.pi)
        right_lng = lng + (distance * math.sin(right_angle)) / (earth_radius * math.cos(math.radians(lat))) * (180 / math.pi)
        
        # For simplicity, we'll use the same distance for top/bottom
        # In a real implementation, you might want to account for pitch and elevation
        top_lat = center_lat + (distance * 0.1) / earth_radius * (180 / math.pi)
        top_lng = center_lng
        bottom_lat = center_lat - (distance * 0.1) / earth_radius * (180 / math.pi)
        bottom_lng = center_lng
        
        return {
            'top_left': (left_lat, left_lng),
            'top_right': (right_lat, right_lng),
            'bottom_left': (left_lat, left_lng),  # Simplified
            'bottom_right': (right_lat, right_lng),  # Simplified
            'center': (center_lat, center_lng),
            'camera_position': (lat, lng)
        }
    
    def get_street_view_with_coordinates(self, location: str, degree: int, size: str = '1024x768', fov: int = 90) -> Dict[str, Any]:
        """
        Get Street View image with calculated edge coordinates.
        
        Args:
            location: Address or coordinates
            degree: Camera heading in degrees (0-360)
            size: Image size (default: '1024x768')
            fov: Field of view in degrees (default: 90)
        
        Returns:
            Dictionary containing image data and edge coordinates
        """
        # Get the image first
        image_result = self.get_street_view_at_degree(location, degree, size)
        
        if not image_result['success']:
            return image_result
        
        # Get coordinates for the location
        try:
            lat, lng = self.get_coordinates(location)
            
            # Calculate edge coordinates
            edges = self.calculate_image_edges(lat, lng, degree, fov)
            
            # Add coordinate information to the result
            image_result.update({
                'coordinates': {
                    'camera_position': (lat, lng),
                    'edges': edges
                }
            })
            
        except Exception as e:
            # If coordinate calculation fails, still return the image
            image_result['coordinate_error'] = str(e)
        
        return image_result
    
    def get_street_view_at_degrees_with_coordinates(self, location: str, degrees: List[int], size: str = '1024x768', fov: int = 90) -> List[Dict[str, Any]]:
        """
        Get Street View images at multiple degrees with edge coordinates.
        
        Args:
            location: Address or coordinates
            degrees: List of camera headings in degrees (0-360)
            size: Image size (default: '1024x768')
            fov: Field of view in degrees (default: 90)
        
        Returns:
            List of dictionaries with image data and edge coordinates
        """
        results = []
        
        for degree in degrees:
            result = self.get_street_view_with_coordinates(location, degree, size, fov)
            results.append(result)
        
        return results
    
    def _build_query_string(self, params: Dict[str, Any]) -> str:
        """Build a query string from parameters."""
        return '&'.join([f"{k}={v}" for k, v in params.items() if v is not None])


if __name__ == "__main__":
    # Example usage
    try:
        service = StreetViewService()
        
        # Example 1: Get Street View at a specific degree
        print("Getting Street View at 90 degrees...")
        result = service.get_street_view_at_degree(
            location="1600 Amphitheatre Parkway, Mountain View, CA",
            degree=90
        )
        
        if result['success']:
            print(f"✅ Success! Got image at {result['degree']} degrees")
            print(f"URL: {result['url']}")
        else:
            print(f"❌ Error: {result['error']}")
        
        # Example 2: Get Street View at multiple degrees
        print("\nGetting Street View at multiple degrees...")
        results = service.get_street_view_at_degrees(
            location="1600 Amphitheatre Parkway, Mountain View, CA",
            degrees=[0, 90, 180, 270]
        )
        
        for result in results:
            if result['success']:
                print(f"✅ {result['degree']}°: Success")
            else:
                print(f"❌ {result['degree']}°: {result['error']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
