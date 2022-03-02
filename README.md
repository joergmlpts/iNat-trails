# iNaturalist observations along hiking trails

This tool reads the route of a hike and generates a table of iNaturalist observations along the trails. It also shows the observations and the route of the hike on a map. Moreover, it saves waypoints of the iNaturalist observations for offline navigation with a GPS device or smartphone.


## Usage

This is a command-line tool. It is called with a .gpx file that describes the route. This .gpx file can be either after a hike downloaded from a gps device or 
smartphone or created before a hike by a mapping tool or website. The gpx files in the [examples directory](https://github.com/joergmlpts/iNat-trails/tree/main/examples)
have been created with the free website [caltopo.com](https://caltopo.com).

Here is an example. This is the command for Linux and macOS

```
./inat_trails.py examples/Rancho_Canada_del_Oro.gpx
```

On Windows the command is:

```
python.exe .\inat_trails.py examples\Rancho_Canada_del_Oro.gpx
```

The output looks like this:
```
Reading 'examples/Rancho_Canada_del_Oro.gpx'...
Loaded 13 named roads and trails: Bald Peaks Trail, Canada Del Oro Cut-Off Trail, Canada Del Oro Trail, Casa Loma Road,
    Catamount Trail, Chisnantuk Peak Trail, Little Llagas Creek Trail, Llagas Creek Loop Trail, Longwall Canyon Trail,
    Mayfair Ranch Trail, Needlegrass Trail, Serpentine Loop Trail.
Loaded 2,708 iNaturalist observations of quality-grade 'research' within bounding box.
Excluded 1,694 observations not along route and 13 with low accuracy.
Loaded 829 taxa.
Waypoints written to './Rancho_Canada_del_Oro_Open_Space_Preserve_all_research_waypoints.gpx'.
Table written to './Rancho_Canada_del_Oro_Open_Space_Preserve_all_research_observations.html'.
Map written to './Rancho_Canada_del_Oro_Open_Space_Preserve_all_research_mapped_observations.html'.
```

This tools finds named trails along this route. It loads iNaturalist observations from the area of the hike and discards those that are not along the trails. It
writes three output files, a waypoints file, a table of observations, and an interactive map. Both the table and the map will pop up in a browser.

The waypoint file can be loaded into the free offline navigation app [OsmAnd](https://osmand.net/). This will allow this offline navigation app to display the
iNaturalist observations along the hiking trails.

The table of observations lists all the organisms that have been observed along the trails along with the trail names they are on. The table for the mammals 
seen in this park looks like this:

<table>
<tr><td><u><b>Scientific Name</b></u></td><td><u><b>Common Name</b></u></td><td><u><b>Observations</b></u></td></tr>
<tr><td></td><td></td><td></td><td></td></tr>
<tr><td><b><i>Canidae</i></b></td><td><b>Canids</b></td><td></td></tr>
<tr><td><i>Canis&nbsp;latrans</i></td><td>Coyote</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/38860133"
target="_blank">38860133</a>, <a href="https://www.inaturalist.org/observations/38860889" target="_blank">38860889</a></td></tr>
<tr><td><i>Urocyon&nbsp;cinereoargenteus</i></td><td>Gray Fox</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/39391329" 
 target="_blank">39391329</a></td></tr><tr><td></td><td></td><td></td><td></td></tr>
<tr><td><b><i>Cervidae</i></b></td><td><b>Deer</b></td><td></td></tr>
<tr><td><i>Odocoileus&nbsp;hemionus</i>&nbsp;ssp.&nbsp;<i>columbianus</i></td><td>Columbian Black-Tailed Deer</td><td>Casa Loma Road: <a
 href="https://www.inaturalist.org/observations/80058758"
 target="_blank">80058758</a>; Little Llagas Creek Trail: <a href="https://www.inaturalist.org/observations/68891936" target="_blank">68891936</a>; Mayfair Ranch
 Trail: <a href="https://www.inaturalist.org/observations/19113219" target="_blank">19113219</a>, <a href="https://www.inaturalist.org/observations/21319391"
target="_blank">21319391</a>, <a href="https://www.inaturalist.org/observations/44158629" target="_blank">44158629</a></td></tr>
<tr><td></td><td></td><td></td><td></td></tr><tr><td><b><i>Cricetidae</i></b></td><td><b>Hamsters, Voles, Lemmings, and Allies</b></td><td></td></tr>
<tr><td><i>Neotoma&nbsp;fuscipes</i></td><td>Dusky-Footed Woodrat</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/52963985"
target="_blank">52963985</a></td></tr><tr><td></td><td></td><td></td><td></td></tr>
<tr><td><b><i>Felidae</i></b></td><td><b>Felids</b></td><td></td></tr>
<tr><td><i>Lynx&nbsp;rufus</i></td><td>Bobcat</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/15630740" 
 target="_blank">15630740</a>, <a href="https://www.inaturalist.org/observations/15689757" target="_blank">15689757</a>, <a
 href="https://www.inaturalist.org/observations/38861135" target="_blank">38861135</a></td></tr><tr><td></td><td></td><td></td><td></td></tr>
<tr><td><b><i>Geomyidae</i></b></td><td><b>Pocket Gophers</b></td><td></td></tr>
<tr><td><i>Thomomys&nbsp;bottae</i></td><td>Botta's Pocket Gopher</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/38869384" 
  target="_blank">38869384</a>, <a href="https://www.inaturalist.org/observations/38875049" target="_blank">38875049</a></td></tr>
<tr><td></td><td></td><td></td><td></td></tr>
<tr><td><b><i>Leporidae</i></b></td><td><b>Hares and Rabbits</b></td><td></td></tr>
<tr><td><i>Sylvilagus&nbsp;bachmani</i></td><td>Brush Rabbit</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/73152597"
 target="_blank">73152597</a>,
 <a href="https://www.inaturalist.org/observations/74462983" target="_blank">74462983</a></td></tr>
<tr><td></td><td></td><td></td><td></td></tr><tr><td><b><i>Sciuridae</i></b></td><td><b>Squirrels</b></td><td></td></tr>
<tr><td><i>Neotamias&nbsp;merriami</i></td><td>Merriam's Chipmunk</td><td>Longwall Canyon Trail: <a href="https://www.inaturalist.org/observations/42605223" 
 target="_blank">42605223</a>; Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/132863" target="_blank">132863</a>, <a 
 href="https://www.inaturalist.org/observations/46538314" target="_blank">46538314</a></td></tr>
<tr><td><i>Otospermophilus&nbsp;beecheyi</i></td><td>California Ground Squirrel</td><td>Casa Loma Road: <a
href="https://www.inaturalist.org/observations/47200360" target="_blank">47200360</a>;
 Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/2328803" target="_blank">2328803</a>,
<a href="https://www.inaturalist.org/observations/15629491" target="_blank"> 15629491</a>, <a href="https://www.inaturalist.org/observations/53667091" 
 target="_blank">53667091</a></td></tr>
<tr><td><i>Sciurus&nbsp;griseus</i></td><td>Western Gray Squirrel</td><td>Mayfair Ranch Trail: <a href="https://www.inaturalist.org/observations/73152599"
 target="_blank">73152599</a></td></tr>
</table>

The numbers are the observation ids; a click opens them on the iNaturalist website. Option `--login_names` can be given to replace these observation ids with login names.

The interactive map shows the route and the iNaturalist observations along the hike. Like the iNaturalist website, the markers on the interactive map have
different colors for different iconic taxa, e.g. markers for plants are green. Hoovering the mouse over a marker shows the identification, a click on a marker
shows a thumbnail picture, the identification, the observer, the date and a special status like invasive or introduced. A further click on that thumbnail opens
the observation in the iNaturalist website in another browser window.

### Command-line options

This script is a command-line tool. It is called with options and file names as arguments. These options are supported:

```
usage: inat_trails.py [-h] [--quality_grade QUALITY_GRADE] [--iconic_taxon ICONIC_TAXON] [--login_names] gpx_file [gpx_file ...]

positional arguments:
  gpx_file              Load GPS track from .gpx file.

optional arguments:
  -h, --help            show this help message and exit
  --quality_grade QUALITY_GRADE
                        Observation quality-grade, values: all, casual, needs_id, research; default research.
  --iconic_taxon ICONIC_TAXON
                        Iconic taxon, values: all, Actinopterygii, Amphibia, Animalia, Arachnida, Aves, Chromista,
                        Fungi, Insecta, Mammalia, Mollusca, Plantae, Protozoa, Reptilia; default all.
  --login_names         Show login name instead of numeric observation id in table of observations.
  --month               Show only observations from this month and the previous and next months.
```

Option `--quality_grade` spcifies the desired quality-grade of the observations to show. By default, only research-grade observations are shown. Alternatively,
all quality grades, or only casual and needs_id can be requested.

Option `--iconic_taxon` allows to restrict the observations to an iconic taxon. This can be used to display observations of e.g. only birds or only plants.

Option `--login_names` replaces the observation id number with the login name in the table of observations.

Option `--month` restricts observations to the current month and the previous
and next months. This is useful for seasonal observations like wildflowers
or migratory birds.

## Dependencies

A handful of dependencies need to be installed in order for `inat_trails.py` to run. Besides Python 3.7 or later, a few packages are needed. On Ubuntu or other
Debian-based Linux distributions the dependencies can be installed with:
```
sudo apt install --yes python3-pip python3-aiohttp python3-shapely
pip3 install folium
```

On other operating systems, Python 3.7 or later and pip need to be installed first and then the dependencies can be installed with:
```
pip install aiohttp folium shapely
```

When appropriate `pip3` should be called instead of `pip` to avoid accidentally installing packages for Python 2.
