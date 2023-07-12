#!/usr/bin/env python3
import asyncio, datetime, gzip, json, math, os, re, sys, time, webbrowser
import xml.etree.ElementTree as ElementTree

import aiohttp  # on Ubuntu install with: sudo apt install --yes python3-aiohttp
from shapely.geometry import shape, Point, LineString, MultiLineString, Polygon, MultiPolygon   # on Ubuntu install with: sudo apt install --yes python3-shapely
from shapely.geometry.base import BaseGeometry
from shapely import strtree
import folium   # on Ubuntu install with: pip3 install folium

from dataclasses import dataclass
from typing import Union, Dict, List, Set, Optional

ACCURACY        = 25      # in meters; skip less accurate observations
BUFFER_DISTANCE = 0.0002  # buffer distance for polygon around trails
TRACK_COLOR     = 'red'   # gps tracks are shown in red

SHOW_BUFFER     = False   # show buffer polygon; enable for debugging
BUFFER_COLOR    = 'green' # buffer polygon around tracks is shown in green


#
# In API v2 we specify the fields that we need returned.
#

FIELDS_TAXA = '(id:!t,name:!t,rank:!t,preferred_common_name:!t,'\
               'default_photo:(square_url:!t),iconic_taxon_name:!t)'
FIELDS_TAXA_WITH_STATUS = FIELDS_TAXA[:-1] + ',' \
                          'listed_taxa:(taxon_id:!t,place:(id:!t),'\
                                       'establishment_means:!t),'\
                          'conservation_statuses:(taxon_id:!t,place:(id:!t),'\
                                                 'status:!t))'
FIELDS_TAXA_WITH_ANCESTORS = FIELDS_TAXA_WITH_STATUS[:-1] + ',' \
                             f'ancestors:{FIELDS_TAXA})'

FIELDS_OBSERVATION = '(id:!t,user:(login:!t,name:!t),location:!t,obscured:!t,'\
                      'public_positional_accuracy:!t,observed_on:!t,'\
                     f'quality_grade:!t,taxon:{FIELDS_TAXA_WITH_STATUS})'


############################################################
# Cache for downloaded iNaturalist and OpenStreetMap data. #
############################################################

OBSERVATION_EXPIRATION =       8 * 3600 # in seconds, 8 hours
TRAILS_EXPIRATION      = 28 * 24 * 3600 # in seconds, 4 weeks
PLACES_EXPIRATION      =  7 * 24 * 3600 # in seconds, 1 week
TAXA_EXPIRATION        = 14 * 24 * 3600 # in seconds, 2 weeks

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

if not os.path.exists(output_directory): os.makedirs(output_directory)

def readJson(file_name):
    with gzip.open(file_name, 'rt', encoding='utf-8') as file:
        return json.load(file)

def writeJson(file_name, data):
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

# used by writeJson() to convert type datetime.datetime to string
def defaultHook(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f'Unsupported type {obj} while writing json.')


######################################################################
# This class issues iNaturalist API calls in parallel using asyncio. #
######################################################################

