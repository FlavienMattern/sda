from datetime import datetime


def get_day(date_str):
    
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day = (date - datetime(date.year, 1, 1, 0, 0)).days + 1
    
    return date.year, day
