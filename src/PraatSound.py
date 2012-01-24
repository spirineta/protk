#given a filename,
#1) reformat data extraction output, putting output in filename_formatted/raw
#2) extract relevant info from all of that, putting it in a folder filename_FP
#3) name filled pause things like filename_FP#_origin.extension

from numpy import *
import sqlite3

##########################################
# 11/14/2011 serguei's addition - import RE
import re
########

from sys import exit
from os import path, mkdir
import os
toplot = True
try:
    from matplotlib import axis
    from matplotlib.pyplot import *
except Exception:
    print "Matplotlib not installed correctly.  Plotting will be disabled."
    toplot = False


wekaListConfig = False
wekaListAll = False

class PraatSound(object):
    
    def __init__(self,options = False,soundData = False,directory = False,headersTotal = False,filename = False,configDir = False,findFP = False,findPhones = False,\
                 phonePre = 0, phonePost = 0, FPpre=0, FPpost=0,kind = "manual",truth = "manual",loadDB = False,quiet = False,writeToFile = False):
        global plot
        global toplot
        self.options = options
        self.soundData = soundData
        self.headersTotal = headersTotal
        self.truth = truth
        self.kind = self.folder = kind
        self.filename = filename
        import time
        t0 = time.time()
        if not self.options.quiet: print "Sound-level: starting",filename,kind
        self.connection = sqlite3.connect(self.options.directory +"db/"+ self.filename + '.db')
        self.cursor = self.connection.cursor()
        self.connection("BEGIN TRANSACTION")

        try:
            #locations of textgrids --later, change all Word and Phone variables.  For now "word" means "tag" and "phone" means "prosody"
            self.autoPhoneLocation = self.options.directory + kind + "/" + self.filename + "-" + self.options.prosodytier + ".TextGrid"
            self.truthWordLocation = self.options.directory + truth + "/" + self.filename + "-" + self.options.tagtier + ".TextGrid"
            self.autoWordLocation = self.options.directory + kind + "/" + self.filename + "-" + self.options.tagtier +  ".TextGrid"
            self.formattedDir = self.options.directory + "formatted/" + self.filename + "_formatted/"
            self.passthroughLocation = self.options.directory + truth + "/" + self.filename + "-"+ self.options.passthroughtier + ".TextGrid"
            
            #populate lists of phonemes, actual words and (sphinx)-predicted words
            self.autoPhoneList = self.createIntervalList(self.autoPhoneLocation,phone=True)
            self.truthWordList = self.createIntervalList(self.truthWordLocation)
            


            #only useful for sphinx stuffg
            self.autoWordList = self.createIntervalList(self.autoWordLocation)
 
            #if it's sphinx, change phonemes to reflect filled pauses
            #this isn't for labeling, but only to change them from "SIL" to "AH"/"M"
            #if it's sphinx, all FPs will be within silences - either at the beginning, middle or end

            self.handleSphinxLabels()

            #TO-DO: expand this later to make it user-editable
            self.tagList = self.options.tags
            self.tagPhonemes()

            #do all processing for each type of praat extracted file
            #put placeholders in database
            self.tableName = 'processed_' +self.filename + '_'+ self.folder

            self.initializeTable()  
            self.addPassThroughLabels()

            for suffix in self.options.config:
             if self.options.config[suffix] == True:
                 self.processSuffixType(suffix) 



            self.connection.commit()
        except Exception,msg:
            import traceback, sys
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            self.connection.commit()
        if not self.options.quiet: print "Sound-level: finished",filename,kind, round(time.time() - t0, 3),"seconds"
        if toplot and type(self.options.graph) != type(False):
            self.plotAll()
        else:
            if not self.options.quiet:
                print "Plotting not selected, or Matplotlib not installed"
    


    def addPassThroughLabels(self):
        '''This function allows for pass-through of prosody-segment-level labels to the database and 
           subsequent ARFF file.  Labels must be in the txtgrid file, prefixed with an exclamation point !, which is 
           a comment character in Praat.  '''
        

        intervalNumber = 0
        infoList = []
        d = {}
        with open(self.passthroughLocation,'r') as sourceFile:
            reading = False
            for line in sourceFile:
                if "intervals [1]:" in line:
                    reading = True
                if reading and "intervals [" in line:
                    #print intervalNumber, d
                    #put d in the database here!!  
                    infoList.append(d)
                    intervalNumber += 1
                    d = {}
                
                #get flags
                if reading and "!" in line:
                    #gets the lable title
                    temp = line[:]
                    title = temp[temp.find('!')+1:temp.find('=')].strip()
                    #gets the lable value
                    label = temp[temp.find('=')+1:].strip().strip('"')
                    d[title] = label

                    
                #if necessary, get xmin/xmax
                if "xmin" in line:
                    s = line[:]
                    s = s.split()
                    d['xmin'] = float(s[2])
                if "xmax" in line:
                    s = line[:]
                    s = s.split()
                    d['xmax'] = float(s[2])
        #print infoList


        ##add to database

        #add columns
        example = infoList[0]
        for key in d:
            if 'xmin' not in key and 'xmax' not in key:
                #add column here
                try:
                    self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + key  + ' TEXT') #why it adds at end?
                except sqlite3.OperationalError,msg:
                    pass    
        #add entries
        counter = -1
        for interval in self.autoPhoneList:
            entered = False
            counter += 1
            middle = (interval[1] + interval[2])/2
            for entry in infoList:
                
                if entry['xmin'] <= middle <= entry['xmax'] and len(entry) > 2:
                    
                    try:  
                        command = 'UPDATE ' + self.tableName.replace('-','')  + \
                        ' SET ' 
                        for e in entry:
                            if 'xmin' not in e and 'xmax' not in e:
                                command = command + e + ' = ' + "'" + entry[e] + "'" + ","
                        command = command[:-1] #take out last comma
                        command += ' WHERE interval_number = ' + str(counter)
                        
                        self.cursor.execute(command)
                        entered = True

                    except Exception,msg:
                        print "ERROR!! in PraatSound.addPassThroughLabels",msg
                    #print entry 
                    #print command
                    break
            # if entered == False:
            #     print interval



                    
    def findSurroundingSilenceDuration(self,phoneIndex,phone,surroundingLength):
        #actually finds the ratio of how much of the "surroundingLength" is a silence
        #first, go to the left until either time-dt is in the duration or it's 0
        #then, go right, adding from that time to the end of the phoneme, 
        #then add the full silence phoneme
        #UNLESS it's between the durations, in which case just add the first plart
        begin = phone[1]
        end = phone[2]
        #find beginning
        tempPhoneIndex = phoneIndex
        silenceTime = 0
        
        beginTime = max(0,begin-surroundingLength) #time to start counting from
        endTime = min(self.autoPhoneList[-1][2],end+surroundingLength) #set final time
        
        #find index with beginTime
        while tempPhoneIndex > 0 and not (self.autoPhoneList[tempPhoneIndex][1] <= beginTime <= self.autoPhoneList[tempPhoneIndex][2]):
            tempPhoneIndex -= 1
        beginIndex = tempPhoneIndex
        tempPhoneIndex = phoneIndex
        
        #find index with end time
        while tempPhoneIndex < len(self.autoPhoneList)-1 and not (self.autoPhoneList[tempPhoneIndex][1] <= endTime <= self.autoPhoneList[tempPhoneIndex][2]):
            tempPhoneIndex += 1
        endIndex = tempPhoneIndex
       
        
        #if those are silences, add the portions
        if self.autoPhoneList[beginIndex][0] == '':
            silenceTime += abs(self.autoPhoneList[beginIndex][2] - beginTime)
        if self.autoPhoneList[endIndex][0] == '':
            silenceTime += abs(self.autoPhoneList[endIndex][1] - endTime)
        #add portions of anything inbetween
        for i in xrange(beginIndex+1,endIndex):
            if i != phoneIndex and self.autoPhoneList[i][0] == '':
               silenceTime += self.autoPhoneList[i][2] - self.autoPhoneList[i][1]
        
        return silenceTime/(surroundingLength*2.0)
        
    
    def handleSphinxLabels(self):
        
        if "sphinx" in self.kind.lower():
            for word in self.autoWordList:
                if self.options.tags[0] in word[0]:
                    fpBegin = word[1]
                    fpEnd = word[2]
                    fpMiddle = (fpBegin+fpEnd)/2
                    fpLength = fpEnd-fpBegin
                    phoneListLocation = -1
                    for phone in self.autoPhoneList:
                        phoneListLocation += 1
                        #butts up against the edge
                        if phone[0] == '' and phone[1] <= fpMiddle <= phone[2]:
                            if phone[1] == fpBegin:
                                if "_UM" in word[0]:
                                    fpType = 'UM'
                                    newphone_AH = ['AH',phone[1], phone[1]+2.0/3.0*fpLength]
                                    newphone_M = ['M',phone[1]+2.0/3.0*fpLength,fpEnd]
                                    newphone_SIL = ['',fpEnd ,phone[2]]
                                    newList = [newphone_AH,newphone_M,newphone_SIL]
                                    del self.autoPhoneList[phoneListLocation]
                                    #insert new ones
                                    counter = 0
                                    for entry in newList:
                                        self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                        counter += 1
                                elif "_AH" in word[0]:
                                    fpType = 'AH'
                                    newphone_AH = ['AH',phone[1], fpEnd]
                                    newphone_SIL = ['',fpEnd ,phone[2]]
                                    newList = [newphone_AH,newphone_SIL]
                                    del self.autoPhoneList[phoneListLocation]
                                    #insert new ones
                                    counter = 0
                                    for entry in newList:
                                        self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                        counter += 1
                                else:
                                    print "ERROR 1"
                                    print word
                            elif phone[2] == fpEnd:
                                if "_UM" in word[0]:
                                    fpType = 'UM'
                                    newphone_SIL = ['',phone[1] ,fpBegin]
                                    newphone_AH = ['AH',fpBegin, fpBegin+2.0/3.0*fpLength]
                                    newphone_M = ['M',fpBegin+2.0/3.0*fpLength,fpEnd]
                                    newList = [newphone_SIL,newphone_AH,newphone_M]
                                    del self.autoPhoneList[phoneListLocation]
                                    #insert new ones
                                    counter = 0
                                    for entry in newList:
                                        self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                        counter += 1
                                elif "_AH" in word[0]:
                                    fpType = 'AH'
                                    newphone_SIL = ['',phone[1] ,fpBegin]
                                    newphone_AH = ['AH',fpBegin, fpEnd]
                                    newList = [newphone_SIL,newphone_AH]
                                    del self.autoPhoneList[phoneListLocation]
                                    #insert new ones
                                    counter = 0
                                    for entry in newList:
                                        self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                        counter += 1
                                else:
                                    print "ERROR 2"
                            elif phone[1] < fpBegin and phone[2] > fpEnd:
                                if '_UM' in word[0]:
                                   newphone_SIL1 = ['',phone[1],fpBegin]
                                   newphone_AH = ['AH',fpBegin,fpBegin+2.0/3.0*fpLength]
                                   newphone_M =  ['M', fpBegin + 2.0/3.0*fpLength,fpEnd]
                                   newphone_SIL2 = ['',fpEnd,phone[2]]
                                   newList = [newphone_SIL1,newphone_AH,newphone_M,newphone_SIL2]
                                   del self.autoPhoneList[phoneListLocation]
                                   #insert new ones
                                   counter = 0
                                   for entry in newList:
                                       self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                       counter += 1
                                elif '_AH' in word[0]:
                                   newphone_SIL1 = ['',phone[1],fpBegin]
                                   newphone_AH = ['AH',fpBegin,fpEnd]
                                   newphone_SIL2 = ['',fpEnd,phone[2]]
                                   newList = [newphone_SIL1,newphone_AH,newphone_SIL2]
                                   del self.autoPhoneList[phoneListLocation]
                                   #insert new ones
                                   counter = 0
                                   for entry in newList:
                                       self.autoPhoneList.insert(phoneListLocation + counter,entry)
                                       counter += 1
                                else:
                                    print "ERROR 3"        
                                
                            else:
                                print "ERROR"
                                raw_input()

        
        
    def initializeTable(self):
        
        self.addTableHeader('duration')
        self.addTableHeader('normalizedDuration')
        self.addTableHeader('silenceDistance')
        self.addTableHeader('silenceDuration')
        self.addTableHeader('silenceDurationNormalized')
        self.addTableHeader('silenceOneSecondSurrounding')
        self.addTableHeader('silenceTwoSecondsSurrounding')
        self.addTableHeader('silenceThreeSecondsSurrounding')
        self.addTableHeader('silenceTenSecondsSurrounding')


        #put headers into database
        #todo-  make this shorter
        for headerType in self.headersTotal:
            #add a new column if necessary
            if self.options.config[headerType]:
                if "shimmer" in headerType.lower() or "jitter" in headerType.lower():
                    startCol = 2
                else: 
                    startCol = 1
                for header in self.headersTotal[headerType][startCol:]:
                    #if columns don't exist, add them
                    try:
                        self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + headerType[1:] + '_' + header.replace('/','') + '_mean REAL' )
                    except sqlite3.OperationalError,msg:
                        pass
                    except:
                        print msg
                        print "header add exception",self.filename
                    try:
                        self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + headerType[1:] + '_' + header.replace('/','') + '_SD REAL')
                    except sqlite3.OperationalError,msg:
                        pass
                    except:
                        print "header add exception",self.filename
                    try:
                        self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + headerType[1:] + '_' + header.replace('/','') + '_meanNorm REAL')
                    except sqlite3.OperationalError,msg:
                        pass
                    try:
                        self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + headerType[1:] + '_' + header.replace('/','') + '_sdNorm REAL')
                    except sqlite3.OperationalError,msg:
                        pass
                    try:
                        self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + \
                        ' add ' + headerType[1:] + '_' + header.replace('/','') + '_slopeNorm REAL')
                    except sqlite3.OperationalError,msg:
                        pass
        #put in placeholders for each phone
        phoneIndex = 0
        for phone in self.autoPhoneList:
            #print phone
            FP = phone[3][self.options.tags[0]]
            if FP: FP = 1
            else: FP = 0
            p = phone[0]
            if len(p) == 0: p = 'SIL'
            p = '\'' + p + '\''
            keys = ' (interval_number, start_time, end_time, uoa_type, ' + self.options.tags[0] + ')'
            values = ' VALUES ('+str(phoneIndex) + ','+str(phone[1])+','+str(phone[2])+','+p+',' + str(FP)+')'
            try:
                self.cursor.execute('REPLACE INTO ' + self.tableName.replace('-','') + keys +values)
            except Exception, msg:
                print "ERROR!! in PraatSound.initializeTable()",self.filename,phone
            phoneIndex += 1                 
        

    def processSuffixType(self,suffix):
        #load data
        source = self.formattedDir + self.filename + suffix
        try:
            keepGoing = True
            suffixDataArray = loadtxt(source,skiprows=1)
        except IOError:
            keepGoing = False
            print "error,",self.filename," could not be opened. Skipping."
        
        if keepGoing:
            #if formant, add ratios
            if "formant" in suffix.lower():
                suffixDataArray = self.addFormantRatios(suffixDataArray)
            
            #find means, standard deviations for normalizaiton
            if "silence" not in suffix.lower():
                vowelNormalizationData = self.normalize(suffix,suffixDataArray)
            #process, enter into database
                
                phoneIndex = 0
                for phone in self.autoPhoneList:
                    self.addPhoneToDatabase(phoneIndex,phone,suffix,suffixDataArray,vowelNormalizationData)
                    phoneIndex += 1
                
    def addPhoneToDatabase(self,phoneIndex,phone,suffix,suffixDataArray,vowelNormalizationData):
        seterr(all='ignore')
        #get info for that phone
        if "pointprocess" in suffix.lower() or "pitch" in suffix.lower():
            (index1,index2) = self.findIndicesPointProcess(suffixDataArray,phone)
        else:
            (index1,index2) = self.findIndicesNormal(suffixDataArray,phone)
        indices = arange(index1,index2+1)
        chunk = suffixDataArray[indices,:]

        #get rid of null-values, if any
        for i in self.options.nullValues:
            if i[0] in suffix:
                nullValue = i[1]
                nullBeginCol = i[2]
                nullEndCol = i[3]
        chunkLength = chunk.shape[1]
        if nullValue:
            chunk = chunk[list(nonzero(chunk[:,nullBeginCol] > nullValue)[0]),:]
        
        
        ################write to file here
        beginMS = str(int(phone[1]*1000))
        endMS = str(int(phone[2]*1000))

        ##########################################
        # 11/14/2011 serguei's change to phone[0]
        # some of the tiers may contain labels that
        # cannot be part of a file name - let's filter those

        segmentlabel = phone[0]
        p = re.compile('[\<\>\?\/\\\,\.\]\[\}\{\~\@\#\$\%\^\&\*\(\)\"\'\:\;]')
        segmentlabel = p.sub("",segmentlabel)

       
        soundType = suffix
        if suffix == '':
            suffix = 'SIL'
        destination = self.options.directory + "extracted/"+ self.kind + "/"   + beginMS + "ms_"  + endMS +"ms_" + segmentlabel  + soundType

         ##########################################

        
        ### is it possible to speed this up by pre-collecting information to be written?
        if self.options.writeToFile:
            try:
                outFile = open(destination,'w')
                #write headers to file
                for header in self.headersTotal[suffix]:
                    outFile.write(header + "\t")
                outFile.write("\n")

                #write data to file
                for line in chunk:
                    for entry in line[:-1]:
                        outFile.write(str(entry) + "\t")
                    outFile.write(str(line[-1]) + "\n")
                outFile.close()
            except IOError, msg:
                print "can't write tabulated results for some reason. Skipping."
                print msg
                self.options.writeToFile = False
                pass
        

        
        if "shimmer" in suffix.lower() or "jitter" in suffix.lower():
            startCol = 2
        else: 
            startCol = 1
        #if chunk isn't zero-length, find mean, sd of them:
        if chunk.shape[0] > 0:
            #find mean, sd column-wise
            means = mean(chunk[:,startCol:],axis=0)
            sds = std(chunk[:,startCol:],axis=0)
            #find normalized mean, sd column-wise
            meansNorm = (means - vowelNormalizationData[:,0])/vowelNormalizationData[:,1]
            #doesn't make sense to normalize the standard deviation
            #so normalize, then take sd of that
            temp = (chunk[:,startCol:] - vowelNormalizationData[:,0])/vowelNormalizationData[:,1]
            sdsNorm = std(temp,axis=0)
            #take slope of normalized values (i.e. how many z-values do they change over the interval?)
            if size(temp) > 1 and abs(temp[-1,0]-temp[0,0]) > 0:
                   slopeNorm = (temp[-1,:] - temp[0,:])/(temp[-1,0]-temp[0,0])
            else: 
                slopeNorm = zeros((temp.shape[1],))
                slopeNorm.fill(nan)
                # slopeNorm
        
            normalizationColumn = 0
            for header in self.headersTotal[suffix][startCol:]:
                meanHeader = suffix[1:] + '_' + header.replace('/','') + '_mean'
                sdHeader = suffix[1:] + '_' + header.replace('/','') + '_SD'
                meanNormHeader = suffix[1:] + '_' + header.replace('/','') + '_meanNorm'
                sdsNormHeader = suffix[1:] + '_' + header.replace('/','') + '_sdNorm'
                slopeNormHeader = suffix[1:] + '_' + header.replace('/','') + '_slopeNorm'
                
                #remove 'nan' and 'inf' values
                meanHeaderValue = str(means[normalizationColumn])
                if "inf" in meanHeaderValue or "nan" in meanHeaderValue:meanHeaderValue = 'Null'
                sdHeaderValue = str(sds[normalizationColumn])
                if "inf" in sdHeaderValue or "nan" in sdHeaderValue:sdHeaderValue = 'Null'
                meanNormHeaderValue = str(meansNorm[normalizationColumn])
                if "inf" in meanNormHeaderValue or "nan" in meanNormHeaderValue: meanNormHeaderValue = 'Null'
                sdsNormHeaderValue = str(sdsNorm[normalizationColumn])
                if "inf" in sdsNormHeaderValue or "nan" in sdsNormHeaderValue: sdsNormHeaderValue = 'Null'
                slopeNormHeaderValue = str(slopeNorm[normalizationColumn])
                if slopeNormHeaderValue == "nan" or "inf" in slopeNormHeaderValue: slopeNormHeaderValue = 'Null'
                
                self.cursor.execute('UPDATE ' + self.tableName.replace('-','') + \
                ' SET ' + \
                    meanHeader + ' = ' + meanHeaderValue + "," + \
                    sdHeader + ' = ' + sdHeaderValue + "," + \
                    meanNormHeader + ' = ' + meanNormHeaderValue + "," + \
                    sdsNormHeader + ' = ' + sdsNormHeaderValue + "," + \
                    slopeNormHeader + ' = ' + slopeNormHeaderValue + \
                ' WHERE interval_number = ' + str(phoneIndex)
                )
                normalizationColumn += 1
        else:
            #apparently chunks are nonexistent
            normalizationColumn = 0
            for header in self.headersTotal[suffix][startCol:]:
                    meanHeader = suffix[1:] + '_' + header.replace('/','') + '_mean'
                    sdHeader = suffix[1:] + '_' + header.replace('/','') + '_SD'
                    meanNormHeader = suffix[1:] + '_' + header.replace('/','') + '_meanNorm'
                    sdsNormHeader = suffix[1:] + '_' + header.replace('/','') + '_sdNorm'
                    slopeNormHeader = suffix[1:] + '_' + header.replace('/','') + '_slopeNorm'
                    
                    self.cursor.execute('UPDATE ' + self.tableName.replace('-','') + \
                    ' SET ' + \
                        meanHeader + ' = ' + 'Null' + "," + \
                        sdHeader + ' = ' + 'Null' + "," + \
                        meanNormHeader + ' = ' + 'Null' + ',' + \
                        sdsNormHeader +  ' = ' + 'Null' + ',' + \
                        slopeNormHeader +  ' = ' + 'Null' + \
                    ' WHERE interval_number = ' + str(phoneIndex)
                    )
        
            
        #ADD NON-PROSODIC INFORMATION
        #duration
        duration = phone[2] - phone[1]
        #duration normalized
        durations = zeros((1,len(self.autoPhoneList)))
        loc = 0
        for i in self.autoPhoneList:
            if "SIL" not in i[0]:
                durations[0,loc] = i[2] - i[1]
                loc += 1
        normalizedDuration = (duration - mean(durations))/std(durations)
        
        self.addEntryToTable(duration,'duration',phoneIndex)
        self.addEntryToTable(normalizedDuration,'normalizedDuration',phoneIndex)
        




        temp = self.findClosestSilence(phone,phoneIndex)
        if temp == 0:
            silenceDistance, silenceDuration = 'nan', duration
        else:
            try:
                silenceDistance, silenceDuration = temp[0], temp[1]
            except TypeError:  #WHY DOES THIS HAPPEN????
                print 'HALP, closestSilenceProblem'
                print temp





        self.addEntryToTable(silenceDistance,'silenceDistance',phoneIndex) 
        self.addEntryToTable(silenceDuration,'silenceDuration',phoneIndex)
        silenceDurationNormalized = (silenceDuration - mean(durations))/std(durations)
        self.addEntryToTable(silenceDurationNormalized,'silenceDurationNormalized',phoneIndex)

        #surrounding silence rating
        #what portion of the 2 secs before and 2 secs after are silence
        oneSecondSurrounding = self.findSurroundingSilenceDuration(phoneIndex,phone,1)
        self.addEntryToTable(oneSecondSurrounding,'silenceOneSecondSurrounding',phoneIndex)
        twoSecondsSurrounding = self.findSurroundingSilenceDuration(phoneIndex,phone,2)
        self.addEntryToTable(twoSecondsSurrounding,'silenceTwoSecondsSurrounding',phoneIndex)
        threeSecondsSurrounding = self.findSurroundingSilenceDuration(phoneIndex,phone,3)
        self.addEntryToTable(threeSecondsSurrounding,'silenceThreeSecondsSurrounding',phoneIndex)
        tenSecondsSurrounding = self.findSurroundingSilenceDuration(phoneIndex,phone,10)
        self.addEntryToTable(tenSecondsSurrounding,'silenceThreeSecondsSurrounding',phoneIndex)



    def findClosestSilence(self,entry,location):
        beginTime = entry[1]
        endTime = entry[2]
        silenceBefore = silenceAfter = None
        #look before
        position = location - 1 

        if entry[0] == '':
            return 0

        while position >= 0 and position < len(self.autoPhoneList):
            if self.autoPhoneList[position][0] == '':
                silenceBefore = beginTime - self.autoPhoneList[position][2]
                silenceBeforeDuration = self.autoPhoneList[position][2] - self.autoPhoneList[position][1]
                break
            position -= 1

        position = location + 1

        while position < len(self.autoPhoneList):
            if self.autoPhoneList[position][0] == '':
                #print "FOUND",self.autoPhoneList[position]
                silenceAfter = self.autoPhoneList[position][1] - endTime
                silenceAfterDuration = self.autoPhoneList[position][2] - self.autoPhoneList[position][1]
                break
            position += 1

       #print silenceBefore, silenceAfter


        if silenceAfter == None and silenceBefore == None:
            return (nan, nan)
        elif silenceAfter == None:
            return (silenceBefore,silenceBeforeDuration)
        elif silenceBefore == None:
            return (silenceAfter,silenceAfterDuration)
        elif silenceBefore < silenceAfter:
            return (silenceBefore,silenceBeforeDuration)
        else:
            return (silenceAfter,silenceAfterDuration)
    



        
    def addEntryToTable(self,thingToEnter,columnHeader,rowNumber):
        if thingToEnter == 'nan' or isnan(thingToEnter):
            thingToEnter = 'Null'

        try:
            self.cursor.execute('UPDATE ' + self.tableName.replace('-','') + \
                ' SET ' + \
                    columnHeader + ' = ' + str(thingToEnter) + \
                ' WHERE interval_number = ' + str(rowNumber)
                )
        except Exception, msg:
            print "error entering into database"
            print msg
        
    
    def addTableHeader(self,headerToAdd,dataType = "REAL"):
 
        try:
            self.cursor.execute('ALTER TABLE ' + self.tableName.replace('-','') + ' add ' + headerToAdd + " " + dataType)
        except sqlite3.OperationalError,msg:
            pass
        except Exception,msg:
            print msg
            print "Header add exception"
        

    
    def addFormantRatios(self,suffixDataArray):
        dataToAdd = zeros((suffixDataArray.shape[0],4))
        dataToAdd[:,0] = suffixDataArray[:,4]/suffixDataArray[:,2]
        dataToAdd[:,1] = suffixDataArray[:,6]/suffixDataArray[:,4]
        dataToAdd[:,2] = suffixDataArray[:,8]/suffixDataArray[:,6]
        dataToAdd[:,3] = suffixDataArray[:,10]/suffixDataArray[:,8]
        suffixDataArray = column_stack((suffixDataArray,dataToAdd))
        del dataToAdd
        return suffixDataArray
    
    def normalize(self,suffix,suffixDataArray):
        '''puts mean and standard deviation for information into the database based on whether the phones are in the testList'''
        prenormdata = zeros((len(suffixDataArray[:,0]),len(suffixDataArray[0,:])))
        prenormdatarow = 0
        for phone in self.autoPhoneList: #
            if "pointprocess" in suffix.lower() or "pitch" in suffix.lower():
                (index1,index2) = self.findIndicesPointProcess(suffixDataArray,phone)
            else:
                (index1,index2) = self.findIndicesNormal(suffixDataArray,phone)
            indices = arange(index1,index2+1)
            #index1 is clearly off
            try:
                prenormdata[prenormdatarow:prenormdatarow+len(indices),:] = suffixDataArray[indices,:]
                prenormdatarow += len(indices)                        
            except ValueError, msg:
                #in the case that the len(indices) isn't the number of indices in the length (for a reason that I don't understand)
                try:
                    prenormdata[prenormdatarow:prenormdatarow+len(indices),:] = suffixDataArray[indices[:-1],:]
                    prenormdatarow += len(indices) 
                except Exception, msg:
                    pass 
                    #BUG - this means that the indices apparently aren't correct, but I don't know why
                    #the number of indices in "indices" would be different than len(indices)
                    
        #get rid of null-values, if any
        for i in self.options.nullValues:
            if i[0] in suffix:    
                nullValue = i[1]
                nullBeginCol = i[2]
                nullEndCol = i[3]

        if nullValue:
            prenormdata = prenormdata[list(nonzero(prenormdata[:,nullBeginCol] > nullValue)[0]),:]
        
        #get rid of rows that only have zeros
        prenormdata = prenormdata[0:prenormdatarow,:]
        
        #if shimmer, jitter don't do first 2 columns
        if "shimmer" in suffix.lower() or "jitter" in suffix.lower():
            colsNotToNormalize = 2
        else: 
            colsNotToNormalize = 1
            
        #find means and standard deviations, put them in array like [mean, sd]   
        cols = arange(colsNotToNormalize,prenormdata.shape[1])
        normalizationData = zeros((len(cols),2))
        ndRow = 0

        for col in cols:

            try:
                mu = mean(prenormdata[:,col])
                sigma = std(prenormdata[:,col])
                normalizationData[ndRow,:] = array([mu,sigma])
                ndRow += 1
            except FloatingPointError:
                pass#return [] #perhaps should return [nan]???    
        
        return normalizationData
       
    def findIndicesNormal(self,suffixDataArray,phone):

        #use linear approximation
        diff = (suffixDataArray[9,0] - suffixDataArray[0,0])/10
        b = suffixDataArray[0,0]
        index1 = int((phone[1] - b)/diff)
        if index1 < 0:
            index1 = 0
        if index1 > suffixDataArray.shape[0]-1:
            index1 = suffixDataArray.shape[0]-1
        index2 = int((phone[2] - b)/diff)
        if index2 < 0:
            index2 = 0
        if index2 > suffixDataArray.shape[0] - 1:
            index2 = suffixDataArray.shape[0] - 1
        #close - now narrow down
        #for t1, you want the time to be the first one greater than or equal to phone[1]
        #if less than, move UP in indices (in a positive way), so use phone[1] - time
        #if more than, move DOWN in indices
        #use sign = (phone[1] - time)/abs(phone[1]-time)
        if phone == self.autoPhoneList[0]:
            index1 = 0