class iNaturalistAPI:

    CALL_LIMIT     =    60     # max calls / minute
    PER_PAGE       =   200     # request 200 items in a single call
    DOWNLOAD_LIMIT = 10000     # at most 10,000 observations can be obtained
    API_V1         = 'https://api.inaturalist.org/v1/' # for places/nearby
    API_V2         = 'https://api.inaturalist.org/v2/'
    MAX_PAGE       = DOWNLOAD_LIMIT // PER_PAGE
    HEADERS        = { 'Content-Type' : 'application/json',
                       'User-Agent'   : 'github.com/joergmlpts/iNat-trails' }

    def __init__(self):
        self.callTimes = []
        self.initCommand()

    def initCommand(self):
        self.url = self.API_V2
        self.results = []

    def getResults(self):
        if isinstance(self.results, list):
            self.results.sort(key=lambda r:r['id'])
        return self.results

    async def get_all_observations_async(self, params):
        await self.api_call('observations', **params)

    def get_all_observations(self, **params):
        self.initCommand()
        params['per_page'] = self.PER_PAGE
        params['page'] = 1
        asyncio.run(self.get_all_observations_async(params))
        return self.getResults()

    async def get_taxa_by_id_async(self, ids, params):
        MAX_TAXA = 30
        splitIds = []
        while len(ids) > MAX_TAXA:
            splitIds.append(ids[:MAX_TAXA])
            ids = ids[MAX_TAXA:]
        splitIds.append(ids)
        tasks = [self.api_call('taxa/' + ','.join(idList), **params)
                 for idList in splitIds]
        await asyncio.gather(*tasks)

    def get_taxa_by_id(self, ids, **params):
        self.initCommand()
        asyncio.run(self.get_taxa_by_id_async(ids, params))
        return self.getResults()

    async def get_places_nearby_async(self, params):
        await self.api_call('places/nearby', **params)

    def get_places_nearby(self, **params):
        self.initCommand()
        self.url = self.API_V1
        params['per_page'] = self.PER_PAGE
        params['page'] = 1
        asyncio.run(self.get_places_nearby_async(params))
        return self.getResults()

    async def get_places_by_id_async(self, id: Union[int, str, Set[int]],
                                     params: Dict[str, int]):
        if isinstance(id, set):
            id = ','.join([str(i) for i in id])
        await self.api_call(f'places/{id}')

    def get_places_by_id(self, id: Union[int, Set[int]]):
        self.initCommand()
        self.url = self.API_V1
        params = { 'per_page': self.PER_PAGE, 'page': 1 }
        asyncio.run(self.get_places_by_id_async(id, params))
        return self.getResults()

    async def get_overpass_async(self, query):
        await self.api_call('', data=query)

    # We use this class to download OpenStreetMap data as well.
    def get_overpass(self, query):
        self.initCommand()
        self.url = 'http://overpass-api.de/api/interpreter'
        iNatCallTimes = self.callTimes
        self.callTimes = []
        asyncio.run(self.get_overpass_async(query))
        self.callTimes = iNatCallTimes
        return self.getResults()

    # Limit us to 60 API calls per minute.
    async def throttleCalls(self):
        while len(self.callTimes) >= self.CALL_LIMIT:
            waitTime = self.callTimes[0] - (time.time() - 60)
            if waitTime > 0:
                await asyncio.sleep(waitTime)
                continue
            self.callTimes = self.callTimes[1:]
        self.callTimes.append(time.time())

    async def api_call(self, cmd, **params):
        await self.throttleCalls()
        async with aiohttp.ClientSession() as session:
            if self.url == self.API_V2:
                assert 'fields' in params
                async with session.get(self.url + cmd, headers=self.HEADERS,
                                       params=params) as response:
                    data = await response.json()
            else:
                async with session.get(self.url + cmd, headers=self.HEADERS,
                                       params=params) as response:
                    if 'application/json' in response.headers['content-type']:
                        data = await response.json()
                    else:
                        # Overpass occasionally sends non-json error messages
                        self.results = await response.text()
                        print(self.results)
                        return

        if 'errors' in data and 'status' in data:
            print(f"API Error (cmd '{cmd}', params '{params}') status "
                  f"{data['status']}: {data['errors']}.",
                  file=sys.stderr)
            return

        if 'results' in data:
            if isinstance(data['results'], list):
                self.results += data['results']
            else:
                assert self.results == []
                self.results = data['results']
        else:
            self.results = data

        if 'page' in params and (data['page'] == self.MAX_PAGE or
                            (data['page'] == 1 and 'id_below' not in params)):
            downloaded = data['per_page'] * params['page']
            if data['total_results'] > downloaded:
                params['id_below'] = data['results'][-1]['id']
                max_page =  min(self.MAX_PAGE,
                                math.ceil((data['total_results'] -
                                           downloaded) /
                                          data['per_page']))
                requests = []
                for page in range(1, max_page+1):
                    params['page'] = page
                    requests.append(self.api_call(cmd, **params))
                await asyncio.gather(*requests)

api = iNaturalistAPI()


##########################################################################
# Reads tracks from gpx files, returns MultiLineString and bounding box. #
##########################################################################

def readGpx(file_names):
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
    min_x = min_y = 180
    max_x = max_y = -180
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

