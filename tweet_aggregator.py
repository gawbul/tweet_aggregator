#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
"""
	Tweet Aggregator
	Catches tweets with the given hash tag
	Coded by Steve Moss (@gawbul)
	Email: gawbul@gmail.com
	Web: http://about.me/gawbul
"""

"""
	See https://dev.twitter.com/docs/api/1.1/get/search/tweets for REST API information information

	print results.keys() gives us:
	[u'search_metadata', u'statuses']
	
	print metadata.keys() gives us:
	[u'count', u'completed_in', u'max_id_str', u'since_id_str', u'next_results', u'refresh_url', u'since_id', u'query', u'max_id']
	
	print statuses[0].keys() gives us:
	[u'contributors', u'truncated', u'text', u'in_reply_to_status_id', u'id', u'source', u'retweeted', u'coordinates', u'entities', u'in_reply_to_screen_name', u'in_reply_to_user_id', u'retweet_count', u'id_str', u'favorited', u'user', u'geo', u'in_reply_to_user_id_str', u'lang', u'created_at', u'in_reply_to_status_id_str', u'place', u'metadata']
	
	print user.keys() gives us:
	[u'follow_request_sent', u'profile_use_background_image', u'default_profile_image', u'id', u'verified', u'profile_text_color', u'profile_image_url_https', u'profile_sidebar_fill_color', u'entities', u'followers_count', u'profile_sidebar_border_color', u'id_str', u'profile_background_color', u'listed_count', u'profile_background_image_url_https', u'utc_offset', u'statuses_count', u'description', u'friends_count', u'location', u'profile_link_color', u'profile_image_url', u'following', u'geo_enabled', u'profile_background_image_url', u'screen_name', u'lang', u'profile_background_tile', u'favourites_count', u'name', u'notifications', u'url', u'created_at', u'contributors_enabled', u'time_zone', u'protected', u'default_profile', u'is_translator']
"""

# import modules required
import time
from datetime import date, timedelta
import re, sys, os, unicodedata
import httplib2
import paramiko
import simplemediawiki
from twython import Twython

# setup the variables we need
tweet_list = []		# store tweets
more = True			# controls tweet capture loop
query = 'term'		# search query - preceding hash automatically added
ccuser = '@user'	# username to cc in tweets - @ is needed
max_id = None		# required for retreiving batches of tweets (count=100)
sftp_host = "your-sftp-address.com"
sftp_port = 22
sftp_username = "YOUR_USERNAME"
sftp_password = "YOUR_PASSWORD"
sftp_basepath = "/var/www/user"
web_base_url = "http://your-web-address.com/tweets"
proxy_dict = {'http':'your-proxy-address.com:3128', 'https':'your-proxy-address.com:3128'}

# set auth variables
# need to create a read/write application at https://dev.twitter.com/
# and fill with apps OAuth settings
consumer_key = 'YOUR_CONSUMER_KEY'
consumer_secret = 'YOUR_CONSUMER_SECRET'
access_token = 'YOUR_ACCESS_TOKEN'
access_token_secret = 'YOUR_ACCESS_TOKEN_SECRET'
callback_url = 'YOUR_CALLBACK_URL'

# setup new Twython object
twitter = Twython(
	app_key=consumer_key,
	app_secret=consumer_secret,
	oauth_token=access_token,
	oauth_token_secret=access_token_secret,
	callback_url=callback_url,
	# need this to pass through a proxy
	proxies = proxy_dict)

# setup unicode filter
# new method of filtering unicode chars seems to work so far
# fails to write chars to output file if don't filter them first
unicode_chars = ''.join(map(unichr, range(128,65535)))
unicode_chars_re = re.compile('[%s]' % re.escape(unicode_chars))

