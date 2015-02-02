<?php

class AllSites {
	public $googleMap = array();
	public $userMap = array();
	public $linkList = array();
	// Index start from [0, 0, 0] to [G, U, L]
	public $googleMapIndex = 0;
	public $userMapIndex = 0;
	public $linkListIndex = 0;
	private $hasValue = true;

	// function __construct($googleFile, $userFile, $progress=NULL) {
	function AllSites($googleFile, $userFile, $progress=NULL) {
		if (!empty($progress)) {
			$this->loadProgres($progress);
		} 
		if (file_exists($googleFile)) {	
			$userView = fopen($userFile, "r") or die ("cannot open file");
			$googleView = fopen($googleFile, "r") or die ("cannot open file");
			if($userView) {
				while (($url = fgets($userView)) !== false) {
					$url = substr($url, 0, -1);
					$filePath = fgets($userView);
					$filePath = substr($filePath, 0, -1);
					if (array_key_exists($url,$this->userMap))
						// Push observations for this url
						array_push($this->userMap[$url], $filePath);
					else {
						// Record this url
						array_push($this->linkList, $url);
						// Create array for the url
						$this->userMap[$url] = array();
						array_push($this->userMap[$url], $filePath);
					}
				}
			}
			if($googleView) {
				while(($url = fgets($googleView)) !== false) {
					$url = substr($url, 0, -1);
					$filePath = fgets($googleView);
					$filePath = substr($filePath, 0, -1);
					if(array_key_exists($url,$this->googleMap))
						array_push($this->googleMap[$url], $filePath);
					else {
						$this->googleMap[$url] = array();
						array_push($this->googleMap[$url], $filePath);
					}
				}
			}
		}
	}

	function visitNext($response=null) {
		// If response is similar, skip the rest Google views, jump to the next user view.
		$linkSize = count($this->linkList);
		$url = $this->linkList[$this->linkListIndex];
		$userSize = count($this->userMap[$url]);
		$googleSize = count($this->googleMap[$url]);
		$end = array();
		array_push($end, $googleSize, $userSize, $linkSize);
		$current = array();
		array_push($current, $this->googleMapIndex, $this->userMapIndex, $this->linkListIndex);
		// Size of the array, 3.
		$ARRAY_SIZE = 3;
		if (($response != null) and ($response == "Similar")) {
			// If it is similar, skip what Google have seen.
			echo "Similar";
			$index = 1;
		} else {
			$index = 0;
		}
		for (; $index < $ARRAY_SIZE; $index ++) {
			if ($current[$index] >= 0 and $current[$index] < $end[$index] - 1) {
				$current[$index] = $current[$index] + 1;
				for ($lowerBits = $index - 1; $lowerBits >= 0; $lowerBits --) {
					$current[$lowerBits] = 0; 
				}
				// Update the variables.
				$this->googleMapIndex = $current[0];
				$this->userMapIndex = $current[1];
				$this->linkListIndex = $current[2];
				return true;
			} else if ($current[$index] < 0) {
				echo "<br> Index not valid, please check!";
			}
		}
		return false;
	}

	function loadProgress($progress) {
		$this->googleMapIndex = $progress[0];
		$this->userMapIndex = $progress[1];
		$this->linkListIndex = $progress[2];
	}

	function getCurrent($response) {
		if ($this->hasValue) {
			$resultURL = $this->linkList[$this->linkListIndex];
			$this->hasValue = $this->visitNext($response);
			return array($this->userMap[$resultURL][$this->userMapIndex], $this->googleMap[$resultURL][$this->googleMapIndex], $resultURL);
		} else {
			return NULL;
		}
	}
}

?>