# Scale a bounding box to a given precision. Call with precision=100 to scale
# to lat/lon precision of two decimals. Returns scaled bounding box.
def scale_bbox(bbox, precision):
    ((min_x, min_y), (max_x, max_y)) = bbox
    min_x = math.floor(min_x * precision) / precision
    min_y = math.floor(min_y * precision) / precision
    max_x = math.ceil(max_x * precision) / precision
    max_y = math.ceil(max_y * precision) / precision
    return ((min_x, min_y), (max_x, max_y))


##########################################################################
# Loads named trails and roads for given bounding box and buffer polygon #
# from OpenStreetMap. Provides member function nearestTrail(lat, lon).   #
##########################################################################

class Trails:

    def __init__(self, bbox, bufferPolygon):
        ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 100)
        file_name = os.path.join(cache_directory,
                                 f'trails_{min_lon:.2f}_{min_lat:.2f}_'
                                 f'{max_lon:.2f}_{max_lat:.2f}.json.gz')
        if os.path.exists(file_name):
            osm_data = readJson(file_name)
        else:
            osm_data = api.get_overpass(f"""
            [out:json];
            way["highway"] ({min_lat},{min_lon},{max_lat},{max_lon});
            (._;>;);
            out;
            """)
            if 'elements' in osm_data:
                writeJson(file_name, osm_data)

        nodes = {} # id -> (lon, lat)
        ways  = {} # name -> [LineString or MultiLineString, ...]
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

    # Return name of nearest trails to (lat, lon) or None.
    def nearestTrail(self, lat, lon):
        if self.STRtree is None:
            return None
        point = Point(lon, lat)
        nearest = self.STRtree.nearest(point)
        if not isinstance(nearest, BaseGeometry): # pull request #1
            assert nearest < len(self.objs)
            nearest = self.objs[nearest]
        return self.obj2name[id(nearest)] \
                   if nearest.distance(point) < 2 * BUFFER_DISTANCE else None


############################
# iNaturalist data loading #
############################

# quality grades of iNaturalist observations
quality_grades    = [ 'casual', 'needs_id', 'research' ]

# color coding for iNaturalist iconic taxa
iconic_taxa2color = { 'Actinopterygii' : 'blue',
                      'Amphibia'       : 'blue',
                      'Animalia'       : 'blue',
                      'Arachnida'      : 'red',
                      'Aves'           : 'blue',
                      'Chromista'      : 'darkred',
                      'Fungi'          : 'purple',
                      'Insecta'        : 'red',
                      'Mammalia'       : 'blue',
                      'Mollusca'       : 'red',
                      'Plantae'        : 'green',
                      'Protozoa'       : 'purple',
                      'Reptilia'       : 'blue' }

@dataclass
class Place:
    id                : int
    name              : str
    bbox_area         : float
    geometry_geojson  : dict
    ancestor_place_ids: List[int]

@dataclass
class Status:
    means: str             # establishment means like "native" or "introduced"
    place: Union[int,str]  # place name or numeric place id

# iNaturalist observation
class Observation:

    def __init__(self, id, obscured, accuracy, lat, lon, date,
                 login, user, quality, trail):
        self.id = id
        self.obscured = obscured
        self.accuracy = accuracy
        self.lat = lat
        self.lon = lon
        if isinstance(date, datetime.datetime):
            date = date.isoformat()
        self.date = date
        self.login = login
        self.user = user
        self.quality = quality
        self.trail = trail

#
# iNaturalist taxon
#
class Taxon:

    def __init__(self, id, name, common_name, square_url, iconic):
        self.id = id
        self.name = name
        self.common_name = common_name
        self.square_url = square_url
        self.children = {}
        self.observations = []
        self.status = None
        self.iconic_taxon_name = iconic

    def add_observation(self, observation):
        self.observations.append(observation)

    def html_name(self, with_common_name=False):
        name_list = self.name.split()
        if len(name_list) <= 2:
            name = '<i>' + self.name + '</i>'
        else:
            name = '<i>' + ' '.join(name_list[:-2]) + '</i> ' + \
                   name_list[-2] + ' <i>' + name_list[-1] + '</i>'
        if with_common_name and self.common_name:
            name += ' (' + self.common_name + ')'
        return name.replace(' ', '&nbsp;').replace('-', '&#8209;')


