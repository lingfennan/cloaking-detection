/*
   chrome.browserAction.onClicked.addListener(function(tab) {
   chrome.tabs.executeScript({
   code: 'document.body.style.backgroundColor="red"'
   });
   });

   chrome.tabs.query({'active': true, 'currentWindow': true},
   function(tabs){
   alert(tabs[0].url);
   console.log(tabs[0].url);

   }
   );
   */

// This is the class for dom features.
var HtmlDomFeatures = function() {
	this.node = [];
	this.bi_node = [];
	this.tri_node = [];
}

var tabURL = window.location.href;
//get visible text
//var clone = $('#content').clone();
//clone.appendTo('body').find(':hidden').remove();
//var raw_text = clone.text();
var raw_text = getText();
var text_arr = nonempty(raw_text.split(/[^A-Za-z0-9]/));
var text = text_arr.toString();
//clone.remove();
console.log(tabURL);

var text_set = uniq(text_arr);
var bigram = uniq(ngram(text_arr,2));
var trigram = uniq(ngram(text_arr,3));

var hash_text = text_set.concat(bigram.concat(trigram));
console.log(hash_text);
var text_hash_val = buildByFeatures(hash_text);
console.log(text_hash_val);

var dom_features = breadthTraversal(document.documentElement);
// Only use node and bi-node features. tri-node is not used.
var node_set = uniq(dom_features.node);
var bi_node_set = uniq(dom_features.bi_node);
var hash_dom = node_set.concat(bi_node_set);
console.log(hash_dom);
var dom_hash_val = buildByFeatures(hash_dom);
console.log(dom_hash_val);

function nonempty(a) {
	return a.filter(function(item) {
		return item == "" ? false : true;
	});
}

function uniq(a) {
	var seen = {};
	return a.filter(function(item) {
		return seen.hasOwnProperty(item) ? false : (seen[item] = true);
	});
}

function ngram(text_array, n){
	var res = [];
	for(i=0; i<text_array.length-(n-1);i++){
		var tmpstr = text_array.slice(i, i+n).join(" ");
		res.push(tmpstr);
	}
	return res;
}

function extract_one_node(node, features) {
	var node_str = node.nodeName;
	for (var i = 0; i < node.attributes.length; i++) {
		node_str += "_" + node.attributes[i].name;
	}
	features.node.push(node_str);
	if (node.parentNode) {
		pn = node.parentNode;
		pn_str = pn.nodeName;
		if (pn.attributes) {
			for (var i = 0; i < pn.attributes.length; i++) {
				pn_str += "_" + pn.attributes[i].name;
			}
		}
		bi_node = pn_str + "," + node_str;
		features.bi_node.push(bi_node);
	}
	if (node.parentNode && node.parentNode.parentNode) {
		grand = node.parentNode.parentNode;
		grand_str = grand.nodeName;
		if (grand.attributes) {
			for (var i = 0; i < grand.attributes.length; i++) {
				grand_str += "_" + grand.attributes[i].nodeName;
			}
		}
		tri_node = grand_str + "," + pn_str + "," + node_str;
		features.tri_node.push(tri_node);
	}
}

function breadthTraversal(node) {
	var queue = [];
	var features = new HtmlDomFeatures();
	queue.push(node);
	while (queue.length > 0) {
		var node = queue.shift();
		// deal with current node
		extract_one_node(node, features);
		for (var i = 0; i < node.children.length; ++i) {
			queue.push(node.children[i]); //go deeper
		}
	}
	return features;
}

function buildByFeatures(features){
	//set inintial param
	var range = 64;
	var word_size = 32;
	var hashs = []; 
	for(var i=0; i<features.length; i++) {
		var hash = CryptoJS.MD5(features[i]);
		hashs.push(hash);
	}
	var vec = [];
	var vec_length = range;
	for(var i=0; i<vec_length; i++){
		vec.push(0);
	}

	var masks = [];
	var masks_length = range;
	for(var i=0; i<masks_length; i++){
		masks.push(1<<i);
	}

	for(var h in hashs){
		// console.log(hashs[h]);
		for(var w_i=0; w_i<range/word_size; w_i++) {
			for(i=0; i<word_size; i++){
				if (hashs[h].words[w_i] & masks[i]) vec[i + w_i * word_size] += 1;
				else vec[i + w_i * word_size] -= 1;
			}
		}
	}

	ans = 0;
	for(i=0; i<range; i++){
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
