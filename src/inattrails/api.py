import asyncio, math, sys, time

import aiohttp  # on Ubuntu install with: sudo apt install --yes python3-aiohttp

from typing import Dict, List, Set, Tuple, Union


##########################################################
# In API v2 we specify the fields that we need returned. #
##########################################################

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


######################################################################
# This class issues iNaturalist API calls in parallel using asyncio. #
######################################################################

class iNaturalistAPI:
    """
    This class issues iNaturalist API calls and overpass API calls
    in parallel using asyncio.
    """

    CALL_LIMIT     =    60     # max calls / minute
    "Limit of API calls/minute."

    PER_PAGE       =   200     # request 200 items in a single call
    "Maximal 200 observations/page."

    DOWNLOAD_LIMIT = 10000     # at most 10,000 observations can be obtained
    "At most 10,000 observations can be obtained."

    API_V1         = 'https://api.inaturalist.org/v1/' # for places/nearby
    API_V2         = 'https://api.inaturalist.org/v2/'

    MAX_PAGE       = DOWNLOAD_LIMIT // PER_PAGE
    HEADERS        = { 'Content-Type' : 'application/json',
                       'User-Agent'   : 'github.com/joergmlpts/iNat-trails' }

    def __init__(self):
        self.callTimes = []
        self.initCommand()

    def initCommand(self) -> None:
        """
        Initalize for one API command. An single API command may request
        multiple pages.
        """
        self.url = self.API_V2
        self.results: List[Dict[str, object]] = []

    def getResults(self):
        """
        Return result obtained by API command.

        :returns: a string from the overpass API or a list of json results from iNaturalist.
        """
        if isinstance(self.results, list):
            self.results.sort(key=lambda r:r['id'])
        return self.results

    async def get_all_observations_async(self, params) -> None:
        """
        Asynchronous method to get multiple pages of iNaturalist observations.

        :returns: a string from the overpass API or a json list from iNaturalist.
        """
        await self.api_call('observations', **params)

    def get_all_observations(self, **params):
        """
        Method to get multiple pages of iNaturalist observations. All pages
        will be combined in one list and can be obtained with `getResults()`.

        :returns: list of json results from iNaturalist.
        """
        self.initCommand()
        params['per_page'] = self.PER_PAGE
        params['page'] = 1
        asyncio.run(self.get_all_observations_async(params))
        return self.getResults()

    async def get_taxa_by_id_async(self, ids: List[str], params) -> None:
        """
        Asynchronous method to get taxa by id. `ids` is a list of numeric taxon
        ids. `params` are parameters to pass to the iNaturalist API.

        iNaturalist returns up to 30 taxa in one call. This function breaks
        down `ids` into chunks of not more than 30 taxa and sends those to
        the iNaturalist API.

        :param ids: List of numeric taxon ids.
        :type ids: List[str]
        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        """
        MAX_TAXA = 30
        splitIds = []
        while len(ids) > MAX_TAXA:
            splitIds.append(ids[:MAX_TAXA])
            ids = ids[MAX_TAXA:]
        splitIds.append(ids)
        tasks = [self.api_call('taxa/' + ','.join(idList), **params)
                 for idList in splitIds]
        await asyncio.gather(*tasks)

    def get_taxa_by_id(self, ids: List[str], **params) -> \
        List[Dict[str, object]]:
        """
        Method to get iNaturalist taxa by id. `ids` is a list of numeric taxon
        ids. `params` are parameters to pass to the iNaturalist API. This
        function returns a list of json dicts for the taxa.

        :param ids: List of numeric taxon ids.
        :type ids: List[str]
        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        :returns: a list of iNaturalist json results
        """
        self.initCommand()
        asyncio.run(self.get_taxa_by_id_async(ids, params))
        return self.getResults()

    async def get_places_nearby_async(self, params) -> None:
        """
        Get places nearby.

        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        """
        await self.api_call('places/nearby', **params)

    def get_places_nearby(self, **params):
        """
        Get places nearby.

        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        :returns: a list of iNaturalist json results
        """
        self.initCommand()
        self.url = self.API_V1
        params['per_page'] = self.PER_PAGE
        params['page'] = 1
        asyncio.run(self.get_places_nearby_async(params))
        return self.getResults()

    async def get_places_by_id_async(self, id: Union[int, str, Set[int]],
                                     params: Dict[str, int]) -> None:
        """
        Get places by numeric id.

        :param id: numeric place id or set of numeric place ids
        :type id: Union[int, Set[int]]
        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        """
        if isinstance(id, set):
            id = ','.join([str(i) for i in id])
        await self.api_call(f'places/{id}', **params)

    def get_places_by_id(self, id: Union[int, Set[int]]):
        """
        Get places by numeric id.

        :param id: numeric place id or set of numeric place ids
        :type id: Union[int, Set[int]]
        :returns: a list of iNaturalist json results
        """
        self.initCommand()
        self.url = self.API_V1
        params = { 'per_page': self.PER_PAGE, 'page': 1 }
        asyncio.run(self.get_places_by_id_async(id, params))
        return self.getResults()

    async def get_overpass_async(self, query: str) -> None:
        await self.api_call('', data=query)

    # We use this class to download OpenStreetMap data as well.
    def get_overpass(self, query: str) -> str:
        """
        Query the overpass API.

        :param query: the overpass query, a string
        :type query: str
        :returns: str
        """
        self.initCommand()
        self.url = 'http://overpass-api.de/api/interpreter'
        iNatCallTimes = self.callTimes
        self.callTimes = []
        asyncio.run(self.get_overpass_async(query))
        self.callTimes = iNatCallTimes
        return self.getResults()

    async def throttleCalls(self) -> None:
        "Limit us to 60 API calls per minute."
        while len(self.callTimes) >= self.CALL_LIMIT:
            waitTime = self.callTimes[0] - (time.time() - 60)
            if waitTime > 0:
                await asyncio.sleep(waitTime)
                continue
            self.callTimes = self.callTimes[1:]
        self.callTimes.append(time.time())

    async def api_call(self, cmd, **params) -> None:
        """
        Make an API call to iNaturalist and overpass API's.

        :param cmd: The command to send to the API, e.g. 'obervations'
        :type cmd: str
        :param params: dict of parameters to send to iNaturalist API.
        :type params: Dict[str, object]
        """
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
                        print(response.text())
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


########################################
# An instance of class iNaturalistAPI. #
########################################

inat_api = iNaturalistAPI()
