import datetime, os, webbrowser
from typing import Dict, List, Tuple

from .cache import output_directory
from .inat_taxon import Taxon
from .inat_observation import iconic_taxa2color

def writeWaypoints(iconic_taxa: List[Taxon], iconic_taxa_arg: str,
                   quality_grade: str, place_name: str) -> None:
    """
    Write waypoints for off-line mapping app OsmAnd on iPhone and Android.

    :param iconic_taxa: list of iconic taxa; the children of iconic taxa are taxa of families; the children of those families are taxa that contain observations
    :type iconic_taxa: list of instances of *Taxon*
    :param iconic_taxa_arg: the iconic taxon from the command-line, used in file name
    :type iconic_taxa_arg: *str*
    :param quality_grade: *'all'* or *'casual'*, *'needs_id'*, *'research'*; used in file name
    :type quality_grade: str
    :param place_name: place name used in file name
    :type place_name: *str*
    """
    place_filename = place_name.replace(' ', '_').replace('/', '_')
    file_name = f'{place_filename}_{iconic_taxa_arg}_{quality_grade}'
    while True:
        gpx_file_name = os.path.join(output_directory,
                                     f'{file_name}_waypoints.gpx')
        try:
            with open(gpx_file_name, 'wt', encoding='utf-8') as f:
                print("<?xml version='1.0' encoding='UTF-8' standalone='yes' "
                      "?>", file=f)
                print('<gpx version="1.1" creator="OsmAnd 3.9.10"',
                      'xmlns="http://www.topografix.com/GPX/1/1"',
                      'xmlns:osmand="https://osmand.net"',
                      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
                      'xsi:schemaLocation="http://www.topografix.com/GPX/1/1',
                      'http://www.topografix.com/GPX/1/1/gpx.xsd">', file=f)
                for iconic in iconic_taxa:
                    if iconic.name not in iconic_taxa2color:
                        print(f"No color for iconic taxon '{iconic}'; "
                              "using black.")
                        iconic_taxa2color[iconic.name] = 'black'
                    color = iconic_taxa2color[iconic.name]
                    for family in iconic.children:
                        for taxon in family.children:
                            name = taxon.name
                            if taxon.common_name:
                                name += ' (' + taxon.common_name + ')'
                            for obs in taxon.observations:
                                icon = 'special_star'
                                background = 'circle'
                                print(file=f)
                                print(f'  <wpt lat="{obs.lat}" '
                                      'lon="{obs.lon}">', file=f)
                                print(f'    <name>{name}</name>', file=f)
                                print( '    <extensions>', file=f)
                                print(f'      <osmand:icon>{icon}'
                                      '</osmand:icon>', file=f)
                                print(f'      <osmand:background>{background}'
                                      '</osmand:background>', file=f)
                                print(f'      <osmand:color>{color}'
                                      '</osmand:color>', file=f)
                                print( '    </extensions>', file=f)
                                print( '  </wpt>', file=f)
                print(file=f)
                print('</gpx>', file=f)
            print(f"Waypoints written to '{file_name}'.")
            return
        except Exception as e:
            if 'File name too long' in str(e):
                file_name = file_name[:len(file_name) // 2]
                print(f'Warning: Cannot write file; shortening file name.')
                continue
            print(f"Error: failed to write waypoints: {e}.")
            if os.path.exists(gpx_file_name):
                os.unlink(gpx_file_name)
            return