#            print "hi"
        elif phone == self.autoPhoneList[-1]:
            index1 = suffixDataArray.shape[0]-1
#            print "bye"
#            print 
        else:
        #t1
            time = suffixDataArray[index1,0]
            if abs(phone[1] - time) > 0:
                sign = (phone[1] - time)/abs(phone[1]-time)
            else:
                sign = 0
            if sign > 0:
                #you're too low, so move up until you're higher
                while index1 < suffixDataArray.shape[0] - 1 and suffixDataArray[index1,0] < phone[1]:
                    index1 += 1
            elif sign < 0: 
                while index1 > 0 and suffixDataArray[index1,0] > phone[1]:
                    #error is here:
                    index1 -= 1
                #bump up one
                index1 += 1
            else:
                pass
        
        if phone == self.autoPhoneList[-1]:
            index2 = suffixDataArray.shape[0]-1
        else:
            #t2
            if index2 >= suffixDataArray.shape[0]-1: index2 = suffixDataArray.shape[0]-1
            time = suffixDataArray[index2,0]
            if abs(phone[2]-time) > 0:
                sign = (phone[2] - time)/abs(phone[2]-time)
            else:
                sign = 0
            if sign > 0:
                #you're too low, so move up until you're higher
                while index2 < suffixDataArray.shape[0]-1 and suffixDataArray[index2,0] < phone[2]:
                    index2 += 1
                #bump down one
                index2 -= 1
            elif sign < 0: 
                while index2 > 0 and suffixDataArray[index2,0] > phone[2]:
                    index2 -= 1
            else:
                pass
        

        if phone[1] == phone[2]:
            return (index1, index1)  
        #oh i see, they were swapping b/c the bottom went one over the max and the top went one under the min. 
        #when it was just one number, they swapped
        if index1 > index2:
            index2,index1 = index1,index2
        return (index1,index2)


        
    def findIndicesPointProcess(self,suffixDataArray,phone):
        seterr(all='ignore')
        #do binary search to find a good guess
        #index1
        minRow = 0
        maxRow = suffixDataArray.shape[0]
        lastmid = 0
        mid = (minRow+maxRow)/2
        while abs(minRow - maxRow) > 4 and not (minRow > maxRow):
            mid = (minRow+maxRow)/2
            if phone[1] > suffixDataArray[mid,0]:
                minRow = mid + 1
            else:
                maxRow = mid - 1
        index1 = mid

        #index 2
        minRow = 0
        maxRow = suffixDataArray.shape[0]
        lastmid = 0
        mid = (minRow+maxRow)/2
        while abs(minRow-maxRow) > 4:# and not (minRow > maxRow):
            lastmid = mid
            mid = (minRow+maxRow)/2
            if phone[2] > suffixDataArray[mid,0]:
                minRow = mid + 1;
            else:
                maxRow = mid - 1;
        index2 = mid
                
        #close - now narrow down
        if phone == self.autoPhoneList[0]:
            index1 = 0
        else:
        #t1
            time = suffixDataArray[index1,0]
            sign = (phone[1] - time)/abs(phone[1]-time)
            if sign > 0:
                #you're too low, so move up until you're higher
                while index1 < suffixDataArray.shape[0] and suffixDataArray[index1,0] < phone[1]:
                    index1 += 1
            elif sign < 0: 
                while index1 > 0 and suffixDataArray[index1,0] > phone[1]:
                    index1 -= 1
                #bump up one
                index1 += 1
        
        if phone == self.autoPhoneList[-1]:
            index2 = suffixDataArray.shape[0]-1
        else:
            #t2
            time = suffixDataArray[index2,0]
            sign = (phone[2] - time)/abs(phone[2]-time)
            if sign > 0:
                #you're too low, so move up until you're higher
                while index2 < suffixDataArray.shape[0] and suffixDataArray[index2,0] < phone[2]:
                    index2 += 1
                #bump down one
                index2 -= 1
            elif sign < 0: 
                while index2 > 0 and suffixDataArray[index2,0] > phone[2]:
                    index2 -= 1

        return (index1,index2)


    def createIntervalList(self,intervalLocation,phone=False):
        '''creates a filled pause object for every interval of that type in the -phone.TextGrid file
        Entries look like:
        ['phonetype',t.begin,t.end,object associated w/interval (if it exists), boolean value telling whether it occurs
        during a filled pause or not (i.e. True/False)]
        It doesn't need to be saved/pickled since it's generated when the object is initialized.
        '''
            
        # if not self.options.quiet: print "Updating list of intervals..."
        intervalList = []
        
        f = open(intervalLocation,'r')
        xmin, xmax, name = False, False, False
        for i in xrange(14): f.next()
        for line in f:
            s = line.split()
            if len(s) > 2:
                if "xmin" in s:
                    xmin = float(s[2])
                if "xmax" in s:
                    xmax = float(s[2])
                if "text" in s[0]:
                    name = s[2][1:-1]
                    entry = [name.replace("'",""), xmin, xmax]
                    intervalList.append(entry)
                    xmin = False
                    xmax = False
                    name = False
        f.close()

        #if the time-list comes from sphinx in the MS-by-MS format, this changes it to normal format
        if phone == True:
            temp = []
            name = intervalList[0][0]
            min_time = intervalList[0][1]
            for i in xrange(1,len(intervalList)):
                if intervalList[i][0] != intervalList[i-1][0]:
                    max_time = intervalList[i-1][2]
                    temp.append([intervalList[i-1][0],min_time,max_time])
                    min_time = intervalList[i][1]
            temp.append([intervalList[-1][0],min_time,intervalList[-1][2]])
            intervalList = temp
        
        return intervalList
        
    def tagPhonemes(self):
        '''uses list of manual/semi words to tag automatically detected phonemes with things like filled pause, repetition, false start, whatever'''
        
        #create space for tag list
        for entry in xrange(len(self.autoPhoneList)):
            self.autoPhoneList[entry].append({})

        #find filled pauses
        #make a filled-pause entry for the tag
        for entry in xrange(len(self.autoPhoneList)):
            self.autoPhoneList[entry][3][self.options.tags[0]] = False
        #set filled pause entry to true if its center occurs during a filled pause
        for entry in self.truthWordList:
            tagTrue = False
            for tag in self.options.tags: 
                if tag in entry[0]:
                    tagTrue = True
            if tagTrue:
                fpBegin = entry[1]
                fpEnd = entry[2]
                fpMiddle = (fpBegin + fpEnd) / 2      
        
        #finds the center of the filled pause and tags the phoneme that occurs concurrently
                for entry in xrange(len(self.autoPhoneList)):
                    if fpMiddle <= self.autoPhoneList[entry][2] and fpMiddle >= self.autoPhoneList[entry][1]:
                        self.autoPhoneList[entry][3][self.options.tags[0]] = True
        ########
        #find everything else (LATER)
    
    def getNormalizationInfo(self):
        #go through each file
        pass


    
        
    def processPhonemes(self):
        #make a table for this in the database
        pass
        


