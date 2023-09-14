from dataclasses import dataclass
from typing import List, Optional, Union

from .inat_place import Place

@dataclass
class Status:
    """
    Status consists of an establishment means and a place.
    """
    means: str
    "establishment means, e.g. 'native' or 'introduced'"
    place: Union[int,str]
    "place name or numeric place id"


def listedTaxa(taxon, places: List[Place]) -> Optional[Status]:
    """
    Get the status of a taxon - like *introduced* or *native* - for a list
    of places.

    :param taxon: iNaturalist taxon in json
    :type taxon: list of dict
    :param places: list of places
    :type places: list of *Place*
    :returns: list of *Status*
    """
    for place in places:
        for status in taxon['conservation_statuses']:
            if status['place'] is not None:
                if status['place']['id'] in [place.id] + \
                   place.ancestor_place_ids:
                    return Status(status['status'], status['place']['id'])
        for lst in taxon['listed_taxa']:
            assert lst['taxon_id'] == taxon['id']
            if lst['place']['id'] in [place.id] + place.ancestor_place_ids:
                return Status(lst['establishment_means'], lst['place']['id'])
    return None