# setup link identification regexs
# this recognises urls in the tweets
pat1 = re.compile(r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\f]+]*)?)", re.IGNORECASE | re.DOTALL)
pat2 = re.compile(r"#(^|[\n ])(((www|ftp)\.[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
# setup username and hashtag identification
pat3 = re.compile("\@(\w+)[\s\W\z]", re.UNICODE)
pat4 = re.compile("\#(\w+)[\s\W\z]", re.UNICODE)

# set output filename based on date in ISO-8601 format
today = date.today()
today = today.strftime("%Y-%m-%d")
output_file = query + "_tweets_%s.html" % today

##############
# get tweets #
##############
print "Retrieving tweets..."
while more:
	# get search results
	if max_id == None:
		results = twitter.search(q="#" + query, count="100", result_type="recent")
	else:
		results = twitter.search(q="#" + query, count="100", max_id=max_id, result_type="recent")

	# get metadata and statuses
	metadata = results['search_metadata']
	statuses = results['statuses']
	
	# parse the next maxid or finish as no more results
	if metadata.has_key('next_results'):
		next_results = metadata['next_results']
		nr_items = next_results.split('&')
		max_id = nr_items[0].split('=')[1]
	else:
		# simple way of catching end of all tweets (no next_results key)
		more = False
		
	# catch an error, if one occurs
	if results.has_key("errors"):
		print results["errors"]
		# do we die gracefully here, or just let python crash out?
		# perhaps it depends what the error is?
		
	# iterate over statuses
	for status in statuses:
		# pull out values into variables
		# replace links with html code
		# turn some items into hyperlinks
		user = status["user"]
		user_name = user['screen_name']
		user_link = "https://twitter.com/" + user_name + "/"
		tweet_text = status["text"] + "\n"
		tweet_text = unicode_chars_re.sub('', tweet_text)
		tweet_text = pat1.sub(r'\1<a href="\2" target="_blank">\2</a>', tweet_text)
		tweet_text = pat2.sub(r'\1<a href="http:/\2" target="_blank">\2</a>', tweet_text)
		tweet_text = re.sub("\#[\s_]", '', tweet_text)
		usernames = pat3.findall(tweet_text)
		usernames = sorted(set(usernames), key = len)
		for name in usernames:
			in_user_link = "https://twitter.com/" + name + "/"
			tweet_text = re.sub("\@" + name, '<a href="' + in_user_link + '" target="_blank">@' + name + '</a>', tweet_text)		
		hashtags = pat4.findall(tweet_text)
		hashtags = sorted(set(hashtags), key = len)
		for tag in hashtags:
			hash_link = "https://twitter.com/search?q=#" + tag + "&src=hash"
			tweet_text = re.sub("\#" + tag + "(?![\w])", '<a href="' + hash_link + '" target="_blank">#' + tag + '</a>', tweet_text)		
		tweet_id = status["id"]
		tweet_link = user_link + "status/" + str(tweet_id)
		tweet_timestamp = time.strftime("%d/%m/%y %H:%M:%S", time.strptime(status["created_at"], "%a %b %d %H:%M:%S +0000 %Y"))

		# remove any retweets (remove exact duplicates)
		if re.match("^RT.*?", tweet_text):
			continue
		
		# add html formatted tweet to tweet list for output later
		tweet_list.append('<P><A HREF=' + user_link + ' TARGET=_blank>@' + user['screen_name'] + '</A> (' + tweet_timestamp + ') - ' + tweet_text + ' (<a href="' + tweet_link + '">original tweet</a>)</P>')
		
# reverse all the tweets, so they are in chronological order
tweet_list.reverse()

# get tweet count
count = len(tweet_list)

#########################
# open file for writing #
#########################

output_path =  os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), output_file)
outfile = open(output_path, "w")

# write the html header
outfile.write("<HTML><HEAD>\n")
outfile.write("<TITLE>#" + query + " tweets</TITLE></HEAD>")
outfile.write("<BODY><FONT FACE=Tahoma><H1>#" + query + " tweets:</H1>")

# iterate through and write to the file
for tweet in tweet_list:
	try:
		outfile.write(str(tweet) + "\n")
	except Exception as e:
		print e
		print tweet.encode('utf-16')
		
# write the html footer
outfile.write("<H3>" + str(count) + " tweets</H3>")
outfile.write("</FONT></BODY></HTML>")

# close the file
outfile.close()

# let user know how many tweets we have and what filename
print "Outputted %d tweets to %s" % (count, output_file)

###################################
# connect to SFTP and upload file #
###################################
# upload to sftp
try:
	transport = paramiko.Transport((sftp_host, sftp_port))
	transport.connect(username = sftp_username, password = sftp_password)
	sftp = paramiko.SFTPClient.from_transport(transport)
	localpath = output_path
	remotepath = sftp_basepath + "/" + query + "/%s" % output_file
	# let user know it's going
	print "Uploading %s to %s..." % (output_file, host)
	sftp.put(localpath, remotepath)
	sftp.close()
	transport.close()
except:
	status = "Retrieved %d tweets for the %s session, but failed to upload (cc %s) #%s." % (count, today, ccuser, query)
	twitter.updateStatus(status=status)
	print status	
	sys.exit()

# let user know we've uploaded
print "Uploaded to %s on %s" % (remotepath, host)

# set www upload url
upload_url = web_base_url + '/%s' % output_file

# change date format
today = date.today()
today = today.strftime("%a %d %b %Y")

# let user know that the raw log has been uploaded
status = "Uploaded %d tweets for the %s session to %s (cc %s) #%s." % (count, today, upload_url, ccuser, query)
twitter.updateStatus(status=status)
print status
