#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
"""
	Tweet Aggregator
	Catches tweet conversations with a particular search term or hash tag
	Coded by Steve Moss (@gawbul)
	Email: gawbul@gmail.com
	Web: http://about.me/gawbul

"""

# import modules required
from twython import Twython
import httplib2
from datetime import date, timedelta
import time
import re, sys, os, unicodedata
import paramiko

# auth variables
consumer_key = '' # Add your consumer key here
consumer_secret = '' # Add your consumer secret here
access_token = '' # Add access token here
access_token_secret = '' # Add access token secret here

twitter = Twython(
	app_key=consumer_key,
	app_secret=consumer_secret,
	oauth_token=access_token,
	oauth_token_secret=access_token_secret,
	# change to your callback url here
	callback_url='http://www.google.co.uk',
	# change this to your proxy server if required
	proxies = {'http':'slb-webcache.hull.ac.uk:3128','https':'slb-webcache.hull.ac.uk:3128'})

# setup unicode filter
# new method of filtering unicode chars seems to work so far
unicode_chars = ''.join(map(unichr, range(128,65535)))
unicode_chars_re = re.compile('[%s]' % re.escape(unicode_chars))

# setup link identification
# this recognises urls in the tweets
pat1 = re.compile(r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\f]+]*)?)", re.IGNORECASE | re.DOTALL)
pat2 = re.compile(r"#(^|[\n ])(((www|ftp)\.[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
# setup username and hashtag identification
pat3 = re.compile("\@(\w+)[\s\W\z]", re.UNICODE)
pat4 = re.compile("\#(\w+)[\s\W\z]", re.UNICODE)

# setup the variables we need
tweet_list = []
page_num = 1

# set output filename based on date
today = date.today()
today = today.strftime("%d%m%y")
output_file = "tweets_%s.html" % today

# get tweets
print "Retrieving tweets..."
count = 0
next_page = 1
results = ""
while page_num <= 15 and next_page == 1:
	# get search results
	# see https://dev.twitter.com/doc/get/search for query information
	search_results = twitter.search(q="#hashtag", page=str(page_num), rpp="100", result_type="recent")

	# get search results keys
	# print search_results.keys() gives us:
	# [u'next_page', u'completed_in', u'max_id_str', u'since_id_str', u'refresh_url', u'results', u'since_id', u'results_per_page', u'query', u'max_id', u'page']

	# simple way of catching end of all tweets
	if not search_results.has_key("next_page"):
		next_page = 0
	
	# catch an error, if one occurs
	if search_results.has_key("error"):
		print search_results["error"]
				
	# got what results we have
	if search_results.has_key("results"):
		results = search_results["results"]
	else:
		results = None

	# get results keys
	# print results[0].keys() gives us:
	# [u'iso_language_code', u'to_user_name', u'to_user_id_str', u'profile_image_url_https', u'from_user_id_str', u'text', u'from_user_name', u'in_reply_to_status_id_str', u'profile_image_url', u'id', u'to_user', u'source', u'in_reply_to_status_id', u'id_str', u'from_user', u'from_user_id', u'to_user_id', u'geo', u'created_at', u'metadata']
	#for key,value in results[0].iteritems():
	#	print str(key) + ": " + str(value)

	# iterate over results
	for result in results:
		# pull out values into variables
		# replace links with html code
		# turn some items into hyperlinks
		from_user = result["from_user"]
		user_link = "https://twitter.com/" + from_user + "/"
		text = result["text"] + "\n"
		text = unicode_chars_re.sub('', text)
		text = pat1.sub(r'\1<a href="\2" target="_blank">\2</a>', text)
		text = pat2.sub(r'\1<a href="http:/\2" target="_blank">\2</a>', text)
		text = re.sub("\#[\s_]", '', text)
		usernames = pat3.findall(text)
		usernames = sorted(set(usernames), key = len)
		for name in usernames:
			in_user_link = "https://twitter.com/" + name + "/"
			text = re.sub("\@" + name, '<a href="' + in_user_link + '" target="_blank">@' + name + '</a>', text)		
		hashtags = pat4.findall(text)
		hashtags = sorted(set(hashtags), key = len)
		for tag in hashtags:
			hash_link = "https://twitter.com/search?q=#" + tag + "&src=hash"
			text = re.sub("\#" + tag + "(?![\w])", '<a href="' + hash_link + '" target="_blank">#' + tag + '</a>', text)		
		tweet_id = result["id"]
		tweet_link = user_link + "status/" + str(tweet_id)
		tweet_timestamp = time.strftime("%d/%m/%y %H:%M:%S", time.strptime(result["created_at"], "%a, %d %b %Y %H:%M:%S +0000"))

		# remove any retweets (remove exact duplicates)
		if re.match("^RT.*?", text):
			continue
		
		# add html formatted tweet to tweet list for output later
		#tweet_list.append('<P>' + str(count + 1) + ': <A HREF=' + user_link + ' TARGET=_blank>@' + from_user + '</A> - ' + text + ' <A HREF=' + tweet_link + ' TARGET=_blank>' + tweet_link + '</A></P>')
		tweet_list.append('<P><A HREF=' + user_link + ' TARGET=_blank>@' + from_user + '</A> (' + tweet_timestamp + ') - ' + text + ' (<a href="' + tweet_link + '">original tweet</a>)</P>')
		
		# increment post count
		count += 1
	
	# increment page number
	page_num +=1

# reverse all the tweets, so they are in chronological order
tweet_list.reverse()

# open file for writing
output_path =  os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), output_file)
outfile = open(output_path, "w")

# write the html header
outfile.write("<HTML><HEAD>\n")
outfile.write("<TITLE>#hashtag tweets</TITLE></HEAD>")
outfile.write("<BODY><FONT FACE=Tahoma><H1>#hashtag tweets:</H1>")

# iterate through and write to the file
for tweet in tweet_list:
	try:
		outfile.write(str(tweet) + "\n")
	except Exception as e:
		print e
		#print re.escape(tweet)
		print tweet.encode('utf-16')
		
# write the html footer
outfile.write("<H3>" + str(count) + " tweets</H3>")
outfile.write("</FONT></BODY></HTML>")

# close the file
outfile.close()

# let user know how many tweets we have and what filename
print "Outputted %d tweets to %s" % (count, output_file)

# connect to SFTP and upload file
try:
	host = "sftp.domain.com"
	port = 22
	transport = paramiko.Transport((host, port))
	username = "username" # change to your username
	password = "password" # change to your password
	transport.connect(username = username, password = password)
	sftp = paramiko.SFTPClient.from_transport(transport)
	localpath = output_path
	remotepath = "/var/www/tweet_aggregator/%s" % output_file
	# let user know it's going
	print "Uploading %s to %s..." % (output_file, host)
	sftp.put(localpath, remotepath)
	sftp.close()
	transport.close()
except:
	status = "Retrieved %d tweets for the %s session, but failed to upload #hashtag." % (count, today)
	twitter.updateStatus(status=status)
	print status	
	sys.exit()
	
print "Uploaded to %s on %s" % (remotepath, host)

# set www upload url
upload_url = 'http://www.domain.com/tweet_aggregator/%s' % output_file

# change date format
today = date.today()
today = today.strftime("%A %d/%m/%Y")

# let user know that the raw log has been uploaded
status = "Uploaded %d tweets for the %s session to %s #hashtag." % (count, today, upload_url)
twitter.updateStatus(status=status)
print status

