count=0
for I in $(seq 10 2 20)
do
	echo $I
	# cp ../US_web_search_list.Chrome.201411${I}*.selenium.crawl/crawl_log*{text,dom} ./
	# user_crawl_log.dom  user_crawl_log.text
	mv 201411${I}_crawl_log.dom US_WS_ad_google_compute_list_$count.dom
	mv 201411${I}_crawl_log.text US_WS_ad_google_compute_list_$count.text
	# mv crawl_log.text 201411${I}_crawl_log.text
	count=`expr $count + 1`
done
