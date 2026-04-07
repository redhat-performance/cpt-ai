"""
OpenSearch client for querying benchmark results.

Provides connection management and query utilities for retrieving
performance test data from OpenSearch.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from opensearchpy import OpenSearch, exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkDataSource:
    """Data source connector for OpenSearch benchmark results."""
    
    def __init__(self):
        """Initialize OpenSearch connection using environment variables."""
        load_dotenv()
        
        self.index_name = os.getenv('OPENSEARCH_INDEX', '')
        
        # Build OpenSearch client configuration
        host = os.getenv('OPENSEARCH_HOST', 'localhost')
        port = int(os.getenv('OPENSEARCH_PORT', '9200'))
        username = os.getenv('OPENSEARCH_USERNAME', 'admin')
        password = os.getenv('OPENSEARCH_PASSWORD', 'admin')
        use_ssl = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
        verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'
        
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        self._verify_connection()
        
    def _verify_connection(self):
        """Verify connection to OpenSearch and log cluster info."""
        try:
            info = self.client.info()
            logger.info(f"✓ Connected to OpenSearch cluster: {info['cluster_name']}")
            logger.info(f"  Version: {info['version']['number']}")
            
            # Check if index exists
            if self.index_name:
                if self.client.indices.exists(index=self.index_name):
                    count = self.client.count(index=self.index_name)
                    logger.info(f"  Index '{self.index_name}' contains {count['count']} documents")
                else:
                    logger.warning(f"  Index '{self.index_name}' does not exist!")
            else:
                logger.warning("  OPENSEARCH_INDEX not configured in .env")
                
        except exceptions.ConnectionError as e:
            logger.error(f"✗ Failed to connect to OpenSearch: {e}")
            raise
        except exceptions.AuthenticationException as e:
            logger.error(f"✗ Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected error during connection: {e}")
            raise
    
    def list_indices(self) -> List[str]:
        """
        List all available indices (excluding system indices).
        
        Returns:
            List of index names
        """
        try:
            indices = self.client.indices.get_alias(index="*")
            # Filter out system indices (those starting with '.')
            user_indices = [idx for idx in indices.keys() if not idx.startswith('.')]
            return sorted(user_indices)
        except Exception as e:
            logger.error(f"Error listing indices: {e}")
            return []
    
    def get_sample_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve a sample of documents for schema exploration.
        
        Args:
            limit: Number of documents to retrieve
            
        Returns:
            List of document sources
        """
        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    "query": {"match_all": {}},
                    "size": limit
                }
            )
            
            documents = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Retrieved {len(documents)} sample documents")
            return documents
            
        except exceptions.NotFoundError:
            logger.error(f"Index '{self.index_name}' not found")
            return []
        except Exception as e:
            logger.error(f"Error fetching sample documents: {e}")
            return []
    
    def get_all_documents(self, max_docs: int = 10000) -> List[Dict[str, Any]]:
        """
        Retrieve all documents from the index using scroll API for large datasets.
        
        Args:
            max_docs: Maximum number of documents to retrieve
            
        Returns:
            List of all document sources
        """
        try:
            all_documents = []
            batch_size = 1000
            
            # Initial search with scroll
            response = self.client.search(
                index=self.index_name,
                scroll='2m',
                size=batch_size,
                body={"query": {"match_all": {}}}
            )
            
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            all_documents.extend([hit['_source'] for hit in hits])
            
            # Continue scrolling until no more results
            while len(hits) > 0 and len(all_documents) < max_docs:
                response = self.client.scroll(
                    scroll_id=scroll_id,
                    scroll='2m'
                )
                scroll_id = response['_scroll_id']
                hits = response['hits']['hits']
                all_documents.extend([hit['_source'] for hit in hits])
            
            # Clean up scroll context
            try:
                self.client.clear_scroll(scroll_id=scroll_id)
            except Exception:
                pass
            
            logger.info(f"Retrieved {len(all_documents)} total documents")
            return all_documents[:max_docs]
            
        except exceptions.NotFoundError:
            logger.error(f"Index '{self.index_name}' not found")
            return []
        except Exception as e:
            logger.error(f"Error fetching all documents: {e}")
            return []
    
    def query_with_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch benchmark results with optional filtering.
        
        Args:
            filters: Dictionary of filters to apply (structure depends on schema)
            limit: Maximum number of results to return
            
        Returns:
            List of benchmark result documents
        """
        # Build query
        if not filters:
            query = {"query": {"match_all": {}}}
        else:
            # Build bool query with filters
            must_clauses = []
            
            # Add filter clauses based on provided filters
            # This will be refined once we understand the schema
            for field, value in filters.items():
                if isinstance(value, list):
                    # Multiple values - use terms query
                    must_clauses.append({"terms": {field: value}})
                else:
                    # Single value - use term query
                    must_clauses.append({"term": {field: value}})
            
            query = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                }
            }
        
        try:
            response = self.client.search(
                index=self.index_name,
                body=query,
                size=limit
            )
            
            documents = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Query returned {len(documents)} documents")
            return documents
            
        except exceptions.RequestError as e:
            logger.error(f"Invalid query: {e}")
            return []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    def get_field_aggregations(self, field: str, size: int = 100) -> Dict[str, int]:
        """
        Get aggregations (unique values and counts) for a specific field.
        Useful for discovering filter options.
        
        Args:
            field: Field name to aggregate (must be keyword type)
            size: Maximum number of buckets to return
            
        Returns:
            Dictionary mapping field values to document counts
        """
        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,  # We only want aggregations, not documents
                    "aggs": {
                        "field_values": {
                            "terms": {
                                "field": field,
                                "size": size
                            }
                        }
                    }
                }
            )
            
            buckets = response['aggregations']['field_values']['buckets']
            result = {bucket['key']: bucket['doc_count'] for bucket in buckets}
            logger.info(f"Found {len(result)} unique values for field '{field}'")
            return result
            
        except Exception as e:
            logger.error(f"Error getting aggregations for field '{field}': {e}")
            return {}
    
    def explore_schema(self) -> Dict[str, Any]:
        """
        Explore and analyze the schema by examining sample documents.
        
        Returns:
            Dictionary with schema information
        """
        samples = self.get_sample_documents(limit=50)
        
        if not samples:
            return {"error": "No documents found"}
        
        # Collect all fields across samples
        all_fields = set()
        field_types = {}
        field_examples = {}
        
        for doc in samples:
            self._extract_fields(doc, all_fields, field_types, field_examples)
        
        schema_info = {
            "total_documents": len(samples),
            "fields": sorted(list(all_fields)),
            "field_count": len(all_fields),
            "field_types": field_types,
            "field_examples": field_examples
        }
        
        logger.info(f"Schema exploration found {len(all_fields)} unique fields")
        return schema_info
    
    def _extract_fields(
        self,
        doc: Dict[str, Any],
        all_fields: set,
        field_types: Dict[str, set],
        field_examples: Dict[str, Any],
        prefix: str = ""
    ):
        """
        Recursively extract field names and types from nested documents.
        
        Args:
            doc: Document or subdocument to analyze
            all_fields: Set to accumulate field names
            field_types: Dictionary mapping field names to observed types
            field_examples: Dictionary mapping field names to example values
            prefix: Field path prefix for nested fields
        """
        for key, value in doc.items():
            field_name = f"{prefix}{key}" if prefix else key
            all_fields.add(field_name)
            
            # Track type
            value_type = type(value).__name__
            if field_name not in field_types:
                field_types[field_name] = set()
            field_types[field_name].add(value_type)
            
            # Store example (first occurrence)
            if field_name not in field_examples:
                field_examples[field_name] = value
            
            # Recurse for nested objects (but not lists)
            if isinstance(value, dict):
                self._extract_fields(
                    value, all_fields, field_types, field_examples,
                    prefix=f"{field_name}."
                )


def main():
    """Test the OpenSearch connection and explore schema."""
    try:
        client = BenchmarkDataSource()
        
        print("\n" + "="*60)
        print("AVAILABLE INDICES")
        print("="*60)
        indices = client.list_indices()
        for idx in indices:
            print(f"  - {idx}")
        
        print("\n" + "="*60)
        print("SCHEMA EXPLORATION")
        print("="*60)
        schema = client.explore_schema()
        
        if "error" in schema:
            print(f"Error: {schema['error']}")
        else:
            print(f"\nTotal documents sampled: {schema['total_documents']}")
            print(f"Total unique fields: {schema['field_count']}")
            print("\nFields and types:")
            for field in schema['fields']:
                types = ', '.join(schema['field_types'][field])
                example = schema['field_examples'][field]
                # Truncate long examples
                if isinstance(example, str) and len(example) > 50:
                    example = example[:47] + "..."
                print(f"  {field:40s} ({types:15s}) = {example}")
        
        print("\n" + "="*60)
        print("SAMPLE DOCUMENTS")
        print("="*60)
        import json
        samples = client.get_sample_documents(limit=3)
        for i, doc in enumerate(samples, 1):
            print(f"\nDocument {i}:")
            print(json.dumps(doc, indent=2)[:500])  # Truncate for readability
            if len(json.dumps(doc, indent=2)) > 500:
                print("... (truncated)")
        
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        print("\nPlease ensure:")
        print("1. You have created a .env file (copy from .env.example)")
        print("2. OpenSearch connection details are correct")
        print("3. OpenSearch server is running and accessible")


if __name__ == "__main__":
    main()



