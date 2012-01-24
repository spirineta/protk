from os import rename
from numpy import *

#takes everything in a given directory and reformatRaws
#it to be in a column structure.

class FormatOutput(object):

    def __init__(self,directory=False,filename=False,options=False,config = None, rawSubDir = "_Short/"):
        if not options:
            self.options = dummy()
            self.options.directory = directory
            self.filename = filename
            self.options.verbose = True
            self.options.config = config
        else:
            self.options = options
            self.filename = filename
        self.rawInputDir = self.options.directory + "praatOutput/" +self.filename + rawSubDir
        self.rawOutputDir = self.options.directory + "formatted/" +  self.filename + "_formatted/"

    def formatRaw(self):
        if not self.options.quiet: print "reformatting raw data from",self.filename
        
        #self.formatBasic(".BasicInfo")
        
        #these are all TIME-DOMAIN files
        if self.options.config[".Sound_RW"]:
            self.formatRawSound(".Sound")
        if self.options.config[".PointProcessCC_RW"]:
            self.formatRawPointProcess(".PointProcessCC")
        if self.options.config[".PointProcessExtrema_RW"]:
            self.formatRawPointProcess(".PointProcessExtrema")
        if self.options.config[".PointProcessPeaks_RW"]:
            self.formatRawPointProcess(".PointProcessPeaks")
        if self.options.config[".PointProcessZeros_RW"]:
            self.formatRawPointProcess(".PointProcessZeros")
        if self.options.config[".HarmonicityAC_RW"]:
            self.formatRawHarmonicity(".HarmonicityAC")
        if self.options.config[".HarmonicityCC_RW"]:
            self.formatRawHarmonicity(".HarmonicityCC")
        if self.options.config[".FormantKeepAll_RW"]:
            self.formatRawFormant(".FormantKeepAll")
        if self.options.config[".FormantSL_RW"]:
            self.formatRawFormant(".FormantSL")
        if self.options.config[".FormantBurg_RW"]:
            self.formatRawFormant(".FormantBurg")
        if self.options.config[".LPCac_RW"]:
            self.formatRawLPC(".LPCac")
        if self.options.config[".LPCBurg_RW"]:
            self.formatRawLPC(".LPCBurg")
        if self.options.config[".LPCCovariance_RW"]:
            self.formatRawLPC(".LPCCovariance")
        if self.options.config[".LPCMarple_RW"]:
            self.formatRawLPC(".LPCMarple")
        if self.options.config[".Silences_RW"]:
            self.formatRawSilence(".Silences")
        if self.options.config[".Intensity_RW"]:
            self.formatRawIntensity(".Intensity")
        if self.options.config[".MFCC_RW"]:
            self.formatRawMFCC(".MFCC")
        if self.options.config[".JitterLocal_RW"]:
            self.formatRawJitter(".JitterLocal")
        if self.options.config[".JitterLocalAbsolute_RW"]:
            self.formatRawJitter(".JitterLocalAbsolute")
        if self.options.config[".JitterPPQ5_RW"]:
            self.formatRawJitter(".JitterPPQ5")
        if self.options.config[".JitterRap_RW"]:
            self.formatRawJitter(".JitterRap")
        if self.options.config[".JitterDDP_RW"]:
            self.formatRawJitter(".JitterDDP")
        if self.options.config[".ShimmerAPQ3_RW"]:
            self.formatRawShimmer(".ShimmerAPQ3")
        if self.options.config[".ShimmerAPQ5_RW"]:
            self.formatRawShimmer(".ShimmerAPQ5")
        if self.options.config[".ShimmerAPQ11_RW"]:
            self.formatRawShimmer(".ShimmerAPQ11")
        if self.options.config[".ShimmerLocal_RW"]:
            self.formatRawShimmer(".ShimmerLocal")
        if self.options.config[".ShimmerLocalDB_RW"]:
            self.formatRawShimmer(".ShimmerLocalDB")
        if self.options.config[".Pitch_RW"]:
            self.formatRawPitch(".Pitch")
        if self.options.config[".PitchAC_RW"]:
            self.formatRawPitch(".PitchAC")
        if self.options.config[".PitchCC_RW"]:
            self.formatRawPitch(".PitchCC")
        if self.options.config[".PitchSHS_RW"]:
            self.formatRawPitch(".PitchSHS")
        

    def formatBasic(self,suffix):
        try:
            outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
            data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 0)
        except:
            print "Error reformatting basic info."
            return
        variables = ['minAmp','maxAmp','absMax','mean','rootMeanSquare','standardDeviation',\
                'energy','power','energyInAir','powerInAir','intensity']
        var = 0
        for line in data:
            outFile.write(str(variables[var]) + "\t" + str(line) + "\n")
            var += 1
        
        outFile.close()
        if not self.options.quiet: print "done"
    
    def formatRawSound(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)
        xmin, xmax, nx, dx, x1 = data[0], data[1], data[2], data[3],data[4]
        outFile.write("time\tamplitude\n")
        t = x1 - dx
        for i in data[10:]:
            t += dx
            outFile.write(str(t) + "\t" + str(i) + "\n")

        outFile.close()
        if not self.options.quiet: print "done"

    def formatRawPointProcess(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 6)
        outFile.write("time\t dt\n")
        last = data[0]
        for i in data[1:]:
            outFile.write(str(i) + "\t"+ str(i-last) + "\n")
            last = i
            
        outFile.close()
        if not self.options.quiet: print "done"

    def formatRawHarmonicity(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)
        xmin, xmax, nx, dx, x1 = data[0], data[1], data[2], data[3],data[4]
        outFile.write("time\tharmonicity\n")
        
        t = x1
        for i in data[10:]:
            t += dx
            outFile.write(str(t) + "\t" + str(i) + "\n")

        outFile.close()
        if not self.options.quiet: print "done"


    def formatRawFormant(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)
        xmin, xmax, nx, dx, x1,maxFormants = data[0], data[1], data[2], data[3],data[4],data[5]

        #write header
        outFile.write("time\tintensity\t")
        for i in xrange(int(maxFormants)):
            outFile.write("\tf" + str(i+1) + "freq\tf" + str(i+1) + "bndwdth")
        outFile.write("\n")

        currentRow = 6 #where to start
        t = x1
        while currentRow < len(data):
            outFile.write(str(t) + "\t")
            outFile.write(str(data[currentRow]) + "\t")
            currentRow += 1
            nFormants = data[currentRow]
            currentRow += 1
            for i in xrange(int(nFormants)):
                outFile.write(str(data[currentRow]) + "\t")
                currentRow += 1
                outFile.write(str(data[currentRow]) + "\t")
                currentRow += 1
            if nFormants < maxFormants:
                for i in xrange(int(maxFormants) - int(nFormants)):
                    outFile.write(str(-1) + "\t")
                    outFile.write(str(-1) + "\t")
            outFile.write("\n")
            t += dx

        outFile.close()
        if not self.options.quiet: print "done"

    def formatRawLPC(self,suffix):
        if not self.options.quiet: print suffix,"...",
        #open files
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)

        #get relevant informatRawion from array
        xmin, xmax, nx, dx, x1,samplingPeriod,maxCoefficients = data[0], data[1], data[2], data[3],data[4],data[5],data[6]

        #write header,
        outFile.write("time")
        for i in xrange(int(maxCoefficients)):
            outFile.write("\tcoef" + str(i+1))
        outFile.write("\tgain")
        outFile.write("\n")

        currentRow = 7 #where to start
        t = x1
        while currentRow < len(data):
            outFile.write(str(t) + "\t")
            nCoefficients = data[currentRow]
            currentRow += 1
            for i in xrange(int(nCoefficients)):
                outFile.write(str(data[currentRow]) + "\t")
                currentRow += 1
            if nCoefficients < int(maxCoefficients):
                for i in xrange(int(maxCoefficients) - int(nCoefficients)):
                    outFile.write(str(-1) + "\t")
            #write gain
            outFile.write(str(data[currentRow]) + "\n")
            currentRow += 1
            outFile.write("\n")
            t += dx

        outFile.close()
        if not self.options.quiet: print "done"

    
    def formatRawSilence(self,suffix):
        if not self.options.quiet: print suffix,"...",
        #open file and skip beginning
        data = open(self.rawInputDir + self.filename + suffix,'r')
        for i in xrange(11):
            data.readline()
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        outFile.write("start\tend\tsilence\n")


        numIntervals = data.readline()

        numProcessed = 0
        while numProcessed < int(numIntervals):
            numProcessed += 1
            t_begin = data.readline()
            t_end = data.readline()
            s = data.readline()
            t_begin = float(t_begin)
            t_end = float(t_end)
            if "silent" in s:
                outFile.write(str(t_begin) + "\t"+ str(t_end) + "\t" + str(1) + "\n")
            elif "sounding" in s:
                outFile.write(str(t_begin) + "\t"+ str(t_end) + "\t" + str(0) + "\n")    
        if not self.options.quiet: print "done"
        outFile.close()

    def formatRawIntensity(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)
        xmin, xmax, nx, dx, x1 = data[0], data[1], data[2], data[3],data[4]
        outFile.write("time\tintensity\n")
        
        t = x1 - dx
        for i in data[10:]:
            t += dx
            outFile.write(str(t) + "\t" + str(i) + "\n")
        outFile.close()
        if not self.options.quiet: print "done"

    def formatRawMFCC(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 3)
        xmin, xmax, nx, dx, x1,maxCoefficients = data[0], data[1], data[2], data[3],data[4],data[7]

        #write header,
        outFile.write("time")
        for i in xrange(int(maxCoefficients) + 1):
            outFile.write("\tcoef" + str(i))
        outFile.write("\n")

        currentRow = 8 #where to start
        t = x1
        while currentRow < len(data):
            outFile.write(str(t) + "\t")
            nCoefficients = data[currentRow]
            currentRow += 1
            for i in xrange(int(nCoefficients) + 1):
                outFile.write(str(data[currentRow]) + "\t")
                currentRow += 1
            if nCoefficients < int(maxCoefficients+1):
                for i in xrange(int(maxCoefficients) - int(nCoefficients)):
                    outFile.write(str(-1) + "\t")
            #write gain
            outFile.write("\n")
            t += dx

        outFile.close()
        if not self.options.quiet: print "done"

    def formatRawJitter(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        outFile.write("start\tend\tjitter\n")

        #in file, replace each --undefined-- with -1
        self.replaceAll(self.rawInputDir+self.filename + suffix,"--undefined--","-1")

        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 2)
        numIntervals = data[0]

        currentRow = 3
        t = data[3]/2
        while currentRow <= int(float(numIntervals))*3 - 1:
            #print currentRow, numIntervals*3
            t_begin = data[currentRow]
            t_end = data[currentRow + 1]
            value = data[currentRow + 2]
            outFile.write(str(t_begin) + "\t"+ str(t_end) + "\t" + str(value) + "\n")
            currentRow += 3
        if not self.options.quiet: print "done"
        outFile.close()

    def formatRawShimmer(self,suffix):
        if not self.options.quiet: print suffix,"...",

        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        outFile.write("start\tend\tshimmer\n")

        #in file, replace each --undefined-- with -1
        self.replaceAll(self.rawInputDir+self.filename + suffix,"--undefined--","-1")

        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 2)
        numIntervals = data[0]

        currentRow = 3
        t = data[3]/2
        while currentRow <= int(float(numIntervals))*3 - 1:
            t_begin = data[currentRow]
            t_end = data[currentRow + 1]
            value = data[currentRow + 2]
            outFile.write(str(t_begin) + "\t"+ str(t_end) + "\t" + str(value) + "\n")
            currentRow += 3
                
        if not self.options.quiet: print "done"
        outFile.close()

    def replaceAll(self,file,searchExp,replaceExp):
        with open(file,'r') as inFile:
            with open(file+'temp','w') as outFile:
                for line in inFile:
                    if searchExp in line:
                        line = line.replace(searchExp,replaceExp)
                    outFile.write(line)
        rename(file+'temp',file)


    def formatRawPitch(self,suffix):
        if not self.options.quiet: print suffix,"...",
        outFile = open(self.rawOutputDir + self.filename   + suffix + "_RW","w")
        data = loadtxt(self.rawInputDir + self.filename + suffix,skiprows = 6)
        outFile.write("time\tpitch\n")
        loc = 0
        while loc < len(data):
            outFile.write(str(data[loc]) + "\t"+str(data[loc+1]) + "\n")
            loc += 2
        if not self.options.quiet: print "done"
        outFile.close()

class dummy(object):
    pass




