import math

def get_bounds(lonmin, lonmax, latmin, latmax, width=800, height=600, tile_size=512):
    """
    Calcule le niveau de zoom optimal et le centre pour une zone délimitée par une bounding box.

    Paramètres :
    - lonmin, lonmax : bornes de longitude
    - latmin, latmax : bornes de latitude
    - width, height : taille du viewport en pixels (par défaut 800x600)
    - tile_size : taille d'une tuile (par défaut 512)

    Retour :
    - zoom : float, niveau de zoom
    - mid_lat : float, latitude centrale
    - mid_lon : float, longitude centrale
    """
    
    # Éviter une division par zéro
    lon_span = max(abs(lonmax - lonmin), 1e-6)
    lat_span = max(abs(latmax - latmin), 1e-6)

    mid_lon = (lonmin + lonmax) / 2.0
    mid_lat = (latmin + latmax) / 2.0

    # Largeur du monde en pixels à zoom 0
    world_map_width = tile_size

    # Zoom horizontal (longitude)
    zoom_lon = math.log2(360.0 / lon_span * (width / world_map_width))

    # Zoom vertical (latitude), en Mercator
    zoom_lat = math.log2(170.1022 / lat_span * (height / world_map_width))

    zoom = min(zoom_lon, zoom_lat)

    # Limites de zoom dans Deck.gl / Mapbox
    zoom = max(0, min(zoom, 22))

    return mid_lon, mid_lat, zoom