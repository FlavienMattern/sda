import numpy as np

def azimut(lat1, long1, lat2, long2):
    
    rad = 180/np.pi
    
    lat1 = lat1/rad
    long1 = long1/rad
    lat2 = lat2/rad
    long2 = long2/rad
    
    dx = (6379*np.cos((lat1+lat2)/2)*(long2-long1))
    dy = (6379*(lat2-lat1))
    
    if dx == 0:
        dx = 0.0000001
    if dy == 0:
        dy = 0.0000001
        
    if dx > 0 and dy > 0:
        az = np.arctan((dx/dy))
        az = rad*az
        baz = az + 180
    
    elif dx > 0 and dy < 0:
        dy = -1*dy
        az = np.arctan(dy/dx)
        az = rad*az + 90
        baz = 180 + az
    
    elif dx < 0 and dy < 0:
        dx = -1*dx
        dy = -1*dy
        az = np.arctan(dx/dy)
        az = rad*az + 180
        baz = az - 180
    
    elif dx < 0 and dy > 0:
        dx = -1*dx
        az = np.arctan(dy/dx)
        az = rad*az + 270
        baz = az - 180
    
    return az, baz



def rotationRTZ(sta1, sta2, inventory, data, newComponents):

    d = data
    output = {}
    
    lat1 = inventory.select(station=sta1)[0][0].latitude
    lon1 = inventory.select(station=sta1)[0][0].longitude
    lat2 = inventory.select(station=sta2)[0][0].latitude
    lon2 = inventory.select(station=sta2)[0][0].longitude
            
    az, baz = azimut(lat1, lon1, lat2, lon2)
    psi = az*np.pi/180
    
    if {"ZZ"}.issubset(d.keys()):
        if "ZZ" in newComponents: output["ZZ"] = d["ZZ"]
   
    if {"EE", "NN", "EN", "NE"}.issubset(d.keys()):
        if "TT" in newComponents: output["TT"] = np.cos(psi)*np.cos(psi)*d["EE"] + np.sin(psi)*np.sin(psi)*d["NN"] - np.cos(psi)*np.sin(psi)*(d["EN"]+d["NE"])
        if "RR" in newComponents: output["RR"] = np.cos(psi)*np.cos(psi)*d["NN"] + np.sin(psi)*np.sin(psi)*d["EE"] + np.cos(psi)*np.sin(psi)*(d["EN"]+d["NE"])
        if "TR" in newComponents: output["TR"] = np.cos(psi)*np.cos(psi)*d["EN"] - np.sin(psi)*np.sin(psi)*d["NE"] + np.cos(psi)*np.sin(psi)*(d["EE"]-d["NN"])
        if "RT" in newComponents: output["RT"] = np.cos(psi)*np.cos(psi)*d["NE"] - np.sin(psi)*np.sin(psi)*d["EN"] + np.cos(psi)*np.sin(psi)*(d["EE"]-d["NN"])
        
    if {"ZE", "ZN"}.issubset(d.keys()):
        if "ZT" in newComponents: output["ZT"] = np.cos(psi)*d["ZE"] - np.sin(psi)*d["ZN"]
        if "ZR" in newComponents: output["ZR"] = np.sin(psi)*d["ZE"] + np.cos(psi)*d["ZN"]

    if {"EZ", "NZ"}.issubset(d.keys()):
        if "TZ" in newComponents: output["TZ"] = np.cos(psi)*d["EZ"] - np.sin(psi)*d["NZ"]
        if "RZ" in newComponents: output["RZ"] = np.sin(psi)*d["EZ"] + np.cos(psi)*d["NZ"]
        
    return output
