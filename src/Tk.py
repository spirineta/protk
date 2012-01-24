#this is the top-level ProTK file that interprets command line arguments and takes input.

from Project import Project
from optparse import OptionParser
from os import path, getcwd
from numpy import seterr
from sys import argv
from shutil import rmtree


#this suppresses a not-useful warning that comes up when graphing

#jobs:
    #set defaults for input arguments
    #parse input arguments
    #run the project (passing in input args)
    
    #in general, two files will be processed: the "truth" and the "auto."  
    #the default subdirectory for "truth" is /manual/  and for "auto" is /auto/
    #both of these can be changed using options.  

seterr(all='raise')

#create global variables
options = args = False



#path stuff
direct = path.abspath(__file__)
s = direct.split('/')
direct = "/" + "/".join(s[:-2]) + "/"


def checkArgs():
    #parse input options
    global options, args, version
    usage = '''type %prog -h for help using specific options.
            Suggested uses:
            Running for first time:

                python Tk.py -t RENAME_truth -s RENAME_auto -p 4 -g 1 -e -x -o

                This erases old results (-e), extracts Praat info (-x), reformats and writes prosodic info to file (-o), plots results (-g 1).  Note that although (-p 4) is selected, graphing requires that p=1, so the value is automatically changed to 1.

				See the README file for more examples.
				
                '''
    parser = OptionParser(usage, version="ProTK 0.2.3")
    version = '0.2.3';


    #default arguments:
    #(can also do this for each argument, but they're easier to see here)
    parser.set_defaults(
                        version = '0.2.3',
                        directory  = direct,
                        configLocation=direct,
                        numProcesses = 1,
                        truth = "manual",
                        beforeAfter = 1,
                        cleanOldResults = False,
                        extractPraat = False,
                        reformat = False,
                        #findIntervals = False,
                        graph = False,
                        writeToFile = False,
                        quiet = False,
                        source = False,
                        praatLocation = "/Applications/Praat.app/Contents/MacOS/Praat",
                        wekaOnly = False,
                        wekaname = "",
                        sphinx = False,
                        tags = "FILLEDPAUSE",
                        tagtier = "word",
                        prosodytier = "phone",
                        passthroughtier = "word"
                        )

    
    parser.add_option("-d", "--directory",
                      action="store", type="string", dest="directory",
                      help="REQUIRED:  full path to the directory to be processed")
                      
    parser.add_option("--tags",
                      action = "store",type="string",dest="tags",
                      help="optional: names of things to tag. Default is filledPauses. This is a placeholder - functionality for this will be added in a future release.")
                      
    parser.add_option("-t", "--truth",
                        action="store", type="string", dest="truth",
                        help="optional: where the 'truth' txtgrid files are.  Default is 'manual'.") 

    parser.add_option("-s", "--source",
                    action="store", type="string",dest="source",
                    help="optional: subfolders to process & make a WEKA file for.  Type case-sensitive foldernames separated by commas with NO spaces.  The default is auto.")

    parser.add_option("-p", "--processes",
                      action="store", type="int", dest="numProcesses",
                      help="optional: The number of processes to run simultaneously during feature extraction.  The default is 1.")

    parser.add_option("-c", "--configLocation",
                      action="store", type="string", dest="configLocation",
                      help="optional: path to the config file, if it's not in the directory of the project")

    parser.add_option("-b", "--beforeAfter",
                      action="store", type="int", dest="beforeAfter",
                      help="optional: integer specifying how many pre/post intervals to include in WEKA file.  Default is 1 (meaning 1 before, 1 after)")

    parser.add_option("-e", "--erase",
                          action="store_true", dest="cleanOldDirs",
                          help="optional: Erases previous extraction results by deleting and recreating db, arff, extracted, praatOutput and formatted directories")
    
    parser.add_option("-x", "--extractpraat",
                      action="store_true", dest="extractPraat",
                      help="optional: extract Prosody information using Praat.  Default is to only do this if being run for the first time.  NOTE: -x does not require an additional argument.")

    parser.add_option("-r", "--reformat",
                      action="store_true", dest="reformat",
                      help="optional: force reformatting of info extracted from Praat. The default is to to do this only if being run for the first time. Doesn't require an additional argument.")

    # parser.add_option("-i", "--findintervals",
    #                   action="store_true", dest="findintervals",
    #                   help="optional:  find intervals and filled pauses for folders specified with -s")

    parser.add_option("-g", "--graph",
                      action="store", type="float", dest="graph",
                      help="optional: Plots intervals and context.  Include a positive number to include context surrounding the graph.  ***IMPORTANT***:if you use this option, -p will be set to 1 due to a limitation in MatPlotLib.")

    parser.add_option("-o", "--writetofile",
                      action="store_true", dest="writeToFile",
                      help="optional: breaks up extracted info and writes it to text files.  Default is to NOT do this.")

    parser.add_option("-q", "--quiet",
                      action="store_true", dest="quiet",
                      help="optional: if used, suppresses all screen output except error messages.")

    parser.add_option("-w", "--wekaname",
                      action="store", type="string",dest="wekaname",
                      help="optional: the name of the weka file to be output.")
                      
    parser.add_option("-z", "--wekaonly",
                    action="store_true",dest="wekaOnly",
                    help="optional: ONLY do weka files, no extraction")
    
    parser.add_option("--sphinx",
                    action="store_true",dest="sphinx",
                    help="optional: MUST USE if files to be processed include output from Sphinx. Tells the reformatter to expect milisecond time stamps in the phoneme file.")

    parser.add_option("--praatpath",
                    action="store",dest="praatLocation",
                    help="optional: path to praat executable if not in default OS X path.  In Linux, it may be /usr/bin/praat")

    parser.add_option("--tag",
                    action="store",dest="tags",
                    help="optional: specify string to search for indicating a particular tag. Default is FILLEDPAUSE")

    parser.add_option("--tagtier",
                    action="store",dest="tagtier",
                    help="optional: specify which tier contains tagged datastring to search for indicating a particular tag. Default is FILLEDPAUSE")


    parser.add_option("--prosodytier",
                    action="store",dest="prosodytier",
                    help="optional: specify the relevant tier for prosodic analysis.  The default is 'phone'.")


    parser.add_option("--passthroughtier",
                    action="store",dest="passthroughtier",
                    help="optional: specify the relevant tier for additional label pass-through. The default is 'word'. Labels must be in the textgrid file for each interval, and start with exclamation marks, i.e. !gaze = 'down' would be a line.")


    
    (options, args) = parser.parse_args()
    

    #parse input arguments
    if len(argv) < 2:
        print "use the flag -h for help"
        if len(argv)>1:            
            for arg in range(1,len(argv)):
                if argv[arg].lower() == "-i":
                    try:
                        directory = argv[arg+1]
                        #check to see if directory exists
                        if not path.isdir(directory):
                            print "error, directory", directory, "does not exist!"
                            exit()
                    except IOError:
                        print "error, directory must be a full path to the files, w/out parentheses"
                        exit()
    if options.graph != False and options.numProcesses != 1:
        options.numProcesses = 1
        print "NOTE: graphing was selected, so only one process will run at a time due to a limitation of MatPlotLib."
    if options.cleanOldResults != False and options.extractPraat != True:
        options.extractPraat = True
        print "NOTE: erasing old results was selected, so Praat must be re-run (-x was also selected)"


def clean():
    '''deletes previous extraction results. do this if you have changed config settings'''
    cleanpath = options.directory 
    foldersToClean = ["arff","extracted","db","praatOutput","formatted", "plots"]       
    for location in foldersToClean:
        if path.lexists(cleanpath + location + "/"):
            rmtree(cleanpath + location + "/")    
        else:
            print "error,",location,"not found and thus not cleaned."
   

#run program
if __name__ == '__main__':
    checkArgs()
    if(options.cleanOldDirs):
        clean()
    project = Project(options)
    del project
