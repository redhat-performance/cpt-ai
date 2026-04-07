"""
Tests for OpenSearch client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.opensearch_client import BenchmarkDataSource


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client."""
    with patch('src.opensearch_client.OpenSearch') as mock_client:
        # Mock the info() response
        mock_client.return_value.info.return_value = {
            'cluster_name': 'test-cluster',
            'version': {'number': '3.2.0'}
        }
        
        # Mock indices.exists()
        mock_client.return_value.indices.exists.return_value = True
        
        # Mock count()
        mock_client.return_value.count.return_value = {'count': 100}
        
        yield mock_client


def test_client_initialization(mock_opensearch_client):
    """Test BenchmarkDataSource initialization."""
    with patch.dict('os.environ', {
        'OPENSEARCH_HOST': 'localhost',
        'OPENSEARCH_PORT': '9200',
        'OPENSEARCH_INDEX': 'test-index'
    }):
        client = BenchmarkDataSource()
        
        assert client.index_name == 'test-index'
        assert client.client is not None


def test_get_sample_documents(mock_opensearch_client):
    """Test retrieving sample documents."""
    # Mock search response
    mock_response = {
        'hits': {
            'hits': [
                {'_source': {'test': 'doc1'}},
                {'_source': {'test': 'doc2'}}
            ]
        }
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            docs = client.get_sample_documents(limit=10)
            
            assert len(docs) == 2
            assert docs[0]['test'] == 'doc1'


def test_get_sample_documents_empty(mock_opensearch_client):
    """Test with no documents returned."""
    mock_response = {'hits': {'hits': []}}
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            docs = client.get_sample_documents()
            
            assert len(docs) == 0


def test_list_indices(mock_opensearch_client):
    """Test listing indices."""
    mock_indices = {
        'user-index-1': {},
        'user-index-2': {},
        '.system-index': {}
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.indices.get_alias = Mock(return_value=mock_indices)
            
            indices = client.list_indices()
            
            assert len(indices) == 2
            assert 'user-index-1' in indices
            assert '.system-index' not in indices


def test_extract_fields():
    """Test field extraction from nested documents."""
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '__init__', lambda x: None):
            client = BenchmarkDataSource()
            
            doc = {
                'field1': 'value1',
                'nested': {
                    'field2': 'value2'
                }
            }
            
            all_fields = set()
            field_types = {}
            field_examples = {}
            
            client._extract_fields(doc, all_fields, field_types, field_examples)
            
            assert 'field1' in all_fields
            assert 'nested' in all_fields
            assert 'nested.field2' in all_fields


def test_query_with_filters(mock_opensearch_client):
    """Test query with filters applied."""
    mock_response = {
        'hits': {
            'hits': [
                {'_source': {'test': 'filtered_doc'}}
            ]
        }
    }
    
    with patch.dict('os.environ', {'OPENSEARCH_INDEX': 'test-index'}):
        with patch.object(BenchmarkDataSource, '_verify_connection'):
            client = BenchmarkDataSource()
            client.client.search = Mock(return_value=mock_response)
            
            filters = {'os_version': '9.5'}
            docs = client.query_with_filters(filters=filters)
            
            assert len(docs) == 1
            assert docs[0]['test'] == 'filtered_doc'
            
            # Verify search was called
            client.client.search.assert_called_once()



