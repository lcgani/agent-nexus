"""Agent 2: Tool Generator - Creates Agent Builder tools"""
from jinja2 import Environment, FileSystemLoader
from typing import Dict
import logging
from datetime import datetime
import time
import hashlib
import re

logger = logging.getLogger(__name__)


class ToolGenerator:
    """Generates Agent Builder tool code from API specs"""
    
    def __init__(self, es_client, templates_dir='templates', skip_index=False):
        self.es = es_client
        self.jinja_env = Environment(loader=FileSystemLoader(templates_dir))
        self.skip_index = skip_index
    
    def generate(self, api_url: str) -> Dict:
        """Generate tool from discovered API"""
        start_time = time.time()
        
        discovery_data = self._get_discovery_data(api_url)
        if not discovery_data:
            raise ValueError(f"No discovery data found for: {api_url}")
        
        existing_tool = self._check_existing_tool(api_url)
        if existing_tool:
            return existing_tool
        
        tool_code = self._generate_tool_code(discovery_data)
        mcp_code = self._generate_mcp_code(discovery_data)
        readme = self._generate_readme(discovery_data)
        
        tool_data = {
            'tool_id': self._generate_tool_id(discovery_data['api_name']),
            'tool_name': self._to_snake_case(discovery_data['api_name']),
            'display_name': discovery_data['api_name'],
            'description': discovery_data['api_description'],
            'api_base_url': discovery_data['base_url'],
            'auth_type': discovery_data['auth_type'],
            'generated_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'source_api_discovery_id': api_url,
            'tool_code': tool_code,
            'mcp_server_code': mcp_code,
            'readme': readme,
            'endpoints_count': discovery_data['total_endpoints'],
            'usage_count': 0,
            'rating': 0.0,
            'review_count': 0,
            'is_verified': False,
            'generation_time_seconds': time.time() - start_time
        }
        
        if not self.skip_index:
            self._store_tool(tool_data)
        
        return tool_data

    
    def _get_discovery_data(self, api_url: str) -> Dict:
        """Retrieve discovery data from ES"""
        doc_id = api_url.replace('/', '_').replace(':', '_').replace('.', '_')
        try:
            result = self.es.client.get(index="api-discoveries", id=doc_id)
            return result['_source']
        except Exception as e:
            query = {"query": {"term": {"api_url.keyword": api_url}}}
            result = self.es.search(index="api-discoveries", body=query)
            if result['hits']['total']['value'] > 0:
                return result['hits']['hits'][0]['_source']
        return None
    
    def _check_existing_tool(self, api_url: str) -> Dict:
        """Check if tool already generated"""
        query = {"query": {"term": {"source_api_discovery_id.keyword": api_url}}}
        result = self.es.search(index="agent-tools", body=query)
        if result['hits']['total']['value'] > 0:
            return result['hits']['hits'][0]['_source']
        return None
    
    def _generate_tool_code(self, discovery_data: Dict) -> str:
        """Generate simple tool code"""
        tool_class = self._to_class_name(discovery_data['api_name'])
        tool_name = self._to_snake_case(discovery_data['api_name'])
        
        code = f'''"""
{discovery_data['api_name']} - Auto-generated Tool
Base URL: {discovery_data['base_url']}
"""
import requests

class {tool_class}:
    def __init__(self, api_key=None):
        self.base_url = "{discovery_data['base_url']}"
        self.api_key = api_key
    
    def _headers(self):
        headers = {{"Content-Type": "application/json"}}
        if self.api_key:
            headers["Authorization"] = f"Bearer {{self.api_key}}"
        return headers
'''
        return code
    
    def _generate_mcp_code(self, discovery_data: Dict) -> str:
        """Generate MCP server code"""
        return f"# MCP Server for {discovery_data['api_name']}\n# Coming soon"
    
    def _generate_readme(self, discovery_data: Dict) -> str:
        """Generate README"""
        return f"# {discovery_data['api_name']}\n\n{discovery_data['api_description']}\n\nEndpoints: {discovery_data['total_endpoints']}"
    
    def _generate_tool_id(self, api_name: str) -> str:
        return hashlib.md5(api_name.encode()).hexdigest()[:12]
    
    def _to_class_name(self, name: str) -> str:
        words = name.replace('-', ' ').replace('_', ' ').replace('.', ' ').split()
        return ''.join(word.capitalize() for word in words)
    
    def _to_snake_case(self, name: str) -> str:
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace(' ', '_').replace('-', '_')
    
    def _store_tool(self, tool_data: Dict) -> None:
        try:
            self.es.index(index='agent-tools', id=tool_data['tool_id'], document=tool_data, timeout='2s')
        except Exception as e:
            pass
