<?php
$m = new Memcached();
$m->addServer('localhost', 11211);

$m->set('int', 99);
$m->set('string', 'a simple string');
$m->set('array', array(11, 12));

echo "asdf";
//$m->getDelayed(array('int', 'array'), true, 'mysleep');
echo "11111111";


$pid = pcntl_fork();
if ($pid == -1) {
	die('could not fork');
} else if ($pid) {
} else {
	mysleep();
exit(0);
}
//var_dump($m->fetchAll());
echo "myend";

function mysleep() {
	sleep(3);
	echo "wake up";
}

?>
