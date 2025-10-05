from dataclasses import dataclass


@dataclass
class Address:
    display_name: str
    lat: float
    lon: float
    place_id: str


@dataclass
class Street:
    name: str
    coordinates: list[tuple[float, float]]  # List of (lat, lon) tuples
    street_type: str  # 'primary', 'secondary', 'residential', etc.


@dataclass
class Intersection:
    lat: float
    lon: float
    connecting_streets: list[str]


@dataclass
class PedestrianPath:
    name: str
    coordinates: list[tuple[float, float]]  # List of (lat, lon) tuples
    path_type: str  # 'footway', 'path', 'pedestrian', 'steps', 'sidewalk'


@dataclass
class Building:
    name: str
    lat: float
    lon: float
    address: str | None = None
