#!/usr/bin/python
# -*- coding: utf-8 -*-

import csv, plistlib, tempfile, argparse
import sys, subprocess, os, re, glob
import time, datetime, math
import feedparser, urllib2, httplib2

from collections import defaultdict
from datetime import datetime

from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

SLEEP_TIME = 60
sleep_count = 0
sleep_randoms = [32, 22, 32, 24, 35, 6, 1, 40, 16, 41, 17, 6, 5, 30, 25, 20, 23, 29, 39, 20, 28, 14, 9, 14, 8, 23, 38, 29, 1, 38, 2, 15, 24, 11, 28, 22, 23, 19, 10, 17, 35, 42, 11, 15, 25, 3, 34, 3, 7, 31, 7, 33, 29, 32, 5, 31, 10, 42, 6, 35, 7, 38, 42, 28, 41, 6, 12, 23, 29, 4, 9, 20, 16, 5, 16, 14, 36, 20, 44, 1, 14, 5, 11, 25, 9, 19, 27, 29, 2, 29, 14, 38, 7, 45, 44, 18, 37, 23, 13, 4]
#sleep_randoms seeded with random numbers from random.org, reseed as necessary, need 200 numbers for good measure
last_sleep_time = 0

bad_mp3_links = []

def get_sleep_time():
	global sleep_count
	global sleep_randoms
	global SLEEP_TIME
	global last_sleep_time

	stime = 0
	if sleep_count > len(sleep_randoms):
		sleep_count = 0
	
	sleep_number = sleep_randoms[sleep_count]
	sleep_count += 1
	new_sleep_time = SLEEP_TIME - sleep_number
	new_sleep_time = abs(new_sleep_time)
	if new_sleep_time == last_sleep_time or new_sleep_time == 0 or new_sleep_time > 60:
		print "recursive"
		stime = get_sleep_time() 
	else:
		stime = new_sleep_time
	
	last_sleep_time = stime
	
	return stime 

_find_duration = re.compile( '.*Duration: ([0-9:]+)', re.MULTILINE )

episode_num_re = re.compile(r'([0-9]{2,3})')
def episodeNumberFromTitle(title):
	results = episode_num_re.search(title)
	if results:
		groups = results.groups()
		return str(int(groups[0]))
	return ""

def min_sec_to_seconds( ms ):
	"Convert a minutes:seconds string representation to the appropriate time in seconds."
	a = ms.split(':')
	#  assert 2 == len( a )	
	if 2 == len(a):
		return float(a[0]) * 60 + float(a[1])
	elif 3 == len(a):
		return float(a[0]) * 3600 + float(a[1])*60 + float(a[2])
	
	return 0

def seconds_to_min_sec( secs ):
  "Return a minutes:seconds string representation of the given number of seconds."
  mins = int(secs) / 60
  secs = int(secs - (mins * 60))
  return "%d:%02d" % (mins, secs)


def retrieve_length( path ):
	"Determine length of tracks listed in the given input files (e.g. playlists)."

	print path + ' duration:'

	total_mutagen = 0.0
	total_ffmpeg = 0.0

	print '%8s%8s%8s  %s' % ('mutagen', 'm:s', 'ffmpeg', 'track')

	if not os.path.exists( path ):
	  print "Error: specified music file '%s' does not exist.\n" % path
	  raise SystemExit(2)

	try:
		audio = MP3( path )
	except (RuntimeError, TypeError, NameError):
		print "The file '" + file_name + "' does not appear to be a valid MP3 file."

	
	seconds = audio.info.length

	ffmpeg = subprocess.check_output(
	  'ffmpeg -i "%s"; exit 0' % path,
	  shell = True,
	  stderr = subprocess.STDOUT )

	match = _find_duration.search( ffmpeg )
	if match: ffmpeg = match.group( 1 )
	else: ffmpeg = '--'

	ffmpeg = ffmpeg.lstrip('0:')

	print '%8.1f%8s%8s  %s' % (seconds, seconds_to_min_sec(seconds), ffmpeg, path )

	total_mutagen = seconds
	total_ffmpeg = min_sec_to_seconds( ffmpeg )

	s = '-' * 6
