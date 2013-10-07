#!/usr/bin/python

import csv
import sys
import datetime
import re
import argparse
import os
import glob

import plistlib
import tempfile

import math

import urllib2
import httplib2

from collections import defaultdict
from datetime import datetime

from mutagen.mp3 import MP3

parser = argparse.ArgumentParser(description='Merge PLIST files')
parser.add_argument('-d', required=True, help='working directory containing PLIST file', dest='working_dir')
parser.add_argument('-c', required=True, help='', dest='cache_dir')
parser.print_help()
args = parser.parse_args()

plist_file_sig = "*.plist";
working_dir = args.working_dir
if working_dir:
	if not os.path.exists(working_dir):
		print("ERROR: no such directory exists at '" + working_dir + "'")
		exit()
	working_dir = os.path.abspath(working_dir)
	
cache_dir = args.cache_dir
if cache_dir:
	if not os.path.exists(cache_dir):
		print("ERROR: no such directory exists at '" + cache_dir + "'")
		print("EXITING for your safety and mine")
		exit()
	cache_dir = os.path.abspath(cache_dir)
	
merge_plist_file = os.path.join(working_dir, "merged.plist")
		
plist_dir_match = os.path.join(working_dir, plist_file_sig)
		
plist_files = glob.glob(plist_dir_match)


cache_loc = os.path.join(cache_dir, ".cache_httplib")
h = httplib2.Http(cache_loc)
h.follow_all_redirects = True

def getContentLocation(link):
    resp, content = h.request(link, headers={'cache-control':'no-cache'})
    print content 
    exit()
    if 'content-location' in resp:
	    contentLocation = resp['content-location']
    return contentLocation    
    
def fileNamedFromURLInDirectory(url,dir):
	name = url.rsplit('/')[-1]
	file = os.path.join(dir, name)
	return file

merge_dict = dict()
for file in plist_files:
	pl = plistlib.readPlist(file)
	for key in pl.viewkeys():
		episodeNumber = pl[key]['episodeNumber']
		if not episodeNumber in merge_dict:
			merge_dict[episodeNumber] = pl[key]	
			mediaUrl = merge_dict[episodeNumber]['mediaUrl']

			if not mediaUrl:
				print "EPISODE " + str(episodeNumber) + " does not seem to have a URL: " + mediaUrl
				continue
			file_name = fileNamedFromURLInDirectory(mediaUrl, cache_dir)
			if os.path.isfile(file_name) :
				print "FILE '" + file_name + "' already exists."
				print mediaUrl
			elif os.path.isdir(file_name):
				print "HEY YOU CHUM! THIS IS A DIRECTORY! KNOWN YOUR PATHS: '" + file_name + "'"
				continue
			else:
				resp, content = h.request(mediaUrl)
				if 'content-location' in resp:
					mediaUrl = resp['content-location']			
					if content:
						with open(file_name, "wb") as file:
							file.write(content)
						if not os.path.exists(file_name):
							print "FAILED TO CREATE FILE '" + file_name + "'."
							continue
					else:
						print "RECEIVED NO CONTENT, FAILED TO CREATE FILE '" + file_name + "'."
						continue
			
			if not os.path.isfile(file_name) :
				print "OK WTF THIS FILE '" + file_name + "' doesn't exists: " + mediaUrl
				continue
				
			audio = MP3(file_name)
			plist_duration = merge_dict[episodeNumber]['duration']
			duration = math.ceil(audio.info.length)
			merge_dict[episodeNumber]['duration'] = duration
			print mediaUrl.rsplit('/')[-1] + " - plist duration: " + str(plist_duration) + "; mutagen duration: " + str(duration)

plistlib.writePlist(merge_dict, merge_plist_file)
#print merge_dict
