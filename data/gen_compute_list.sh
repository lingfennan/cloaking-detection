WORD_FILE=$1
PREFIX=$2
echo "Need two parameters! The word file and the prefix for compute list"
ls ../data/$WORD_FILE.selenium.crawl/ad_crawl_log*google > ../data/$WORD_FILE.computed/${PREFIX}_ad_google_compute_list
ls ../data/$WORD_FILE.selenium.crawl/search_crawl_log*google > ../data/$WORD_FILE.computed/${PREFIX}_search_google_compute_list
ls ../data/$WORD_FILE.selenium.crawl/ad_crawl_log*[^google] > ../data/$WORD_FILE.computed/${PREFIX}_ad_user_compute_list
ls ../data/$WORD_FILE.selenium.crawl/search_crawl_log*[^google] > ../data/$WORD_FILE.computed/${PREFIX}_search_user_compute_list
