import simhash
import random

# 6 blocks, 3 bits may differ

corpus = simhash.Corpus(6, 3)


# Generate 1M random hashes and random queries
import random
count = 10000
hashes  = [random.randint(0, 1 << 64) for i in range(count)]
queries = [random.randint(0, 1 << 64) for i in range(count)]

# Insert the hashes
corpus.insert_bulk(hashes)

# Find matches; returns a list of results, each element contains the match
# for the corresponding element in the query
matches = corpus.find_first_bulk(queries)

print matches
# Find more matches; returns a list of lists, each of which corresponds to 
# the query of the same index
matches = corpus.find_all_bulk(queries)

print matches
