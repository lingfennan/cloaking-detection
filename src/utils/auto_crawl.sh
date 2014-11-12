# start from today 10:00 o'clock
hour="10:00"
gap="2 days"
nextdate=$(date +%Y-%m-%d)
while true;
do
	# sleep until specific time
	difference=$(($(date -d "$nextdate $hour" +%s) - $(date +%s)))
	echo "Next run is on $nextdate $hour"
	if [ $difference -lt 0 ]
	then
		echo "Sleeping $((86400 + difference)) seconds"
		sleep $((86400 + difference))
	else
		echo "Sleeping $difference seconds"
		sleep $difference
	fi
	echo "Crawling webpages......................"
	python crawl.py data/US_web_search_list.Chrome data/google_bot_list 8
	# update parameters
	previousdate=$nextdate
	nextdate=$(date -d "$previousdate $gap" +%Y-%m-%d)
	echo "previous"
	echo $previousdate
	echo "next"
	echo $nextdate
	sleep 2
done
