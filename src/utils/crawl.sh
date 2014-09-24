LOCATION="Inside Google"
THREADS=$1
INPUT_FILE=$2
USER_AGENT_FILE=$3
REFERER_FILE=$4

if [ "$THREADS" == "" ]
then
	THREADS=10
fi

if [ "$INPUT_FILE" == "" ]
then
	INPUT_FILE="data/url_list"
fi

if [ "$USER_AGENT_FILE" == "" ]
then
	USER_AGENT_FILE="data/user_agent_list"
fi

if [ "$REFERER_FILE" == "" ]
then
	REFERER_FILE="data/referer_list"
fi

# Download content for $line with $USER_AGENT AND $REFERER
Fetch_One_Link()
{
	line=$1
	if [ "$line" != "" ]
	then
		# echo "Fetching $line ............."
		# Dealing with format
		TEMP_LINE=$(echo $line)
		URL_MD5=$(echo -n $TEMP_LINE | md5sum | cut -f1 -d" ")
		# Record path information, and URL.
		LOG_LINE=$URL_MD5','$TEMP_LINE

		TEMP_OUTPUT=$OUT_DIR$URL_MD5
		mkdir -p $TEMP_OUTPUT
		curl_status=$(curl --retry 1 --globoff -A "$USER_AGENT"  --referer "$REFERER" -s -L -w "%{http_code},%{url_effective}" -o $TEMP_OUTPUT'/'$DOC_NAME "$TEMP_LINE")
		content=$(cat $TEMP_OUTPUT'/'$DOC_NAME)
		if [ $? != 0 ]
		then
			echo 'Cat failed'
			echo 'Cat failed,'$LOG_LINE >> $OUT_DIR"failure"
			continue
		fi
		
		# Regular expressions to look at
		re1="The previous page is sending you to <a href=\"([^\"]+)\">"
		re2="m.navigateTo\(parent,window,\"([^\"]+)\"\)"
		re3="<CLICK_RESPONSE><CLICK_ID></CLICK_ID></CLICK_RESPONSE>"

		# Deal with simple redirects
		if [[ $content =~ $re1 ]]
		then
			echo 'Previous page'
			# echo ${BASH_REMATCH[1]}
			curl_status=$(curl --retry 1 --globoff -A "$USER_AGENT"  --referer "$REFERER" -s -L -w "%{http_code},%{url_effective}" -o $TEMP_OUTPUT'/'$DOC_NAME "${BASH_REMATCH[1]}")
		elif [[ $content =~ $re2 ]]
		then
			echo 'Navigate to'
			# echo ${BASH_REMATCH[1]}
			curl_status=$(curl --retry 1 --globoff -A "$USER_AGENT"  --referer "$REFERER" -s -L -w "%{http_code},%{url_effective}" -o $TEMP_OUTPUT'/'$DOC_NAME "${BASH_REMATCH[1]}")
		elif [[ $content =~ $re3 ]]
		then
			# consider invalid click as failure
			echo 'Invalid click'
			echo 'JunkContent,'$LOG_LINE >> $OUT_DIR"failure"
			continue
		fi

		# 1. Get http code and url effective from curl write.
		# 2. If http code is 200, then log to success, else to failure.
		# 3. If the url is redirected (maybe all the urls are), then log both original url and the effective url.
		IFS=',' read -ra curl_statuses <<< "$curl_status"
		HTTP_CODE=${curl_statuses[0]}
		URL_EFFECTIVE=${curl_statuses[1]}
		URL_EFF_MD5=$(echo -n $URL_EFFECTIVE | md5sum | cut -f1 -d" ")
		if [ "$URL_MD5" != "$URL_EFF_MD5" ]
		then
			LOG_LINE=$LOG_LINE','$URL_EFF_MD5','$URL_EFFECTIVE
		fi
		if [ $HTTP_CODE -ne 200 ]
		then
			echo $HTTP_CODE','$LOG_LINE >> $OUT_DIR"failure"
		else
			echo $LOG_LINE >> $OUT_DIR"success"
			echo $URL_MD5','$URL_EFFECTIVE >> $OUT_DIR"landing_page"
			echo $TEMP_OUTPUT'/'$DOC_NAME','$URL_EFFECTIVE >> $BASE_DIR"html_path_list"
		fi
	fi
}

# Download content from URL list ($INPUT_FILE) with agent $USER_AGENT and referer $REFERER
Fetch_URL_List()
{
	USER_AGENT=$1
	REFERER=$2

	# output document name
	DOC_NAME="index.html" 
	# Dealing with user agent and referer
	# The md5 for user agent and referer
	USER_AGENT_REFERER_MD5=$(echo -n $USER_AGENT$REFERER | md5sum | cut -f1 -d" ")
	LOG_INFO="Input file is:$INPUT_FILE, User agent is:$USER_AGENT, Referer is:$REFERER, md5 of {User agent | referer} is:$USER_AGENT_REFERER_MD5, Start time is $(date +"%T/%m/%d/%Y")."
	echo $LOG_INFO

	# The base directory for output
	BASE_DIR=$(pwd)"/"$INPUT_FILE"."$TODAY".crawl/"
	echo $BASE_DIR
	OUT_DIR=$BASE_DIR"data_curl_$USER_AGENT_REFERER_MD5/"
	mkdir -p $OUT_DIR

	SIMPLIFIED_LOG_INFO="$USER_AGENT_REFERER_MD5:$USER_AGENT:$REFERER"
	echo $SIMPLIFIED_LOG_INFO >> $BASE_DIR"curl_urls.log"


	while read line
	do
		while [ `jobs | wc -l` -ge $THREADS ]
		do
			sleep 2
		done
		Fetch_One_Link $line &
	done <$INPUT_FILE
}


# Record start
echo "The script is running $LOCATION, input file is $INPUT_FILE, user agent file is $USER_AGENT_FILE, referer file is $REFERER_FILE, start time is $(date +"%T/%m/%d/%Y")." >> "crawl.log"

# Get current date
TODAY=$(date +"%Y%m%d-%H%M%S")
while read USER_AGENT
do
	while read REFERER
	do
		echo "Fetch_URL_List \"$USER_AGENT\" \"$REFERER\""
		# user agent and referer cannot be missing, so add quote
		Fetch_URL_List "$USER_AGENT" "$REFERER"
	done < $REFERER_FILE
done < $USER_AGENT_FILE

# Record end
echo "The script is running $LOCATION, input file is $INPUT_FILE, user agent file is $USER_AGENT_FILE, referer file is $REFERER_FILE, end time is $(date +"%T/%m/%d/%Y")." >> "crawl.log"