#################### Plotting functions ###################
#if plotting is selected as an option, go through each filled pause in the TRUTH file, plot it and the surrounding region.  
    
    def plotAll(self,normalized = True, toFile = True):
        #make directory for results
        print "Making plots..."
        if not os.path.isdir(self.options.directory + "plots/"):
            mkdir(self.options.directory + "plots/")
        
        #get list of filled pauses
        self.FPList = []
        for i in self.truthWordList:
            if self.options.tags[0].lower() in i[0].lower():
                self.FPList.append(i)
        
        try:
            self.plotFormants()
        except Exception, msg:
            print msg
        try:
            self.plotShimmer()
        except Exception, msg:
            print msg
        try:
            self.plotJitter()
        except Exception, msg:
            print msg
        try:
            self.plotHarmonicity()
        except Exception, msg:
            print msg
        try:
            self.plotPointProcess()
        except Exception, msg:
            print msg
        try:
            self.plotPitchIntensity()
        except Exception, msg:
            print "PLOT ERROR"
            print msg
        for name in [".LPCac_RW", ".LPCBurg_RW",".LPCCovariance_RW",".LPCMarple_RW"]:
            try:
                self.plotLPC(name)
            except Exception, msg:
                print "PLOT ERROR"
                print msg
        try:
            self.plotMFCC()
        except Exception, msg:
            print "PLOT ERROR"
            print msg

    def plotFormants(self):
        
        suffix = ".FormantBurg_RW"
        nameList = ["time","intensity","f1freq","f2freq","f3freq","f4freq"]
        y_label = "Frequency (Hz)"
        miny = 0
        maxy = 6000
        appendage = ""
        if self.options.config[suffix]: self.makeFormantTables(suffix,nameList,y_label, miny, maxy, appendage)
        
    #can't do formant ratios yet, b/c ratios aren't calculated in the formatted bit. Have to make new function.    
    def plotFormantRatios(self):
        suffix = ".FormantBurg_RW"
        nameList = ["time","f2/f1","f3/f2","f4/f3","f5/f4"]
        y_label = "Ratio"
        miny = -1
        maxy = 8
        appendage = "_ratios"
        if self.options.config[suffix]:self.makeFormantTables(suffix,nameList,y_label,miny,maxy, appendage)
        
    def plotShimmer(self):
        suffixes = [".ShimmerLocal_RW",".ShimmerAPQ3_RW",".ShimmerAPQ5_RW",".ShimmerAPQ11_RW",".ShimmerAPQ3_RW",".ShimmerLocalDB_RW"]
        
        y_label = "Value"
        miny = -5
        maxy = 5
        if self.options.config[suffixes[0]]:self.makeTables(suffixes,y_label,miny,maxy)
    
    def plotJitter(self):
        suffixes = [".JitterDDP_RW",".JitterRap_RW",".JitterLocal_RW",".JitterLocalAbsolute_RW",".JitterPPQ5_RW"]
        y_label = "Value"
        miny = -5
        maxy = 5
        if self.options.config[suffixes[0]]:self.makeTables(suffixes,y_label,miny,maxy)
        

        
    def plotHarmonicity(self):
        suffixes = [".HarmonicityCC_RW",".HarmonicityAC_RW"]
        y_label = "Value"
        miny = -5
        maxy = 5
        if self.options.config[suffixes[0]]:self.makeTables(suffixes,y_label,miny,maxy)
        
    def plotPointProcess(self):
        
        suffixes = [".PointProcessCC_RW",".PointProcessExtrema_RW",".PointProcessPeaks_RW",".PointProcessZeros_RW"]
        y_label = "dt"
        miny = 0
        maxy = 6000
        if self.options.config[suffixes[0]]:self.makeTables(suffixes,y_label,miny,maxy)
        
        
    def plotPitchIntensity(self):
        suffixes = [".Pitch_RW",".PitchSHS_RW",".PitchAC_RW",".PitchCC_RW",".Intensity_RW"]
        y_label = "Value"
        miny = 0
        maxy = 6000
        if self.options.config[suffixes[0]]:self.makeTables(suffixes,y_label,miny,maxy)
        
    def plotLPC(self, suffix, findMinMax = False):

        nameList = ["time","coef1","coef2","coef3","coef4","coef5","coef6","coef7",\
                                       "coef8","coef9","coef10","coef11","coef12","coef13","coef14","coef15","coef16","gain"]
        y_label = "Value"
        miny = -5
        maxy = 5
        if self.options.config[suffix]:self.makeLPCTables(suffix,nameList,y_label,miny,maxy, '', findMinMax)
        
    def plotMFCC(self, findMinMax = True):
        suffix = ".MFCC_RW"
        nameList = ["time","coef0","coef1","coef2","coef3","coef4","coef5","coef6","coef7",\
                                       "coef8","coef9","coef10","coef11","coef12"]
        y_label = "Value"
        miny = -5
        maxy = 5
        if self.options.config[suffix]: self.makeLPCTables(suffix,nameList,y_label,miny,maxy, '', findMinMax)
        
            
    def makeTables(self,suffixes,y_label,miny,maxy):
        #open the reformatted file
        outDir = self.options.directory + "plots/"
        #for each filled pause, plot the number of surrounding seconds (-g number)
        for i in self.FPList:
            for suffix in suffixes:
                source = self.formattedDir + self.filename +  suffix
                try:
                    data = loadtxt(source,skiprows=1)
                except IOError:
                    print "error,",self.filename," could not be opened for plotting", suffix,". Skipping."
                    continue

                f = open(source,'r')
                headers = f.readline()
                headers = headers.split()
                f.close()

                columnList = []

                for p in range(1, len(headers)): #don't include time, just plot against it.
                    columnList.append((p,headers[p]))
                begin = i[1]
                end = i[2]
                self.shoulder = self.options.graph
                beginMS = str(int(begin*1000))
                endMS = str(int(end*1000))
                ##figure out where to start and end plot
                plot(data[:,0],data[:,columnList[-1][0]],'.',label = suffix)
            miny = min(data[:,columnList[-1][0]])
            miny = 0
            maxy = max(data[:,columnList[-1][0]])
            #print suffix, begin, end
            axis([begin-self.shoulder,end+self.shoulder,miny,maxy])
            title(suffix[0])
            xlabel("time (s)")
            legend()
            axvspan(begin,end, facecolor='grey', alpha=0.3)
            ylabel(y_label)
            savefig(outDir + self.filename +"_" + suffix[1:] + "_" + self.kind + "_" + self.options.tags[0] + "_" + beginMS + "_" + endMS,dpi=100)
            clf()
            
    def makeFormantTables(self,suffix,nameList,y_label,miny,maxy,appendage, findMinMax = False):
        #open the reformatted file
        source = self.formattedDir + self.filename +  suffix
        try:
            data = loadtxt(source,skiprows=1)
        except IOError:
            print "error,",self.filename," could not be opened for plotting. Skipping."
            return

        f = open(source,'r')
        headers = f.readline()
        headers = headers.split()
        f.close()

        columnList = []

        for i in range(1, len(headers)): #don't include time, just plot against it.
            if headers[i] in nameList:
                columnList.append((i,headers[i]))
        legend()
        outDir = self.options.directory + "plots/"

        #for each filled pause, plot the number of surrounding seconds (-g number)
        for i in self.FPList:
            begin = i[1]
            end = i[2]
            self.shoulder = self.options.graph
            beginMS = str(int(begin*1000))
            endMS = str(int(end*1000))
            ##figure out where to start and end plot

            for i in columnList:
                plot(data[:,0],data[:,i[0]],'.',label = i[1])
            if findMinMax:
                miny = min(data[:,i[0]])
                maxy = max(data[:,i[0]])
            else:
                axis([begin-self.shoulder,end+self.shoulder,miny,maxy])
            title(suffix[1:])
            xlabel("time (s)")
            legend()
            axvspan(begin,end, facecolor='grey', alpha=0.3)
            ylabel(y_label)
            savefig(outDir + self.filename +"_" + suffix[1:] + "_" + self.kind+ "_" + appendage+ "_" + self.options.tags[0] + "_" + beginMS + "_" + endMS,dpi=100)
            clf()
           
            
    def makeLPCTables(self,suffix,nameList,y_label,miny,maxy,appendage, findMinMax = False):
        #open the reformatted file
        #print suffix
        source = self.formattedDir + self.filename +  suffix
        try:
            data = loadtxt(source,skiprows=1)
        except IOError:
            print "error,",self.filename," could not be opened for plotting. Skipping."
            return

        f = open(source,'r')
        headers = f.readline()
        headers = headers.split()
        f.close()

        columnList = []

        for i in range(1, len(headers)): #don't include time, just plot against it.
            if headers[i] in nameList:
                columnList.append((i,headers[i]))
        legend()

        outDir = self.options.directory + "plots/"

        #for each filled pause, plot the number of surrounding seconds (-g number)
        for i in self.FPList:
            begin = i[1]
            end = i[2]
            
            self.shoulder = self.options.graph
            beginMS = str(int(begin*1000))
            endMS = str(int(end*1000))
            #print suffix, begin, end, i, self.shoulder
            ##figure out where to start and end plot
            for i in columnList:
                plot(data[:,0],data[:,i[0]],'.',label = i[1])
            if findMinMax:
                miny = min(data[:,i[0]])
                maxy = max(data[:,i[0]])
                axis([begin-self.shoulder,end+self.shoulder,miny,maxy])
            else:
                axis([begin-self.shoulder,end+self.shoulder,miny,maxy])
            title(suffix[1:])
            xlabel("time (s)")
            legend()
            axvspan(begin,end, facecolor='grey', alpha=0.3)
            ylabel(y_label)
            savefig(outDir + self.filename +"_" + suffix[1:] + "_" + self.kind+ "_" + appendage+ "_" + self.options.tags[0] + "_" + beginMS + "_" + endMS,dpi=100)
            clf()
