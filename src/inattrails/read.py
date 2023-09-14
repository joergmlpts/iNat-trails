import xml.etree.ElementTree as ElementTree

from shapely.geometry import LineString, MultiLineString # on Ubuntu install with: sudo apt install --yes python3-shapely

from typing import Union, Dict, List, Set, Tuple, Optional


"""
Reads tracks from gpx files, returns MultiLineString and bounding box.
"""

def readGpx(file_names: List[str]) -> Tuple[MultiLineString,
                                            Tuple[Tuple[float,float],
                                                  Tuple[float,float]]]:
    """
    Reads .gpx files of tracks and returns a MultiLineString and
    the bounding box.

    :param file_names: list of .gpx file names
    :type file_names: List[str]
    :returns: a tuple consisting of a MultiLineString instance and the bounding box
    """
    trksegs = []
    for fn in file_names:
        print(f"Reading '{fn}'...")
        root = ElementTree.parse(fn).getroot()
        assert root.tag.endswith('gpx')
        namespace = root.tag[:-3]
        for trkseg in root.iter(f'{namespace}trkseg'):
            seg = [(float(trkpt.attrib['lon']), float(trkpt.attrib['lat']))
                   for trkpt in trkseg.findall(f'{namespace}trkpt')]
            if len(seg) > 1:
                trksegs.append(seg)
    min_x = min_y = 180.0
    max_x = max_y = -180.0
    lineStrings = []
    for track in trksegs:
        x = [coord[0] for coord in track]
        min_x = min(min_x, min(x))
        max_x = max(max_x, max(x))
        y = [coord[1] for coord in track]
        min_y = min(min_y, min(y))
        max_y = max(max_y, max(y))
        lineStrings.append(LineString(track))
    ε = 1e-7 # bbox must not degenerate to line or point
    return MultiLineString(lineStrings), ((min_x-ε, min_y-ε),
                                          (max_x+ε, max_y+ε))
