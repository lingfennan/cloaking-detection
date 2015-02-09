#!/bin/bash
#
# INFILE=$1
BASEDIR='../data/all.computed/'
INFILE=$BASEDIR'search_user_list'
# in the above step, we just processed search_google_list
LEARN=$BASEDIR'search_google_list'

#python cluster_learning.py -f learn -i ../data/all.computed/search_google_text_list -o ../data/all.computed/search_google_list.text -t TEXT -c 1.1
#python cluster_learning.py -f learn -i ../data/all.computed/search_google_dom_list -o ../data/all.computed/search_google_list.dom -t DOM -c 1.1
while read observed_file
do
	# this parameter is based on what i observed from site_dynamics sites.
	echo "Results on $observed_file.text.filt.dedup"
	#python cloaking_detection.py -f detect -i $observed_file.text.filt.dedup -l $LEARN.text.learned -t TEXT -r 1.8 -c 1.2
	python cloaking_detection.py -f detect -i $observed_file.text.filt.dedup -l $LEARN.text.learned -t TEXT -r 15 -c 3.0

	echo "Results on $observed_file.dom.filt.dedup"
	python cloaking_detection.py -f detect -i $observed_file.dom.filt.dedup	-l $LEARN.dom.learned -t DOM -r 10 -c 3.0

	INTERSECT=$observed_file.cloaking.intersect
	ls $observed_file.*.cloaking | python utils/data_util.py -f intersect_sites -o $INTERSECT
done < $INFILE

BASEDIR='../data/all.computed/'
LEARN=$BASEDIR'search_google_list'

RESULT=$BASEDIR'search.detection.result'
LEARNED=$BASEDIR'search.detection.learned'

ls $BASEDIR*.intersect | python utils/data_util.py -f merge_sites -o $BASEDIR'search.detection.result'

python utils/util.py -f evaluation_form -i $RESULT  -p ObservedSites

python utils/data_util.py -f get_learned_eval -i $RESULT -l $LEARN.text.learned -o $LEARNED
