################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
File parameters for the package.

Module correlationsParam
========================

.. topic:: correlations.correlationsParam

    This module provide the parameters of the package :mod:`correlations`.

:Parameters: 

        **ListOfStations**: list
            The list of stations. Only correlations which correspond to these stations are compute.
            
        **FormatTrace**: str
            The format to load the trace. Set only 'npy' (for numpy array format).

        **FormatSave**: str
            The format to save the correlation. Set only 'npy' (for numpy array format) or 'mat' (for matlab format).
            
        **FirstDay**, **FirstYear**: int or str
            A julian day and a year.
            FirstDay and FirstYear compose the date 'FirstYear/FirstDay'.
            Only traces with date *after* this date are processed.

        **LastDay**, **LastYear**: int or str
            A julian day and a year.
            LastDay and LastYear compose the date 'LastYear/LastDay'.
            Only traces with date *after* this date are processed.
            
        
        **LenTrace**: int
            The length of the trace.
            
        **Maxlag**: int
            The lag of the correlations.
            
        **GoodNumber**: int
            A number great than LenTrace+Maxlag to optimize the time
            computing of Fourier transform. If you do not know, set the smaller
            power of two greater than LenTrace+Maxlag.
            
            
        **ListOfDates**: list
            A list of dates. 
            
            .. Note::
            
                If this list is not empty, it will be take into account
                instead of the attributes **FirstDay**, **FirstYear**, **LastDay**, **LastYear**.
                This provides an ad hoc solution to compute correlations for dates that are not of the form 'year/day'.
        
            
        
        
"""
########DO NOT DELETE THIS LINE########

# ##FirstDay
# FirstDay = 1
# ##FirstYear
# FirstYear = 2019
# ##LastDay
# LastDay = 1
# ##LastYear
# LastYear = 2020


# #param for correlation
# # for 1Hz - 4h

# ##Fech
# Fech = 0
# ##Maxlag
# Maxlag = 1200
# ##LenTrace
# LenTrace = 8640000
# ##GoodNumber
# GoodNumber = 99000
# ##NumberSubLen
# NumberSubLen = 96

# #param for save
# FormatTrace= 'npy'#set only 'npy' or 'mat'
# FormatSave = 'mat'#set only 'npy' or 'mat'

# ##ListOfStations
# ListOfStations = ['HOHE']
# if __name__ == '__main__':
#     pass