# for json taxon returns id, name, common name, square_url, and iconic taxon
def taxonInfo(taxon):
    id = taxon['id']
    name = taxon['name']
    rank = taxon['rank']
    if rank in ['variety', 'subspecies']:
        name_list = name.split()
        kind = 'ssp.' if rank == 'subspecies' else 'var.'
        name = ' '.join(name_list[0:2] + [kind, name_list[-1]])
    cname = ''
    if 'preferred_common_name' in taxon:
        cname = re.sub('(^|-|\s)(\S)', lambda m: m.group(1) +
                                                 m.group(2).upper(),
                       taxon['preferred_common_name'])
        cname = ' '.join([n.lower() if n == 'And' else n
                          for n in cname.split()])
    square_url = None
    if 'default_photo' in taxon and \
       taxon['default_photo'] is not None and \
       'square_url' in taxon['default_photo']:
        square_url = taxon['default_photo']['square_url']
    iconic_taxon_name = None
    if 'iconic_taxon_name' in taxon:
        iconic_taxon_name = taxon['iconic_taxon_name']
    #print(json.dumps(taxon, indent=4, default=defaultHook))
    if 'listed_taxa' in taxon:
        print('listed_taxa...', name, taxon['listed_taxa'])
    return (id, name, cname, square_url, iconic_taxon_name)

# returns list of instances of class Taxon. The list is ordered by scientific
# name. Each taxon contains a list of observations.
def getObservations(bbox, bufferPolygon, iconic_taxa, quality_grade, month,
                    trails):
    month_range = '1,2,3,4,5,6,7,8,9,10,11,12'
    if month:
        month = datetime.date.today().month
        month_range = f'{month},{1 if month == 12 else month+1},' \
                      f'{12 if month == 1 else month-1}'
    ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 100)
    file_name = os.path.join(cache_directory,
                             f'observations_{iconic_taxa}_{min_lon:.2f}_'
                             f'{min_lat:.2f}_{max_lon:.2f}_{max_lat:.2f}_'
                             f'{month_range}_{quality_grade}.json.gz')

    if os.path.exists(file_name):
        observations = readJson(file_name)
    else:
        observations = api.get_all_observations(
            fields               = FIELDS_OBSERVATION,
            captive              = 'false',
            identified           = 'true',
            geoprivacy           = 'open',
            acc_below_or_unknown = ACCURACY,
            hrank                = 'species',
            iconic_taxa          = list(iconic_taxa2color) \
                                   if iconic_taxa == 'all' else iconic_taxa,
            nelat                = max_lat,
            nelng                = max_lon,
            swlng                = min_lon,
            swlat                = min_lat,
            quality_grade        = quality_grades if quality_grade == 'all' \
                                   else quality_grade,
            month                = month_range)
        writeJson(file_name, observations)

    print(f"Loaded {len(observations):,} iNaturalist observations of quality-"
          f"grade '{'all' if quality_grade is None else quality_grade}' within"
          " bounding box.")

    id2taxon = {}
    obsOutside = obsAccuracy = 0
    for result in observations:
        user = result['user']
        login = user['login']
        user = user['name'] if user['name'] else login
        lat, lon = [float(num) for num in result['location'].split(',')]
        if result['public_positional_accuracy'] is not None and \
           result['public_positional_accuracy'] > ACCURACY:
            obsAccuracy += 1
            continue
        if not bufferPolygon.contains(Point(lon, lat)):
            obsOutside += 1
            continue
        #print(json.dumps(result, indent=4, default=defaultHook))
        observation = Observation(result['id'], result['obscured'],
                                  result['public_positional_accuracy'],
                                  lat, lon, result['observed_on'],
                                  login, user, result['quality_grade'],
                                  trails.nearestTrail(lat, lon))
        id = result['taxon']['id']
        if id not in id2taxon:
            _, name, cname, square_url, iconic = taxonInfo(result['taxon'])
            id2taxon[id] = Taxon(id, name, cname, square_url, iconic)
        id2taxon[id].add_observation(observation)

    if obsOutside > 0 or obsAccuracy > 0:
        print(f'Excluded {obsOutside:,} observations not along route '
              f'and {obsAccuracy:,} with low accuracy.')
    taxa = list(id2taxon.values())
    taxa.sort(key=lambda t:t.name)
    return ancestorInfo(bbox, taxa, bufferPolygon)

