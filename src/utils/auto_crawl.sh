# start from today 10:00 o'clock
googlehour="10:00"
nongooglehour="12:36"
gap="1 days"
nextdate=$(date +%Y-%m-%d)
while true;
do
	# sleep until specific time
	difference=$(($(date -d "$nextdate $nongooglehour" +%s) - $(date +%s)))
	echo "Next run is on $nextdate $nongooglehour"
	if [ $difference -lt 0 ]
	then
		echo "Sleeping $((86400 + difference)) seconds"
		sleep $((86400 + difference))
	else
		echo "Sleeping $difference seconds"
		sleep $difference
	fi
	echo "Crawling webpages......................"
	python crawl.py ../../data/US_web_search_list.Chrome ../../data/non_google_bot_list_1 8
	previousdate=$nextdate
	nextdate=$(date -d "$previousdate $gap" +%Y-%m-%d)
	echo "previous"
	echo $previousdate
	echo "next"
	echo $nextdate

	# sleep until specific time
	difference=$(($(date -d "$nextdate $googlehour" +%s) - $(date +%s)))
	echo "Next run is on $nextdate $googlehour"
	if [ $difference -lt 0 ]
	then
		echo "Sleeping $((86400 + difference)) seconds"
		sleep $((86400 + difference))
	else
		echo "Sleeping $difference seconds"
		sleep $difference
	fi
	echo "Crawling webpages......................"
	python crawl.py ../../data/US_web_search_list.Chrome ../../data/google_bot_list 8
	# update parameters
	previousdate=$nextdate
	nextdate=$(date -d "$previousdate $gap" +%Y-%m-%d)
	echo "previous"
	echo $previousdate
	echo "next"
	echo $nextdate
	sleep 2
done
