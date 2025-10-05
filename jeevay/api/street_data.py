import requests

from jeevay.api.models import Street, Intersection, PedestrianPath, Building


class OverpassAPI:
    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GeoX/1.0 (Accessible mapping demo)'
        })

    def get_streets_around(self, lat: float, lon: float, radius: int = 500) -> list[Street]:
        """Get streets around a coordinate within specified radius (meters)."""

        # Overpass QL query for roads and streets
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(primary|secondary|tertiary|residential|unclassified|service)$"]
             (around:{radius},{lat},{lon});
        );
        out geom;
        """

        try:
            response = self.session.post(self.base_url, data={'data': query})
            response.raise_for_status()
            data = response.json()

            streets = []
            for element in data.get('elements', []):
                if element['type'] == 'way' and 'geometry' in element:
                    # Extract street information
                    tags = element.get('tags', {})
                    name = tags.get('name', 'Unnamed Street')
                    highway_type = tags.get('highway', 'unknown')

                    # Convert geometry to coordinate list
                    coordinates = []
                    for node in element['geometry']:
                        coordinates.append((node['lat'], node['lon']))

                    if coordinates:  # Only add streets with valid coordinates
                        street = Street(
                            name=name,
                            coordinates=coordinates,
                            street_type=highway_type
                        )
                        streets.append(street)

            return streets

        except requests.RequestException as e:
            print(f"Error fetching street data: {e}")
            return []

    def get_intersections_around(self, lat: float, lon: float, radius: int = 500) -> list[Intersection]:
        """Get major intersections around a coordinate."""

        query = f"""
        [out:json][timeout:25];
        (
          node["highway"~"^(traffic_signals|crossing)$"]
              (around:{radius},{lat},{lon});
        );
        out;
        """

        try:
            response = self.session.post(self.base_url, data={'data': query})
            response.raise_for_status()
            data = response.json()

            intersections = []
            for element in data.get('elements', []):
                if element['type'] == 'node':
                    intersection = Intersection(
                        lat=element['lat'],
                        lon=element['lon'],
                        connecting_streets=[]  # Would need additional query to find connected streets
                    )
                    intersections.append(intersection)

            return intersections

        except requests.RequestException as e:
            print(f"Error fetching intersection data: {e}")
            return []

    def get_pedestrian_paths_around(self, lat: float, lon: float, radius: int = 500) -> list[PedestrianPath]:
        """Get pedestrian paths (footways, sidewalks, etc.) around a coordinate."""

        # Query for pedestrian-accessible ways
        # Note: sidewalks are usually mapped with footway + sidewalk tag, not highway=sidewalk
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(footway|path|pedestrian|steps)$"]
             (around:{radius},{lat},{lon});
        );
        out geom;
        """

        try:
            response = self.session.post(self.base_url, data={'data': query})
            response.raise_for_status()
            data = response.json()

            paths = []
            for element in data.get('elements', []):
                if element['type'] == 'way' and 'geometry' in element:
                    tags = element.get('tags', {})
                    name = tags.get('name', 'Unnamed Path')
                    path_type = tags.get('highway', 'unknown')

                    # Convert geometry to coordinate list
                    coordinates = []
                    for node in element['geometry']:
                        coordinates.append((node['lat'], node['lon']))

                    if coordinates:
                        path = PedestrianPath(
                            name=name,
                            coordinates=coordinates,
                            path_type=path_type
                        )
                        paths.append(path)

            return paths

        except requests.RequestException as e:
            print(f"Error fetching pedestrian path data: {e}")
            return []

    def get_buildings_around(self, lat: float, lon: float, radius: int = 500) -> list[Building]:
        """Get buildings with addresses around a coordinate."""

        # Query for buildings and POIs with addresses
        # Include both nodes (POIs) and ways (building polygons)
        query = f"""
        [out:json][timeout:25];
        (
          node["addr:housenumber"]
              (around:{radius},{lat},{lon});
          way["addr:housenumber"]
             (around:{radius},{lat},{lon});
          relation["addr:housenumber"]
             (around:{radius},{lat},{lon});
        );
        out center;
        """

        try:
            response = self.session.post(self.base_url, data={'data': query})
            response.raise_for_status()
            data = response.json()

            buildings = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})

                # Build address string
                addr_parts = []
                if 'addr:housenumber' in tags:
                    addr_parts.append(tags['addr:housenumber'])
                if 'addr:street' in tags:
                    addr_parts.append(tags['addr:street'])
                address = ' '.join(addr_parts) if addr_parts else None

                # Get name (for POIs)
                name = tags.get('name', address or 'Unnamed Building')

                # Get coordinates based on element type
                if element['type'] == 'node':
                    building_lat = element['lat']
                    building_lon = element['lon']
                elif element['type'] in ['way', 'relation'] and 'center' in element:
                    building_lat = element['center']['lat']
                    building_lon = element['center']['lon']
                else:
                    # Skip elements without coordinates
                    continue

                building = Building(
                    name=name,
                    lat=building_lat,
                    lon=building_lon,
                    address=address
                )
                buildings.append(building)

            return buildings

        except requests.RequestException as e:
            print(f"Error fetching building data: {e}")
            return []
