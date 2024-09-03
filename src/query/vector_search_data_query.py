data = {
    'query' : {
        'bool' : {
            'must': [
                {'match': {'item': 'test sentence'}},
                {'terms': {'item_id' : [1,2,3,4]}}
            ],
            'filter': [{'bool' : {'must': [{'terms': {'user_id': [5,6,7,8]}}]}}],
            'boost': 0.1
        }
    },
    'knn': {
        'field': 'emb', 
        'query_vector': query_emb, # List[float]
        'k' : 10000,
        'num_candidates': 10000, 
        'filter': [{'bool' : {'must': [{'terms': {'user_id': [5,6,7,8]}}]}}],
        'boost': 1
    },
    'fields': ['user_id', 'item_id', 'item'],
    'size': 10000,
    'min_score': 0.8,
    '_source': False,
    'track_total_hits': True,
    'explain': True
}

hits = es_client.vector_search(instance_name='a', method_name='b', index='test_dev.emb', data=data, request_timeout=10)
