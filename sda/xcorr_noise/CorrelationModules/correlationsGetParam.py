################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Get the parameters.

Module correlationsGetParam
===========================

.. topic:: correlations.correlationsGetParam

    Provide a class :class:`Param` in order to get the parameters
    defined in the module :mod:`correlations.correlationsParam` and from the line argument.
    Provide also a derived class :class:`ParamWithLastDateCompute` which inherits of all the attributes and
    provides attributes and methods to know the correlations already compute (the last date already done).
    
    .. inheritance-diagram:: 
        Param
        ParamWithLastDateCompute
        :parts: 1
        
"""


import sys, os
# import correlationsParam
# import correlationsUtil
# import correlationsExceptions
import pickle
# import correlationsTestParam

from sda.xcorr_noise.CorrelationModules import correlationsParam
from sda.xcorr_noise.CorrelationModules import correlationsUtil
from sda.xcorr_noise.CorrelationModules import correlationsExceptions
from sda.xcorr_noise.CorrelationModules import correlationsTestParam

class Param(object):
    """
    
    :Line arguments: (with the order)
    
    * If TypeListStations is the string 'oneList':
            
    <TypeOfList>\n
    <RootPathLoad>\n 
    <RootPathSave>\n
    <FirstComponent>\n
    <SecondComponent>\n
    <NumberSubListOfDates>\n
    <IndexSublistDates>\n
    <NumberSubListOfStations>\n
    <IndexSublistStations>
                        
    * If TypeListStations is the string 'twoLists':
    
    <TypeOfList>\n
    <RootPathLoad>\n
    <RootPathSave>\n
    <FirstComponent>\n
    <SecondComponent>\n
    <NumberSubListOfDates>\n
    <IndexSublistDates>\n
    <NumberSubListOfStations>\n
    <FirstIndexSublistStations>\n
    <SecondIndexSublistStations>
    
    
    :Attributes:
        
        **TypeListStations**: str
            Two possibles values: 'oneList' or 'twoLists'. Two kind of instance,
            parameters for compute correlation for one list or for two disjoints sublists.
        
        **NumberSubListOfDates**: int
            The number of sublist to do from the list 'ListOfDates' defined in module :mod:`correlationsParam` 
                        
        **IndexSublistDates**: int
            The index of a sublist of dates form the list of sublist.
        
        **ListOfDates**: list of str
            The sublist of dates induce by parameters *NumberSubListOfDates* and *IndexSublistDates*.
        
        **LenListOfDates**: int
            The length of the list of dates
            
        **NumberSubListOfStations**: int
            The number of sublist to do from the list 'ListOfStations' defined in the module :mod:`correlationsParam` 
        
        **IndexSublistStations**: int
            It is defined only if *TypeListStations* is 'oneList'.
            The index of a sublist of stations form the list of sublist.

        **ListOfStations**: list
            It is defined only if *TypeListStations* is 'oneList'.
            The sublist of stations induce by parameters *NumberSubListOfStations* and *IndexSublistStations*.

        **FirstIndexSublistStations**: int 
            It is defined only if *TypeListStations* is 'twoLists'.
            The index of a first sublist of stations form the list of sublist.
        
        **FirstListOfStations**: list
            It is defined only if *TypeListStations* is 'twoLists'.
            The sublist of stations induce by parameters *NumberSubListOfStations* and *FirstIndexSublistStations*.

        **SecondIndexSublistStations**: int 
            It is defined only if *TypeListStations* is 'twoLists'.
            The index of a second sublist of stations form the list of sublist.
        
        **SecondListOfStations**: list
            It is defined only if *TypeListStations* is 'twoLists'.
            The sublist of stations induce by parameters *NumberSubListOfStations* and *SecondIndexSublistStations*.
        
        **FormatTrace**:
            The format to load trace defined in the module :mod:`correlationsParam`
            
        **FormatSave**:
            The format to save the correlation defined in the module :mod:`correlationsParam`
        
        **LoadDirectory**: string
            The directory to read the traces.
        
        **SaveDirectory**: string
            The directory to save the correlations.
            
    """

    def __init__(self, config):
        self.testParam = correlationsTestParam.TestValueParam()
        self.getFormatIO()
        ListOfDates = self.getListOfDates(config)
        self.LenListOfDates = len(ListOfDates)
        ListOfStations =  sorted(self.getListOfStations(config))
        self.LenListOfStations = len(ListOfStations)
        self.__DictNumberInlineArgs = {
                                     'TypeListStations':'onelist',
                                     'LoadDirectory':2,
                                     'SaveDirectory':3,
                                     'ComponentFirstStation':4,
                                     'ComponentSecondStation':5,
                                     'NumberSubListOfDates':6,
                                     'IndexSublistDates':7,
                                     'NumberSubListOfStations':8,
                                     'IndexSublistStations':9,
                                     'FirstIndexSublistStations':9,
                                     'SecondIndexSublistStations':10
                                     }
        self.getParamInline(config)
        self.ListOfDates = correlationsUtil.makeListOfSubListFromList(ListOfDates, self.NumberSubListOfDates)[self.IndexSublistDates]
        if self.TypeListStations ==  'oneList':
            self.ListOfStations = correlationsUtil.makeListOfSubListFromList(ListOfStations, self.NumberSubListOfStations)[self.IndexSublistStations]
            self.LenSublistStations = len(self.ListOfStations)
        elif self.TypeListStations ==  'twoLists':
            self.FirstListOfStations = correlationsUtil.makeListOfSubListFromList(ListOfStations, self.NumberSubListOfStations)[self.FirstIndexSublistStations]
            self.LenFirstSublistStations = len(self.FirstListOfStations)
            self.SecondListOfStations = correlationsUtil.makeListOfSubListFromList(ListOfStations, self.NumberSubListOfStations)[self.SecondIndexSublistStations]
            self.LenSecondSublistStations = len(self.SecondListOfStations)
    
    def getFormatIO(self):
        try:
            # self.FormatTrace = correlationsParam.FormatTrace
            self.FormatTrace = "npy"
            if not self.testParam.isGoodFormatTrace(FormatTrace = self.FormatTrace):
                raise correlationsExceptions.ErrorParamFromParamFile('FormatTrace')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('FormatTrace')
        try:
            # self.FormatSave = correlationsParam.FormatSave
            self.FormatSave = "mat"
            if not self.testParam.isGoodFormatSave(FormatSave = self.FormatSave):
                raise correlationsExceptions.ErrorParamFromParamFile('FormatSave')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('FormatSave')
    
    def getListOfDates(self, config):        
        try:
            # FirstDay = int(correlationsParam.FirstDay)
            # FirstYear = int(correlationsParam.FirstYear)
            # LastDay = int(correlationsParam.LastDay)
            # LastYear = int(correlationsParam.LastYear)
            FirstDay = int(config["FirstDay"])
            FirstYear = int(config["FirstYear"])
            LastDay = int(config["LastDay"])
            LastYear = int(config["LastYear"])
            if not self.testParam.isGoodJulianDayOfYear(FirstDay, FirstYear) and self.testParam.isGoodJulianDayOfYear(LastDay, LastYear):
                raise correlationsExceptions.ErrorParamFromParamFile('ListOfDates')
            ListOfDates = list(correlationsUtil.listDateIterator(str(FirstDay), str(FirstYear), str(LastDay), str(LastYear)))
            
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('ListOfDates')
        return sorted(ListOfDates)

    def getListOfStations(self, config):
        return config["stations"] 
        # if  hasattr(correlationsParam, 'ListOfStations') and isinstance(correlationsParam.ListOfStations, list) and correlationsParam.ListOfStations:
        #     return correlationsParam.ListOfStations
        # else:
        #     raise correlationsExceptions.ErrorParamFromParamFile('ListOfStations')

    def getParamInline(self, config):
        self.__getTypeOfListStations(config)
        # self.__testNumberOfArgsInline(config)
        self.__getLoadDirectory(config)
        self.__getSaveDirectory(config)
        self.__getComponents(config)
        self.__getArgsSublistDate(config)
        self.__getArgsSublistStations(config)
    
    def __getTypeOfListStations(self, config):
        try:
            self.TypeListStations = config["TypeListStations"]
            if not self.testParam.isGoodTypeOfList(TypeListStations = self.TypeListStations):
                raise correlationsExceptions.ErrorValueInlineArgument('TypeListStations', len(sys.argv[1:]))
        except IndexError:
            raise correlationsExceptions.ErrorNumberInlineArgument('EmptyInlineArgs', len(sys.argv[1:]))
    
    def __testNumberOfArgsInline(self, config):
        if not self.testParam.isGoodNumberInlineArgs(NumberArgs = len(sys.argv[1:]),\
         TypeListStations = self.TypeListStations, LenDictNumberInlineArgs = len(list(self.__DictNumberInlineArgs.keys()))):
            raise correlationsExceptions.ErrorNumberInlineArgument('NumberArgvOneListStation', len(sys.argv[1:]))

    def __getLoadDirectory(self, config):
        LoadDirectory = config['SaveDirectory']
        if not self.testParam.isGoodLoadDirectory(LoadDirectory = LoadDirectory):
            raise correlationsExceptions.ErrorValueInlineArgument('LoadDirectory', LoadDirectory)
        else:
            self.LoadDirectory = LoadDirectory
    
    def __getSaveDirectory(self, config):
        SaveDirectory = config['SaveDirectory']
        if not self.testParam.isGoodSaveDirectory(SaveDirectory = SaveDirectory):
            raise correlationsExceptions.ErrorValueInlineArgument('SaveDirectory', SaveDirectory)
        else:
            self.SaveDirectory = SaveDirectory

    def __getComponents(self, config):
        ComponentFirstStation = config["ComponentFirstStation"]
        if not self.testParam.isGoodComponent(ComponentStation = ComponentFirstStation):
            raise  correlationsExceptions.ErrorValueInlineArgument('ComponentFirstStation', ComponentFirstStation)
        else:
            self.ComponentFirstStation = ComponentFirstStation
        
        ComponentSecondStation = config["ComponentSecondStation"]
        if not self.testParam.isGoodComponent(ComponentStation = config["ComponentSecondStation"]):
            raise  correlationsExceptions.ErrorValueInlineArgument('ComponentSecondStation', ComponentSecondStation)
        else:
            self.ComponentSecondStation = ComponentSecondStation
        
    def __getArgsSublistDate(self, config):
        NumberSubListOfDates = config["NumberSubListOfDates"]
        try:
            NumberSubListOfDates = int(NumberSubListOfDates)
            if not self.testParam.isGoodNumberSublist(NumberSubList=NumberSubListOfDates, LenList=self.LenListOfDates):
                raise correlationsExceptions.ErrorValueInlineArgument('NumberSubListOfDates', NumberSubListOfDates)
            else:
                self.NumberSubListOfDates = NumberSubListOfDates
        except ValueError:
            raise correlationsExceptions.ErrorValueInlineArgument('NumberSubListOfDates', NumberSubListOfDates)
        
        IndexSublistDates = config["IndexSublistDates"]
        try:
            IndexSublistDates = int(IndexSublistDates)
            if not self.testParam.isGoodIndexSublist(IndexSublist=IndexSublistDates, NumberSubList = self.NumberSubListOfDates):
                raise correlationsExceptions.ErrorValueInlineArgument('IndexSublistDates', IndexSublistDates, NumberSubListOfDates = self.NumberSubListOfDates)
            else:
                self.IndexSublistDates = IndexSublistDates
        except ValueError:
            raise correlationsExceptions.ErrorValueInlineArgument('IndexSublistDates', IndexSublistDates, NumberSubListOfDates = self.NumberSubListOfDates)

    def __getArgsSublistStations(self, config):
        NumberSubListOfStations = config["NumberSubListOfStations"]
        try:
            NumberSubListOfStations = int(NumberSubListOfStations)
            if not self.testParam.isGoodNumberSublist(NumberSubList=NumberSubListOfStations, LenList=self.LenListOfStations):
                raise correlationsExceptions.ErrorValueInlineArgument('NumberSubListOfStations', NumberSubListOfStations)
            else:
                self.NumberSubListOfStations = NumberSubListOfStations
        except ValueError:
            raise correlationsExceptions.ErrorValueInlineArgument('NumberSubListOfStations', NumberSubListOfStations)
        
        if self.TypeListStations == 'oneList':
            IndexSublistStations = config["IndexSublistStations"]
            try:
                IndexSublistStations = int(IndexSublistStations)
                if not self.testParam.isGoodIndexSublist(IndexSublist=IndexSublistStations, NumberSubList = self.NumberSubListOfStations):
                    raise correlationsExceptions.ErrorValueInlineArgument('IndexSublistStations', IndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
                else:
                    self.IndexSublistStations = IndexSublistStations
            except ValueError:
                raise correlationsExceptions.ErrorValueInlineArgument('IndexSublistStations', IndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
        
        if self.TypeListStations == 'twoLists':
            FirstIndexSublistStations = sys.argv[self.__DictNumberInlineArgs['FirstIndexSublistStations']]
            try:
                FirstIndexSublistStations = int(FirstIndexSublistStations)
                if not self.testParam.isGoodIndexSublist(IndexSublist=FirstIndexSublistStations, NumberSubList = self.NumberSubListOfStations):
                    raise correlationsExceptions.ErrorValueInlineArgument('FirstIndexSublistStations', FirstIndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
                else:
                    self.FirstIndexSublistStations = FirstIndexSublistStations
            except ValueError: 
                raise correlationsExceptions.ErrorValueInlineArgument('FirstIndexSublistStations', FirstIndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
            SecondIndexSublistStations = sys.argv[self.__DictNumberInlineArgs['SecondIndexSublistStations']]
            try:
                SecondIndexSublistStations = int(SecondIndexSublistStations)
                if not self.testParam.isGoodIndexSublist(IndexSublist=SecondIndexSublistStations, NumberSubList = self.NumberSubListOfStations):
                    raise correlationsExceptions.ErrorValueInlineArgument('SecondIndexSublistStations', SecondIndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
                else:
                    self.SecondIndexSublistStations = SecondIndexSublistStations
            except ValueError:
                raise correlationsExceptions.ErrorValueInlineArgument('SecondIndexSublistStations', SecondIndexSublistStations, NumberSubListOfStations = self.NumberSubListOfStations)
        
    def __repr__(self):
        StringParamInline = 'TypeListStations: ' + self.TypeListStations + '\n'
        StringParamInline += 'LoadDirectory: ' + self.LoadDirectory + '\n'
        StringParamInline += 'SaveDirectory: ' + self.SaveDirectory + '\n'
        StringParamInline += 'ComponentFirstStation: ' + self.ComponentFirstStation + '\n'
        StringParamInline += 'ComponentSecondStation: ' + self.ComponentSecondStation + '\n'
        StringParamInline += 'NumberSubListOfDates: ' + str(self.NumberSubListOfDates) + '\n'
        StringParamInline += 'IndexSublistDates: ' + str(self.IndexSublistDates) + '\n'
        StringParamInline += 'NumberSubListOfStations: ' + str(self.NumberSubListOfStations) + '\n'
        StringParamInline += 'ListOfDates: ' + str(self.ListOfDates) + '\n'
        if self.TypeListStations == 'oneList':
            StringParamInline += 'IndexSublistStations: ' + str(self.IndexSublistStations) + '\n'
            StringParamInline += 'ListOfStations: ' + str(self.ListOfStations) + '\n'
        if self.TypeListStations == 'twoLists':
            StringParamInline += 'FirstIndexSublistStations: ' + str(self.FirstIndexSublistStations) + '\n'
            StringParamInline += 'FirstListOfStations: ' + str(self.FirstListOfStations) + '\n'
            StringParamInline += 'SecondIndexSublistStations: ' + str(self.SecondIndexSublistStations) + '\n'
            StringParamInline += 'SecondListOfStations: ' + str(self.SecondListOfStations) + '\n'
        return StringParamInline

class ParamWithLastDateCompute(Param):
    """
    Provides method :func:`getIndexLastDateCompute` and :func:`writeLastDateCompute` in order to get
    and save the last date for the correlations made for exactly the same parameters.
    
    :Base class: :class:`Param`
        Inherits all attibutes of the base class.
        
    :Attributes:
        
        **DirLastDateCompute**: str
            The directory where, if it exists, is the last date compute. 
            
        **FileLastDateCompute**: str
            The file name where, if it exists, is the last date compute.

        **IndexLastDateCompute**: str
            The index, if it exists, of the last date compute. It is None otherwise.

    """
    def __init__(self, config):
        Param.__init__(self, config)
        self.DirLastDateCompute = self.__getDirectoryLastDateCompute()
        self.FileLastDateCompute = self.__getFileLastDateCompute()
        self.IndexLastDateCompute = self.getIndexLastDateCompute()
        if self.IndexLastDateCompute is not None:
            self.ListOfDates = self.ListOfDates[self.IndexLastDateCompute+1:]
        self.LenListOfDates = len(self.ListOfDates)
    
    def __getDirectoryLastDateCompute(self):
        DirLastDateCompute = os.sep + self.SaveDirectory + os.sep + 'DirLastDateCompute' + os.sep
        return DirLastDateCompute
    
    def __getStringOfParameters(self):
        StringParameters = self.ComponentFirstStation + self.ComponentSecondStation + '_' + \
            str(self.NumberSubListOfDates) + '_' + str(self.IndexSublistDates) + '_'
        if self.TypeListStations == 'oneList':
            StringParameters += str(self.NumberSubListOfStations) + '_' + str(self.IndexSublistStations)
        if self.TypeListStations == 'twoLists':
            StringParameters += str(self.NumberSubListOfStations) + '_' + str(self.FirstIndexSublistStations)\
            + '_' +  str(self.SecondIndexSublistStations)
        return StringParameters
    
    def __getFileLastDateCompute(self):
        FileLastDateCompute = 'LastDateCompute_' + self.__getStringOfParameters()
        return FileLastDateCompute

    def __getKeyDictLastDateCompute(self):
        return 'LastDateCompute'
    
    def getIndexLastDateCompute(self):
        """
        Give the index of the list of dates for the last date computed (for exactly
        the same parameters). Return None otherwise.
        """
        IndexLastDateCompute = None
        if os.path.isfile(self.DirLastDateCompute + self.FileLastDateCompute):
            try:
                with open(self.DirLastDateCompute + self.FileLastDateCompute, 'r') as fileDictLastDate:
                    DictLastDateCompute = pickle.load(fileDictLastDate)
                if DictLastDateCompute[self.__getKeyDictLastDateCompute()] is not None:
                    IndexLastDateCompute = self.ListOfDates.index(DictLastDateCompute[self.__getKeyDictLastDateCompute()])
            except:
                pass
        return IndexLastDateCompute
    
    def writeLastDateCompute(self, date):
        """
        Save the index of the list of dates for the last date computed 
        (for exactly the same parameters) (with cPikle file).
        If an exception is raised, do nothing.        
        """
        DictLastDateCompute = {}
        if not os.path.isdir(self.DirLastDateCompute):
            try: 
                os.makedirs(self.DirLastDateCompute, 0o770)
            except:
                try: 
                    os.makedirs(self.DirLastDateCompute, 0o770)
                except:
                    pass
        DictLastDateCompute[self.__getKeyDictLastDateCompute()] = date
        # print(self.DirLastDateCompute)
        # print(self.DirLastDateCompute[1::])
        
        #####AJOUT JR
        try:
            os.mkdir(self.DirLastDateCompute[1::])
            # print('DirLastDateCompute Created')
        except:
            pass
        #####
    
#	print self.DirLastDateCompute
        with open(self.DirLastDateCompute[1::] + self.FileLastDateCompute, 'wb') as fileDictLastDate:
            pickle.dump(DictLastDateCompute, fileDictLastDate, -1)

if __name__ == '__main__':
    pass
