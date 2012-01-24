#ProTK objects are organized as follows:
#The Project is the main object that keeps track of all the info associated with 
#a given project (list of files, directory, options chosen, etc)
#it also initiates the processing and distributes jobs to cores



from multiprocessing import Pool
from shutil import rmtree
from os import path, listdir, system, remove, mkdir
import os
import sys
from Unit import Unit
from gc import collect
import sqlite3
from numpy import *


import datetime

#JOBS:
    #maintain project-wide data
        #list of files
        #location of Praat application        
    #check for presence of all required files
    #make each Unit run in parallel (info extraction)
    #make WEKA file

#keeps the data associated with a particular project (set of files).
class Project(object):
    
    #this only happens for brand-new projects
    def __init__(self,options):

        #command line options
        self.options = options
        #list of files to process
        self.fileList = []
        #global config file
        self.options.wekaListConfig = False
        
        #reformat items in options that should be a list
        if type(self.options.source) == str:
            self.options.source = self.options.source.split(",")
        if type(self.options.tags) == str:
            self.options.tags = self.options.tags.split(",")
        #if self.options.cleanOldResults:
        #    self.options.cleanOldResults = self.options.cleanOldResults.split(",")
        #set config location option
        if not self.options.configLocation:
            self.options.configLocation = self.options.directory + "config.txt"
        else:
            self.options.configLocation = self.options.configLocation + "config.txt"
        
        #all possible suffixes (everything possibly extracted from Praat)
        self.options.suffixes = [".PointProcessCC_RW",".PointProcessExtrema_RW",".PointProcessPeaks_RW",".PointProcessZeros_RW",".HarmonicityAC_RW",\
                         ".HarmonicityCC_RW",".FormantBurg_RW",".FormantKeepAll_RW",".FormantSL_RW",".FormantBurg_RW",".LPCac_RW",\
                         ".LPCBurg_RW",".LPCCovariance_RW",".LPCMarple_RW",".Silences_RW",".Intensity_RW",".MFCC_RW",".JitterLocal_RW",\
                         ".JitterLocalAbsolute_RW",".JitterPPQ5_RW",".JitterRap_RW",".JitterDDP_RW",".ShimmerAPQ3_RW",".ShimmerAPQ5_RW",\
                         ".ShimmerAPQ11_RW",".ShimmerLocal_RW",".ShimmerLocalDB_RW",".Pitch_RW",".PitchAC_RW",".PitchCC_RW",".PitchSHS_RW", ".Sound_RW"]
                         
        self.options.vowels = ["AA","AE","AH","AO","AW","AX","AY","EH","EL","EN","ER","EY","IH","IY","OW","OY","UH","UW","Y"]
        self.options.phones = ["AA","AE","AH","AO","AW","AX","AY","B","CH","D","DH","EH","EL","EN",\
                          "ER","EY","F","G","HH","IH","IY","JH","K","L","M","N","NG","OW","OY",\
                          "P","R","S","SH","T","TH","UH","UW","V","W","Y","Z","ZH","SIL"]
        
        
        #this is helpful for reformatting stuff from Praat - Praat gives different measures "null" values if they can't be calculated
        self.options.nullValues = \
        [   ["MFCC",None,None,None],\
        ["Jitter",-1,2,2],\
        ["Pitch",None,None,None],\
        ["Shimmer",-1,2,2],\
        ["PointProcess",None,None,None],\
        ["Sound",None,None,None],\
        ["Harmonicity",-200,1,1],\
        ["Formant",-1,2,11],\
        ["LPC",-1,1,16],\
        ["Intensity",None,None,None]]
        
           
        #load file list from wav directory  
        self.getFileList()
        if options.numProcesses > len(self.fileList):
            options.numProcesses = len(self.fileList)
        
        if not self.options.wekaOnly:
            #verify needed txtgrid files exist
            self.checkRequiredFiles()
        
            #convert txtgrid files
            self.convertTxtgrid(self.options.truth)
            for folder in self.options.source:
                self.convertTxtgrid(folder)
        
        #make sure proper TextGrid files exist 
        self.checkForTextGridFiles()


        #extract intervals and filled pauses in parallel!
        self.run()

        
    def checkForTextGridFiles(self):
        required = []
        required.append(self.options.tagtier)
        required.append(self.options.prosodytier)
        required.append(self.options.passthroughtier)
        for folder in self.options.source:
            for fname in self.fileList:
                for r in required:
                    if not path.isfile(self.options.directory + folder + "/" + fname + "-" + r + ".TextGrid"):
                        print "error, the tier you specified (",str(fname + "-" + r + ".TextGrid"),") doesn't exist. Check your input!"
                        print "exiting."
                        exit()

    def getFileList(self):
        '''gets list of files to be processed based on the contents of the wav/ directory'''
        dirList = listdir(self.options.directory + "wav/")
        self.fileList = []
        for fname in dirList:
            if fname.endswith(".wav"):
                self.fileList.append(fname[0:-4])
                
    def checkRequiredFiles(self):
        '''makes sure textgrid files exist for each wav file, and that a config file exists'''
        #check for config file, and load it.  Make it part of options.
        #load config file in the 2 required formats
        self.options.config = {}
        self.loadConfig()
        self.options.praatConfig = []
        self.loadPraatConfig()
        
        #for truth and each other directory:
            #make sure the directories exist
            #check for txtgrid files
            
        #TRUTH
        if not path.lexists(self.options.directory + self.options.truth + "/"):
            print "error, the",self.options.truth,"directory doesn't exist (it's where your 'truth' files should be)! Exiting."
            exit()

        toExtract = self.options.source
        if toExtract:
            for folder in toExtract:
                if not path.isdir(self.options.directory + folder + "/"):     
                    print "error, the",self.options.directory + folder + "/","directory doesn't exist! You listed it as a folder to process. Exiting."
                    exit()
                for fname in self.fileList:
                    if not path.isfile(self.options.directory + folder + "/" + fname + ".txtgrid"):
                        print "error, the required",fname,".txtgrid file doesn't exist in ./",folder,"/"
                        print "exiting."
                        exit()
                    if not self.options.extractPraat and not path.isdir(self.options.directory + 'formatted/' + fname + '_formatted/'):
                        print "You first need to extract prosodic information with Praat.  Re-run with the -x flag."
                        exit()

        #check to make sure directories to be cleaned exist
        #if self.options.cleanOldResults:
        #    for folder in self.options.cleanOldResults:
        #        if not path.isdir(self.options.directory + "extracted/" + folder + "/"):
        #            print "error, the",folder,"directory doesn't exist! Exiting."
        #            exit()
                
                
        praatscriptpath = os.path.abspath(__file__)
        s = praatscriptpath.split('/')
        praatscriptpath = '/' + '/'.join(s[:-1]) +   "/extractInfoSingle.praat"
        self.options.praatscriptpath = praatscriptpath
        #make sure praat script is there
        if not path.isfile(praatscriptpath):
            print "error, the praat script isn't in the same directory as the rest of the package files! Printing file list and exiting."
            print os.system("ls")
            print path.isfile(praatscriptpath)
            print self.options.praatscriptpath
            exit()
            
        #folder for db files
        if not path.lexists(self.options.directory + "db/"):
            mkdir(self.options.directory + "db/")
        if not path.lexists(self.options.directory + "arff/"):
            mkdir(self.options.directory + "arff/")
          
          
    def run(self): 
        if not self.options.wekaOnly:
            if not self.options.quiet: print "Running Extraction..."
            #clean old results, if asked
            if self.options.cleanOldResults:    
                self.clean()
            
            #extract
            if self.options.numProcesses == 1:
                for f in self.fileList:
                    #if f > "UMN013_PD-BDAE_WK_05":
                    self.extract(f,self.options)
                self.truthProcessed = True
            else:
                NOmulti(self.options.numProcesses,self.fileList,self.options)
        
        #create weka file
        for i in self.options.source:
            self.createWEKAFile(i)
        
    def formatForInsert(self,entry):
        entry = list(entry)
        for e in range(len(entry)):
            if type(entry[e]) == unicode:
                entry[e] = "\'" + str(entry[e]) + "\'"
            if entry[e] == None:
                entry[e] = 'NULL'
        return tuple(entry)
    
    def extract(self,f,options):    
        if True:
            x = Unit(filename=f,options=options)
            del x
            collect()

    def loadConfig(self):
        '''loads information from configuration file to figure out which types to process'''
        self.options.config = {}
        for suffix in self.options.suffixes:
            self.options.config[suffix] = False
        done = False
        while(not done):
            try:
                f = open(self.options.configLocation, 'r')
                for line in f:
                    if line[0] != "#":
                        s = line.split()
                        if s[1] == "True":
                            s[1] = True
                        elif s[1] == "False":
                            s[1] = False
                        else:
                            print s
                            print "Error! Config file not formatted correctly. True/False don't work."
                            raise
                        if not s[0] in self.options.config:
                            print s
                            print "Error! Config file not formatted correctly. Something is wrong with the suffixes."
                            raise
                        self.options.config[s[0]] = s[1]
                done = True
                
            except IOError:
                print "Error. Configuration file not found, or formatted incorrectly."
                print "Enter full path and name of configuration file name:"
                self.options.configSource = raw_input()
        f.close()

        #if the global config file is not assigned, make it
        if not self.options.wekaListConfig:
            self.options.wekaListConfig = []
            for k in self.options.config.keys():
                if self.options.config[k]:
                    self.options.wekaListConfig.append(k)
            self.options.wekaListConfig.sort()
    
    def loadPraatConfig(self):
        '''loads info from configuration file to determine which praat extractions to do'''
        if not path.isfile(self.options.directory + "config.txt"):
            print "a config.txt file must be in the directory with all the files."
            print "looked in directory ",self.options.directory
            exit()
        f = open(self.options.directory + "config.txt")
        for line in f:
            if "#" not in line:
                s = line.split()
                if "true" in s[1].lower():
                    self.options.praatConfig.append(1)
                elif "false" in s[1].lower():
                    self.options.praatConfig.append(0)
                else:
                    "error, config file not formatted correctly for Praat input!"
                    exit()



