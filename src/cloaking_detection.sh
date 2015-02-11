#!/bin/bash
#
# INFILE=$1
TYPE=$1
BASEDIR=$2
FILT=$3

echo "Note: I need to specify TYPE [ad/search] [BASEDIR, eg. $BASEDIR, and compile the user list, either search user list or ad user list, with no suffix"


#BASEDIR='../data/all.computed/'
ls $BASEDIR*$TYPE*user*compute_list > $BASEDIR$TYPE'_user_list'
INFILE=$BASEDIR$TYPE'_user_list'
# in the above step, we just processed $TYPE_google_list
LEARN=$BASEDIR$TYPE'_google_list'


# for search, use text r 15, c 3
# for search, use dom 10, c 3

# for ad, use text r 10, c 2
# for ad, use dom 8, c 2
if [ "$TYPE" == "ad" ]; then
	TEXT_R=8
	TEXT_C=3
	DOM_R=4
	DOM_C=2
else
	TEXT_R=15
	TEXT_C=3
	DOM_R=8
	DOM_C=2
fi


ls $BASEDIR*$TYPE*google*list.dom*${FILT}dedup  > $BASEDIR$TYPE'_google_dom_list'
ls $BASEDIR*$TYPE*google*list.text*${FILT}dedup  > $BASEDIR$TYPE'_google_text_list'

python cluster_learning.py -f learn -i $BASEDIR$TYPE'_google_text_list' -o $BASEDIR$TYPE'_google_list.text' -t TEXT -c 1.1
python cluster_learning.py -f learn -i $BASEDIR$TYPE'_google_dom_list' -o $BASEDIR$TYPE'_google_list.dom' -t DOM -c 1.1
while read observed_file
do
	# this parameter is based on what i observed from site_dynamics sites.
	echo "Results on $observed_file.text.${FILT}dedup"
	python cloaking_detection.py -f detect -i $observed_file.text.${FILT}dedup -l $LEARN.text.learned -t TEXT -r $TEXT_R -c $TEXT_C

	echo "Results on $observed_file.dom.${FILT}dedup"
	python cloaking_detection.py -f detect -i $observed_file.dom.${FILT}dedup -l $LEARN.dom.learned -t DOM -r $DOM_R -c $DOM_C

	INTERSECT=$observed_file.cloaking.intersect
	echo "Intersection file is $INTERSECT"
	ls $observed_file.${FILT}*.cloaking | python utils/data_util.py -f intersect_sites -o $INTERSECT
done < $INFILE

LEARN=$BASEDIR$TYPE'_google_list'

RESULT=$BASEDIR$TYPE'.detection.result'
LEARNED=$BASEDIR$TYPE'.detection.learned'

ls $BASEDIR*$TYPE*.intersect | python utils/data_util.py -f merge_sites -o $RESULT

python utils/util.py -f evaluation_form -i $RESULT  -p ObservedSites

python utils/data_util.py -f get_learned_eval -i $RESULT -l $LEARN.text.learned -o $LEARNED
