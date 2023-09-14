import datetime, os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from shapely.geometry import shape, Point, Polygon  # on Ubuntu install with: sudo apt install --yes python3-shapely

from .cache import cache_directory, readJson, writeJson, scale_bbox
from .api import inat_api, FIELDS_OBSERVATION, FIELDS_TAXA_WITH_ANCESTORS
from .inat_taxon import Taxon, taxonInfo
from .inat_place import getPlacesNearby, getPlacesById
from .inat_status import listedTaxa
from .trails import Trails


ACCURACY = 25
"observation accuracy in meters; skip less accurate observations"

quality_grades    = [ 'casual', 'needs_id', 'research' ]
"Quality grades of iNaturalist observations."

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
"Color coding for iNaturalist iconic taxa."


# iNaturalist observation
class Observation:
    """
    This class represents a single iNaturalist observation.

    :param id: numeric observation id
    :type id: *int*
    :param obscured: is the locatin obscured?
    :type obscured: *bool*
    :param accuracy: location accuracy in meters or  *None*
    :type accuracy: *float* or *None*
    :param lat: latitude
    :type lat: *float*
    :param lon: longitude
    :type lon: *float*
    :param date: date is ISO format
    :type date: *str*
    :param login: login name of user who made this observation
    :type login: *str*
    :param user: user name if there is one, login name otherwise
    :type user: *str*
    :param quality: observation's quality-grade: *casual*, *needs_id*, *research*
    :type quality: *str*
    :param trail: trail name or - for off-trail observations - *None*
    :type trail: *str* or *None*
    """
    def __init__(self, id: int, obscured: bool, accuracy: Optional[float],
                 lat: float, lon: float, date: datetime.datetime, login: str,
                 user: str, quality: str, trail: Optional[str]):
        self.id = id
        self.obscured = obscured
        self.accuracy = accuracy
        self.lat = lat
        self.lon = lon
        if isinstance(date, datetime.datetime):
            self.date = date.isoformat()
        elif isinstance(date, str):
            self.date = date
        self.login = login
        self.user = user
        self.quality = quality
        self.trail = trail