#++++++++++++++++++++++++++++++++++++++++++++++

    def convertTxtgrid(self,subfolder):
        '''separates all txtgrid files into -TIER.TextGrid 
        files and makes sure their format is correct for the use of the
        Praat Prosody program. This has to be done before Praat Prosody can function
        properly.'''

        #1) open file into array, initialize n=1
        #2) go through array, record "name = "word"" variables into another array, along with their locations in array
        #3) for each name/word in array:
            #open file
            #write first 14 lines with modifications in size and name lines
            #write everything (changing silence and lower case) until you get to next item[n]: in line

        for filename in self.fileList:
            dest = self.options.directory + subfolder + "/"
            source = dest + filename + ".txtgrid"

            #1) open file into array, initialize n=1
            with open(source,'r') as f:
                sourceFileList = f.readlines() 
            #record where "items" are
            itemLocations = []
            for i in xrange(len(sourceFileList)):
                if "item [" in sourceFileList[i]:
                    itemLocations.append(i)
            itemLocations = itemLocations[1:] #get rid of the first one in the header
            numTiers = len(itemLocations)

            #2) record name = variables into dictionary, along with locations
            #dictionary keeping track of tiers
            tierList = []
            for line in sourceFileList:
                if "name = " in line:
                    s = line.split()
                    tierList.append(s[2].strip('"'))

            #3) for each name/word in dictionary, do stuff
            n=0
            for entry in tierList:
                resultList = sourceFileList[:] #copy to a new list
                resultList[6] = "size = 1\n"
                with open(dest + filename + "-" + entry + ".TextGrid",'w') as destinationFile:
                    for line in xrange(8):
                        destinationFile.write(resultList[line])
                    if n < numTiers -1:
                        for line in resultList[itemLocations[n]:itemLocations[n+1]]:
                            x = line
                            #make phones upper case
                            if "text" in x:
                                x = x.upper()
                                x = x.replace("TEXT","text")
                            #delete word and phone labels
                            if 'name = "' + entry + '"' in x:
                                x = x.replace(entry,"")
                            #delete silence markers
                            if "SIL" in x:
                                x = x.replace("SIL","")
                            if "sil" in x:
                                x = x.replace("sil","")
                            if "item [" in x:
                                x = "\titem [1]:\n"
                            destinationFile.write(x)
                    elif n == numTiers - 1:
                        for line in resultList[itemLocations[n]:]:
                            x = line
                            #make phones upper case
                            if "text" in x:
                                x = x.upper()
                                x = x.replace("TEXT","text")
                            #delete word and phone labels
                            if 'name = "' + entry + '"' in x:
                                x = x.replace(entry,"")
                            #delete silence markers
                            if "SIL" in x:
                                x = x.replace("SIL","")
                            if "sil" in x:
                                x = x.replace("sil","")
                            if "item [" in x:
                                x = "\titem [1]:\n"
                            destinationFile.write(x)
                n += 1

        #make directory for parsed files
        # for filename in self.fileList:
        #     dest = self.options.directory + subfolder + "/"
        #     #open files
        #     word = open(dest + filename + "-" + self.options.tagtier + ".TextGrid",'w')
        #     phone = open(dest + filename + "-" + self.options.prosodytier + ".TextGrid",'w')
        #     sourceFile = open(self.options.directory + subfolder + "/" + filename + ".txtgrid",'r')
        #     #go through files, writing relevant bits
        #     writeBoth = True
        #     writeWord = False
        #     writePhone = False
        #     #correct formatting issues
        #     for line in sourceFile:
        #         x = line
        #         #make phones upper case
        #         if "text" in x:
        #             x = x.upper()
        #             x = x.replace("TEXT","text")
        #         #delete word and phone labels
        #         if 'name = "word"' in x:
        #             x = x.replace("word","")
        #         if 'name = "phone"' in x:
        #             x = x.replace("phone","")
        #         #delete silence markers
        #         if "SIL" in x:
        #             x = x.replace("SIL","")
        #         if "sil" in x:
        #             x = x.replace("sil","")
        #         #there's only one item in each file now
        #         if "size = 2\n" in x:
        #             x = x.replace("2","1")
        #         #write to each file when appropriate    
        #         if "item [1]" in line:
        #             writeBoth = False
        #             writeWord = True
        #             writePhone = False
        #         if "item [2]:" in line:
        #             x = x.replace("2","1")
        #             writeBoth = False
        #             writePhone = True
        #             writeWord = False
        #         if writeBoth:
        #             word.write(x)
        #             phone.write(x)
        #         if writeWord:
        #             word.write(x)
        #         if writePhone:
        #             phone.write(x)
        #     word.close()
        #     phone.close()
            
