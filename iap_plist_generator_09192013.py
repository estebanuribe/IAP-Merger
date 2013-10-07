#!/usr/bin/python
# -*- coding: utf-8 -*-

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

import feedparser

import urllib2
import httplib2

from collections import defaultdict
from datetime import datetime

from mutagen.mp3 import MP3

episode_num_re = re.compile(r'([0-9]{2,3})')
def episodeNumberFromTitle(title):
	results = episode_num_re.search(title)
	if results:
		groups = results.groups()
		return str(int(groups[0]))
	return ""


def podcastDataFromPodcastRSSFeed():
	rss_url = "http://insideacting.podbean.com/feed/"
	feed = feedparser.parse(rss_url)
	items = feed["items"]
	
	podcasts_dict = defaultdict(str)
	
	for item in items:
		episode_num = episodeNumberFromTitle(item["title"])
		if episode_num:
			duration = 0
			thumbnailUrl = ""
			podcastUrl = item["link"]
			mediaUrl = ""
			description = item["description"]
			published = item["published"]
			title = item["title"]
			
#			print item["title"] + " (" + item["published"] + " ): " + item["link"] + "\n " + item["description"] + "\n"
			for link in item["links"]:
				url = link["href"]
				if ".mp3" in url:
					mediaUrl = url
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
ext = "plist"
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
		
	audio = MP3(file_name)
	duration = math.ceil(audio.info.length)
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
	if not mediaUrl:
		mediaUrl = pw["mediaUrl"]

	#if "blip.tv" in mediaUrl:
	#	missing_media[key] = mediaUrl
	#	mediaUrl = ""

	podcast["mediaUrl"] = mediaUrl
	
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

	duration = podcast["duration"]
	if not duration:
		if not "blip.tv" in mediaUrl:
			duration = durationFromMediaUrl(mediaUrl)
			if duration:
				podcast["duration"] = duration
		else:
			duration = 0

	podcasts[key] = podcast
	count = count + 1

print "Total episodes: " + str(count)
plistlib.writePlist(podcasts, output_file)

#print podcasts
#print missing_media