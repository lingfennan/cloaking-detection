#!/bin/bash
java -jar ../../dep/selenium-server-standalone-2.44.0.jar -role hub &
java -jar ../../dep/selenium-server-standalone-2.44.0.jar -role node -hub http://localhost:4444/grid/register -browser browserName=chrome,maxInstances=12,platform=LINUX -Dwebdriver.chrome.driver=../../data/trend/linux_chromedriver -timeout 60 &