#++++++++++++++++++++++++++++




    def clean(self):
            print "\n"
   #     '''deletes previous extraction results. do this if you have changed config settings'''
   #     cleanpath = self.options.directory 
   #     foldersToClean = ["arff","extracted","db","praatOutput","formatted", "plots"]       
   #     for location in foldersToClean:
   #         if path.lexists(cleanpath + location + "/"):
   #             rmtree(cleanpath + location + "/")
   #             
   #             
   #         else:
   #             print "error,",location,"not found and thus not cleaned."
        
    
    def createWEKAFile(self,source):
        '''makes weka filei depending on the configuration settings and the contents of the SQL database.'''
        if not self.options.quiet: print "WEKA",source
        filename = "arff/"+source + ".arff"
        
        
        bad = []

        #set global attribute setting to false
        #it'll be created properly when the header is made
        if not self.options.quiet: print "Creating WEKA Header"

        # current date and time
        now = datetime.datetime.now()

        #########################################################################
        # 11/14/2011 Serguei's changes
        # added date/time and the Unit of analysis information to the ARFF header
        #########################################################################

        #MAKE HEADER
        f = open(self.options.directory + filename + self.options.wekaname,'w')
        arffname = self.options.directory + "arff/"+filename + self.options.wekaname
        f.write("% 1. Title: Acoustic Feature Detection Output\n")
        f.write("%\n") 
        f.write("% 2. Sources:\n")
        f.write("%      (a) Created with: ProTK version "+self.options.version+"\n")
        f.write("%      (b) Date Created: "+ now.strftime("%Y/%m/%d") +"\n")
        f.write("%\n")
        f.write("% 3. The @RELATION name contains the targets (e.g., FPU,FPM) on the left \n%\t and the Unit of Analysis (uoa) on the right (e.g. word) \n")
        f.write("% \n")
        f.write("% 4. The @ATTRIBUTES below specify a set of features extracted from the audio \n%\t that correspond to the unit of analysis selected with --prosodytier option \n")
        f.write("% 5. The lines following @DATA tag contain feature values in the same order as the features listed in the @ATTRIBUTES list \n")
        f.write("% \n")
        f.write("@RELATION " + self.options.tags[0] + "_" + self.options.prosodytier + "\n\n")
        

        #get header information from first database - in the header, we just want from the current source
        sampleDB = self.fileList[0]
        self.options.connection = sqlite3.connect(self.options.directory + "db/"+sampleDB + ".db")
        self.cursor = self.options.connection.cursor()
        self.cursor.execute('pragma table_info(processed_' + self.fileList[0].replace("-",'') + "_" + source.replace("-",'') + ')')
        all_header_data = self.cursor.fetchall()
        headers_to_exclude = ['interval_number','start_time','end_time'] + self.options.tags  #++++++++++++++++++++++++++
        
        #sort headers in alphabetical order
        #won't work b/c data depends on header order to determine whether they go in the list
        #++++++++++++++++++++++++++++++++++++++++++++++++ DO SOMETHING HERE - arff files don't have proper PHONEME labels, don't list data where they're supposed to
        textHeaders = {}
        for i in all_header_data:
            if i[1] not in headers_to_exclude:
                if "REAL" in i[2]:
                    f.write("@ATTRIBUTE\t" + i[1] + "\tNUMERIC\n")
                elif "TEXT" in i[2]:
                    textList = []
                    for filename in self.fileList:
                        #go through all DB's
                        sampleDB = filename + ".db"
                        tempConnection = sqlite3.connect(self.options.directory  +"db/"+ sampleDB)
                        tempCursor = tempConnection.cursor()
                        for sourced in self.options.source:
                            tempTable = "processed_" + filename.replace("-",'') + "_" + sourced.replace("-",'')
                            tempCursor.execute('SELECT ' + i[1] + '  from ' + tempTable)
                            temp = tempCursor.fetchall()
                            for j in temp:
                                textList.append(str(j[0]))
                    textList = list(set(textList))
                    textList.sort()
                    attributeLabels = "{"
                    for j in textList:
                        attributeLabels = attributeLabels + j.replace("'","") + ", "
                    attributeLabels = attributeLabels[0:-2] + "}"
                    f.write("@ATTRIBUTE\t" + i[1] + "\t" + attributeLabels + "\n")
                    textHeaders[i[1]] = attributeLabels
                else: 
                    print "UH OH!!! one of the database entries isn't labeled as REAL or TEXT"
        #create phoneme attribute
         
        #BEFORE AND AFTER headers
        baList = self.beforeAfterList(self.options.beforeAfter)
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        #if not self.options.quiet: print self.cursor.fetchall()
        for entry in baList:
            for i in all_header_data:
                if i[1] not in headers_to_exclude:
                    if "REAL" in i[2]:
                        f.write("@ATTRIBUTE\t" + i[1] + str(entry) + "\tNUMERIC\n")
                    elif "TEXT" in i[2]:
