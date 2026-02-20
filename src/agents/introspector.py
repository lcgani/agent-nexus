import requests
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class APIIntrospector:
    """Discovers API endpoints, schemas, and authentication"""
    
    COMMON_SPEC_PATHS = [
        "/openapi.json", "/openapi.yaml",
        "/swagger.json", "/swagger.yaml",
        "/api-docs", "/docs/openapi.json",
        "/v1/openapi.json", "/api/openapi.json"
    ]
    
    COMMON_PROBE_PATHS = [
        "/api", "/v1", "/v2", "/users",
        "/health", "/status", "/ping"
    ]
    
    def __init__(self, es_client):
        self.es = es_client
    
    def discover(self, api_url: str) -> Dict:
        logger.info(f"Starting discovery for: {api_url}")
        api_url = api_url.rstrip('/')
        
        existing = self._check_existing(api_url)
        if existing:
            logger.info(f"API already discovered: {api_url}")
            return existing
        
        spec_data = self._find_openapi_spec(api_url)
        
        if spec_data:
            logger.info("OpenAPI spec found, parsing...")
            discovery_result = self._parse_openapi_spec(spec_data, api_url)
        else:
            logger.info("No OpenAPI spec found, attempting manual discovery...")
            discovery_result = self._manual_discovery(api_url)
        
        discovery_result['discovered_at'] = datetime.utcnow().isoformat()
        self._store_discovery(discovery_result)
        
        return discovery_result

    
    def _check_existing(self, api_url: str) -> Optional[Dict]:
        query = {
            "query": {"term": {"api_url.keyword": api_url}},
            "sort": [{"discovered_at": "desc"}],
            "size": 1
        }
        result = self.es.search(index="api-discoveries", body=query)
        if result['hits']['total']['value'] > 0:
            return result['hits']['hits'][0]['_source']
        return None
    
    def _find_openapi_spec(self, api_url: str) -> Optional[Dict]:
        for spec_path in self.COMMON_SPEC_PATHS:
            spec_url = f"{api_url}{spec_path}"
            try:
                response = requests.get(spec_url, timeout=10)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        spec = response.json()
                    elif 'yaml' in content_type or 'yml' in content_type:
                        import yaml
                        spec = yaml.safe_load(response.text)
                    else:
                        try:
                            spec = response.json()
                        except:
                            import yaml
                            spec = yaml.safe_load(response.text)
                    
                    if 'openapi' in spec or 'swagger' in spec:
                        logger.info(f"Found spec at: {spec_url}")
                        return spec
            except Exception as e:
                logger.debug(f"No spec at {spec_url}: {e}")
                continue
        return None

    
    def _parse_openapi_spec(self, spec: Dict, api_url: str) -> Dict:
        try:
            info = spec.get('info', {})
            servers = spec.get('servers', [])
            base_url = servers[0]['url'] if servers else api_url
            
            endpoints = []
            paths = spec.get('paths', {})
            
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method in ['get', 'post', 'put', 'patch', 'delete']:
                        endpoints.append({
                            'path': path,
                            'method': method.upper(),
                            'summary': details.get('summary', ''),
                            'description': details.get('description', ''),
                            'parameters': details.get('parameters', []),
                            'request_body': details.get('requestBody'),
                            'responses': details.get('responses', {})
                        })
            
            auth_type = self._detect_auth_from_spec(spec)
            
            return {
                'api_url': api_url,
                'api_name': info.get('title', 'Unknown API'),
                'api_description': info.get('description', ''),
                'base_url': base_url,
                'has_openapi_spec': True,
                'openapi_spec_url': api_url,
                'auth_type': auth_type,
                'endpoints': endpoints,
                'total_endpoints': len(endpoints),
                'discovery_status': 'complete'
            }
        except Exception as e:
            logger.error(f"Error parsing OpenAPI spec: {e}")
            return {
                'api_url': api_url,
                'discovery_status': 'failed',
                'error_message': str(e)
            }

    
    def _detect_auth_from_spec(self, spec: Dict) -> str:
        security_schemes = spec.get('components', {}).get('securitySchemes', {})
        if not security_schemes:
            return 'none' if 'security' not in spec else 'unknown'
        
        first_scheme = list(security_schemes.values())[0]
        scheme_type = first_scheme.get('type', '').lower()
        
        if scheme_type == 'http':
            scheme = first_scheme.get('scheme', '').lower()
            return 'bearer' if scheme == 'bearer' else 'basic' if scheme == 'basic' else 'unknown'
        elif scheme_type == 'oauth2':
            return 'oauth2'
        elif scheme_type == 'apikey':
            return 'api_key'
        return 'unknown'
    
    def _manual_discovery(self, api_url: str) -> Dict:
        discovered_endpoints = []
        
        for path in self.COMMON_PROBE_PATHS:
            test_url = f"{api_url}{path}"
            for method in ['GET', 'POST']:
                try:
                    if method == 'GET':
                        response = requests.get(test_url, timeout=5)
                    else:
                        response = requests.post(test_url, timeout=5)
                    
                    if response.status_code < 500:
                        discovered_endpoints.append({
                            'path': path,
                            'method': method,
                            'status_code': response.status_code,
                            'summary': f"Discovered via probing",
                            'description': ''
                        })
                        logger.info(f"Found endpoint: {method} {path}")
                except Exception as e:
                    logger.debug(f"Probe failed: {e}")
                    continue
        
        auth_type = 'required' if any(e['status_code'] == 401 for e in discovered_endpoints) else 'unknown'
        
        return {
            'api_url': api_url,
            'api_name': api_url.split('//')[1].split('/')[0],
            'api_description': 'Discovered via manual probing',
            'base_url': api_url,
            'has_openapi_spec': False,
            'auth_type': auth_type,
            'endpoints': discovered_endpoints,
            'total_endpoints': len(discovered_endpoints),
            'discovery_status': 'partial' if discovered_endpoints else 'failed'
        }
    
    def _store_discovery(self, discovery_data: Dict) -> None:
        doc_id = discovery_data['api_url'].replace('/', '_').replace(':', '_').replace('.', '_')
        self.es.index(index='api-discoveries', id=doc_id, document=discovery_data)
        logger.info(f"Stored discovery for: {discovery_data['api_url']}")
