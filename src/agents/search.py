from sentence_transformers import SentenceTransformer
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class CatalogSearch:
    def __init__(self, es_client):
        self.es = es_client
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        logger.info(f"Searching for: {query}")
        
        query_embedding = self.embedding_model.encode(query).tolist()
        
        search_body = {
            "knn": {
                "field": "description_embedding",
                "query_vector": query_embedding,
                "k": top_k,
                "num_candidates": 100
            },
            "_source": [
                "tool_id", "tool_name", "display_name",
                "description", "api_base_url", "auth_type",
                "usage_count", "rating", "endpoints_count"
            ]
        }
        
        result = self.es.search(index="agent-tools", body=search_body)
        ranked_results = self._rank_results(result['hits']['hits'])
        return ranked_results[:top_k]
    
    def _rank_results(self, hits: List[Dict]) -> List[Dict]:
        scored_results = []
        
        for hit in hits:
            tool = hit['_source']
            es_score = hit['_score']
            
            popularity_score = min(tool.get('usage_count', 0) / 1000.0, 1.0)
            rating_score = tool.get('rating', 0) / 5.0
            
            composite_score = (es_score * 0.7 + popularity_score * 0.2 + rating_score * 0.1)
            
            scored_results.append({
                'tool': tool,
                'relevance_score': es_score,
                'popularity_score': popularity_score,
                'rating_score': rating_score,
                'composite_score': composite_score
            })
        
        scored_results.sort(key=lambda x: x['composite_score'], reverse=True)
        return scored_results
    
    def index_tool(self, tool_data: Dict) -> None:
        embedding = self.embedding_model.encode(tool_data['description']).tolist()
        tool_data['description_embedding'] = embedding
        
        self.es.update(
            index='agent-tools',
            id=tool_data['tool_id'],
            body={'doc': {'description_embedding': embedding}}
        )
        logger.info(f"Indexed tool with embedding: {tool_data['tool_name']}")
