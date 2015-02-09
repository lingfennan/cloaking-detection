#!/bin/bash
INFILE=$1
LEARN=$2

while read observed_file
do
	# this parameter is based on what i observed from site_dynamics sites.
	echo "Results on $observed_file.text.filt.dedup"
	python cloaking_detection.py -f detect -i $observed_file.text.filt.dedup -l $LEARN.text.learned -t TEXT -r 1.8 -c 1.2
	echo "Results on $observed_file.dom.filt.dedup"
	python cloaking_detection.py -f detect -i $observed_file.dom.filt.dedup -l $LEARN.dom.learned -t DOM -r 1.7 -c 1.8

	INTERSECT=$observed_file.cloaking.intersect
	ls $observed_file.*.cloaking | python utils/data_util.py -f intersect_sites -o $INTERSECT
done < $INFILE
