<?php

/* 
exmample query:

http://moon.gtisc.gatech.edu/?userFile=uf&googleFile=gf&table=table

Process:
1. Load comparison table
2. Get the first TODO, mark it as Processing
3. User submit response with Similar(No)/Different(Yes)/PageBroken(PageBroken)/NotSure(NotSure)
3a. In order to avoid Processing state items unlabeled, we run a cron job to periodically set all the
Processing to TODO in tables from database LabelDB.
3b. If the user submit Similar(No), then current observation is marked as similar. We don't need to
label the rest pairs anymore. Mark these items as NoByRef.
4. This system should be able to show the current accuracy.
5. The system should be able to reuse already labelled data. To give an estimate of the result
after parameter adjustment.
 */
include("mysql_db.php");

if (isset($_GET["userFile"])) {
	$userFile = $_GET["userFile"];
} else {
	$userFile = "user_sees";
}
if (isset($_GET["googleFile"])) {
	$googleFile = $_GET["googleFile"];
} else {
	$googleFile = "google_sees";
}
if (isset($_GET["table"])) {
	$table_name = $_GET["table"];
} else {
	$table_name = "search_text";
}
$oper = new Operations;

// POST Handler
if (isset($_POST["submit"])) {
	$action = $_POST["submit"];
	if ($action == "submit") {
		$oper->processed($table_name, $_POST["response"], $_POST["id"], $_POST["url"], 
			$_POST["user"]);
	} else if ($action == "exit") {
		$oper->processed($table_name, "TODO", $_POST["id"]);
	} else if ($action == "skip url") {
		$oper->skipUrl($table_name, $_POST["url"]);
	}
}

// check whether there is more to show
$count = $oper->countRows($table_name);
if ($count == -1) {
	$oper->createTableAndLoadComparisonTask($userFile, $googleFile, $table_name);
	// $oper->createTable($table_name);
	// $oper->loadComparisonTask($userFile, $googleFile, $table_name);
} else if ($count == 0) {
	die("The table has no items");
	// $oper->loadComparisonTask($userFile, $googleFile, $table_name);
	// $result = $oper->processing($table_name);
	// $count = $oper->countRows($table_name);
} else if ($count > 0) {
	$result = $oper->processing($table_name);
}
echo "Current id: " . $result["id"] . ", Total count: " . $count . "<br>";
?>

<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" type="text/css" href="style.css">
<?php
echo "<title>" . $table_name . "</title>";
?>
</head>
<body>

<form method="post">
<div class="wrapper">
<input class="button" type="radio" name="response" value="No">Similar
<input class="button" type="radio" name="response" value="Yes">Different
<input class="button" type="radio" name="response" value="PageBroken">PageBroken
<input class="button" type="radio" name="response" value="NotSure">Not Sure
<br>
<input class="button" type="submit" name="submit" value="submit">
<input class="button" type="submit" name="submit" value="skip url">
<input class="button" type="submit" name="submit" value="exit">
</div>

<?php
$url = $result["url"];
$userFilePath = $result["userFilePath"];
if ($userFilePath == "") {
	$userFilePath = "empty.html";
}
$googleFilePath = $result["googleFilePath"];
if ($googleFilePath == "") {
	$googleFilePath = "empty.html";
}
$id = $result["id"];

echo "<b>URL:</b> " . $url . "<br>";
echo "<input type='hidden' name='user' value='$userFilePath'>";
echo "<input type='hidden' name='google' value='$googleFilePath'>";
echo "<input type='hidden' name='id' value='$id'>";
echo "<input type='hidden' name='url' value='$url'>";
echo "</form>";
echo "<div class='note'>User sees</div><div class='note'>Google sees</div>";
echo "<iframe class='siteview' src='$userFilePath'></iframe>";
echo "<iframe class='siteview' src='$googleFilePath'></iframe>";
?>

</body> 
</html> 
