################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Test the validity of parameters.

Module tracesTestParam
======================
"""

import os
from sda.xcorr_noise2.PreProcessingModules.TraceModules import tracesUtil

class TestValueParam(object):
    """
    Provide methods in order to test the value of the parameters.
    """
    def isGoodFormatSave(self, **kwargs):
        if kwargs['FormatTraceSave'] in ['mat','npy']:
            return True
        else:
            return False
    def isGoodLoadDirectory(self, **kwargs):
        """
        Check if a directory exist and can be read.
        
        Parameter: dict
            A dictionary with a key 'LoadDirectory'.
        """
        if os.access(kwargs['LoadDirectory'], os.F_OK) and os.access(kwargs['LoadDirectory'], os.R_OK):
            return True
        else:
            return False
    def isGoodSaveDirectory(self, **kwargs):
        """
        Check if a directory exist or can be create.
        
        Parameter: dict
            A dictionary with a key 'SaveDirectory'.
        """
        # print((kwargs['SaveDirectory']))
        if tracesUtil.isValidPathDirToWrite(kwargs['SaveDirectory']):
            return True
        else:
            return False
    def isGoodComponent(self, **kwargs):
        if kwargs['ComponentStation'] in ['E','N','Z','BHE','BHN','BHZ']: ######## modif perso !!
            return True
        else:
            return False
    def isGoodJulianDayOfYear(self, day, year):
        if tracesUtil.isLeapYear(year):
            LastDayYear = 366
        else:
            LastDayYear = 365
        if int(day)>0 and int(day)<=LastDayYear:
            return True
        else:
            return False
    def isGoodOrderDates(self, FirstDay, FirstYear, LastDay, LastYear):
        if int(FirstYear) < int(LastYear) or (int(FirstYear) == int(LastYear) and int(FirstDay) <= int(LastDay)):
            return True
        else:
            return False