def getObservations(bbox: Tuple[Tuple[float,float],Tuple[float,float]],
                    bufferPolygon: Polygon, iconic_taxa: str,
                    quality_grade: str, month: bool,
                    trails: Trails) -> Tuple[List[Taxon], str]:
    """
    Returns trees of taxa. Observations are stored at the taxa. Each list of
    taxa is alphabetically ordered by scientific name. Taxa contain lists of
    observations.

    :param bbox: bounding box
    :type bbox: pair of two pairs, the min longitude and latitude and the max longitude and latitude
    :param bufferPolygon: buffer polygon around the tracks of the hike
    :type bufferPolygon: shapely.geometry.Polygon
    :param quality_grade: *'all'* or *'casual'*, *'needs_id'*, *'research'*
    :type quality_grade: str
    :param month: download observations only of current, previous and next months
    :type month: bool
    :param trails: instance of class *Trails* to lookup trail name
    :type trails: *Trails*
    :returns: tuple consisting of a list of iconic taxa; the children of these iconic taxa are taxa of families; the children of the taxa of families contain the observations and a suggestion for the place name
    """
    month_range = '1,2,3,4,5,6,7,8,9,10,11,12'
    if month:
        no_month = datetime.date.today().month
        month_range = f'{no_month},{1 if no_month == 12 else no_month+1},' \
                      f'{12 if no_month == 1 else no_month-1}'
    ((min_lon, min_lat), (max_lon, max_lat)) = scale_bbox(bbox, 100)
    file_name = os.path.join(cache_directory,
                             f'observations_{iconic_taxa}_{min_lon:.2f}_'
                             f'{min_lat:.2f}_{max_lon:.2f}_{max_lat:.2f}_'
                             f'{month_range}_{quality_grade}.json.gz')

    if os.path.exists(file_name):
        observations = readJson(file_name)
    else:
        observations = inat_api.get_all_observations(
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

    id2taxon: Dict[int,Taxon] = {}
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


def ancestorInfo(bbox: Tuple[Tuple[float,float],Tuple[float,float]],
                 observations: List[Taxon],
                 bufferPolygon: Polygon) -> Tuple[List[Taxon],str]:
    """
    For a list of taxa with observations, return if list of iconic taxa and a
    suggestion for the place name.

    The iconc taxa are roots of trees. Each iconic taxon has children which are
    families. The children of these families are the leaf taxa with
    observations. The lists of iconic taxa, lists of families and lists of leaf
    taxa are all sorted by scientific names in alphabetical order.

    :param bbox: bounding box
    :type bbox: pair of two pairs, the min longitude and latitude and the max longitude and latitude
    :param observations: list of taxa; each taxon has a list of observations
    :param observations: list of instances of *Taxon*
    :param bufferPolygon: buffer polygon around the tracks of the hike
    :type bufferPolygon: shapely.geometry.Polygon
    :returns: tuple consisting of a list of iconic taxa; the children of these iconic taxa are taxa of families; the children of the taxa of families contain the observations and a suggestion for the place name
    """
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
        if id not in taxon_by_id:
            lookup_ids.append(id)

    # load uncached taxa from iNaturalist
    if len(lookup_ids):
        print(f'{len(lookup_ids)} uncached '
              f'tax{"on" if len(lookup_ids) == 1 else "a"} to download...')
        results = inat_api.get_taxa_by_id(lookup_ids,
                                          fields=FIELDS_TAXA_WITH_ANCESTORS)

        # insert taxa into cache
        for itaxon in results:
            taxon_by_id[str(itaxon['id'])] = itaxon

    # save cache
    if len(taxon_by_id) != taxon_by_id_initial_size:
        writeJson(taxa_file, taxon_by_id)

    places = getPlacesNearby(bbox, bufferPolygon)

    # Turn leaf taxa with observations into trees with iconic taxa and families.

    @dataclass
    class Iconic:
        iconic  : Taxon
        families: Dict[str, Taxon]

    name2iconic: Dict[str,Iconic] = {}
    for taxon in observations:
        if taxon.iconic_taxon_name not in name2iconic:
            for ancestor in taxon_by_id[str(taxon.id)]['ancestors']:
                if ancestor['name'] == taxon.iconic_taxon_name:
                    i_id, i_name, i_cname, i_url, _ = taxonInfo(ancestor)
            name2iconic[taxon.iconic_taxon_name] = \
                Iconic(Taxon(i_id, i_name, i_cname, i_url, i_name), {})

        for ancestor in taxon_by_id[str(taxon.id)]['ancestors']:
            if ancestor['rank'] == 'family':
                f_id, f_name, f_cname, f_url, f_iconic = taxonInfo(ancestor)

        if f_name not in name2iconic[taxon.iconic_taxon_name].families:
            name2iconic[taxon.iconic_taxon_name].families[f_name] = \
                Taxon(f_id, f_name, f_cname, f_url, f_iconic)
        name2iconic[taxon.iconic_taxon_name].families[f_name]. \
            children.append(taxon)
        taxon.status = listedTaxa(taxon_by_id[str(taxon.id)], places)

    iconic_taxa: List[Taxon] = []
    for iconic in sorted(name2iconic.values(), key=lambda i:i.iconic.name):
        # sort children of each family
        for f in iconic.families.values():
            f.children = sorted(f.children, key=lambda t:t.name)
        # sort families
        iconic.iconic.children = sorted(iconic.families.values(),
                                        key=lambda t:t.name)
        iconic_taxa.append(iconic.iconic)

    # For all taxa, replace place id with place name.
    place_id2name: Dict[int,str] = { pl.id : pl.name for pl in places }
    lookup_places: Set[int] = set([int(t.status.place) for i in iconic_taxa
                                   for f in i.children for t in f.children
                                   if t.status is not None
                                   if t.status.place not in place_id2name])
    if len(lookup_places) > 0:
        for pl in getPlacesById(lookup_places):
            place_id2name[pl.id] = pl.name
    for iconic_taxon in iconic_taxa:
        for family in iconic_taxon.children:
            for taxon in family.children:
                if taxon.status is not None:
                    taxon.status.place = place_id2name[int(taxon.status.place)]

    # Find a guess for the place name.
    place_guess = None
    for place in places:
        if shape(place.geometry_geojson).intersection(bufferPolygon).area > \
           0.5 * bufferPolygon.area:
            place_guess = place.name
            break

    return iconic_taxa, 'Unknown Place' if place_guess is None else place_guess
