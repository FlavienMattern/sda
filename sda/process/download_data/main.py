from obspy import UTCDateTime
import  obspy.clients.fdsn.mass_downloader as mdl
from obspy.clients.fdsn import Client
import os
from datetime import datetime
from sda.core.logs import add_log

# For more information on the usage of massive downloader :
# https://docs.obspy.org/pr/filter/packages/autogen/obspy.clients.fdsn.mass_downloader.html
    


def get_mseed_storage(network, station, location, channel, starttime, endtime):   
    day = starttime.strftime("%Y-%m-%d")
    folder = os.path.join(dataPathGlobalVariable, "waveforms")
    fileName = os.path.join(
        network, station, f"{network}.{station}.{location}.{channel}",
        f"{day}.mseed"
    )
    fileFullName = os.path.join(folder, fileName)
    
    
    if os.path.exists(fileFullName):
        # Returning True means that neither the data nor the StationXML file
        # will be downloaded.
        return True
    else:
        # If a string is returned the file will be saved in that location.
        return fileFullName



def download_data(
        outputPath,
        dataPath=None,
        
        # Domain definitions
        domainType="rectangular", # ["circular", "rectangular", "global"]
        latitudes=(None,None), # (latmin, latmax) Tuple of Min/Max latitude for Rectangular domain
        longitudes=(None,None), # (lomin, lonmax) Tuple of Min/Max longitude for Rectangular domain
        latitude=None, # Center latitude for Circular domain
        longitude=None, # Center longitude for Circular domain
        minradius=None, # [km] Minimum distance from center of Circular domain
        maxradius=None, # [km] Maximum distance from center of Circular domain

        # Resctrictions
        starttime=None, endtime=None,
        station_starttime=None, station_endtime=None,
        chunklength_in_sec=None,
        network=None, station=None, location=None, channel=None,
        exclude_networks=tuple(), exclude_stations=tuple(),
        limit_stations_to_inventory=None,
        reject_channels_with_gaps=True, minimum_length=0.9,
        sanitize=True, minimum_interstation_distance_in_m=1000,
        channel_priorities=("HH[ZNE12]", "BH[ZNE12]",
                            "MH[ZNE12]", "EH[ZNE12]",
                            "LH[ZNE12]", "HL[ZNE12]",
                            "BL[ZNE12]", "ML[ZNE12]",
                            "EL[ZNE12]", "LL[ZNE12]",
                            "SH[ZNE12]"),
        location_priorities=("", "00", "10", "01", "20", "02", "30",
                            "03", "40", "04", "50", "05", "60",
                            "06", "70", "07", "80", "08", "90",
                            "09"),
        
        # Massive Downloader object
        providers=None, # List of known providers (e.g. ["RESIF", "IRIS"]). None: to consider all known providers
        # It can be a list of client manually defined:
        # my_client = Client("RESIF", user="username", password="pwd")
        # providers = [my_client, "IRIS", ...]
        debug=False, configure_logging=True,
        
        # Download properties
        mseed_storage=None, # "DATA_PATH/waveforms/{network}/{station}/{location}/{channel}/{starttime}_{endtime}.mseed"
        stationxml_storage=None,
        download_chunk_size_in_mb=20, threads_per_client=3,
        print_report=True
        
    ):
    """Download seismic waveforms and StationXML metadata with ObsPy's MassDownloader.
    Most parameters are passed directly to MassDownloader;
    see the [ObsPy usage examples](https://docs.obspy.org/packages/autogen/obspy.clients.fdsn.mass_downloader.html#usage-examples)
    for more details.
    Waveforms and inventories are stored under `<dataPath>/waveforms` and
    `<dataPath>/inventory`, unless custom paths are provided.

    Parameters:
        outputPath (str): Project output directory, created if necessary.
        dataPath (str | None): Dataset directory; `None` uses `<outputPath>/data`.
        domainType (str): Geographic selection: `"rectangular"`, `"circular"` or `"global"`.
        latitudes (tuple[float, float]): Latitude bounds in degrees for a rectangular domain,
            e.g. `(40.0, 45.0)`.
        longitudes (tuple[float, float]): Longitude bounds in degrees for a rectangular domain,
            e.g. `(-120.0, -115.0)`.
        latitude (float | None): Center latitude in degrees for a circular domain.
        longitude (float | None): Center longitude in degrees for a circular domain.
        minradius (float | None): Inner radius of a circular domain, in angular degrees,
            e.g. `0.0`. Required for a circular domain.
        maxradius (float | None): Outer radius of a circular domain, in angular degrees,
            e.g. `1.0`. Required for a circular domain.
        starttime (str | UTCDateTime): UTC start of the waveform request,
            e.g. `"2023-01-01T00:00:00"`. Must be provided for a defined request period.
        endtime (str | UTCDateTime): UTC end of the waveform request,
            e.g. `"2023-01-02T00:00:00"`. Must be provided for a defined request period.
        station_starttime (str | UTCDateTime | None): Start of the StationXML metadata period;
            `None` uses `starttime`. May extend earlier than the waveform request.
        station_endtime (str | UTCDateTime | None): End of the StationXML metadata period;
            `None` uses `endtime`. May extend later than the waveform request.
        chunklength_in_sec (float | None): Duration of each download segment in seconds,
            e.g. `86400` for daily files. `None` requests the whole period as one segment.
        network (str | None): FDSN network selector, e.g. `"IU"` or `"IU,G*"`;
            `None` leaves networks unrestricted.
        station (str | None): FDSN station selector, e.g. `"ANMO"` or `"A*"`;
            `None` leaves stations unrestricted.
        location (str | None): FDSN location selector, e.g. `"00"` or `"00,10"`;
            `None` uses `location_priorities`.
        channel (str | None): FDSN channel selector, e.g. `"BHZ"` or `"BH*"`;
            `None` uses `channel_priorities`.
        exclude_networks (tuple[str, ...] | list[str]): Network patterns to exclude,
            e.g. `["BW", "G*"]`. An empty sequence excludes none.
        exclude_stations (tuple[str, ...] | list[str]): Station patterns to exclude,
            e.g. `["STR", "AL??"]`. An empty sequence excludes none.
        limit_stations_to_inventory (Inventory | None): Restrict downloads to stations in this
            ObsPy inventory, while keeping all other selection criteria.
        reject_channels_with_gaps (bool): Reject downloaded waveform files containing gaps
            or overlaps.
        minimum_length (float): Minimum accepted data coverage as a fraction of the requested
            segment, between `0` and `1`; `0.9` requires at least 90% coverage.
        sanitize (bool): Delete downloaded waveform files that have no associated StationXML
            metadata.
        minimum_interstation_distance_in_m (float): Minimum separation in meters between
            newly selected and already selected stations, also used to detect duplicates.
        channel_priorities (tuple[str, ...] | list[str]): Preferred channel patterns, in order,
            e.g. `["HH[ZNE]", "BH[ZNE]"]`. Ignored when `channel` is set.
        location_priorities (tuple[str, ...] | list[str]): Preferred location codes, in order,
            e.g. `["", "00", "10"]`. Ignored when `location` is set.
        providers (list[str | Client] | None): FDSN provider names, service URLs or configured
            ObsPy clients, e.g. `["RESIF"]`. `None` tries all providers known to ObsPy.
        debug (bool): Enable detailed MassDownloader logging.
        configure_logging (bool): Let MassDownloader configure its console logger.
        mseed_storage (str | callable | None): Waveform storage template.
            `None` uses `<dataPath>/waveforms/NET/STA/NET.STA.LOC.CHA/YYYY-MM-DD.mseed`.
        stationxml_storage (str | callable | None): StationXML storage template.
            `None` uses `<dataPath>/inventory/{network}/{station}.xml`.
        download_chunk_size_in_mb (float): Target size in megabytes of each bundled waveform
            download request; distinct from the time segmentation above.
        threads_per_client (int): Number of simultaneous waveform download threads per provider.
        print_report (bool): Print the MassDownloader summary after downloading.

    Notes:
        - Existing waveform paths are skipped by the default storage template.
        - This function writes files (waveforms and metadata) and does not return a dataset object.

    Example:
        Download daily vertical-component files for a rectangular region:

        ```python
        from sda.process import download_data

        download_data(
            outputPath="/path/to/output",
            domainType="rectangular",
            latitudes=(40.0, 45.0),
            longitudes=(-120.0, -115.0),
            starttime="2023-01-01T00:00:00",
            endtime="2023-01-03T00:00:00",
            chunklength_in_sec=86400,
            network="TA",
            channel="BHZ",
        )
        ```

        Select stations within one degree of a point:

        ```python
        from sda.process import download_data

        download_data(
            outputPath="/path/to/output",
            domainType="circular",
            latitude=48.58,
            longitude=7.75,
            minradius=0.0,
            maxradius=1.0,
            starttime="2023-01-01T00:00:00",
            endtime="2023-01-02T00:00:00",
            chunklength_in_sec=86400,
            providers=["RESIF"],
            channel="HHZ",
        )
        ```
    """

    add_log("#"*50, level="info")
    add_log("Start process: download_data", level="info")

    if not os.path.isdir(outputPath): os.makedirs(outputPath)
    
    # Prepare files
    if dataPath == None:
        dataPath = os.path.join(outputPath, "data")
    
    
    # Define geographical domain
    if domainType == "rectangular":
        domain = mdl.RectangularDomain(minlatitude=min(latitudes), maxlatitude=max(latitudes),
                                       minlongitude=min(longitudes), maxlongitude=max(longitudes))
    elif domainType == "circular":
        domain = mdl.CircularDomain(latitude=latitude, longitude=longitude,
                                    minradius=minradius, maxradius=maxradius)
    elif domainType == "global":
        domain = mdl.GlobalDomain()  
    
    # Restrictions
    starttime = UTCDateTime(starttime)
    endtime   = UTCDateTime(endtime)
    restrictions = mdl.Restrictions(
        starttime, endtime,
        station_starttime, station_endtime,
        chunklength_in_sec,
        network, station, location, channel,
        exclude_networks, exclude_stations,
        limit_stations_to_inventory,
        reject_channels_with_gaps, minimum_length,
        sanitize, minimum_interstation_distance_in_m,
        channel_priorities, location_priorities
    )
    
    # Massive Downloader object
    mdlObject = mdl.MassDownloader(providers, debug, configure_logging)

    # Download data
    global dataPathGlobalVariable # To be accessed by get_mseed_storage()
    dataPathGlobalVariable = dataPath
    if mseed_storage == None:
        mseed_storage = get_mseed_storage
    if stationxml_storage == None:
        stationxml_storage = os.path.join(dataPath, "inventory", "{network}", "{station}.xml")
    
    mdlObject.download(
        domain, restrictions,
        mseed_storage, stationxml_storage,
        download_chunk_size_in_mb, threads_per_client, print_report 
    )

    add_log("End process: download_data", level="info")
    add_log("#"*50, level="info")
