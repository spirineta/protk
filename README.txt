This is ProTK v0.2.2
====================

Release Information
-------------------
Author: T. Christie and Serguei Pakhomov
Contact: tchristie@umn.edu
Organization: University of Minnesota
Last Modified: August 9, 2011


License Information
-------------------
This program is free software; you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the 
Free Software Foundation; either version 2 of the License, or (at your 
option) any later version.  

This program is distributed in the hope that it will be useful, but 
WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General 
Public License for more details.

You should have received a copy of the GNU General Public License along 
with this program; if not, write to the Free Software Foundation, Inc., 
59 Temple Place, Suite 330, Boston, MA 02111-1307 USA


What is ProTK for?
-------------------
See Usage, and the included paper.



Installation
-------------------

ProTK v0.2 is written to work in a Mac/Linux environment.

1) REQUIRED SOFTWARE: 
PRAAT
First, you should install Praat:
http://www.fon.hum.uva.nl/praat/
or with Linux:
apt-get install praat

The expected install path is:
"/Applications/Praat.app/Contents/MacOS/Praat"

If you are running Linux or have Praat installed in a different location, you can change the path with a command-line flag (see below)

IMPORTANT: The Praat script included in ProTK works with Praat 5.1, 5.1.78, and 5.2.13.  The latest version of Praat for OS X (5.2.32) appears to have changed the way scripts are parsed, so the included script does not work.

PYTHON
ProTK is written to work with Python v2.6.  Plotting will not work with version 2.7, but everything else should.  You can downlost Python v2.6 here:
http://www.python.org/download/releases/2.6.6/

NUMPY
NumPy is also used for numerical computations. It can be downloaded here:
http://sourceforge.net/projects/numpy/
Be sure to download a version of NumPy compatible with Python 2.6.  As of this writing, v2.6 is the latest version of Python that NumPy supports.

You can check that everything is installed correctly by (on OSX/Linux)
> python2.6
>> import numpy 
If you get no errors, you're good to go.  You can close Python by typing quit().

MATPLOTLIB
Matplotlib is required for plotting.  You can run ProTK without the plotting option by leaving out the -g flag when running.  You can download Matplotlib here:
http://sourceforge.net/projects/matplotlib/files/matplotlib/matplotlib-1.0/matplotlib-1.0.0-python.org-py2.6-macosx10.3.dmg/download for OSX.


2) PACKAGE

Several folders were included in the zip file:

ProTK_v0.2.2_code/
This contains the Python code for the program

wav/
This is where you should put your .wav files to be processed

RENAME_*/
This is where your .txtgrid files go.  ProTK is designed to create training and testing sets for WEKA, a machine-learning classifier.  Therefore, the "true", reference textgrid files should go in one folder and the files to be evaluated go in the other.  ProTK expects each .txtgrid file to have "phone" and "word" tiers, even if they both contain phoneme information.  An example file is included in the  sample_files folder, called EXAMPLE.txtgrid.    You should change the "RENAME" folder names to reflect the type of recognition the processes have undergone.



