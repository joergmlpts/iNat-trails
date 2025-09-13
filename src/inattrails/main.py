import argparse, os, webbrowser

from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon   # on Ubuntu install with: sudo apt install --yes python3-shapely

from .cache import output_directory
from .read import readGpx
from .trails import Trails, BUFFER_DISTANCE
from .inat_taxon import Taxon
from .inat_observation import getObservations, quality_grades, \
                              iconic_taxa2color
from .gen_map import getMap
from .write_table import writeTable
from .write_waypoints import writeWaypoints


#####################################
# Command-line argument processing. #
#####################################

def fileName(fn: str) -> str:
    """
    Is argument a valid filename?

    :param fn: file name
    :type fn: *str*
    :raises argparse.ArgumentTypeError: if the argument is not a valid file name
    :returns: *fn*
    """
    if os.path.isfile(fn):
        try:
            with open(fn, 'r') as f:
                return fn
        except:
            pass
    raise argparse.ArgumentTypeError(f"File '{fn}' cannot be read.")

def qualityGrade(quality: str) -> str:
    """
    Is *quality* a valid quality-grade?

    :param quality: 'casual', 'needs_id', 'research', or 'all'
    :type quality: *str*
    :raises argparse.ArgumentTypeError: if the argument is not *'all'* or a valid quality grade
    :returns: *quality* in lower case
    """
    arg = quality.lower()
    if arg == 'all' or arg in quality_grades:
        return arg
    raise argparse.ArgumentTypeError(f"Quality-grade '{quality}' "
                                     "not supported.")

def iconicTaxa(iconic: str) -> str:
    """
    Is *iconic* a valid iconic taxon?

    :param iconic:  'all' or 'Actinopterygii', ...
    :type iconic: *str*
    :raises argparse.ArgumentTypeError: if the argument is not *'all'* or a valid iconic taxon
    :returns: *'all'* or *iconic* with first letter capitalized
    """
    if len(iconic) >= 2:
        arg = iconic[0].upper() + iconic[1:].lower()
        if iconic.lower() == 'all':
            return 'all'
        elif arg in iconic_taxa2color:
            return arg
    raise argparse.ArgumentTypeError(f"Iconic taxon '{iconic}' not supported.")

def main():
    """
    Main program, parses command line, reads gps tracks, computes buffer
    polygon, downloads road and trails, downloads observations, writes
    waypoints, table, and map.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('gpx_file', type=fileName, nargs='+',
                        help='Load GPS track from .gpx file.')
    parser.add_argument('--quality_grade', type=qualityGrade,
                        help='Observation quality-grade, values: all, '
                        f"{', '.join(quality_grades)}; default research.",
                        default='research')
    parser.add_argument('--iconic_taxon', type=iconicTaxa,
                        help='Iconic taxon, values: all, '
                        f"{', '.join(iconic_taxa2color)}; default all.",
                        default='all')
    parser.add_argument('--login_names', action="store_true",
                        help='Show login name instead of numeric observation '
                        'id in table of observations.')
    parser.add_argument('--month', action="store_true",
                        help='Show only observations from this month and the '
                        'previous and next months.')
    args = parser.parse_args()

    # read tracks and bounding box from .gpx files
    lineStrings, bbox = readGpx(args.gpx_file)

    # compute buffer polygons around tracks
    bufferPolygon = lineStrings.buffer(BUFFER_DISTANCE)

    # get trails and roads in buffer polygon
    trails = Trails(bbox, bufferPolygon)

    # get observations in the buffer polygon and their taxa as
    # well as a guess for the place name
    iconic_taxa, place_name = getObservations(bbox, bufferPolygon,
                                              args.iconic_taxon,
                                              args.quality_grade,
                                              args.month, trails)

    # write waypoints for offline mapping app OsmAnd on iPhone and Android
    writeWaypoints(iconic_taxa, args.iconic_taxon, args.quality_grade,
                   place_name)

    # write html table of observations and the trails they are on
    writeTable(iconic_taxa, args.iconic_taxon, args.quality_grade,
               args.month, place_name, args.login_names)

    # write html with observations on an interactive map
    place_filename = place_name.replace(' ', '_').replace('/', '_')
    file_name = f'{place_filename}_{args.iconic_taxon}_{args.quality_grade}'
    map = getMap(bbox, iconic_taxa, lineStrings, bufferPolygon)
    while True:
        map_file_name = os.path.join(output_directory,
                                     f'{file_name}_mapped_observations.html')
        try:
            map.save(map_file_name)
            print(f"Map written to '{map_file_name}'.")
            webbrowser.open(map_file_name)
            return
        except Exception as e:
            if 'File name too long' in str(e):
                file_name = file_name[:len(file_name) // 2]
                print(f'Warning: Cannot write file; shortening file name.')
                continue
            print(f"Error: failed to write mapped observations: {e}.")
            if os.path.exists(map_file_name):
                os.unlink(map_file_name)
            return


if __name__ == '__main__':
    main()
