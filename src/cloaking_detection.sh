#!/bin/bash
INFILE=$1
LEARN=$2

python cloaking_detection.py -f detect -i ../data/abusive_words_9_category.computed/$1.text -l ../data/abusive_words_9_category.computed/$2.text.learned -t TEXT -n 10 -n 20
python cloaking_detection.py -f detect -i ../data/abusive_words_9_category.computed/$1.dom -l ../data/abusive_words_9_category.computed/$2.dom.learned -t DOM -n 10 -n 20

INTERSECT=$1.n20_r10.intersect
ls ../data/abusive_words_9_category.computed/$1.*.cloaking | python utils/data_util.py -f intersect_sites -o ../data/abusive_words_9_category.computed/$INTERSECT
