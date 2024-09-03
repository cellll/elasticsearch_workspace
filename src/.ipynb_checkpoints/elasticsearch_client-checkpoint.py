import os
import time
import json
import requests
import elasticsearch 
from typing import List, Dict

from utils import get_basic_logger, get_es_client

# es logger
import logging
es_logger = logging.getLogger("elastic_transport.transport")
es_logger.setLevel(logging.WARNING)


class SearchEngineElasticClient: # 조회만
    def __init__(self, logger=None, timeout=10, max_retries=1, retry_on_timeout=True):
        
        logger = get_basic_logger() if not logger else logger
        self.logger = logger
        self.es = get_es_client(timeout=timeout, max_retries=max_retries, retry_on_timeout=retry_on_timeout)
        
        
    def analyze(self, instance_name:str, method_name:str, index_name:str, body:dict) -> dict:
        
        resp = {}
        try:
            resp = self.es.indices.analyze(
                index = index_name, 
                body = body
            )
            
        except elasticsearch.NotFoundError as nfe:
            self.logger.error(f'[{instance_name}:{method_name}] index {index_name} not exists.')
        except Exception as e:
            self.logger.error(f'[{instance_name}:{method_name}] Exception raised in count : {e}')
            
        return resp
        
        
    def count(self, instance_name:str, method_name:str, index:str, query:dict, size=0):
        """ query에 해당하는 데이터(document) 개수 count
        
        Args:
            instance_name: 이 함수를 호출하는 instance의 이름
            method_name: 이 함수를 호출하는 instance속 method의 이름 
            index: 개수 조회할 index name
            query: query 조건
            size: 기본 0 (count용)
        
        Returns:
            total_count: index내에 query에 해당하는 document 수 
            
        Note: 
            오류 발생 시 (index name이 없거나 기타 exception 발생) 에러 로그 출력 후 total_count 0 반환
        """
        try:
            resp = self.es.search(index=index, query=query, size=0, track_total_hits = True)
            total_count = self.get_hits_count(resp)
        except elasticsearch.NotFoundError as nfe:
            self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            total_count = 0
        except Exception as e:
            self.logger.error(f'[{instance_name}:{method_name}] Exception raised in count : {e}')
            total_count = 0

        return total_count
    
    
    def search(self, instance_name:str, method_name:str, index:str, query:dict, size=10000):
        """ 검색 수행. scroll 자동 적용.
        
        Args:
            query: query 조건문
        Returns:
            total_hits: 전체 검색 결과
        """
        total_hits = list()
        t0 = time.time()
        
        """ 1. Total count """ 
        total_count = self.count(instance_name, method_name, index, query, size=0)
        
        """ 2. Scroll and search """
        if total_count > size: # scroll, search
            try:
                resp = self.es.search(index=index, query=query, scroll='1m', size=size, track_total_hits=True)
                scroll_id = resp['_scroll_id']
                hits = self.get_hits(resp)
                total_hits.extend(hits)

                while len(hits) > 0:
                    resp = self.es.scroll(scroll_id = scroll_id, scroll='1m')
                    hits = self.get_hits(resp)
                    total_hits.extend(hits)

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in scroll search : {e}')
        else: # search
            try:
                resp = self.es.search(index=index, query=query, size=size)
                hits = self.get_hits(resp)
                total_hits.extend(hits)

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in search : {e}')
                
        t1 = time.time()
        self.logger.debug(f'[SEARCH] [{instance_name}:{method_name}], index: {index}, total_count: {total_count}, get {len(total_hits)} hits, Elapsed : {t1 - t0}s')
        return total_hits
    
    
    def search_with_data(self, instance_name:str, method_name:str, index:str, data:dict, size=10000):
        """ 검색 수행. scroll 자동 적용.
        
        Args:
            data
                query: query 조건문
        Returns:
            total_hits: 전체 검색 결과
        """
        total_hits = list()
        t0 = time.time()
        
        """ 1. Total count """ 
        total_count = self.count(instance_name, method_name, index, data['query'], size=0)
        
        """ 2. Scroll and search """
        if total_count > size: # scroll, search
            try:
                resp = self.es.search(index=index, body=data, scroll='1m', size=size, track_total_hits=True)
                scroll_id = resp['_scroll_id']
                hits = self.get_hits(resp)
                total_hits.extend(hits)
                
                if size > 1:
                    while len(hits) > 0:
                        resp = self.es.scroll(scroll_id = scroll_id, scroll='1m')
                        hits = self.get_hits(resp)
                        total_hits.extend(hits)

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in scroll search : {e}')
        else: # search
            try:
                resp = self.es.search(index=index, body=data, size=size)
                hits = self.get_hits(resp)
                total_hits.extend(hits)

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in search : {e}')
                
        t1 = time.time()
        self.logger.debug(f'[SEARCH] [{instance_name}:{method_name}], index: {index}, total_count: {total_count}, get {len(total_hits)} hits, Elapsed : {t1 - t0}s')
        return total_hits
    
        
    def vector_search(self, instance_name:str, method_name:str, index:str, data:dict, request_timeout=10):
        """ vector search
        
        Args:
            instance_name
            method_name
            index
            data: query 조건문. 이 함수를 호출하는 곳에서 query 조건문을 만들어서 이 함수로 전달 호출 (embedding 값 포함)
            request_timeout: search 기능 수행 timeout
        
        Returns:
            total_hits: query 조건문에 해당하는 vector search 결과 전체
        """
        total_hits = list()
        t0 = time.time()
        try:
            resp = self.es.search(index=index, body=data, request_timeout=request_timeout)
            hits = self.get_hits(resp)
            total_hits.extend(hits)
        except elasticsearch.NotFoundError as nfe:
            self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
        except Exception as e:
            self.logger.error(f'[{instance_name}:{method_name}] Exception raised in search : {e}')
            
        t1 = time.time()
        self.logger.debug(f'[SEARCH] [{instance_name}:{method_name}], index: {index}, get {len(total_hits)} hits, Elapsed : {t1 - t0}s')

        return total_hits
    
    
    def search_with_aggs(self, instance_name:str, method_name:str, index:str, data:dict, size=10000):
        
        """ 검색 + aggs 수행. scroll 자동 적용.
        
        Args:
            query: query 조건문
        Returns:
            total_hits: 전체 검색 결과
            total_aggs: 전체 aggregation 결과
        """
        total_hits = list()
        total_aggs = list()
        t0 = time.time()
        
        """ 1. Total count """ 
        total_count = self.count(instance_name, method_name, index, data['query'], size=0)
        
        """ 2. Scroll and search """
        if total_count > size: # scroll, search
            try:
                resp = self.es.search(index=index, body=data, scroll='1m', size=size, track_total_hits=True)
                scroll_id = resp['_scroll_id']
                # hits
                hits = self.get_hits(resp)
                total_hits.extend(hits)
                
                # aggregations
                if 'aggregations' in resp:
                    total_aggs.append(resp['aggregations'])

                while len(hits) > 0:
                    resp = self.es.scroll(scroll_id = scroll_id, scroll='1m')
                    hits = self.get_hits(resp)
                    total_hits.extend(hits)
                    
                    # aggregations
                    if 'aggregations' in resp:
                        total_aggs.append(resp['aggregations'])

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in scroll search : {e}')
        else: # search
            try:
                resp = self.es.search(index=index, body=data, size=size)
                
                # hits
                hits = self.get_hits(resp)
                total_hits.extend(hits)
                
                # aggregations
                if 'aggregations' in resp:
                    total_aggs.append(resp['aggregations'])

            except elasticsearch.NotFoundError as nfe:
                self.logger.error(f'[{instance_name}:{method_name}] index {index} not exists.')
            except Exception as e:
                self.logger.error(f'[{instance_name}:{method_name}] Exception raised in search : {e}')
                
                
        t1 = time.time()
        self.logger.debug(f'[SEARCH] [{instance_name}:{method_name}], index: {index}, total_count: {total_count}, get {len(total_hits)} hits, {len(total_aggs)} aggs. Elapsed : {t1 - t0}s')
        return total_hits, total_aggs
        
        
    def create_index(self, mapping_name:str, index_name:str) -> dict:
        """ Elasticsearch index 생성
        
        1. mapping file load 
        2. index exists 체크 
            1) 없으면 생성
            2) 있으면 일단 안하고 return 

        Args:
            mapping_name: str = f'{MONGO_DB_NAME}_{MONGO_COL_NAME}'
        """
        
        result = {'status': False, 'created_count': 0, 'reason' : ''}
        
        # 1. es config, mapping file load 
        basepath = os.path.dirname(os.path.realpath(__file__))
        basepath = os.path.dirname(basepath)
        mapping_dirpath = os.path.join(basepath, 'utils', 'es_mappings')
        mapping_filename = f'{mapping_name}.mapping'
        mapping_filepath = os.path.join(mapping_dirpath, mapping_filename)
        
        if not os.path.exists(mapping_filepath):
            result['reason'] = f'mapping filepath not exists : {mapping_filepath}'
            return result
        
        
        # 2. index exists 체크 
        try:
            exists_resp = self.es.indices.get(index=index_name)
            is_exists = True
            
        except elasticsearch.NotFoundError as nfe: # not found -> create
            is_exists = False
            
        except Exception as e: # 그 외 exception -> 생성 안하도록 is_exists = True
            is_exists = True
            
        # 1) 없으면 생성
        if not is_exists: 
            try:
                with open(mapping_filepath, 'r') as f: 
                    mapping = json.load(f)
            except Exception as e: 
                result['reason'] = f'Load mapping file failed. filepath: {mapping_filepath}, {e}'
                return result
            
            try:
                create_resp = self.es.indices.create(index=index_name, body=mapping)
                result['status'] = create_resp['acknowledged']
                if result['status']:
                    result['created_count'] += 1
                    
            except elasticsearch.BadRequestError as bre:
                result['reason'] = f'{type(bre)}, {bre.message}'
                
            except Exception as e:
                result['reason'] = f'{type(e)}, {e}'
            
        else: # 2) 있으면 일단 안하고 return 
            result['status'] = True
            result['reason'] = f'index exists : {index_name}'
        
        return result
            
            
    def get_hits_count(self, resp):
        count = 0
        if 'hits' in resp:
            if 'total' in resp['hits']:
                if 'value' in resp['hits']['total']:
                    count = resp['hits']['total']['value']
        return count

        
    def get_hits(self, resp):
        hits = list()
        if 'hits' in resp:
            if 'hits' in resp['hits']:
                hits = resp['hits']['hits']
        return hits
            