#	print '%8s%8s%8s  %s' % (s, s, s, s )
#	print '%8.1f%8s%8s  %s' % (total_mutagen, seconds_to_min_sec(total_mutagen), seconds_to_min_sec(total_ffmpeg), 'total' )

	return (total_mutagen, total_ffmpeg)


podcasts_list = []
blog_podcast_list = []

def podcastDataFromPodcastRSSFeed():
	rss_url = "http://insideacting.podbean.com/feed/"
	feed = feedparser.parse(rss_url)
	items = feed["items"]
	podcasts_dict = defaultdict(str)
	
	for item in items:
		episode_num = episodeNumberFromTitle(item["title"])
		if episode_num:
			published = 0
			duration = 0
			thumbnailUrl = ""
			podcastUrl = item["link"]
			mediaUrl = ""
			description = item["description"]
			if "published" in item:
				published = time.mktime(datetime.strptime(item["published"], "%a, %d %b %Y %H:%M:%S +0000").timetuple())
				print item["published"]
			title = item["title"]

#			print item["title"] + " (" + item["published"] + " ): " + item["link"] + "\n " + item["description"] + "\n"

#			print item["links"]
			for link in item["links"]:
				url = link["href"]
				if ".mp3" in url:
					mediaUrl = url
					podcasts_list.append(url)

					#print link
					if "length" in link:
						duration = link["length"]
				elif ".jpg" in url:
					thumbnailUrl = url
			
			podcast = {"title":title, "episodeBlogLink":podcastUrl, 
					   "publishedDate":published, "item_id":published,
					   "thumbnailUrl":thumbnailUrl, "description":description,
					    "mediaUrl":mediaUrl, "duration":duration} 
			podcasts_dict[episode_num] = podcast
	return podcasts_dict


def podcastsDataFromWebsiteRSSFeed():
	rss_url = "http://www.insideactingpodcast.com/feeds/posts/default?alt=rss&max-results=500"
	feed = feedparser.parse(rss_url)

	items = feed["items"]

	url_re = re.compile(r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))')

	podcasts_dict = defaultdict(str)

	def findURLTypesInText(text):
		results_dict = {"urls":[],"jpg":"","mp3":""}
		results = url_re.findall(text)
		if results:
			for result_group in results:
				for url in result_group:
					if url:
						results_dict["urls"].append(url)
						if ".jpg" in url:
							results_dict["jpg"] = url
						elif ".mp3" in url:
							results_dict["mp3"] = url
		return results_dict

	def findImageURLInText(text):
		
		results = url_re.findall(text)
		if results:
			for result_group in results:
				for url in result_group:
					if "jpg" in url:
						return url
		return ""

	
	def findMediaURLInText(text):
		results = url_re.findall(text)
		if results:
			for result_group in results:
				for url in result_group:
					if "mp3" in url:
						return url
		return ""

	for item in items:
		episode_num = episodeNumberFromTitle(item["title"])
		if episode_num:
			urls = findURLTypesInText(item["summary"])
			thumbnailUrl = urls["jpg"]
			mediaUrl = urls["mp3"]
			urlsSummary = ", ".join(urls["urls"])
#			thumbnailUrl = findImageURLInText(item["summary"])
#			mediaUrl = findMediaURLInText(item["summary"])
			if not mediaUrl:
				print episode_num + ": has no mediaUrl; " + item["title"] + item["summary"]
			else:
				blog_podcast_list.append(mediaUrl)
					
			if not thumbnailUrl:
				print "********\n"
				print "EPISODE " + episode_num + ": has no thumbnailUrl; \n" + item["link"]
				print urlsSummary + "\n--------"
					
			podcast = {"thumbnailUrl":thumbnailUrl,"mediaUrl":mediaUrl,"link":item["link"],"description":item["summary"]}
			podcasts_dict[episode_num] = podcast

	return podcasts_dict

DEFAULTTHUMBNAILURL = "http://img.podbean.com/itunes-logo/436854/IAP-album-art01.jpg"

parser = argparse.ArgumentParser(description='IAP plist check')
parser.add_argument('-d', required=True, help='where to output checked PLIST file', dest='output_dir')
parser.print_help()
args = parser.parse_args()

output_dir = args.output_dir
if output_dir:
	if os.path.isfile(output_dir) or not os.path.isdir(output_dir):
		print("ERROR: no such directory at '" + output_dir + "'")
		exit()
	output_dir = os.path.abspath(output_dir)

