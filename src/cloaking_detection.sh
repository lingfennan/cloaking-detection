USER_IN=$1
GOOGLE_TEXT_IN=$2
GOOGLE_DOM_IN=$3

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

# The .learned suffix will be appended automatically
python cluster_learning.py -f learn -i $GOOGLE_TEXT_IN -o $GOOGLE_TEXT_IN'.text' -t TEXT -c 1.1
python cluster_learning.py -f learn -i $GOOGLE_DOM_IN -o $GOOGLE_DOM_IN'.dom' -t DOM -c 1.1
python cloaking_detection.py -f detect -i $USER_IN'.text' -l $GOOGLE_TEXT_IN'.text.learned' -t TEXT -r $TEXT_R -c $TEXT_C
python cloaking_detection.py -f detect -i $USER_IN'.dom' -l $GOOGLE_DOM_IN'.dom.learned' -t DOM -r $DOM_R -c $DOM_C
RESULT=$USER_IN'.detection.result'
LEARNED=$USER_IN'.detection.learned'
echo "Intersection file is $RESULT"
ls $USER_IN.*.cloaking | python utils/data_util.py -f intersect_sites -o $RESULT
python utils/util.py -f evaluation_form -i $RESULT  -p ObservedSites
echo $GOOGLE_TEXT_IN'.text.learned'
python utils/data_util.py -f get_learned_eval -i $RESULT -l $GOOGLE_TEXT_IN.text.learned -o $LEARNED
