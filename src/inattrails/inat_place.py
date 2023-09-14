import os
from dataclasses import dataclass
from typing import List, Set, Tuple, Union

from shapely.geometry import shape, Polygon  # on Ubuntu install with: sudo apt install --yes python3-shapely

from .cache import cache_directory, readJson, writeJson, scale_bbox
from .api import inat_api


@dataclass
class Place:
    """
    Class *Place* represents a named place.
    """
    id                : int
    "numeric place id"
    name              : str
    "place name"
    bbox_area         : float
    "area of the bounding box"
    geometry_geojson  : dict
    "geojson of the place"
    ancestor_place_ids: List[int]
    "place ids of this place's ancestors"


def getPlacesNearby(bbox: Tuple[Tuple[float,float],Tuple[float,float]],
                    bufferPolygon: Polygon) -> List[Place]:
    """
    Download list of places for given bounding box. Return list of those
    that intersect buffer polygon.

    :param bbox: bounding box
    :type bbox: pair of two pairs, the min longitude and latitude and the max longitude and latitude
    :param bufferPolygon: buffer polygon around the tracks of the hike
    :type bufferPolygon: shapely.geometry.Polygon
    :returns: a list of instances of class *Place* in increasing order of bbox area
    """
    ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 1000)
    places_file = os.path.join(cache_directory,
                               f'places_{min_lon:.3f}_{min_lat:.3f}_'
                               f'{max_lon:.3f}_{max_lat:.3f}.json.gz')
    if os.path.exists(places_file):
        places = readJson(places_file)
    else:
        places = inat_api.get_places_nearby(nelat = max_lat, nelng = max_lon,
                                            swlng = min_lon, swlat = min_lat)
        writeJson(places_file, places)

    places = [ Place(place['id'], place['name'], place['bbox_area'],
                     place['geometry_geojson'],
                     [] if place['ancestor_place_ids'] is None
                        else place['ancestor_place_ids'])
              for kind in ['standard', 'community']
              for place in places[kind]
              if shape(place['geometry_geojson']).intersects(bufferPolygon) ]
    places.sort(key=lambda p:p.bbox_area)
    return places


def getPlacesById(id: Union[int, Set[int]]) -> List[Place]:
    """
    Get single place or multiple places by numeric id.

    :param id: numeric place id or set of numeric place ids
    :type id: *int* or set of *int*
    :returns: a list of instances of class *Place* in increasing order of bbox area
    """
    places_file = os.path.join(cache_directory,
                               f'places_{sorted(id)}.json.gz'
                               if isinstance(id, set)
                               else f'places_{id}.json.gz')
    if os.path.exists(places_file):
        places = readJson(places_file)
    else:
        places = inat_api.get_places_by_id(id)
        writeJson(places_file, places)

    places = [ Place(place['id'],
                     place['display_name'] if 'display_name' in place
                                           else place['name'],
                     place['bbox_area'], place['geometry_geojson'],
                     [] if place['ancestor_place_ids'] is None
                        else place['ancestor_place_ids']) for place in places ]
    places.sort(key=lambda e:e.bbox_area)
    return places