#                         #have to look in all the results to find list of text options
                        f.write("@ATTRIBUTE\t" + i[1] + str(entry) + "\t" + textHeaders[i[1]] + "\n")
                    else: 
                        print "UH OH!!! one of the database entries isn't labeled as REAL or TEXT"  
        #TAGS              
        #to do - make it look through all the files for tags - maybe the first doesn't have all of them
        
#        for tag in [self.options.tags[0]]:     #don't need this until we have multiple tags   
        tag = self.options.tags[0]
        textList = []               
        for filename in self.fileList:                    
            sampleDB = filename + ".db"        
            tempConnection = sqlite3.connect(self.options.directory +"db/" + sampleDB)
            tempCursor = tempConnection.cursor()
            for sourced in self.options.source:    
                tempTable = "processed_" + filename.replace('-','') + "_" + sourced.replace("-",'')
                tempCursor.execute('SELECT ' + tag + '  from ' + tempTable)
                temp = tempCursor.fetchall()
                for j in temp:
                    textList.append(str(j[0]))
        textList = list(set(textList))
        textList.sort()
        attributeLabels = "{"
        for j in textList:
            attributeLabels = attributeLabels + j + ", "
        attributeLabels = attributeLabels[0:-2] + "}"
        #if not self.options.quiet: print attributeLabels
        f.write("@ATTRIBUTE\t" + tag + "\t" + attributeLabels + "\n")
        if not self.options.quiet: print "writing data",source        
        f.write("\n@DATA\n")
        f.close()
        multiWEKA(self.fileList,bad,self.options.numProcesses,self.options,all_header_data,source,headers_to_exclude,baList)        

           
               
        
            
    def beforeAfterList(self,number):                
        if number == 0:
            return []
        res = []
        for i in xrange(1,number+1):
            res.append(i*-1)
            res.append(i)
        return res
        
    
