# start from today 10:00 o'clock
googlehour="16:00"
nongooglehour="16:00"
gap="1 days"
while true;
do
	nextdate=$(date +%Y%m%d)
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
	outdir=$(echo ../../data/US_web_search_list.Chrome*$nextdate*.crawl)
	tgzfile=$outdir'.tgz'
	tar -zcf $tgzfile $outdir
	# save space
	mv $tgzfile /data/urlcrawl/cloaking-data/
	rm -r $outdir

	nextdate=$(date +%Y%m%d)
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
	outdir=$(echo ../../data/US_web_search_list.Chrome*$nextdate*.crawl)
	tgzfile=$outdir".tgz"
	tar -zcf $tgzfile $outdir
	# save space
	mv $tgzfile /data/urlcrawl/cloaking-data/
	rm -r $outdir
done
