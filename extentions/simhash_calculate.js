/*
chrome.extension.onRequest.addListener(
		function(request, sender, sendResponse) {
			if(request.method == "getText"){
				sendResponse({data: document.all[0].innerText, method: "getText"}); //same as innerText
			}
		}
		);

		*/


chrome.tabs.getSelected(null, function(tab){
	    chrome.tabs.executeScript(tab.id, {code: "alert('test');"}, function(response) {
		            
		        });
});

   chrome.tabs.query({'active': true, 'currentWindow': true},
	function(tabs){
		alert(tabs[0].url);
		console.log(tabs[0].url);

	}
   );


console.log(getText());
var tabURL = window.location.href;
//get visibel text
var clone = $('#content').clone();
clone.appendTo('body').find(':hidden').remove();
var raw_text = clone.text();
console.log(raw_text);
var text_arr = raw_text.split(" +");
var text = text_arr.toString();
clone.remove();


console.log(tabURL);
/*
   chrome.tabs.getSelected(null, function(tab){
   console.log(tab);
   });
   */


var text_set = removedup(text_arr).toString();
var bigram = ngram(text,2).toString();
var trigram = ngram(text,3).toString();
var hash_text = text_set.concat(bigram.concat(trigram));
console.log(hash_text);
var text_hash_val = buildByFeatures(hash_text);
console.log(text_hash_val);

function removedup(arr){
	var unique = [];
	$.each(arr, function(i, el){
		if($.inArray(el, unique) === -1) unique.push(el);
	});
	return unique;
}


function ngram(text, n){
	var text_array = text.split(" ");
	var res = [];
	for(i=0; i<text_array.length-(n-1);i++){
		var tmpstr = "";
		for(j=i;j<n;j--){
			tmpstr = tmpstr.concat(text_array[i]);
		}
		res.push(tmpstr);
	}
	return res;
}

function buildByFeatures(features){
	//set inintial param
	var range = 64;
	var hashs; 
	for(var i=0;i<features.length;i++)
		hashs.push(CryptoJS.MD5(features[i]));
	var vec = [];
	var vec_length = range;
	for(var i=0;i<range;i++){
		vec.push(0);
	}

	var masks = [];
	var masks_lengh = range;
	for(var i=0;i<range;i++){
		vec.push(1<<i);
	}

	for(var h in hashs){
		for(i=0;i<range;i++){
			if(h&masks[i]) vec[i]+=1;
			else vec[i]-=1;
		}
	}

	ans = 0;
	for(i=0;i<range;i++){
		if(vec[i]>=0)
			ans |= masks[i];
	}
	return ans;
}





function getText(){
	return document.body.innerText 
}

function getHTML(){
	return document.body.outerHTML
}