def getPlacesNearby(bbox, bufferPolygon):
    ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 1000)
    places_file = os.path.join(cache_directory,
                               f'places_{min_lon:.3f}_{min_lat:.3f}_'
                               f'{max_lon:.3f}_{max_lat:.3f}.json.gz')
    if os.path.exists(places_file):
        places = readJson(places_file)
    else:
        places = api.get_places_nearby(nelat = max_lat, nelng = max_lon,
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

def getPlacesById(id: Union[int, Set[int]]):
    places_file = os.path.join(cache_directory,
                               f'places_{sorted(id)}.json.gz'
                               if isinstance(id, set)
                               else f'places_{id}.json.gz')
    if os.path.exists(places_file):
        places = readJson(places_file)
    else:
        places = api.get_places_by_id(id)
        writeJson(places_file, places)

    places = [ Place(place['id'],
                     place['display_name'] if 'display_name' in place
                                           else place['name'],
                     place['bbox_area'], place['geometry_geojson'],
                     [] if place['ancestor_place_ids'] is None
                        else place['ancestor_place_ids']) for place in places ]
    places.sort(key=lambda e:e.bbox_area)
    return places

def listedTaxa(taxon, places):
    for place in places:
        for status in taxon['conservation_statuses']:
            if status['place'] is not None:
                if status['place']['id'] in [place.id] + place.ancestor_place_ids:
                    return Status(status['status'], status['place']['id'])
        for lst in taxon['listed_taxa']:
            assert lst['taxon_id'] == taxon['id']
            if lst['place']['id'] in [place.id] + place.ancestor_place_ids:
                return Status(lst['establishment_means'], lst['place']['id'])

# augment observations with ancestor info: iconic taxon, and family
def ancestorInfo(bbox, observations, bufferPolygon):
    taxa_file = os.path.join(cache_directory, 'taxa.json.gz')
    taxon_by_id = {}
    taxon_by_id_initial_size = 0

    # load cached taxa
    if os.path.exists(taxa_file):
        taxon_by_id = readJson(taxa_file)
        taxon_by_id_initial_size = len(taxon_by_id)
        print(f'Loaded {taxon_by_id_initial_size} taxa.')

    # find taxa not already in cache
    lookup_ids = []
    for taxon in observations:
        id = str(taxon.id)
        if not id in taxon_by_id:
            lookup_ids.append(id)

    # load uncached taxa from iNaturalist
    if len(lookup_ids):
        print(f'{len(lookup_ids)} uncached taxa to download...')
        results = api.get_taxa_by_id(lookup_ids,
                                     fields=FIELDS_TAXA_WITH_ANCESTORS)

        # insert taxa into cache
        for taxon in results:
            taxon_by_id[str(taxon['id'])] = taxon

    # save cache
    if len(taxon_by_id) != taxon_by_id_initial_size:
        writeJson(taxa_file, taxon_by_id)

    places = getPlacesNearby(bbox, bufferPolygon)

    iconic2families = {}
    iconic2taxa = {}
    for taxon in observations:
        if taxon.iconic_taxon_name not in iconic2families:
            iconic2families[taxon.iconic_taxon_name] = {}
            for ancestor in taxon_by_id[str(taxon.id)]['ancestors']:
                if ancestor['name'] == taxon.iconic_taxon_name:
                    i_id, i_name, i_cname, i_url, _ = taxonInfo(ancestor)
            iconic2taxa[taxon.iconic_taxon_name] = Taxon(i_id, i_name,
                                                         i_cname, i_url,
                                                         None)
        families = iconic2families[taxon.iconic_taxon_name]
        for ancestor in taxon_by_id[str(taxon.id)]['ancestors']:
            if ancestor['rank'] == 'family':
                f_id, f_name, f_cname, f_url, f_iconic = taxonInfo(ancestor)
        if not f_name in families:
            families[f_name] = Taxon(f_id, f_name, f_cname,
                                     f_url, f_iconic)
        families[f_name].children[taxon.name] = taxon
        taxon.status = listedTaxa(taxon_by_id[str(taxon.id)], places)

    iconic_taxa = []
    for iconic in sorted(iconic2families):
        iconic_taxon = iconic2taxa[iconic]
        iconic_taxon.children = sorted(iconic2families[iconic].values(),
                                       key=lambda t:t.name)
        iconic_taxa.append(iconic_taxon)

    # For all taxa, replace place id with place name.
    place_id2name = { pl.id : pl.name for pl in places }
    lookup_places = set([t.status.place for i in iconic_taxa
                         for f in i.children for t in f.children.values()
                         if t.status is not None
                         if t.status.place not in place_id2name])
    if len(lookup_places) > 0:
        for pl in getPlacesById(lookup_places):
            place_id2name[pl.id] = pl.name
    for iconic_taxon in iconic_taxa:
        for family in iconic_taxon.children:
            for taxon in family.children.values():
                if taxon.status is not None:
                    taxon.status.place = place_id2name[taxon.status.place]

    place_guess = None
    for place in places:
        if shape(place.geometry_geojson).intersection(bufferPolygon).area > \
           0.5 * bufferPolygon.area:
            place_guess = place.name
            break

    return iconic_taxa, 'Unknown Place' if place_guess is None else place_guess


######################
# Write Output Files #
######################

# Display observations on an interactive map.
def getMap(bbox, iconic_taxa, lineStrings, bufferPolygon):
    ((min_lon, min_lat), (max_lon, max_lat)) = bbox
    m = folium.Map(tiles=None)
    folium.FitBounds([(max_lat, max_lon), (min_lat, min_lon)]).add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreet Map',
                     max_zoom=19).add_to(m)
    folium.raster_layers.TileLayer(tiles='http://{s}.google.com/vt/lyrs=s,h&x='
                                   '{x}&y={y}&z={z}', max_zoom=20,
                                   attr='Imagery &copy;2021 CNES / Airbus Land'
                                   'sat / Copernicus Maxar Technologies, '
                                   'Planet.com, U.S. Geological Survey, USDA'
                                   ' Farm Service Agency, Map data &copy;2021'
                                   ' Google', name='Google Satellite (hybrid)',
                                   subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
                                   overlay=False, control=True).add_to(m)
    folium.TileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                     name='Open TopoMap', max_zoom=17,
                     attr='Map data: &copy; <a href="https://www.openstreet'
                     'map.org/copyright">OpenStreetMap</a> contributors, <a'
                     ' href="http://viewfinderpanoramas.org">SRTM</a> | Map'
                     ' style: &copy; <a href="https://opentopomap.org">Open'
                     'TopoMap</a> (<a href="https://creativecommons.org/lic'
                     'enses/by-sa/3.0/">CC-BY-SA</a>)').add_to(m)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/'
                     'services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
                     attr='Tiles &copy; Esri &mdash; National Geographic,'
                     ' Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA,'
                     ' METI, NRCAN, GEBCO, NOAA, iPC', name='National Geo'
                     'graphics Terrain', max_zoom=16).add_to(m)
    folium.raster_layers.TileLayer(tiles='http://{s}.google.com/vt/lyrs=m&x={x}'
                                   '&y={y}&z={z}', attr='Map data &copy; '
                                   'Google', name='Google Maps', max_zoom=20,
                                   subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
                                   overlay=False, control=True).add_to(m)
    folium.TileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGS'
                     'ImageryOnly/MapServer/tile/{z}/{y}/{x}', max_zoom=16,
	             attr='Tiles courtesy of the <a href="https://usgs.gov/">'
                     'U.S. Geological Survey</a>',
                     name='USGS Satellite').add_to(m)
    folium.TileLayer('https://macrostrat.org/api/v2/maps/burwell/emphasized/'
                     '{z}/{x}/{y}/tile.png', max_zoom=20, name='Macrostrat '
                     'Geologic Map',
                     attr='Tiles <a href="https://macrostrat.org/map/#/z=14.0'
                     f'/x={(min_lon+max_lon)/2:.4f}/y={(min_lat+max_lat)/2:.4f}'
                     '/bedrock/lines/" target="_blank">macrostrat.org</a> '
                     '&copy; UW Madison').add_to(m)

    if SHOW_BUFFER:
        folium.PolyLine(locations=[(coord[1],coord[0]) for coord in
                                   bufferPolygon.exterior.coords],
                        color=BUFFER_COLOR, tooltip='buffer polygon').add_to(m)
        for interior in bufferPolygon.interiors:
            folium.PolyLine(locations=[(coord[1],coord[0]) for coord in
                                       interior.coords], color=BUFFER_COLOR,
                            tooltip='buffer polygon').add_to(m)

    # show the route (.gpx tracks)
    for lineString in lineStrings.geoms:
        folium.PolyLine(locations=[(coord[1],coord[0]) # folium uses (lat, lon)
                                   for coord in lineString.coords],
                        tooltip='gps track',
                        color=TRACK_COLOR).add_to(m)

    # set markers for the observations
    for iconic_taxon in iconic_taxa:
        if iconic_taxon.name not in iconic_taxa2color:
            print(f"No color for iconic taxon '{iconic}'; using black.")
            iconic_taxa2color[iconic_taxon.name] = 'black'
        color = iconic_taxa2color[iconic_taxon.name]

        for family in iconic_taxon.children:
            fg = folium.FeatureGroup(name=family.html_name(True),
                                     show=family.name not in ['Cyperaceae',
                                                              'Poaceae',
                                                              'Juncaceae'])
            for taxon in family.children.values():
                tooltip = taxon.html_name(with_common_name=True)
                for obs in taxon.observations:
                    popup = '<table><tr><td><a href="https://inaturalist.'+\
                            f'org/observations/{obs.id}" target="_blank">'+\
                            f'<img src="{taxon.square_url}">' +\
                            f'</a></td><td>{tooltip}<br/>{obs.user}'
                    if obs.date is not None:
                        popup += ',&nbsp;' + obs.date[:10]
                    if obs.accuracy is not None:
                        popup += f'<br/>accuracy&nbsp;{obs.accuracy:,}' \
                                  '&nbsp;meters'
                    if taxon.status is not None and \
                       taxon.status.means != 'native':
                        popup += '<br/><font color="red">' + \
                                 taxon.status.means + '</font>'
                    popup += '</td></tr></table>'
                    folium.Marker([obs.lat, obs.lon], popup=popup,
                                  icon=folium.Icon(color=color),
                                  tooltip=tooltip).add_to(fg)
            fg.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m

