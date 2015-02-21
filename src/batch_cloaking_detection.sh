# USER_IN is the list of user observations, with suffix removed
# GOOGLE_TEXT_IN is the list of google computed text observations
# GOOGLE_DOM_IN is the list of google computed dom observations
USER_IN=$1
GOOGLE_TEXT_IN=$2
GOOGLE_DOM_IN=$3

# for search, use text r 15, c 3
# for search, use dom 10, c 3
# for ad, use text r 10, c 2
# for ad, use dom 8, c 2
TEXT_R=15
TEXT_C=2.1
DOM_R=13
DOM_C=1.8

python utils/data_util.py -f merge_user_sites -i $USER_IN
# The .learned suffix will be appended automatically
python cluster_learning.py -f learn -i $GOOGLE_TEXT_IN -o $GOOGLE_TEXT_IN'.text' -t TEXT -c 0.7
python cluster_learning.py -f learn -i $GOOGLE_DOM_IN -o $GOOGLE_DOM_IN'.dom' -t DOM -c 0.7
python cloaking_detection.py -f detect -i $USER_IN'.text' -l $GOOGLE_TEXT_IN'.text.learned' -t TEXT -r $TEXT_R -c $TEXT_C -o $GOOGLE_TEXT_IN'.text.cloaking' 
python cloaking_detection.py -f detect -i $USER_IN'.dom' -l $GOOGLE_DOM_IN'.dom.learned' -t DOM -r $DOM_R -c $DOM_C -o $GOOGLE_TEXT_IN'.dom.cloaking'
RESULT=$GOOGLE_TEXT_IN'.detection.result'
LEARNED=$GOOGLE_TEXT_IN'.detection.learned'
echo "Intersection file is $RESULT"
ls $GOOGLE_TEXT_IN.*.cloaking | python utils/data_util.py -f intersect_sites -o $RESULT
python utils/util.py -f evaluation_form -i $RESULT  -p ObservedSites
echo "Input is "$GOOGLE_TEXT_IN".text.learned"
echo "Learned Evaluation is $LEARNED"
python utils/data_util.py -f get_learned_eval -i $RESULT -l $GOOGLE_TEXT_IN.text.learned -o $LEARNED
