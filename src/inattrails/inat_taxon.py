import re
from typing import Dict, List, Optional, Tuple

from .inat_status import Status

#
# iNaturalist taxon
#
class Taxon:
    """
    This class stores an iNaturalist taxon.

    :param id: numeric taxon id
    :type id: *int*
    :param name: scientific name
    :type name: *str*
    :param common_name: common name or *None*
    :type common_name: *str* or *None*
    :param square_url: URL to a load thumbnail image for this taxon
    :type square_url: *str* or *None*
    :param iconic: this taxon's iconic taxon
    :type iconic: *str*
    """

    def __init__(self, id: int, name: str, common_name: str,
                 square_url: str, iconic: str):
        self.id = id
        self.name = name
        self.common_name = common_name
        self.square_url = square_url
        self.children: List['Taxon'] = []
        self.observations: List['Observation'] = []
        self.status: Optional[Status] = None
        self.iconic_taxon_name = iconic

    def add_observation(self, observation: 'Observation'):
        """
        Append an observation to this taxon's list of observations.

        :param observation: an instance of class *Observation*
        :type observation: *Observation*
        """
        self.observations.append(observation)

    def html_name(self, with_common_name=False) -> str:
        """
        Return the html-formatted name for this taxon, the scientific name
        italicized as a whole or in parts. Optionally, append the common name
        in parentheses.

        :param with_common_name: If *True* append the common name in parentheses.
        :type with_common_name: *bool*
        """
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
def taxonInfo(taxon: Dict[str, object]) -> Tuple[int, str, str, str, str]:
    """
    Extract components for class *Taxon* from json downloaded from iNaturalist.

    :param taxon: json data for taxon obtained from iNaturalist API
    :type taxon: dict
    :returns: 5-tuple consisting of taxon id, scientific name, common name or *None*, url for thumbnail image, name of iconic taxon
    """

    assert isinstance(taxon['id'], int)
    id: int = taxon['id']
    name = taxon['name']
    assert isinstance(name, str)
    rank = taxon['rank']
    if rank in ['variety', 'subspecies', 'form']:
        name_list = name.split()
        kind = 'ssp.' if rank == 'subspecies' else \
                      'f.' if rank == 'form' else 'var.'
        name = ' '.join(name_list[0:2] + [kind, name_list[-1]])
    cname = ''
    if 'preferred_common_name' in taxon:
        preferred_common_name = taxon['preferred_common_name']
        assert isinstance(preferred_common_name, str)
        cname = re.sub('(^|-|\s)(\S)', lambda m: m.group(1) +
                                                 m.group(2).upper(),
                       preferred_common_name)
        cname = ' '.join([n.lower() if n == 'And' else n
                          for n in cname.split()])
    square_url = ''
    if 'default_photo' in taxon and \
       isinstance(taxon['default_photo'], dict) and \
       'square_url' in taxon['default_photo']:
        square_url = taxon['default_photo']['square_url']
    iconic_taxon_name = ''
    if 'iconic_taxon_name' in taxon:
        assert isinstance(taxon['iconic_taxon_name'], str)
        iconic_taxon_name = taxon['iconic_taxon_name']
    return (id, name, cname, square_url, iconic_taxon_name)
