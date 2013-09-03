#!/bin/python

import csv
import sys
import datetime
import re
import argparse
import os
import glob

import plistlib

from collections import defaultdict
from datetime import datetime

parser = argparse.ArgumentParser(description='Merge PLIST files')
parser.add_argument('-d', required=True, help='working directory containing PLIST file', dest='working_dir')
parser.print_help()
args = parser.parse_args()

plist_file_sig = "*.plist";
working_dir = args.working_dir
if working_dir:
	if not os.path.exists(working_dir):
		print("ERROR: no such directory exists at '" + working_dir + "'")
		exit()
	working_dir = os.path.abspath(working_dir)

merge_plist_file = os.path.join(working_dir, "merged.plist")
		
plist_dir_match = os.path.join(working_dir, plist_file_sig)
		
plist_files = glob.glob(plist_dir_match)
print "PLIST files: " + ";".join(plist_files)

merge_dict = dict()

for file in plist_files:
	pl = plistlib.readPlist(file)
	print pl.viewkeys()
	for key in pl.viewkeys():
		episodeNumber = pl[key]['episodeNumber']
		if not episodeNumber in merge_dict:
			merge_dict[episodeNumber] = pl[key]		
		else:
			print "Already have this key: " + key + ", episode: " + episodeNumber

plistlib.writePlist(merge_dict, merge_plist_file)
#print merge_dict