now = datetime.now()
timestamp = now.strftime("%Y%m%d") 	
root = "merge"
ext = ".plist"
file_name = root + timestamp + ext
output_file = os.path.join(output_dir, file_name) 

#cache_dir = tempfile.gettempdir()
cache_dir = output_dir
#print cache_dir

cache_loc = os.path.join(cache_dir, ".cache_httplib")
h = httplib2.Http(cache_loc)
h.follow_all_redirects = True

print cache_loc

def fileNamedFromURLInDirectory(url,dir):
	name = url.rsplit('/')[-1]
	file = os.path.join(dir, name)
	return file

def durationFromMediaUrl(mediaUrl):
	duration = 0
	file_name = fileNamedFromURLInDirectory(mediaUrl, cache_dir)
	if os.path.isfile(file_name) :
		print "FILE '" + file_name + "' already exists."
	elif os.path.isdir(file_name):
		print "HEY YOU CHUM! THIS IS A DIRECTORY! KNOWN YOUR PATHS: '" + file_name + "'"
		return 0
	else:
		print file_name + ": " + mediaUrl
		print "RETRIEVING '" + mediaUrl + "'"
		resp, content = h.request(mediaUrl)
		if 'content-location' in resp:
			mediaUrl = resp['content-location']			
			if content:
				with open(file_name, "wb") as file:
					file.write(content)
				if not os.path.exists(file_name):
					print "FAILED TO CREATE FILE '" + file_name + "'."
					return 0
			else:
				print "RECEIVED NO CONTENT, FAILED TO CREATE FILE '" + file_name + "'."
				return 0
	
	if not os.path.isfile(file_name) :
		print "OK WTF THIS FILE '" + file_name + "' doesn't exists: " + mediaUrl
		return 0
		
	#attempt to check if MP3 is valid
	try:
		audio = MP3(file_name)
		if audio:
			duration = math.ceil(audio.info.length)
		retrieve_length(file_name)

	except (RuntimeError, TypeError, NameError):
		print "The file '" + file_name + "' does not appear to be a valid MP3 file."
		bad_mp3_links.append(mediaUrl)

	print "NAP TIME! I'm so sleepy!"	
	stime = get_sleep_time()
	time.sleep(stime)
	print "That was a nice '" + str(stime) + "' second nap.  Time to go work again!"
	return duration

#print podcastDataFromPodcastRSSFeed()
podcasts_itunes = podcastDataFromPodcastRSSFeed()
podcasts_web = podcastsDataFromWebsiteRSSFeed()

podcasts = defaultdict(str)
count = 0

missing_media = defaultdict(str)

#blip_tv = {"24":"http://j67.video2.blip.tv/13720004633947/Insideactingpodcast-Episode24BonnieGillespiePart2283.mp3?ir=16189&amp;sr=153",

for key in podcasts_itunes.viewkeys():
	podcast = podcasts_itunes[key]
	pw = podcasts_web[key]

	mediaUrl = podcast["mediaUrl"]

	#if "blip.tv" in mediaUrl:
	#	missing_media[key] = mediaUrl
	#	mediaUrl = ""
	
	description = podcast["description"]
	if not description:
		description = pw["description"]
		if not description:
			print "Episode " + key + " has no description anywhere!"
			exit()
		else:
			podcast["description"] = description

	thumbnailUrl = podcast["thumbnailUrl"]
	if thumbnailUrl == DEFAULTTHUMBNAILURL or not thumbnailUrl:
		if "thumbnailUrl" in pw:
			thumbnailUrl = pw["thumbnailUrl"]
		if not thumbnailUrl:
			podcast["thumbnailUrl"] = DEFAULTTHUMBNAILURL
		else:
			podcast["thumbnailUrl"] = thumbnailUrl

	duration = durationFromMediaUrl(mediaUrl)
	if duration:
		podcast["duration"] = float(duration)
	print "duration: " + str(duration)

	podcasts[key] = podcast
	count = count + 1

print "Total episodes: " + str(count)
plistlib.writePlist(podcasts, output_file)


print "ERROR: Couldn't get accurate times for the following mp3s"
print bad_mp3_links
#print podcasts_list
#rint blog_podcast_list
#print podcasts
#print missing_media