#multiprocessing functions can't be methods, because then pickling causes infinite recursion
#NO stands for non-object (obv)
def NOextract(f,options):
    try:
        if True:
            x = Unit(filename=f,options=options)
            del x    
    except Exception,msg:
        print "UNIT EXCEPTION",f,msg
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
    
def NOmulti(numProcesses,fileList,options):
    pool = Pool(processes=numProcesses)
    for f in fileList:
        try:
            a = pool.apply_async(NOextract,[f,options])
        except Exception,msg:
            print "POOL EXCEPTION",f,msg
    a.wait()
    #makes sure everything closes correctly
    pool.close()
    pool.join()
    
def multiWEKA(fileList,bad,numProcesses,options,all_header_data,source,headers_to_exclude,baList):


    import time
    t0 = time.time()
    pool = Pool(processes=numProcesses)
    for fname in fileList:     
        if fname not in bad:
            try:
                a = pool.apply_async(addToWEKA,[fileList,options,fname,all_header_data,source,headers_to_exclude,baList])#.get(99999999)
            except:
                print "EXCEPTION HERE",fname
    a.wait()
    pool.close()
    pool.join()
    if not options.quiet: print "time for extracting from database",time.time()-t0
    t0 = time.time()
    
    #add temp files to file list and delete them - this part is quick
    f = open(options.directory + "arff/"+ source + ".arff",'a')
    for fname in fileList:
        #if "UMN007_NBAT2_03" not in fname and "auto_sphinx.arff_UMN009_NBAT2_04" not in fname:
        infile = open(options.directory +"arff/"+source + ".arff" + "_" + fname,'r')
        for line in infile:
            f.write(line)
        infile.close()
        remove(options.directory + "arff/"+source + ".arff" + "_" + fname)
    f.close()
    if not options.quiet: print "time for consolidating arff files",time.time()-t0

        
