import  mysql.connector
cnx = mysql.connector.connect.connect(user='root', password='asdf', host='localhost', database='LabelDB')
cursor = cnx.cursor()
query_dom = select("SELECT url, userFilePath FROM test_intersect_google_dom WHERE label='Yes'");
query_text = select("SELECT url, userFilePath FROM test_intersect_google_text WHERE label='Yes'");
cursor.execute(query_dom)

for (url, userFilePath) in cursor:
	print url
	print userFilePath
	print'============'

cursor.close();
cnx.close();

