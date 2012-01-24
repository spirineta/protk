from PraatSound import *
from ReformatPraat import FormatOutput
from shutil import rmtree
from os import path, mkdir, system, remove, makedirs
from numpy import loadtxt
from gc import collect

#level of a particular file, with sub-PraatSounds for semi/manual/auto
class Unit(object):

    def __init__(self,filename,options=False,directory=False,praatLocation = False,config = False,reformat = False,extractPraat = False,loadData = True,truth="manual",\
                 source = "auto"):
        
        self.options = options
        if not self.options.quiet: print "Unit-level: starting",filename
        self.filename = filename
        self.formattedDir = self.options.directory + "formatted/" + self.filename + "_formatted/"
        #make subdirectories for praat output & reformatted output
        self.createPraatDirectories()
        #extract praat
        if self.options.extractPraat:
            self.processPraat()
            self.reformat()
        #reformat
        if self.options.reformat and not self.options.extractPraat:
            self.reformat()
        #holds all the sound data
        self.soundData = {}
        self.headersTotal = {}
        self.headersToAdd = {}
        
        if loadData:
            self.loadSoundData()

        try:
            remove(self.options.directory +"db/"+ self.filename +'.db')
        except Exception:
            pass
        self.connection = sqlite3.connect(self.options.directory +"db/"+ self.filename +'.db')
        self.cursor = self.connection.cursor()
        
        
        
        for folder in self.options.source:
            #create database tables
            tableName = 'processed_' + self.filename + '_'+ folder
            
            self.cursor.execute('CREATE TABLE IF NOT EXISTS ' + tableName.replace('-','') +  ' (interval_number INTEGER PRIMARY KEY, start_time REAL, end_time REAL, uoa_type TEXT,' + self.options.tags[0] + ' INTEGER)')
            self.connection.commit()
            
            self.sourcePraatSound = PraatSound(options = self.options,filename = self.filename, soundData = self.soundData,headersTotal = self.headersTotal,findFP = True,findPhones = True,kind=folder,truth=self.options.truth)
            del self.sourcePraatSound
       
        #perhaps not necessary, but leave until you're sure there's no multiprocessing memory leak
        del self.soundData, self.headersTotal, self.headersToAdd
        collect()
        if not self.options.quiet: print "Unit-level: finished",filename
        
        
    def reformat(self):
        #delete reformatted data that already exists
        if path.lexists(self.options.directory + "formatted/" + self.filename + "_formatted/"):
            rmtree(self.options.directory + "formatted/" + self.filename + "_formatted/")
            mkdir(self.options.directory + "formatted/" + self.filename + "_formatted/")
        else: print "error, no praat output location exists"        
        #create reformat object
        reformat = FormatOutput(options=self.options,filename=self.filename)
        #reformat raw output
        reformat.formatRaw()
        del reformat
        collect()

    def createPraatDirectories(self):
        #praat output

        ###################################
        # 11/14/2011 Serguei's changes
        # changed path.isdir to ath.lexists call
        ###################################
        
        if not path.exists(self.options.directory + "db"):
            try:
                mkdir(self.options.directory + "db/")
            except:
                pass
        if not path.exists(self.options.directory + "arff"):
            try:
                mkdir(self.options.directory + "arff/")
            except:
                pass
        if not path.exists(self.options.directory + "praatOutput"):
            try:
                mkdir(self.options.directory + "praatOutput/")
            except:
                pass
        if not path.exists(self.options.directory + "praatOutput/" + self.filename + "_Short"):
            try:
                mkdir(self.options.directory + "praatOutput/" + self.filename +  "_Short/")
            except:
                pass
        #reformatted data
        if not path.exists(self.options.directory + "formatted"):
            try:
                mkdir(self.options.directory + "formatted/")
            except:
                pass
        if not path.exists(self.options.directory + "formatted/" + self.filename + "_formatted"):
            try:
                mkdir(self.options.directory + "formatted/" + self.filename +  "_formatted/")
            except:
                pass
        #extracted data
        if not path.exists(self.options.directory + "extracted"):
            try:
                mkdir(self.options.directory + "extracted/")
            except:
                pass
        #make folder for truth
        if not path.exists(self.options.directory + "extracted/" + self.options.truth + ""):
            try:
                mkdir(self.options.directory + "extracted/" + self.options.truth + "/")
            except:
                pass
            #make one for all others
        #make folder for sources    
        for folder in self.options.source:
            if not path.exists(self.options.directory + "extracted/" + folder + ""):
                try:
                    mkdir(self.options.directory + "extracted/" + folder + "/")
                except:
                    pass


    def processPraat(self):
        #delete whatever was in the praat directory before
        if path.lexists(self.options.directory + "praatOutput/" + self.filename + "_Short/"):
            rmtree(self.options.directory + "praatOutput/" + self.filename + "_Short/")
            mkdir(self.options.directory + "praatOutput/" + self.filename + "_Short/")
        else: print "error, no praat output location exists"
        
        #do processes one-by-one depending on config file, on a file-by-file basis
        praatCommand = ""
        #where Praat is located
        if not self.options.quiet: print self.options.praatLocation
        praatCommand += self.options.praatLocation
        #where the script is located
        praatCommand += " " + self.options.praatscriptpath#"extractInfoSingle.praat"
        #where the source is located
        praatCommand += " " + self.options.directory
        #what the filename is
        praatCommand += " " + self.filename
        #where the destination is going to be
        for i in self.options.praatConfig:
            praatCommand += " " + str(i)
        if not self.options.quiet: print "calling praat with",praatCommand
        if not self.options.quiet: print "extracting Praat info from",self.filename                      
        system(praatCommand)


    def loadSoundData(self,headersOnly = False):
        '''loads data to do normalization/extraction with'''
       
        for entry in self.options.suffixes:
            self.soundData[entry] = False
            self.headersToAdd[entry] = False
            
        #set which headers to add to which - sorry this is so long
        self.headersToAdd[".Sound_RW"] = []
        self.headersToAdd[".Intensity_RW"] = []
        self.headersToAdd[".JitterLocal_RW"] = []
        self.headersToAdd[".JitterLocalAbsolute_RW"] = []
        self.headersToAdd[".JitterPPQ5_RW"] = []
        self.headersToAdd[".JitterRap_RW"] = []
        self.headersToAdd[".JitterDDP_RW"] = []
        self.headersToAdd[".ShimmerAPQ3_RW"] = []
        self.headersToAdd[".ShimmerAPQ5_RW"] = []
        self.headersToAdd[".ShimmerAPQ11_RW"] = []
        self.headersToAdd[".ShimmerLocal_RW"] = []
        self.headersToAdd[".ShimmerLocalDB_RW"] = []
        self.headersToAdd[".Pitch_RW"] = []
        self.headersToAdd[".PitchAC_RW"] = []
        self.headersToAdd[".PitchCC_RW"] = []
        self.headersToAdd[".PitchSHS_RW"] = []
        self.headersToAdd[".PointProcessCC_RW"] = []
        self.headersToAdd[".PointProcessExtrema_RW"] = []
        self.headersToAdd[".PointProcessPeaks_RW"] = []
        self.headersToAdd[".PointProcessZeros_RW"] = []
        self.headersToAdd[".HarmonicityAC_RW"] = []
        self.headersToAdd[".HarmonicityCC_RW"] = []
        self.headersToAdd[".FormantBurg_RW"] = ["f2/f1","f3/f2","f4/f3","f5/f4"]
        self.headersToAdd[".FormantSL_RW"] = ["f2/f1","f3/f2","f4/f3","f5/f4"]
        self.headersToAdd[".FormantKeepAll_RW"] = ["f2/f1","f3/f2","f4/f3","f5/f4"]
        self.headersToAdd[".LPCac_RW"] = []
        self.headersToAdd[".LPCCovariance_RW"]= []
        self.headersToAdd[".LPCBurg_RW"]= []
        self.headersToAdd[".LPCMarple_RW"] = []
        self.headersToAdd[".Silences_RW"] = []
        self.headersToAdd[".MFCC_RW"] = []


        #loads all data from text file in order to do mean, standard deviation, etc
        for entry in self.options.suffixes:
            if self.options.config[entry]:
                source = self.formattedDir + self.filename + entry
                try:
                    f = open(source,'r')
                    header = f.readline()
                    header = header.split()
                    #do it differently depending on file
                    if self.headersToAdd[entry]:
                        for additionalHeader in self.headersToAdd[entry]:
                            header.append(additionalHeader)  
                    self.headersTotal[entry] = header
                    f.close()

                except IOError:
                    print "HELP! Problem adding additional headers in file",entry
            else: self.headersTotal[entry] = self.headersToAdd[entry] = self.soundData[entry]= False

