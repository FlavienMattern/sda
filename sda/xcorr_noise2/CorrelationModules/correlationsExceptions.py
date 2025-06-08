################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Classes of exceptions for the package.

Module correlationsExceptions
=============================

.. inheritance-diagram::
         ExceptionCorrelations
         ErrorParamAttribute
         ErrorParam
         ErrorParamFromParamFile
         ErrorInlineArgument
         ErrorNumberInlineArgument
         ErrorValueInlineArgument
         
"""

class ExceptionCorrelations(Exception):
    pass

class ErrorParamAttribute(ExceptionCorrelations):
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

class ErrorParam(ExceptionCorrelations):
    def __init__(self, NameArgument):
        self.NameArgument = NameArgument
        
    def __str__(self):
        self.__GeneralMessage =""
        return self.__GeneralMessage

class ErrorParamFromParamFile(ErrorParam):
    def __init__(self, NameArgument, **kwargs):
        ErrorParam.__init__(self, NameArgument)
    
    def __str__(self):
        self.ErrorParamFromParamFile = ErrorParam.__str__(self)
        if self.NameArgument == 'ListOfDates':
            self.__Message = "There is no list of dates named \'ListOfDates\' define in the module named: " + correlationsParam.__file__
            self.__Message += "\nOr the list of dates \'ListOfDates\' is empty,"
            self.__Message += "\nOr there is no all the attributes named : \'FirstDay\', \'FirstYear\', \'LastDay\', \'LastYear\'"
        if self.NameArgument == 'badOrderDates':
            self.__Message = "Error for parameters date: the first date is greater than the last date in the file:" +  correlationsParam.__file__
        if self.NameArgument == 'ListOfStations':
            self.__Message = "There is no list of stations named \'ListOfStations\' define in the module named: " + correlationsParam.__file__
            self.__Message += "\nOr the list of station \'ListOfStations\' is empty,"
        if self.NameArgument == 'LenTrace':
            self.__Message = "There is no integer named \'LenTrace\' stricly greater than 0 in the module named: " + correlationsParam.__file__
        if self.NameArgument == 'NumberSubLen':
            self.__Message = "There is no integer named \'NumberSubLen\' stricly greater than 0 in the module named: " + correlationsParam.__file__
        if self.NameArgument == 'GoodNumber':
            self.__Message = "There is no integer named \'GoodNumber\' stricly greater than parameter \'LenTrace\' in the module named: " + correlationsParam.__file__
        if self.NameArgument == 'Maxlag':
            self.__Message = "There is no integer named \'Maxlag\' stricly greater than 0 in the module named: " + correlationsParam.__file__
        if self.NameArgument == 'FormatTrace':
            self.__Message = "There is no string named \'FormatTrace\' in the module named: " + correlationsParam.__file__
            self.__Message += "\nOr the format is not exactly \'npy\'"
        if self.NameArgument == 'FormatSave':
            self.__Message = "There is no string named \'FormatSave\' in the module named: " + correlationsParam.__file__
            self.__Message += "\nOr the format is not  \'npy\' or \'mat\'"
        return self.ErrorParamFromParamFile + self.__Message

class ErrorInlineArgument(ErrorParam):
    def __init__(self, NameArgument):
        ErrorParam.__init__(self, NameArgument)
    def __str__(self):
        self.__GeneralMessage ="""
