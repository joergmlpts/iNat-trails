import datetime, os, webbrowser
from typing import Dict, List, Tuple

from .cache import output_directory
from .inat_taxon import Taxon
from .inat_observation import Observation


def writeTable(iconic_taxa: List[Taxon], iconic_taxa_arg: str,
               quality_grade: str, month: bool,  place_name: str,
               logins: bool) -> None:
    """
    Write html table of observations and the trails they are found on.

    :param iconic_taxa: list of iconic taxa; the children of iconic taxa are taxa of families; the children of those families are taxa that contain observations
    :type iconic_taxa: list of instances of *Taxon*
    :param iconic_taxa_arg: the iconic taxon from the command-line, used in file name
    :type iconic_taxa_arg: *str*
    :param quality_grade: *'all'* or *'casual'*, *'needs_id'*, *'research'*; used in file name
    :type quality_grade: str
    :param month: parameter *month* from command-line; used in file name
    :type month: *bool*
    :param place_name: place name used in file name
    :type place_name: *str*
    :param logins: if *True* use observer's login name in table; use numeric observation id if *False*
    :type logins: *bool*
    """
    place_filename = place_name.replace(' ', '_').replace('/', '_')
    file_name = f'{place_filename}_{iconic_taxa_arg}_{quality_grade}'
    while True:
        observations_file_name = os.path.join(output_directory,
                                              f'{file_name}_observations.html')
        try:
            with open(observations_file_name, 'wt', encoding='utf-8') as f:
                print('<html>', file=f)
                print('<h1>'
                      f'{quality_grade[0].upper()}{quality_grade[1:].lower()}'
                      f'-grade Observations from {place_name} on '
                      'iNaturalist</h1>', file=f)
                suffix = ' for observations around this month' if month else ''
                today = datetime.date.today()
                print(f'<p>Generated on {today.month}/{today.day}/{today.year} '
                      'with <a href="https://inat-trails.readthedocs.io/'
                      'en/latest/usage.html" '
                      f'target="_blank">iNat-trails</a>{suffix}.</p>', file=f)
                for iconic in iconic_taxa:
                    cname = f' - {iconic.common_name}' if iconic.common_name \
                                                       is not None else ''
                    print(f'<h2><i>{iconic.name}</i>{cname}</h2>', file=f)
                    print('<table>', file=f)
                    print('<tr><td><u><b>Scientific Name</b></u></td><td><u><b>'
                          'Common Name</b></u></td><td><u><b>Observations</b>'
                          '</u></td></tr>', file=f)
                    for family in iconic.children:
                        print('<tr><td></td><td></td><td></td><td></td></tr>',
                              file=f)
                        print(f'<tr><td><b>{family.html_name(False)}</b></td>'
                              f'<td><b>{family.common_name}</b></td><td></td>'
                              '</tr>', file=f)
                        for taxon in family.children:
                            name = taxon.html_name(with_common_name=False)
                            cname = taxon.common_name
                            if taxon.status is not None and \
                               taxon.status.means == 'introduced':
                                name = '<font color="red">' + name + '</font>'
                                cname = '<font color="red">' + cname + '</font>'

                            trail2obs: Dict[str,List[Observation]] = {}
                            no_trail_obs: List[Observation] = []
                            for obs in taxon.observations:
                                if obs.trail is None:
                                    no_trail_obs.append(obs)
                                else:
                                    if obs.trail in trail2obs:
                                        trail2obs[obs.trail].append(obs)
                                    else:
                                        trail2obs[obs.trail] = [obs]

                            def webLinks(observations):
                                linkList = ['<a href="https://www.inaturalist.'
                                            f'org/observations/{obs.id}" '
                                            'target="_blank">'
                                            f'{obs.login if logins else obs.id}'
                                            '</a>' for obs in observations]
                                return ', '.join(linkList)

                            observations = [f'{trail}: '
                                            f'{webLinks(trail2obs[trail])}'
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
            return
        except Exception as e:
            if 'File name too long' in str(e):
                file_name = file_name[:len(file_name) // 2]
                print(f'Warning: Cannot write file; shortening file name.')
                continue
            print(f"Error: failed to write observation table: {e}.")
            if os.path.exists(observations_file_name):
                os.unlink(observations_file_name)
            return
