################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Some tools for the package.

Module correlationsUtil
=======================
"""

import os
from sda.xcorr_noise2.CorrelationModules import correlationsExceptions


def isValidPathDirToWrite(pathDir):
    """

    :Parameter: 
        **pathDir**: string
            the directory path to be check

    :return: True if you can write on the path-directory or create it.

    """
    # print(pathDir)
    ListDirFromPathDir = pathDir.split(os.sep)
    len(ListDirFromPathDir)
    ListDirFromPathDir
#    for i in ListDirFromPathDir:
#	ListDirFromPathDir[i]
    ListSubPath = []
    SubPath=''
    for dir in ListDirFromPathDir:
        SubPath += dir + os.sep
        ListSubPath.append(SubPath)
    isValidPath = False
    for path in ListSubPath[::-1]:
        if os.access(path, os.W_OK):
            isValidPath = True
    
    # print(path)
    # print(isValidPath)   

#    if os.access(pathDir, os.W_OK):
#            isValidPath = True
    return isValidPath

def makeListOfSubListFromList(List, numberSubList=1):
    """
    Return a List of disjoint sublists of same length.

    :parameters:
         **List**: List
             A List of object.
         **numberSubList**: int (optional)
             A number strictly positive of the sublists to be made from List, default is 1.
         
    :return: 
        Return a List of disjoints  *numberSubList* sublists. 
        All sublists have the same length (or -1 for the lastest),
        ordered with the order as List.
        
    .. note::
        * If the number of sublist is greater than the length of the List, return only the not empty sublists, i.e. sublist with one element.

        * If the number of sublist is less than 1, it is set to 1.


    :Example:
    
        >>> L=[7, 'h8', 78, 59.0, 'aze', 8, 6, 4]
        >>> print makeListOfSubListFromList(L,3)
        [[7, 'h8', 78], [59.0, 'aze', 8], [6, 4]]
        >>> print makeListOfSubListFromList(L,10)
        [[7], ['h8'], [78], [59.0], ['aze'], [8], [6], [4]]

    """
    if numberSubList < 1:
        numberSubList = 1
    LenShortSubList = int(len(List)/numberSubList)
    LenLongSubList = int(len(List)/numberSubList)+1
    LenTotalLongSublist = (len(List)-LenShortSubList*numberSubList)*LenLongSubList
    ListOfSubList = []
    for indice in range(0, LenTotalLongSublist, LenLongSubList):
        ListOfSubList.append(List[indice:indice+LenLongSubList])
    if not LenShortSubList == 0:
        for indice in range(LenTotalLongSublist, len(List), LenShortSubList):
                ListOfSubList.append(List[indice:indice+LenShortSubList])
    return ListOfSubList


def isLeapYear(year):
        """
        :return: True if **year** is a leap year
        """
        if year % 100 != 0 and year % 4 == 0:
            return True
        elif year % 100 == 0 and year % 400 == 0:
            return True
        else:
            return False


class listDateIterator():
    """
    Get an instance of an iterator of dates from the first year/day until the last year/day (both include) 
    
    :Parameters:
        **FirstDay**: int-like
            The first day 
        **FirstYear**: int-like
            The first year
        **LastDay**: int-like
            The last day
        **LastYear**: int-like
            The last year

    :Example:
    
        >>> it = listDateIterator(360,2008,5,'2009')
        >>> for date in it:
        ...   print date,
        ... 
        2008/360 2008/361 2008/362 2008/363 2008/364 2008/365 2008/366 2009/001 2009/002
         2009/003 2009/004 2009/005

    """
    def __init__(self, FirstDay, FirstYear, LastDay, LastYear):
        if int(FirstYear) > int(LastYear) or  \
          (int(FirstYear) == int(LastYear) and int(FirstDay) > int(LastDay)):
            raise correlationsExceptions.ErrorParamFromParamFile('badOrderDates')
        self.FirstDay = str(FirstDay)
        self.LastDay = str(LastDay)
        self.LastYear = str(LastYear)
        self.currentDay = str(FirstDay)
        if int(self.currentDay) == 1:
            self.currentYear = str(int(FirstYear)-1)
            if self.__isLeapYear(int(self.currentYear)):
                self.currentDay = '366'
            else:
                self.currentDay = '365'
        else:            
            self.currentDay = str(int(FirstDay)-1)
            self.currentYear = str(int(FirstYear))
        self.currentDate = str(self.currentYear  + os.sep + self.currentDay)
    def __iter__(self):
        return self
    def __next__(self):
        if self.__isLeapYear(int(self.currentYear)):
            self.lastDayYear = '366'
        else:
            self.lastDayYear = '365'
        if (self.currentYear == self.LastYear and int(self.currentDay) == int(self.LastDay)):
            raise StopIteration
        else:
            if self.currentDay == self.lastDayYear:
                self.currentDay = '001'
                self.currentYear = str(int(self.currentYear) + 1)
                self.currentDate = str(self.currentYear + os.sep + self.currentDay)
            else:
                self.currentDay = str(int(self.currentDay) + 1)
                if int(self.currentDay) <10:
                    self.currentDay = '00' + str(self.currentDay)
                elif int(self.currentDay) <100:
                    self.currentDay = '0' + str(self.currentDay)
                self.currentDate = str(self.currentYear + os.sep + self.currentDay)
            return self.currentDate

    def __isLeapYear(self, year):
        """
        :return: True if **year** is a leap year
        """
        if year % 100 != 0 and year % 4 == 0:
            return True
        elif year % 100 == 0 and year % 400 == 0:
            return True
        else:
            return False

class LastNewValueGenerator(object):
    def __init__(self, generator):
        self._generator = generator
        
    def __iter__(self):
        fisrtElement = True
        for element in self._generator:
            if fisrtElement:
                fisrtElement = False
                previousElement = element
            else:
                if previousElement != element:
                    yield (previousElement)
                else:
                    yield None
                previousElement = element
        yield element

class LastNewValueGeneratorOfIndex(object):
    def __init__(self, Generator, indexYield):
        self.__generator = Generator
        self.__indexYield = indexYield
        
    def __iter__(self):
        fisrtElement = True
        for ListElement in self.__generator:
            ListElement = list(ListElement)
            if fisrtElement:
                fisrtElement = False
                previousListElement = ListElement
                
            else:
                if previousListElement[self.__indexYield] != ListElement[self.__indexYield]:
                    yield (previousListElement)
                else:
                    previousListElement[self.__indexYield] = None
                    yield (previousListElement)
                previousListElement = ListElement
        yield previousListElement

class LastNewValueGeneratorOfListIndex(object):
    """
    **A generator for filtering iterable**.
    
    Given a iterable and a sublist of indexes, generate only the values
    of the iterable for which the sublist of values defined by the 
    the sublist of indexes are the last new values. Last new values
    are the values such that the future next values generate will be different.
    
    In the cases of the sublist are not the new last values, yield values depend on the parameter **TypeYield**.
    There are 3 choices:
        
        * (default option) yield None values, set TypeYield='NoneValues'
        
        * Do not yield anything, set TypeYield='Nothing'
        
        * yield only others values, set TypeYield='OtherValues'
    

    :Parameters:
        
        **Iterable**: iterable
        
        **ListIndexTestYield**: list or int
            A sublist of indexes of the tuple generate by **Generator**.
        
        **TypeYield**: str
            The type of yield made (see above).
            
    :Example:
    
        Given an iterable and an instance \'it\':
        
        .. code-block:: python
        
            ListNumber01 = [1,2,2,1,5,8,9,10,10, 4, 4,4,4,4,8,17,17]
            ListNumber02 = [2,2,5,5,5,5,5, 8, 9,10,10,4,4,4,4, 9,12]
            ListNumber03 = [2,8,8,8,8,8,5, 5, 8, 9,10,4,4,4,4, 9,12]
            it=zip(ListNumber01, ListNumber02, ListNumber03)
            
        >>> for n in it: print n,
        ... 
        (1, 2, 2) (2, 2, 8) (2, 5, 8) (1, 5, 8) (5, 5, 8) (8, 5, 8) (9, 5, 5) (10, 8, 5)
         (10, 9, 8) (4, 10, 9) (4, 10, 10) (4, 4, 4) (4, 4, 4) (4, 4, 4) (8, 4, 4) (17, 9, 9) (17, 12, 12)
            
            ..    class Gen(object):
                    def __init__(self):
                        self.ListNumber01 = [1,2,2,1,5,8,9,10,10, 4, 4,4,4,4,8,17,17]
                        self.ListNumber02 = [2,2,5,5,5,5,5, 8, 9,10,10,4,4,4,4, 9,12]
                        self.ListNumber03 = [2,8,8,8,8,8,5, 5, 8, 9,10,4,4,4,4, 9,12]
                    def __iter__(self):
                        for i, j, k in zip(self.ListNumber01,self.ListNumber02, self.ListNumber03):
                            yield i, j, k
                g= Gen()
            
            
        >>> NewGen= LastNewValueGeneratorOfListIndex(it, [0], 'NoneValues')
        >>> for n in NewGen: print n,
        ... 
        [1, 2, 2] [None, 2, 8] [2, 5, 8] [1, 5, 8] [5, 5, 8] [8, 5, 8] [9, 5, 5] [None, 
        8, 5] [10, 9, 8] [None, 10, 9] [None, 10, 10] [None, 4, 4] [None, 4, 4] [4, 4, 4
        ] [8, 4, 4] [None, 9, 9] [17, 12, 12]
        >>> NewGen= LastNewValueGeneratorOfListIndex(it, 0, 'OtherValues')
        >>> for n in NewGen: print n,
        ... 
        [1, 2, 2] [2, 8] [2, 5, 8] [1, 5, 8] [5, 5, 8] [8, 5, 8] [9, 5, 5] [8, 5] [10, 9
        , 8] [10, 9] [10, 10] [4, 4] [4, 4] [4, 4, 4] [8, 4, 4] [9, 9] [17, 12, 12]
        >>> NewGen= LastNewValueGeneratorOfListIndex(it, [0], 'Nothing')
        >>> for n in NewGen: print n,
        ... 
        [1, 2, 2] [2, 5, 8] [1, 5, 8] [5, 5, 8] [8, 5, 8] [9, 5, 5] [10, 9, 8] [4, 4, 4]
         [8, 4, 4] [17, 12, 12]
        >>> NewGen= LastNewValueGeneratorOfListIndex(it, [0,2], 'NoneValues')
        >>> for n in NewGen: print n,
        ... 
        [1, 2, 2] [None, 2, None] [2, 5, 8] [1, 5, 8] [5, 5, 8] [8, 5, 8] [9, 5, 5] [10,
         8, 5] [10, 9, 8] [4, 10, 9] [4, 10, 10] [None, 4, None] [None, 4, None] [4, 4, 
         4] [8, 4, 4] [17, 9, 9] [17, 12, 12]
        >>> NewGen= LastNewValueGeneratorOfListIndex(it, [0,1,2], 'NoneValues')
        >>> for n in NewGen: print n,
        ... 
        [1, 2, 2] [2, 2, 8] [2, 5, 8] [1, 5, 8] [5, 5, 8] [8, 5, 8] [9, 5, 5] [10, 8, 5]
         [10, 9, 8] [4, 10, 9] [4, 10, 10] [None, None, None] [None, None, None] [4, 4, 
         4] [8, 4, 4] [17, 9, 9] [17, 12, 12]
            
    .. Note::
    
        **Requirement**: The elements must be able to be compared with '==' operation.
        
    """
    def __init__(self, Iterable, ListIndexTestYield, TypeYield = 'NoneValues'):
        self.__Iterable = Iterable
        if  isinstance(ListIndexTestYield, int):
            self.__ListTestIndexYield = [ListIndexTestYield]
        else:
            self.__ListTestIndexYield = ListIndexTestYield
        self.__TypeYield = TypeYield
    def __iter__(self):
        fisrtElement = True
        previousListElement = None
        for ListElement in self.__Iterable:
            ListElement = list(ListElement)
            if fisrtElement:
                fisrtElement = False
                previousListElement = ListElement
            else:
                ListComparaisonElement = [ListElement[elem] == previousListElement[elem] for elem in self.__ListTestIndexYield]
                if not min(ListComparaisonElement):
                    yield (previousListElement)
                else:
                    if self.__TypeYield == 'NoneValues':
                        yield ([None if indexElem in self.__ListTestIndexYield else elem for indexElem, elem in enumerate(previousListElement)])
                    elif self.__TypeYield == 'OtherValues':
                        yield ([elem for indexElem, elem in enumerate(previousListElement) if not indexElem in self.__ListTestIndexYield])
                previousListElement = ListElement
        if previousListElement is not None:
            yield previousListElement



if __name__ == '__main__':
    pass