\n\n\n
Inline parameters: sequence of string separate by blank:\n \
For one list of stations: \n \
<TypeOfList> <RootPathLoad> <RootPathSave> <FirstComponent> <SecondComponent> <NumberSubListOfDates> \
<IndexSublistDates> <NumberSubListOfStations> <IndexSublistStations> \n \
For two lists of stations: \n \
<TypeOfList> <RootPathLoad> <RootPathSave> <FirstComponent> <SecondComponent> <NumberSubListOfDates> \
<IndexSublistDates> <NumberSubListOfStations> <FirstIndexSublistStations> <SecondIndexSublistStations> \n\n
"""
        self.MessageToStop = "\nError on getting parameters: The program must be stopped\n\n"
        self.__Message = ""
        if self.NameArgument == 'TypeListStations':
            self.__Message = "First inline argument should be one of the strings \'oneList\' or \'twoLists\'"
        self.ErrorParamMsg = self.__GeneralMessage + self.__Message + self.MessageToStop
        return self.ErrorParamMsg
        

class ErrorNumberInlineArgument(ErrorInlineArgument):
    def __init__(self, NameArgument, NumberOfArg):#, DictArgument=None):
        ErrorInlineArgument.__init__(self, NameArgument)
        self.NumberOfArg = NumberOfArg
        
    def __str__(self):
        self.ErrorNumberInlineArgument = ErrorInlineArgument.__str__(self)
        self.__NumberArgvInlineOneListStations = 9
        self.__NumberArgvInlineTwoListStations = 10
        self.__Message = ""
        if self.NameArgument == 'EmptyInlineArgs':
            self.__Message = "The inline argument should be not empty!"
        if self.NameArgument == 'NumberArgvOneListStation':
            self.__Message = "the number of inline arguments for one list of stations should be exactly "\
             + str(self.__NumberArgvInlineOneListStations) + " and not " + str(self.NumberOfArg)
        if self.NameArgument == 'NumberArgvTwoListStation':
            self.__Message = "the number of inline arguments for two lists of stations should be exactly "\
            + str(self.__NumberArgvInlineTwoListStations) + " and not " + str(self.NumberOfArg)
        self.ErrorNumberInlineArgument = self.ErrorNumberInlineArgument + self.__Message
        return self.ErrorNumberInlineArgument

class ErrorValueInlineArgument(ErrorInlineArgument):

    def __init__(self, NameArgument, ValueArgument, **kwargs):
        ErrorInlineArgument.__init__(self, NameArgument)
        self.ValueArgument = ValueArgument
        self.DictArgument = kwargs
        
    def __str__(self):
        self.Message = ""
        if self.NameArgument == 'LoadDirectory':
            self.Message = "the directory \'" + str(self.ValueArgument) + "\' for loading traces does not exist or you have no permissions to read it."
        elif self.NameArgument == 'SaveDirectory':
            self.Message = "Cannot write on the directory \'" + str(self.ValueArgument) + " or cannot create it."
        elif self.NameArgument == 'FirstComponent':
            self.Message = "Argument \'FirstComponent\' should be a letter among \'E\', \'N\' and \'Z' and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'SecondComponent':
            self.Message = "Argument \'SecondComponent\' should be a letter among \'E\', \'N\' and \'Z' and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'NumberSubListOfDates':
            self.Message = "Argument \'NumberSubListOfDates\' should be a positive and not null integer less than the length of the list and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'IndexSublistDates':
            self.Message = "Argument \'IndexSublistDates\' should be a positive and not null integer strictly less than " + str(self.DictArgument['NumberSubListOfDates']) + " and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'NumberSubListOfStations':
            self.Message = "Argument \'NumberSubListOfStations\' should be a positive and not null integer less than the number of stations and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'IndexSublistStations':
            self.Message = "Argument \'IndexSublistStations\' should be a positive and not null integer strictly less than " + str(self.DictArgument['NumberSubListOfStations']) +  " and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'FirstIndexSublistStations':
            self.Message = "Argument \'FirstIndexSublistStations\' should be a positive and not null integer strictly less than " + str(self.DictArgument['NumberSubListOfStations']) +  " and not \'" + str(self.ValueArgument) + "\'."
        elif self.NameArgument == 'SecondIndexSublistStations':
            self.Message = "Argument \'SecondIndexSublistStations\' should be a positive and not null integer strictly less than " + str(self.DictArgument['NumberSubListOfStations']) +  " and not \'" + str(self.ValueArgument) + "\'."
        return ErrorInlineArgument.__str__(self) + self.Message

if __name__ == '__main__':
    pass
