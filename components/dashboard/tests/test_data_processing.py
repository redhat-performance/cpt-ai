"""
Tests for data processing module.
"""

import pytest
import pandas as pd
from src.data_processing import BenchmarkDataProcessor


@pytest.fixture
def processor():
    """Create a BenchmarkDataProcessor instance."""
    return BenchmarkDataProcessor()


@pytest.fixture
def sample_documents():
    """Create sample benchmark documents."""
    return [
        {
            "metadata": {
                "document_id": "test_1",
                "test_timestamp": "2025-11-01T10:00:00Z",
                "os_vendor": "rhel",
                "cloud_provider": "aws",
                "instance_type": "m5.24xlarge",
                "scenario_name": "test_scenario"
            },
            "test": {
                "name": "coremark",
                "version": "v1.0"
            },
            "system_under_test": {
                "hardware": {
                    "cpu": {
                        "model": "Intel Xeon",
                        "cores": 96,
                        "architecture": "x86_64"
                    },
                    "memory": {
                        "total_gb": 373
                    }
                },
                "operating_system": {
                    "distribution": "rhel",
                    "version": "9.5",
                    "kernel_version": "5.14.0"
                }
            },
            "results": {
                "status": "PASS",
                "primary_metric": {
                    "name": "score",
                    "value": 500000.0,
                    "unit": "BOPs"
                },
                "runs": {
                    "run_0": {
                        "metrics": {
                            "multicore_score": 500000.0,
                            "singlecore_score": 5000.0
                        }
                    }
                }
            }
        },
        {
            "metadata": {
                "document_id": "test_2",
                "test_timestamp": "2025-11-02T10:00:00Z",
                "os_vendor": "rhel",
                "cloud_provider": "aws",
                "instance_type": "m5.24xlarge",
                "scenario_name": "test_scenario"
            },
            "test": {
                "name": "streams",
                "version": "v1.0"
            },
            "system_under_test": {
                "hardware": {
                    "cpu": {
                        "model": "Intel Xeon",
                        "cores": 96,
                        "architecture": "x86_64"
                    },
                    "memory": {
                        "total_gb": 373
                    }
                },
                "operating_system": {
                    "distribution": "rhel",
                    "version": "9.4",
                    "kernel_version": "5.14.0"
                }
            },
            "results": {
                "status": "PASS",
                "primary_metric": {
                    "name": "bandwidth",
                    "value": 180000.0,
                    "unit": "MB/s"
                },
                "runs": {
                    "run_0": {
                        "metrics": {
                            "copy_mb_per_sec": 180000.0
                        }
                    }
                }
            }
        }
    ]


def test_documents_to_dataframe(processor, sample_documents):
    """Test conversion of documents to DataFrame."""
    df = processor.documents_to_dataframe(sample_documents)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert 'test_name' in df.columns
    assert 'os_version' in df.columns
    assert 'primary_metric_value' in df.columns


def test_documents_to_dataframe_empty(processor):
    """Test with empty document list."""
    df = processor.documents_to_dataframe([])
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_filter_data(processor, sample_documents):
    """Test data filtering."""
    df = processor.documents_to_dataframe(sample_documents)
    
    # Filter by OS version
    filtered = processor.filter_data(df, os_versions=['9.5'])
    assert len(filtered) == 1
    assert filtered['os_version'].iloc[0] == '9.5'
    
    # Filter by test name
    filtered = processor.filter_data(df, test_names=['coremark'])
    assert len(filtered) == 1
    assert filtered['test_name'].iloc[0] == 'coremark'


def test_get_unique_values(processor, sample_documents):
    """Test extraction of unique values."""
    df = processor.documents_to_dataframe(sample_documents)
    
    os_versions = processor.get_unique_values(df, 'os_version')
    assert set(os_versions) == {'9.4', '9.5'}
    
    test_names = processor.get_unique_values(df, 'test_name')
    assert set(test_names) == {'coremark', 'streams'}


def test_calculate_statistics(processor, sample_documents):
    """Test statistics calculation."""
    df = processor.documents_to_dataframe(sample_documents)
    
    stats = processor.calculate_statistics(df, group_by=['test_name'])
    
    assert isinstance(stats, pd.DataFrame)
    assert 'count' in stats.columns
    assert 'mean' in stats.columns
    assert 'std' in stats.columns
    assert len(stats) == 2  # Two test types


def test_detect_outliers(processor, sample_documents):
    """Test outlier detection."""
    df = processor.documents_to_dataframe(sample_documents)
    
    df_with_outliers = processor.detect_outliers(df, method='iqr')
    
    assert 'is_outlier' in df_with_outliers.columns
    assert df_with_outliers['is_outlier'].dtype == bool


def test_extract_record_missing_fields(processor):
    """Test record extraction with missing fields."""
    incomplete_doc = {
        "metadata": {"document_id": "test_3"},
        "test": {},
        "results": {}
    }
    
    record = processor._extract_record(incomplete_doc)
    
    assert isinstance(record, dict)
    assert record['document_id'] == 'test_3'
    assert 'test_name' in record
    assert 'status' in record



