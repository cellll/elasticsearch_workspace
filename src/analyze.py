import os
import json
from datetime import timedelta
import warnings
warnings.filterwarnings(action='ignore')
from elasticsearch import Elasticsearch
client = Elasticsearch(
    'https://127.0.0.1:19200',
    basic_auth=("elastic", 'password'),
    verify_certs=False
)


# analyze
resp = client.indices.analyze(
    index='index_name',
    body={
        'analyzer': 'my_text_analyzer',
        'text': 'hi test text'
    }
)
for token in resp['tokens']:
    print (token)


resp = client.indices.analyze(
    index='index_name',
    body={
        "tokenizer" : "my_nori_tokenizer",
        "text" : 'hi test text',
        "attributes" : ["posType", "leftPOS", "rightPOS", "morphemes", "reading"],
        "explain": True
    }
)
for token in resp['detail']['tokenizer']['tokens']:
    print (token)


# termvector
resp = client.termvectors(
    index = 'index_name',
    id = '12345',
    fields = 'sentence.nori'
)
term_vectors = resp.body['term_vectors']['sentence.nori']['terms']
print (term_vectors) # dict