# write html table of observations and the trails they are on
def writeTable(iconic_taxa, iconic_taxa_arg, quality_grade, month,
               place_name, logins):
    place_filename = place_name.replace(' ', '_').replace('/', '_')
    observations_file_name = os.path.join(output_directory,
                                          f'{place_filename}_{iconic_taxa_arg}_'
                                          f'{quality_grade}_observations.html')

    with open(observations_file_name, 'w', encoding='utf-8') as f:
        print('<html>', file=f)
        print(f'<h1>{quality_grade[0].upper()}{quality_grade[1:].lower()}'
              f'-grade Observations from {place_name} on iNaturalist</h1>',
              file=f)
        suffix = ' for observations around this month' if month else ''
        today = datetime.date.today()
        print(f'<p>Generated on {today.month}/{today.day}/{today.year} with '
              '<a href="https://github.com/joergmlpts/iNat-trails" '
              f'target="_blank">iNat-trails</a>{suffix}.</p>', file=f)
        for iconic in iconic_taxa:
            families = iconic.children
            cname = f' - {iconic.common_name}' if iconic.common_name \
                                               is not None else ''
            print(f'<h2><i>{iconic.name}</i>{cname}</h2>', file=f)
            print('<table>', file=f)
            print('<tr><td><u><b>Scientific Name</b></u></td><td><u><b>Common '
                  'Name</b></u></td><td><u><b>Observations</b></u></td></tr>',
                  file=f)
            for family in iconic.children:
                print('<tr><td></td><td></td><td></td><td></td></tr>', file=f)
                print(f'<tr><td><b>{family.html_name(False)}</b></td>'
                      f'<td><b>{family.common_name}</b></td><td></td></tr>',
                      file=f)
                for taxon in sorted(family.children.values(),
                                    key=lambda t:t.name):
                    name = taxon.html_name(with_common_name=False)
                    cname = taxon.common_name
                    if taxon.status is not None and \
                       taxon.status.means == 'introduced':
                        name = '<font color="red">' + name + '</font>'
                        cname = '<font color="red">' + cname + '</font>'

                    trail2obs = {}
                    no_trail_obs = []
                    for obs in taxon.observations:
                        if obs.trail is None:
                            no_trail_obs.append(obs)
                        else:
                            if obs.trail in trail2obs:
                                trail2obs[obs.trail].append(obs)
                            else:
                                trail2obs[obs.trail] = [obs]

                    def webLinks(observations):
                        linkList = ['<a href="https://www.inaturalist.org/'
                                    f'observations/{obs.id}" '
                                    'target="_blank">'
                                    f'{obs.login if logins else obs.id}</a>'
                                    for obs in observations]
                        return ', '.join(linkList)

                    observations = [f'{trail}: {webLinks(trail2obs[trail])}'
                                    for trail in sorted(trail2obs)]
                    if no_trail_obs:
                        observations.append(webLinks(no_trail_obs))
                    print(f'<tr><td>{name}</td><td>{cname}</td>'
                          f'<td>{"; ".join(observations)}</td></tr>',
                          file=f)
            print('</table><p>', file=f)
        print('</html>', file=f)
    print(f"Table written to '{observations_file_name}'.")
    webbrowser.open(observations_file_name)

