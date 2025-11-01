################################################
# Codes developed for the Whisper Project,
# FP7 ERC Advanced grant 227507
# by Xavier Briand: xav.briand.whisper@gmail.com
# with Michel Campillo and Philippe Roux.
################################################
"""
Compute correlations.

Module correlationsCorrelation
==============================

Provide a classes in order to compute the correlation.

.. inheritance-diagram::
         Correlation
         CorrelationForSublen
         :parts: 1
"""

from sda.process.xcorr_noise.CorrelationModules import correlationsExceptions
import scipy.fftpack
import numpy
import os
import scipy



class Correlation(object):
    """
    Provide attributes for the parameters of a correlation
    and a method :func:`makeCorrWithMaxlag` to compute the correlation.
    
    :Attributes:
        
        **LenTrace**: int
            Defined in the module :mod:`correlations.correlationsParam`.
            
        **Maxlag**: int
            Defined in the module :mod:`correlations.correlationsParam`.
        
        **GoodNumber**: int
            Defined in the module :mod:`correlations.correlationsParam`.
        
    """
    def __init__(self, config):
        self.getMaxlag(config)
        self.getLenTrace(config)
        self.getGoodNumber(config)
        self.SaveSubLen = config["SaveSubLen"]
        self.NewFrequence = config["NewFrequence"]
        self.SaveDirectory = config["SaveDirectory"]
        
    def getMaxlag(self, config):
        try:
            # self.Maxlag = int(correlationsParam.Maxlag)
            self.Maxlag = config["Maxlag"]
            if not self.Maxlag>0:
                raise correlationsExceptions.ErrorParamFromParamFile('Maxlag')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('Maxlag')
    
    def getLenTrace(self, config):
        try:
            # self.LenTrace = int(correlationsParam.LenTrace)
            self.LenTrace = config["LenTrace"]
            if not self.LenTrace>0:
                raise correlationsExceptions.ErrorParamFromParamFile('LenTrace')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('LenTrace')
    
    def getGoodNumber(self, config):
        try:
            # self.GoodNumber = int(correlationsParam.GoodNumber)
            self.GoodNumber = config["GoodNumber"]
            if not self.GoodNumber>=self.LenTrace:
                raise correlationsExceptions.ErrorParamFromParamFile('GoodNumber')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('GoodNumber')     
        
    def __repr__(self):
        StringParam = "The parameters for the correlation: \n"
        StringParam += 'LenTrace: ' + str(self.LenTrace) + '\n'
        StringParam += 'GoodNumber: ' + str(self.GoodNumber) + '\n'
        StringParam += 'Maxlag: ' + str(self.Maxlag) + '\n'
        return StringParam

    def makeCorrWithMaxlag(self, trace01, trace02):
        """
        Return the correlation of trace01 and trace02.
        
        :Parameters:
            **trace01**, **trace02**: numpy array
                the traces for the correlation:
        
        .. Note:: 
            **Requirement**:
            The trace **trace01** and **trace02** are supposed to have the **same length**.
        """
        tr2 = numpy.zeros(self.GoodNumber)
        tr2[0:self.LenTrace] = trace01
        tr2 = scipy.fftpack.fft(tr2,overwrite_x=True)
        tr2.imag *= -1
        tr1 = numpy.zeros(self.GoodNumber)
        tr1[self.Maxlag:self.Maxlag+self.LenTrace]= trace02
        tr2 *= scipy.fftpack.fft(tr1,overwrite_x=True)
        return (scipy.fftpack.ifft(tr2,overwrite_x=True)[0:2*self.Maxlag+1].real)


    def makeCorrWithMaxlagNormailzed(self, trace01, trace02):
        """
        Return the correlation of trace01 and trace02 normalized.
        
        :Parameters:
            **trace01**, **trace02**: numpy array
                the traces for the correlation:
        
        .. Note:: 
            **Requirement**:
            The trace **trace01** and **trace02** are supposed to have the **same length**.
            
        """
        tr2 = numpy.zeros(self.GoodNumber)
        tr2[0:self.LenTrace] = trace01
        tr2[0:self.LenTrace] /= numpy.sqrt(numpy.sum(tr2[0:self.LenTrace]**2))
        tr2 = scipy.fftpack.fft(tr2,overwrite_x=True)
        tr2.imag *= -1 # Take complex conjugate
        tr1 = numpy.zeros(self.GoodNumber)
        # If there is an error of shape here, you may change GoodNumber to match
        tr1[self.Maxlag:self.Maxlag+self.LenTrace]= trace02
        tr1[self.Maxlag:self.Maxlag+self.LenTrace] /= numpy.sqrt(numpy.sum(tr1[self.Maxlag:self.Maxlag+self.LenTrace]**2))
        tr2 *= scipy.fftpack.fft(tr1,overwrite_x=True) # Compute cross correlation by multiplying spectrum in frequency domain
        return (scipy.fftpack.ifft(tr2,overwrite_x=True)[0:2*self.Maxlag+1].real)
        
