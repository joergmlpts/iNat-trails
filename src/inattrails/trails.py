import os

from shapely.geometry import shape, Point, LineString, MultiLineString, Polygon, MultiPolygon   # on Ubuntu install with: sudo apt install --yes python3-shapely
from shapely.geometry.base import BaseGeometry
from shapely import strtree

from .api   import inat_api
from .cache import cache_directory, readJson, writeJson, scale_bbox

from typing import Union, Dict, List, Set, Tuple, Optional


BUFFER_DISTANCE = 0.0002  # buffer distance for polygon around trails


##########################################################################
# Loads named trails and roads for given bounding box and buffer polygon #
# from OpenStreetMap. Provides member function nearestTrail(lat, lon).   #
##########################################################################

class Trails:
    """
    Class *Trails* downloads all named roads and trails within the bounding box
    from the *overpass* API or our local cache. It intersects these roads and
    trails with the buffer polygon. It inserts non-empty intersections into an
    STRTree that allows us to look up the closest trail for given coordinates.

    :param bbox:
    :type bbox: tuple consiting of two pairs, a pair of the min longitude and min latitude and other pair of the  max longitude and max latitude
    :param bufferPolygon: buffer polygon around the tracks of the hike
    :type bufferPolygon: shapely.geometry.Polygon
    """

    def __init__(self, bbox: Tuple[Tuple[float,float],Tuple[float,float]],
                 bufferPolygon: Polygon):
        ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 100)
        file_name = os.path.join(cache_directory,
                                 f'trails_{min_lon:.2f}_{min_lat:.2f}_'
                                 f'{max_lon:.2f}_{max_lat:.2f}.json.gz')
        if os.path.exists(file_name):
            osm_data = readJson(file_name)
        else:
            osm_data = inat_api.get_overpass(f"""
            [out:json];
            way["highway"] ({min_lat},{min_lon},{max_lat},{max_lon});
            (._;>;);
            out;
            """)
            if 'elements' in osm_data:
                writeJson(file_name, osm_data)

        nodes: Dict[int,Tuple[float,float]] = {}
        "id -> (lon, lat)"
        ways: Dict[str,List[Union[LineString,MultiLineString]]] = {}
        "name -> [LineString or MultiLineString, ...]"
        if 'elements' in osm_data:
            for elem in osm_data['elements']:
                type = elem['type']
                if type == 'node':
                    nodes[elem['id']] = (elem['lon'], elem['lat'])
                else:
                    assert type == 'way'
                    if 'nodes' not in elem or len(elem['nodes']) < 2 or \
                       'name' not in elem['tags']:
                        continue
                    lineString = LineString([nodes[n] for n in elem['nodes']])
                    if lineString.intersects(bufferPolygon):
                        name = elem['tags']['name']
                        if name not in ways:
                            ways[name] = []
                        ways[name].append(lineString.
                                          intersection(bufferPolygon))
        self.objs = []
        self.obj2name = {}
        for name in sorted(ways):
            lineStringList = ways[name]
            if len(lineStringList) == 1:
                obj = lineStringList[0]
            else:
                flat = [] # flat list of LineString
                for l in lineStringList:
                    if l.geom_type == 'LineString':
                        flat.append(l)
                    else:
                        assert l.geom_type == 'MultiLineString'
                        flat += l.geoms
                obj = MultiLineString(flat)
            self.objs.append(obj)
            self.obj2name[id(obj)] = name
        self.STRtree = strtree.STRtree(self.objs) if self.objs else None
        print(f'Loaded {len(ways)} named roads and trails: '
              f"{', '.join(sorted(ways))}.")

    def nearestTrail(self, lat: float, lon: float) -> Optional[str]:
        """
        Return name of nearest trails to (*lat*, *lon*) or *None*.

        :param lat: latitude
        :type lat: float
        :param lon: latitude
        :type lon: float
        :returns: name of nearest trails or *None*
        """
        if self.STRtree is None:
            return None
        point = Point(lon, lat)
        nearest = self.STRtree.nearest(point)
        if not isinstance(nearest, BaseGeometry): # pull request #1
            assert nearest < len(self.objs)
            nearest = self.objs[nearest]
        return self.obj2name[id(nearest)] \
                   if nearest.distance(point) < 2 * BUFFER_DISTANCE else None