# write waypoints for off-line mapping app OsmAnd on iPhone and Android
def writeWaypoints(iconic_taxa, iconic_taxa_arg, quality_grade, place_name):
    place_filename = place_name.replace(' ', '_').replace('/', '_')
    file_name = os.path.join(output_directory, f'{place_filename}_'
                             f'{iconic_taxa_arg}_{quality_grade}_waypoints.gpx')
    with open(file_name, 'w', encoding='utf-8') as f:
        print("<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
              file=f)
        print('<gpx version="1.1" creator="OsmAnd 3.9.10"',
              'xmlns="http://www.topografix.com/GPX/1/1"',
              'xmlns:osmand="https://osmand.net"',
              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
              'xsi:schemaLocation="http://www.topografix.com/GPX/1/1',
              'http://www.topografix.com/GPX/1/1/gpx.xsd">', file=f)
        for iconic in iconic_taxa:
            if iconic.name not in iconic_taxa2color:
                print(f"No color for iconic taxon '{iconic}'; using black.")
                iconic_taxa2color[iconic.name] = 'black'
            color = iconic_taxa2color[iconic.name]
            for family in iconic.children:
                for taxon in family.children.values():
                    name = taxon.name
                    if taxon.common_name:
                        name += ' (' + taxon.common_name + ')'
                    for obs in taxon.observations:
                        icon = 'special_star'
                        background = 'circle'
                        print(file=f)
                        print(f'  <wpt lat="{obs.lat}" lon="{obs.lon}">',
                              file=f)
                        print(f'    <name>{name}</name>', file=f)
                        print( '    <extensions>', file=f)
                        print(f'      <osmand:icon>{icon}</osmand:icon>',
                              file=f)
                        print(f'      <osmand:background>{background}'
                              '</osmand:background>', file=f)
                        print(f'      <osmand:color>{color}</osmand:color>',
                              file=f)
                        print( '    </extensions>', file=f)
                        print( '  </wpt>', file=f)
        print(file=f)
        print('</gpx>', file=f)
    print(f"Waypoints written to '{file_name}'.")


#####################################
# Command-line argument processing. #
#####################################

if __name__ == '__main__':
    import argparse

    def fileName(fn):
        if os.path.isfile(fn):
            try:
                with open(fn, 'r') as f:
                    return fn
            except:
                pass
        raise argparse.ArgumentTypeError(f"File '{fn}' cannot be read.")

    def qualityGrade(quality):
        arg = quality.lower()
        if arg == 'all' or arg in quality_grades:
            return arg
        raise argparse.ArgumentTypeError(f"Quality-grade '{quality}' "
                                         "not supported.")

    def iconicTaxa(iconic):
        if len(iconic) >= 2:
            arg = iconic[0].upper() + iconic[1:].lower()
            if iconic.lower() == 'all':
                return 'all'
            elif arg in iconic_taxa2color:
                return arg
        raise argparse.ArgumentTypeError(f"Iconic taxon '{iconic}' "
                                         "not supported.")

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
    file_name = os.path.join(output_directory,
                             f'{place_filename}_{args.iconic_taxon}_'
                             f'{args.quality_grade}_'
                             f'mapped_observations.html')
    getMap(bbox, iconic_taxa, lineStrings, bufferPolygon).save(file_name)
    print(f"Map written to '{file_name}'.")
    webbrowser.open(file_name)
