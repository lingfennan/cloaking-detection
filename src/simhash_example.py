from simhash import Simhash
print '%x' % Simhash('How are you? I am fine. Thanks.').value
print '%x' % Simhash('How are u? I am fine.     Thanks.').value
print '%x' % Simhash('How r you?I    am fine. Thanks.').value


from simhash import Simhash, SimhashIndex
data = {
	1: u'How are you? I Am fine. blar blar blar blar blar Thanks.',
	2: u'How are you i am fine. blar blar blar blar blar than',
	3: u'This is simhash test.',
}
objs = [(str(k), Simhash(v)) for k, v in data.items()]
index = SimhashIndex(objs)

print index.bucket_size()

s1 = Simhash(u'How are you i am fine. blar blar blar blar blar thank')
print index.get_near_dups(s1)

index.add('4', s1)
print index.get_near_dups(s1)

# build by features
print '%x' % Simhash('How').value
print '%x' % Simhash(['How']).value
print '%x' % Simhash(['How', 'are', 'you']).value


