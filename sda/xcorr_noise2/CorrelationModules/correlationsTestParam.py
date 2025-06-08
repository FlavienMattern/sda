################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Test the validity of parameters.

Module correlationsTestParam
============================
"""

import os
from sda.xcorr_noise2.CorrelationModules import correlationsUtil

class TestValueParam(object):
    def isGoodFormatTrace(self, **kwargs):
        if kwargs['FormatTrace'] in ['npy','mat']:
            return True
        else:
            return False
    def isGoodFormatSave(self, **kwargs):
        if kwargs['FormatSave'] in ['mat','npy']:
            return True
        else:
            return False
    def isGoodTypeOfList(self, **kwargs):
        if kwargs['TypeListStations'] in ['oneList', 'twoLists']:
            return True
        else:
            return False
    def isGoodNumberInlineArgs(self, **kwargs):
        if kwargs['TypeListStations'] == 'oneList':
            if kwargs['NumberArgs'] == kwargs['LenDictNumberInlineArgs']-2:
                return True
            else:
                return False
        if kwargs['TypeListStations'] == 'twoLists':
            if kwargs['NumberArgs'] == kwargs['LenDictNumberInlineArgs']-1:
                return True
            else:
                return False
    def isGoodLoadDirectory(self, **kwargs):
        if os.access(kwargs['LoadDirectory'], os.F_OK) and os.access(kwargs['LoadDirectory'], os.R_OK):
            return True
        else:
            return False
    def isGoodSaveDirectory(self, **kwargs):
        if correlationsUtil.isValidPathDirToWrite(kwargs['SaveDirectory']):
            return True
        else:
            return False
    def isGoodComponent(self, **kwargs):
        if kwargs['ComponentStation'] in ['E','N','Z','BHZ','BHE','BHN']:
            return True
        else:
            return False
    def isGoodNumberSublist(self, **kwargs):
        if kwargs['NumberSubList']>0 and kwargs['NumberSubList']<=kwargs['LenList']:
            return True
        else:
            return False
    def isGoodIndexSublist(self, **kwargs):
        if kwargs['IndexSublist']>=0 and kwargs['IndexSublist']<=kwargs['NumberSubList']:
            return True
        else:
            return False
    def isGoodJulianDayOfYear(self, day, year):
        if correlationsUtil.isLeapYear(year):
            LastDayYear = 366
        else:
            LastDayYear = 365
        if int(day)>0 and int(day)<=LastDayYear:
            return True
        else:
            return False
