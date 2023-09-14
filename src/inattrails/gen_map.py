from typing import List, Tuple

from .inat_taxon import Taxon
from .inat_observation import iconic_taxa2color

from shapely.geometry import MultiLineString, Polygon  # on Ubuntu install with: sudo apt install --yes python3-shapely
import folium   # on Ubuntu install with: pip3 install folium


SHOW_BUFFER     = False   # show buffer polygon; enable for debugging
BUFFER_COLOR    = 'green' # buffer polygon around tracks is shown in green
TRACK_COLOR     = 'red'   # gps tracks are shown in red


######################
# Write Output Files #
######################

def getMap(bbox: Tuple[Tuple[float,float],Tuple[float,float]],
           iconic_taxa: List[Taxon], lineStrings: MultiLineString,
           bufferPolygon: Polygon) -> folium.Map:
    """
    Based on *folium* write an interactive map to an html file and open it
    in a browser.

    :param bbox: bounding box
    :type bbox: pair of two pairs, the min longitude and latitude and the max longitude and latitude
    :param iconic_taxa: list of iconic taxa; the children of iconic taxa are taxa of families; the children of those families are taxa that contain observations
    :type iconic_taxa: list of instances of *Taxon*
    :param lineStrings: the track of a hike represented as line strings
    :type lineStrings: shapely.geometry.MultiLineString
    :param bufferPolygon: buffer polygon around the tracks of the hike
    :type bufferPolygon: shapely.geometry.Polygon
    """
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
            print(f"No color for iconic taxon '{iconic_taxon}'; using black.")
            iconic_taxa2color[iconic_taxon.name] = 'black'
        color = iconic_taxa2color[iconic_taxon.name]

        for family in iconic_taxon.children:
            fg = folium.FeatureGroup(name=family.html_name(True),
                                     show=family.name not in ['Cyperaceae',
                                                              'Poaceae',
                                                              'Juncaceae'])
            for taxon in family.children:
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
