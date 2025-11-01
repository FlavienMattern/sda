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