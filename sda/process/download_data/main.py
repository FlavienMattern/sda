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
    """Download seismic data from using ObsPy's MassDownloader. This function downloads waveform data and station metadata for a specified geographical domain and time period from various seismic data providers.

    Parameters:
        outputPath (str): Path to the main output directory where data will be stored.
        dataPath (str, optional): Path to the dataset directory. If `None`, defaults to `<outputPath>/data`.
        domainType (str, optional): Type of geographical domain. Options: `"rectangular"`, `"circular"`, `"global"`. Default is `"rectangular"`.
        latitudes (tuple, optional): `(latmin, latmax)` - Minimum and maximum latitude for rectangular domain.
        longitudes (tuple, optional): `(lonmin, lonmax)` - Minimum and maximum longitude for rectangular domain.
        latitude (float, optional): Center latitude for circular domain.
        longitude (float, optional): Center longitude for circular domain.
        minradius (float, optional): Minimum distance from center of circular domain (in km).
        maxradius (float, optional): Maximum distance from center of circular domain (in km).
        starttime (str | UTCDateTime): Start time for data download.
        endtime (str | UTCDateTime): End time for data download.
        station_starttime (str | UTCDateTime, optional): Stations must have been operational at or before this time.
        station_endtime (str | UTCDateTime, optional): Stations must have been operational at or after this time.
        chunklength_in_sec (float, optional): Length of one chunk (i.e., one file) in seconds for splitting downloads.
        network (str, optional): Network code(s) to download (e.g., `"IU"` or `"IU,G*"`).
        station (str, optional): Station code(s) to download (e.g., `"ANMO"` or `"A*"`).
        location (str, optional): Location code(s) to download (e.g., `"00"`, `"00,01,10"`).
        channel (str, optional): Channel code(s) to download (e.g., `"BHZ"` or `"BH*"`).
        exclude_networks (tuple, optional): Network codes to exclude from download (e.g., `["BW", "GR"]`, `["F*", "G?"]`).
        exclude_stations (tuple, optional): Station codes to exclude from download (e.g., `["AL??", "*O"]`, `["STR", "W*"]`).
        limit_stations_to_inventory (Inventory, optional): If provided, only stations in this inventory will be downloaded. All other restrictions still apply, this just serves to further limit the set of stations to download.
        reject_channels_with_gaps (bool, optional): Reject channels that have gaps or overlaps. Default is `True`.
        minimum_length (float, optional): Minimum length of trace as fraction of requested time span (0.0-1.0). Default is `0.9`.
        sanitize (bool, optional): Ensure stations are sufficiently separated and clean metadata. Default is `True`.
        minimum_interstation_distance_in_m (float, optional): Minimum distance between stations in meters when `sanitize=True`. Default is `1000`.
        channel_priorities (tuple, optional): Priority order for channel selection when multiple options exist. Default is `("HH[ZNE12]", "BH[ZNE12]", ...)`.
        location_priorities (tuple, optional): Priority order for location codes when multiple options exist. Default is `("", "00", "10", ...)`.
        providers (list, optional): List of data providers (e.g., `["RESIF", "IRIS"]`). If `None`, all known providers are considered. Can also be a list of manually configured FDSN clients.
        debug (bool, optional): Enable debug mode for detailed logging. Default is `False`.
        configure_logging (bool, optional): Configure logging for the MassDownloader. Default is `True`.
        mseed_storage (str | callable, optional): Path template or function for storing miniSEED files. If `None`, uses default storage pattern via `get_mseed_storage()`.
        stationxml_storage (str, optional): Path template for storing StationXML files. If `None`, defaults to `<dataPath>/inventory/{network}/{station}.xml`.
        download_chunk_size_in_mb (int, optional): Size of download chunks in megabytes. Default is `20`.
        threads_per_client (int, optional): Number of parallel download threads per client. Default is `3`.
        print_report (bool, optional): Print download report upon completion. Default is `True`.
    
    Returns:
        `None`

    Notes:
        - Creates output directories if they don't exist.
        - Uses ObsPy's MassDownloader for parallel downloads from multiple providers.
        - Supports rectangular, circular, and global domain selections.
        - Automatically handles channel and location code prioritization.
        - The `mseed_storage` can be either a string path template or a callable function that returns storage paths.

    Example:
        ```python
                from sda.process import download_data
                
                # Download data for a rectangular region
                download_data(
                    outputPath="/path/to/output",
                    domainType="rectangular",
                    latitudes=(40.0, 45.0),
                    longitudes=(-120.0, -115.0),
                    starttime="2023-01-01",
                    endtime="2023-01-02",
                    network="TA",
                    channel="BHZ"
                )
                
                # Download data for a circular region around a point
                download_data(
                    outputPath="/path/to/output",
                    domainType="circular",
                    latitude=35.0,
                    longitude=-118.0,
                    minradius=0,
                    maxradius=100,
                    starttime="2023-01-01",
                    endtime="2023-01-02"
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