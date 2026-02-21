import click
from elasticsearch import Elasticsearch
from src.agents.introspector import APIIntrospector
from src.agents.generator import ToolGenerator
from src.agents.search import CatalogSearch
from src.agents.orchestrator import ToolOrchestrator
from src.config import Config
from src.elasticsearch.client import ESClient
from src.elasticsearch.schemas import (
    API_DISCOVERIES_MAPPING,
    AGENT_TOOLS_MAPPING,
    TOOL_USAGE_LOGS_MAPPING
)
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Agent Nexus - Turn any API into an AI-native tool in 30 seconds"""
    pass


@cli.command()
@click.argument('api_url')
@click.option('--output-dir', default='generated_tools', help='Output directory')
@click.option('--skip-index', is_flag=True, help='Skip Elasticsearch indexing for speed')
def generate(api_url, output_dir, skip_index):
    config = Config()
    es = ESClient(config.elasticsearch_url, config.elasticsearch_api_key)

    introspector = APIIntrospector(es, skip_index=skip_index)
    discovery = introspector.discover(api_url)
    
    if discovery['discovery_status'] == 'failed':
        click.echo(f"Failed: {discovery.get('error_message')}")
        return
    
    generator = ToolGenerator(es, skip_index=skip_index)
    tool_data = generator.generate(api_url)
    
    os.makedirs(output_dir, exist_ok=True)
    
    tool_file = os.path.join(output_dir, f"{tool_data['tool_name']}.py")
    readme_file = os.path.join(output_dir, f"{tool_data['tool_name']}_README.md")
    
    with open(tool_file, 'w') as f:
        f.write(tool_data['tool_code'])
    
    with open(readme_file, 'w') as f:
        f.write(tool_data['readme'])
    
    click.echo(f"✓ {tool_data['tool_name']} ({tool_data['generation_time_seconds']:.1f}s)")


@cli.command()
@click.argument('query')
@click.option('--top-k', default=5, help='Number of results')
def search(query, top_k):
    click.echo(f"Searching for: {query}")
    
    config = Config()
    es = ESClient(config.elasticsearch_url, config.elasticsearch_api_key)
    
    search_agent = CatalogSearch(es)
    results = search_agent.search(query, top_k)
    
    click.echo(f"\nTop {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        tool = result['tool']
        score = result['composite_score']
        click.echo(f"{i}. {tool['display_name']} (score: {score:.2f})")
        click.echo(f"   {tool['description'][:100]}...")
        click.echo(f"   Base URL: {tool['api_base_url']}")
        click.echo(f"   Endpoints: {tool['endpoints_count']}")
        click.echo()


@cli.command()
def setup():
    click.echo("Setting up Elasticsearch...")
    
    config = Config()
    es = Elasticsearch(config.elasticsearch_url)
    
    for index_name, mapping in [
        ('api-discoveries', API_DISCOVERIES_MAPPING),
        ('agent-tools', AGENT_TOOLS_MAPPING),
        ('tool-usage-logs', TOOL_USAGE_LOGS_MAPPING)
    ]:
        if es.indices.exists(index=index_name):
            click.echo(f"✓ Index already exists: {index_name}")
        else:
            es.indices.create(index=index_name, body=mapping)
            click.echo(f"✓ Created index: {index_name}")
    
    click.echo("\nSetup complete!")


if __name__ == '__main__':
    cli()
