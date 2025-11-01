################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Classes of exceptions for the package.

Module tracesExceptions
=======================

.. inheritance-diagram::
         ExceptionTraces
         ErrorParamAttribute
         ErrorParam
         ErrorParamFromParamFile
"""



class ExceptionTraces(Exception):
    pass

class ErrorParamAttribute(ExceptionTraces):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def __str__(self):
        self.__Message = ""
        if 'classBadAttribute' in self.kwargs:
            self.__Message = '\nObject passed to the instance of the class: '+ self.kwargs['classBadAttribute']
            if  'ListMissingMethod' in self.kwargs:
                if len(self.kwargs['ListMissingMethod'])==1:
                    self.__Message += ' has not the method:\n'
                else:
                    self.__Message += ' has not all the methods:\n'
                for attr in  self.kwargs['ListMissingMethod']:
                    self.__Message += '\'' + attr + '\'\n'
                if  'ListMissingAttribute' in self.kwargs:
                    self.__Message += ' and '
            if  'ListMissingAttribute' in self.kwargs:
                if len(self.kwargs['ListMissingAttribute'])==1:
                    self.__Message += ' has not the Attribute:\n'
                else:
                    self.__Message += ' has not all the Attributes:\n'
                for attr in  self.kwargs['ListMissingAttribute']:
                    self.__Message += '\'' + attr + '\'\n'
        return self.__Message

class ErrorParam(ExceptionTraces):
    def __init__(self, NameArgument):
        self.NameArgument = NameArgument
        
    def __str__(self):
        self.__GeneralMessage =""
        return self.__GeneralMessage

class ErrorParamFromParamFile(ErrorParam):
    def __init__(self, NameArgument, **kwargs):
        ErrorParam.__init__(self, NameArgument)
    
    def __str__(self):
        if self.NameArgument == 'ListOfDates':
            self.__Message = "\nThere is no all the attributes named : \'FirstDay\', \'FirstYear\', \'LastDay\', \'LastYear\'"
            self.__Message += "\nOr the days are not valid"
        self.ErrorParamFromParamFile = ErrorParam.__str__(self)
        if self.NameArgument == 'badOrderDates':
            self.__Message = "Error for parameters date: the first date is greater than the last date."
        if self.NameArgument == 'ListOfStations':
            self.__Message = "There is no list of stations named \'ListOfStations\' define in the module."
            self.__Message += "\nOr the list of station \'ListOfStations\' is empty,"
        if self.NameArgument == 'FormatTraceSave':
            self.__Message = "There is no string named \'FormatTrace\' in the module."
            self.__Message += "\nOr the format is not exactly \'mat\' or \'npy\'"
        if self.NameArgument == 'LoadDirectory':
            self.__Message = "There is no string named \'LoadDirectory\' in the module."
            self.__Message += "\nOr the LoadDirectory do not exist or cannot be read."
        if self.NameArgument == 'SaveDirectory':
            self.__Message = "There is no string named \'SaveDirectory\' in the module."
            self.__Message += "\nOr the SaveDirectory cannot be write."
        if self.NameArgument == 'ComponentStation':
            self.__Message = "There is no string named \'ComponentStation\' in the module."
            self.__Message += "\nOr the ComponentStation is not a letter in \'E\', \'N\', \'Z\'."
        if self.NameArgument == 'NewFrequence':
            self.__Message = "There is no float named \'NewFrequence\' in the module."
            
        return self.ErrorParamFromParamFile + self.__Message


if __name__ == '__main__':
    pass
