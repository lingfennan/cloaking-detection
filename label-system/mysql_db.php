<?php
include("all_sites.php");

class MySQLDB {
	private $connection;	// The MySQL database connection

	/* Class constructor */
	function MySQLDB(){
		$servername = "localhost";
		$username = "root";
		$password = "asdf";
		$dbname = "LabelDB";

		/* Make connection to database */
		$this->connection = mysql_connect($servername, $username, $password) or die(mysql_error());
		mysql_select_db($dbname, $this->connection) or die(mysql_error());
	}

	/* Transactions functions */
	function begin(){
		$null = mysql_query("START TRANSACTION", $this->connection);
		return mysql_query("BEGIN", $this->connection);
	}
	
	function commit(){
		return mysql_query("COMMIT", $this->connection);
	}
	
	function rollback(){
		return mysql_query("ROLLBACK", $this->connection);
	}
	
	function transaction($q_array){
		$retval = 1;
	
		$this->begin();
		$result_array = array();
		foreach ($q_array as $qa) {
			$result = mysql_query($qa['query'], $this->connection);
			if (is_resource($result)) {
				$r_array = array();
				while($r = mysql_fetch_assoc($result)) {
					array_push($r_array, $r);
				}
				$result = $r_array;
			}
			array_push($result_array, $result);
			if (mysql_affected_rows() == 0) $retval = 0;
		}
		if ($retval == 0) {
			$this->rollback();
			return array(false, $result_array);
		} else {
			$this->commit();
			return array(true, $result_array);
		}
	}

	function selectUpdate($select, $update_format) {
		// select id first, then update the value related to this id, return result.
		$this->begin();
		$result = mysql_query($select, $this->connection);
		$last_result = NULL;
		while($r = mysql_fetch_assoc($result)) {
			$id = $r["id"];
			$update = sprintf($update_format, $id);
			
			mysql_query($update, $this->connection);
			$last_result = $r;
		}
		if (mysql_affected_rows() == 0) {
			$this->rollback();
			return NULL;
		} else {
			$this->commit();
			return $last_result;
		}
	}
};

class Operations {
	/* Create database connection object */
	private $database;
	function Operations() {
		$this->database = new MySQLDB;
	}