def addToWEKA(fileList,options,fname,all_header_data,source,headers_to_exclude,baList):
    #this reads from main database and adds to temp files
    #you can do simultaneous READS from a database, but not writes
    f = open(options.directory + 'arff/'+ source + ".arff" + "_" + fname,'w')

    connection = sqlite3.connect(options.directory +"db/"+ fname + '.db')
    cursor = connection.cursor()

    try:
        #ROW-based options
        sampleTable = "processed_" + fname.replace('-','') + "_" + source
        cursor.execute('SELECT MAX(interval_number) from ' + sampleTable.replace('-',''))
        temp = cursor.fetchall()[0][0]
        if not options.quiet: print fname,"has",temp,"intervals"
        numRows = temp + 1
        rowText = ""
        
        #could make this faster by reading everything, THEN sorting through it
        for i in xrange(numRows):
            cursor.execute('SELECT uoa_type from ' + sampleTable.replace('-','') + ' WHERE interval_number = ' + str(i))
            data = cursor.fetchall()
            temp = str(data[0][0])
            temp = temp.replace("'","")
            import time
            #if temp in options.vowels:
            t0 = time.time()
            cursor.execute('SELECT * from ' + sampleTable.replace('-','') + ' WHERE interval_number = ' + str(i))
            data = cursor.fetchall()[0]
            t0 = time.time()
            if len(all_header_data) == len(data):
                rowText = ""
                for j in range(len(all_header_data)):
                    if all_header_data[j][1] not in headers_to_exclude:
                        data_to_add = data[j]
                        if data_to_add == None or "NULL" in str(data_to_add):
                            data_to_add = "?"
                        if type(data_to_add) == float:
                            data_to_add = str(round(data_to_add,5))
                        rowText = rowText + str(data_to_add) + ","
                #BEFORE AND AFTER DATA        
                for entry in baList:
                    rowNum = i + entry
                    cursor.execute('SELECT * from ' + sampleTable.replace('-','') + ' WHERE interval_number = ' + str(rowNum))
                    #question: what happens when there are no befores and afters?  Ehhh???  
                    x = cursor.fetchall()
                    if len(x) > 0:
                        data = x[0]
                    else:
                        temp_list = []
                        for h in all_header_data:
                            temp_list.append(None)
                            data = tuple(temp_list)
                    for k in range(len(all_header_data)):
                        if all_header_data[k][1] not in headers_to_exclude:
                            data_to_add = data[k]
                            if data_to_add == None or "NULL" in str(data_to_add):
                                data_to_add = "?"
                            if type(data_to_add) == float:
                                data_to_add = str(round(data_to_add,5))
                            rowText = rowText + str(data_to_add) + ","
 
                #for tag in options.tags:
                tag = options.tags[0]
                cursor.execute('SELECT '+ tag +' FROM ' + sampleTable.replace('-','') + ' WHERE interval_number = ' + str(i))
                zzz = cursor.fetchall()[0][0]
                if type(data_to_add) == float:
                    data_to_add = str(round(data_to_add,5))
                rowText = rowText + str(zzz)
                f.write(rowText.replace("'","") + "\n")
            else:
                print "data length",len(data),"header length",len(all_header_data),fname
            
    except Exception,msg:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        print "ERROR with file",fname
        print msg
    f.close()
    