Usage
-------------------
To run ProTK you need at least one set of WAV and corresponding Txtgrid files in subfolders of the ProTK directory (the WAV files must be in wav/ but you can call the textgrid file whatever you want - say "truth).  These Txtgrid files should have two tiers: a phone tier and a word tier.  In the "truth" condition, the words in the word tier should be labeled as FILLEDPAUSE_UM or FILLEDPAUSE_AH in the case of filled pauses.  These will be used to mark filled pauses in the truth AND any other source folder.  

In the terminal, change directories to the directory containing
the code (ProTK_v0.2.2_code - changing directories isn't strictly necessary).  From there, you can type:
python Tk.py -h
or
python2.6 Tk.py -h  (if your default Python is not 2.6)
to see the command line options.  The available options and their default values are:

directory = "../",
configLocation="../",
numProcesses = 1,
truth = "manual",
beforeAfter = 1,
writeToFile = False,
cleanOldResults = False,
extractPraat = False,
reformat = False,
graph = False
writeToFile = False,
quiet = False,
source = False,
praatLocation = "/Applications/Praat.app/Contents/MacOS/Praat",
wekaOnly = False,
wekaname = "",
tags = "FILLEDPAUSE",
tagtier = "word",
prosodytier = "phone"


Options:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory=DIRECTORY
                        REQUIRED:  full path to the directory to be processed
  --tags=TAGS           optional: names of things to tag. Default is
                        filledPauses. This is a placeholder - functionality
                        for this will be added in a future release.
  -t TRUTH, --truth=TRUTH
                        optional: where the 'truth' txtgrid files are.
                        Default is 'manual'.
  -s SOURCE, --source=SOURCE
                        optional: subfolders to process & make a WEKA file
                        for.  Type case-sensitive foldernames separated by
                        commas with NO spaces.  The default is auto.
  -p NUMPROCESSES, --processes=NUMPROCESSES
                        optional: The number of processes to run
                        simultaneously during feature extraction.  The default
                        is 1.
  -c CONFIGLOCATION, --configLocation=CONFIGLOCATION
                        optional: path to the config file, if it's not in the
                        directory of the project
  -b BEFOREAFTER, --beforeAfter=BEFOREAFTER
                        optional: integer specifying how many pre/post
                        intervals to include in WEKA file.  Default is 1
                        (meaning 1 before, 1 after)
  -e, --erase           optional: Erases previous extraction results by
                        deleting and recreating db, arff, extracted,
                        praatOutput and formatted directories
  -x, --extractpraat    optional: extract Prosody information using Praat.
                        Default is to only do this if being run for the first
                        time.  NOTE: -x does not require an additional
                        argument.
  -r, --reformat        optional: force reformatting of info extracted from
                        Praat. The default is to to do this only if being run
                        for the first time. Doesn't require an additional
                        argument.
  -g GRAPH, --graph=GRAPH
                        optional: Plots intervals and context.  Include a
                        positive number to include context surrounding the
                        graph.  ***IMPORTANT***:if you use this option, -p
                        will be set to 1 due to a limitation in MatPlotLib.
  -o, --writetofile     optional: breaks up extracted info and writes it to
                        text files.  Default is to NOT do this.
  -q, --quiet           optional: if used, suppresses all screen output except
                        error messages.
  -w WEKANAME, --wekaname=WEKANAME
                        optional: the name of the weka file to be output.
  -z, --wekaonly        optional: ONLY do weka files, no extraction
  --sphinx              optional: MUST USE if files to be processed include
                        output from Sphinx. Tells the reformatter to expect
                        milisecond time stamps in the phoneme file.
  --praatpath=PRAATLOCATION
                        optional: path to praat executable if not in default
                        OS X path.  In Linux, it may be /usr/bin/praat
  --tag=TAGS            optional: specify string to search for indicating a
                        particular tag. Default is FILLEDPAUSE
  --tagtier=TAGTIER     optional: specify which tier contains tagged
                        datastring to search for indicating a particular tag.
                        Default is FILLEDPAUSE
  --prosodytier=PROSODYTIER
                        optional: specify the relevant tier for prosodic
                        analysis.  The default is 'phone'.


Suggested uses:
A typical usage is:

    python Tk.py -t RENAME_truth -s RENAME_auto -p 4 -g 1 -e -x -o

                This erases old results (-e), extracts Praat info (-x), reformats and writes prosodic info to file (-o), plots results (-g 1).  Note that although (-p 4) is selected, graphing requires that p=1, so the value is automatically changed to 1.

Using an existing project (where info has already been extracted and reformatted), to re-calculate the WEKA ARFF files in the "new" directories, type:

         python Tk.py -s new,new2,new7 -t MANUAL -z

*******IMPORTANT********
 
- if processing *.wav files for the first time, you must use the -x flag to do initial Praat extraction.

- if plotting, limitations in the Matplotlib package require that only one process is run at a time.  Therefore, p is set to 1 automatically.