	function createTableAndLoadComparisonTask($userFile, $googleFile, $table_name="Label_TODO") {
		// Generate create query
		$create_format = "CREATE TABLE %s (id INT(16) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
			url VARCHAR(1000) NOT NULL,
			userFilePath VARCHAR(1000) NOT NULL,
			googleFilePath VARCHAR(1000) NOT NULL,
			label ENUM('Pharmacy', 'Gambling', 'Loan', 'TrafficSale', 'PPC', 'Error', 'IllegalService', 'Phishing', 'BadDomain', 'Malware',
		       	'SEOBusiness', 'No', 'NoByRef', 'PageBroken', 'NotSure', 'TODO', 'Processing'))";
		/*
			Traffic Sale Error
			Legitimate Software SEO-ed Business PPC
			Fake-AV CPALead Insurance Link farm

			label ENUM('Adult', 'Pharmacy', 'Cheat', 'Gambling', 'Phishing', 'BadDomain',
		 */
		// TODO is the start state,
		// Processing is the processing state,
		// Yes, No, NoByRef, PageBroken, NotSure are processed state.
		// Yes means cloaking
		// No mean not cloaking
		// NoByRef means:
		// For a specific site, when comparing user view with Google view, if we already identified
		// a similar copy, then it is not cloaking (No). We mark the rest as NoByRef.
		$create_query = sprintf($create_format, $table_name);
		$q = array(
			array("query" => $create_query),
			);
		$this->database->transaction($q);
		$this->loadComparisonTask($userFile, $googleFile, $table_name);
	}

	function loadBlock($insert_str, $values_array, $start, $size) {
		$sub_array = array_slice($values_array, $start, $size);
		$load_query = $insert_str . implode(",", $sub_array);
		$q = array(
			array("query" => $load_query),
			);
		$this->database->transaction($q);
	}

	function loadComparisonTask($userFile, $googleFile, $table_name) {
		$all_sites = new AllSites($googleFile, $userFile);
		$insert_format = "INSERT INTO %s (url, userFilePath, googleFilePath, label) VALUES ";
		$insert_str = sprintf($insert_format, $table_name);
		$values_format = "('%s', '%s', '%s', 'TODO')";
		$values_array = array();
		while (True) {
			$result = $all_sites->getCurrent(True);
			if ($result == NULL) break;
			$userFilePath = substr($result[0], 2);
			$googleFilePath = substr($result[1], 2);
			$resultURL = $result[2];
			$values_str = sprintf($values_format, 
				mysql_real_escape_string($resultURL), $userFilePath,
			       	$googleFilePath);
			array_push($values_array, $values_str);
		}
		$block_size = 500;
		$block_count = count($values_array) / $block_size;
		$residue = count($values_array) % $block_size;
		for ($x = 0; $x < $block_count; $x ++) {
			$this->loadBlock($insert_str, $values_array, $x * $block_size, $block_size);
		}
		if ($residue != 0) {
			$this->loadBlock($insert_str, $values_array, $block_count * $block_size, $residue);
		}
	}

	function countRows($table_name, $field=NULL, $label=NULL) {
		// count how many rows there is in the table
		// -1 means table doesn't exist
		// o.w. it returns number of rows
		if ($field == NULL) {
			$count_format = "SELECT COUNT(*) FROM %s";
		} else {
			$count_format = "SELECT COUNT(DISTINCT(%s)) ";
			$count_format = sprintf($count_format, $field);
			$count_format = $count_format . " FROM %s";
			if ($label != NULL) {
				$suffix = sprintf(" where label = '%s'", $label);
				$count_format = $count_format . $suffix;
			}
		}
		$count_query = sprintf($count_format, $table_name);
		$q = array(
			array("query" => $count_query),
			);
		$result = $this->database->transaction($q);
		if ($result[0] and $result[1][0] != NULL) {
			if ($field == NULL) {
				return $result[1][0][0]["COUNT(*)"];
			} else {
				return $result[1][0][0]["COUNT(DISTINCT(" . $field . "))"];
			}
		} else {
			return -1;
		}
	}

	function processing($table_name) {
		$select_format = "SELECT * FROM %s where label = 'TODO' limit 1";
		$update_format = "UPDATE %s SET label = 'Processing'";
		$select_query = sprintf($select_format, $table_name);
		$update_format = sprintf($update_format, $table_name) . " WHERE id = %d";
		$result = $this->database->selectUpdate($select_query, $update_format);
		return $result;
	}
	
	function processed($table_name, $label, $id, $url=NULL, $userFilePath=NULL) {
		// set label to the response state, if it is currently in Processing state
		$update_format = "UPDATE %s SET label = '%s' where id = %d and label = '%s'";
		$update_query = sprintf($update_format, $table_name, $label, $id, "Processing");
		$q = array(
			array("query" => $update_query),
			);
		$this->database->transaction($q);
		// If label is no, label all the matched label=TODO/url/userFilePath to NoByRef
		if ($label == "No") {
			$select_format = "SELECT * FROM %s where label = 'TODO' and url = '%s' and 
				userFilePath = '%s'";
			$update_format = "UPDATE %s SET label = 'NoByRef'";
			$select_query = sprintf($select_format, $table_name, $url, $userFilePath);
			$update_format = sprintf($update_format, $table_name) . " WHERE id = %d";
			$result = $this->database->selectUpdate($select_query, $update_format);
		} 
	}

	function skipUrl($table_name, $label, $url) {
		// Skip a URL and mark all the TODO items as NotSure
		$select_format = "SELECT * FROM %s where label = 'TODO' and url = '%s'";
		$update_format = "UPDATE %s SET label = '" . $label . "'";
		$select_query = sprintf($select_format, $table_name, $url);
		$update_format = sprintf($update_format, $table_name) . " WHERE id = %d";
		$result = $this->database->selectUpdate($select_query, $update_format);
	}

	function setTodo() {
		$show_tables_query = "SHOW tables";
		$q = array(
			array("query" => $show_tables_query),
		);
		$result = $this->database->transaction($q);
		$result = $result[1];
		$result = array_slice($result[0], 1);
		foreach($result as $table_name) {
			$update_format = "UPDATE %s SET label = 'TODO' where label = 'Processing' or label = ''";
			$update_query = sprintf($update_format, $table_name["Tables_in_LabelDB"]);
			$q = array(
				array("query" => $update_query),
			);
			$this->database->transaction($q);
		}
	}
}

// Used while debugging
function test() {
	$oper = new Operations;
	$table_name = "my_table";
	$googleFile = "google_sees";
	$userFile = "user_sees";
	// $oper->createTable($table_name);
	// $oper->loadComparisonTask($userFile, $googleFile, $table_name);
	$result = $oper->processing($table_name);
	print var_dump($result);
	$id = $result["id"];
	$label = 'Yes';
	$oper->processed($table_name, $label, $id);
	print $oper->countRows($table_name);
}
?>

