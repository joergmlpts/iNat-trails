import datetime, gzip, json, math, os, sys, time
from typing import Tuple

"""
Cache for downloaded iNaturalist and OpenStreetMap data.
"""

OBSERVATION_EXPIRATION = 8 * 3600
"8 hours in seconds"

TRAILS_EXPIRATION      = 28 * 24 * 3600
"4 weeks in seconds"

PLACES_EXPIRATION      = 7 * 24 * 3600
"1 week in seconds"

TAXA_EXPIRATION        = 14 * 24 * 3600
"2 weeks in seconds"

if sys.platform == 'win32':
    cache_directory  = os.path.expanduser('~/AppData/Local/inat_trails')
    output_directory = os.path.expanduser('~/Documents')
else:
    cache_directory  = os.path.expanduser('~/.cache/inat_trails')
    output_directory = '.'

if os.path.exists(cache_directory):
    # purge all expired cache entries
    now = time.time()
    for file in os.listdir(cache_directory):
        fullPath = os.path.join(cache_directory, file)
        mtime = os.path.getmtime(fullPath)
        delete = False
        if file.startswith('observations_'):
            delete = mtime + OBSERVATION_EXPIRATION < now
        elif file.startswith('places_'):
            delete = mtime + PLACES_EXPIRATION < now
        elif file == 'taxa.json.gz':
            delete = mtime + TAXA_EXPIRATION < now
        elif file.startswith('trails_'):
            delete = mtime + TRAILS_EXPIRATION < now
        if delete:
            try:
                os.remove(fullPath)
            except Exception as e:
                print(f"Could not delete expired cache '{fullPath}': {e}.",
                      file=sys.stderr)
else:
    os.makedirs(cache_directory)

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

def readJson(file_name: str):
    """
    Read json data from file.

    :param file_name: Name of file to read json data from.
    :type file_name: str
    :returns: json (list or dict)
    """
    with gzip.open(file_name, 'rt', encoding='utf-8') as file:
        return json.load(file)

def writeJson(file_name: str, data):
    """
    Write json data to file.

    :param file_name: Name of file to write json data to.
    :type file_name: str
    :param data: json data
    :type data: json (list or dict)
    """
    def cleanup(exception):
        try:
            os.remove(file_name) # remove only partially written file
        except:
            pass
        raise exception
    try:
        with gzip.open(file_name, 'wt', encoding='utf-8') as file:
            json.dump(data, file, default=defaultHook)
    except KeyboardInterrupt as e:
        cleanup(e)
    except Exception as e:
        cleanup(e)

def defaultHook(obj):
    "Called by *writeJson()* to convert type *datetime.datetime* to string."
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f'Unsupported type {obj} while writing json.')


def scale_bbox(bbox: Tuple[Tuple[float,float],
                           Tuple[float,float]], precision: int):
    """
    Scale a bounding box to a given precision. Call with precision=100 to scale
    to lat/lon precision of two decimals. Returns scaled bounding box.

    :param bbox: bounding box
    :type bbox: pair of two pairs, the min longitude and latitude and the max longitude and latitude
    :param precision: the precision, number of decimals desired
    :type precision: int, a power of 10
    """
    ((min_x, min_y), (max_x, max_y)) = bbox
    min_x = math.floor(min_x * precision) / precision
    min_y = math.floor(min_y * precision) / precision
    max_x = math.ceil(max_x * precision) / precision
    max_y = math.ceil(max_y * precision) / precision
    return ((min_x, min_y), (max_x, max_y))

