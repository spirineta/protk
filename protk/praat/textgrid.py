'''
Created on Jan 23, 2012

@author: jacobokamoto
'''

import re

class TextGrid():
    
    def __init__(self, filename):
        self.filename = filename
        self.xmin = 0.0
        self.xmax = 0.0
        self.num_tiers = 0
        self.has_tiers = False
        self.tiers = []
        self.parse()
        
    def parse(self):
        
        f = None
        
        try:
            f = open(self.filename)
        except IOError:
            print ">> ERROR: Could not open textgrid file at %s" % self.filename
            return
        
        print ">> Opened textgrid at %s" % self.filename
        
        lines = f.readlines()
        
        i=0
        while i < len(lines):
            
            line = lines[i]
            
            if i == 0:
                filetype_parts = [z.strip() for z in line.split('=')]
                filetype = filetype_parts[1].strip("'").strip('"')
                
                if filetype != 'ooTextFile':
                    print ">> WARNING: Textgrid filetype is not ooTextFile, is '%s'" % filetype
                else:
                    print ">> Textgrid file is of type '%s'" % filetype
            
            elif i == 1:
                obj_parts = [z.strip() for z in line.split('=')]
                obj_class = obj_parts[1].strip("'").strip('"')
                
                if obj_class != 'TextGrid':
                    print ">> WARNING: Textgrid object class is not 'TextGrid', is '%s'" % obj_class
                else:
                    print ">> Textgrid file has object class '%s'" % obj_class
                    
            else:
                
                if line.strip() == '':
                    i+=1
                    continue
                
                tokens = [z.strip() for z in line.split('=')]
                
                if tokens[0] == 'xmin':
                    self.xmin = float(tokens[1])
                elif tokens[0] == 'xmax':
                    self.xmax = float(tokens[1])
                elif tokens[0] == 'size':
                    self.num_tiers = 4
                elif tokens[0] == 'tiers? <exists>':
                    self.has_tiers = True
                elif tokens[0] == 'item []:' or tokens[0] == 'item[]:':
                    print "Beginning tier processing"
                    self.parse_items(lines[i+1:])
                    break
            
            i += 1

    def parse_items(self,lines):
        curtier = -1
        
        tiers = []    
        
        i=0
        j=0
        for line in lines:
            m = re.search(r'item \[\d+\]:',line.strip())
            if m:
                if curtier != -1:
                    tiers.append((curtier,j))
                curtier = j
                i+=1
            j+=1
        
        tiers.append((curtier,j))
        
        print ">> Parsing %d interval tiers" % i
        
        for tier in tiers:
            self.tiers.append(IntervalTier(lines[tier[0]:tier[1]]))
            
        
class IntervalTier():
    
    def __init__(self,lines):
        self.lines = lines
        self.metadata = {}
        self.type = None
        self.xmin = 0.0
        self.xmax = 0.0
        self.num_intervals = 0
        self.intervals = []
        self.parse()
        
    def parse(self):
        curival = -1
        
        ivals = []
        
        i=0
        j=0
        for line in self.lines:
            
            m = re.search(r'intervals \[\d+\]:',line.strip())
            if m:
                if curival != -1:
                    ivals.append((curival,j))
                curival = j
                i+=1
                
            else:
                tokens = [z.strip() for z in line.split('=')]
                
                if tokens[0] == 'class':
                    self.metadata['class'] = tokens[1].strip("'").strip('"')
                elif tokens[0] == 'name':
                    self.type = tokens[1].strip("'").strip('"')
                elif tokens[0] == 'xmin':
                    self.xmin = float(tokens[1])
                elif tokens[0] == 'xmax':
                    self.xmax = float(tokens[1])
                elif tokens[0] == 'intervals: size':
                    self.num_intervals = int(tokens[1])
                
            j+=1
            
        for ival in ivals:
            self.intervals.append(Interval(self.type,self.lines[ival[0]:ival[1]]))
        
        print ">>     Parsed %d intervals" % i

class Interval():
    
    def __init__(self,type,lines):
        self.lines = lines
        self.xmin = 0.0
        self.xmax = 0.0
        self.text = None
        self.extra = {}
        self.parse()
        
    def parse(self):
        
        for line in self.lines:
            m = re.search(r'intervals \[\d+\]:',line.strip())
            if m:
                continue
            
            tokens = [z.strip() for z in line.split('=')]
            
            print tokens
            
            if tokens[0] == 'xmin':
                self.xmin = float(tokens[1])
            elif tokens[0] == 'xmax':
                self.xmax = float(tokens[1])
            elif tokens[0] == 'text':
                self.text = tokens[1].strip("'").strip('"')
            else:
                if len(tokens) > 1:
                    self.extra[tokens[0].strip("!")] = tokens[1]
                else:
                    self.extra[tokens[0].strip("!")] = tokens[0]