class CorrelationForSublen(Correlation):
    
    def __init__(self, config):
        self.getNumberSubLen(config)
        Correlation.__init__(self, config)
        self.LenTraceTotal = self.LenTrace
        self.LenTrace = int(self.LenTrace/self.NumberSubLen)#Redefine the length of trace
    
    def __repr__(self):
        StringParam = Correlation.__repr__(self)
        StringParam += 'NumberSublen: ' + str(self.NumberSubLen) + '\n'
        return StringParam
        
    def getNumberSubLen(self, config):
        try:
            # self.NumberSubLen = int(correlationsParam.NumberSubLen)
            self.NumberSubLen = config["NumberSubLen"]
            if not self.NumberSubLen>0:
                raise correlationsExceptions.ErrorParamFromParamFile('NumberSubLen')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('NumberSubLen')
        
    def getGoodNumber(self, config):#redefine the method for the test of length
        try:
            # self.GoodNumber = int(correlationsParam.GoodNumber)
            self.GoodNumber = config["GoodNumber"]
            if not self.GoodNumber*self.NumberSubLen>=self.LenTrace:
                raise correlationsExceptions.ErrorParamFromParamFile('GoodNumber')
        except (AttributeError, ValueError):
            raise correlationsExceptions.ErrorParamFromParamFile('GoodNumber')
        
    def makeCorrelationSubLenStackWithNormalisationAndMaxlag(self, trace01, trace02, date, comp, sta1, sta2):
        corr = numpy.zeros(2*self.Maxlag+1, dtype='float')
        N = self.NumberSubLen*len(trace01)/self.LenTraceTotal
        numberCorr = 0
        for i in range(int(N)):
            ti = self.LenTrace*i * 1./self.NewFrequence
            tf = self.LenTrace*(i+1) * 1./self.NewFrequence
            t1 = trace01[self.LenTrace*i:self.LenTrace*(i+1)]
            t2 = trace02[self.LenTrace*i:self.LenTrace*(i+1)]
            if numpy.max(numpy.abs(t1)) >= 1e-20:
                if numpy.max(numpy.abs(t2)) >= 1e-20:
                    xcorr = self.makeCorrWithMaxlagNormailzed(t1, t2)
                    corr += xcorr
                    numberCorr += 1
                    # Save Sublen
                    if self.SaveSubLen:
                        folder = os.path.join(self.SaveDirectory[:-3], "CorrelationsSubLen", comp, f"{sta1}-{sta2}")
                        try:
                            os.makedirs(folder)
                        except:
                            pass
                        filename = os.path.join(folder, f"{date}_{ti}-{tf}.npy")
                        with open(filename, 'wb') as f:
                            numpy.save(f, xcorr)
                    
        return corr/float(numberCorr), float(numberCorr)/N

if __name__ == '__main__':
    #c=Correlation()
    c=CorrelationForSublen()
    #print(c)    
