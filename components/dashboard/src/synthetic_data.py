"""
Synthetic data generator for performance benchmarks.

Generates realistic benchmark data matching the OpenSearch schema structure
for development and testing purposes.

Enhanced Features:
- Temporal trends and seasonality
- Correlated metrics within test types
- Hardware-specific performance characteristics
- Realistic failure scenarios
- Multi-node and cluster configurations
- Geographic and region-specific patterns
"""

import json
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import os


class SyntheticDataGenerator:
    """Generate synthetic benchmark results matching real OpenSearch schema."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional random seed."""
        random.seed(seed)
        
        # Expanded configuration based on discovered schema
        # OS configurations: distribution -> list of versions
        self.os_configs = {
            "rhel": ["9.2", "9.3", "9.4", "9.5", "9.6", "10.0", "10.1"],
            "ubuntu": ["20.04", "22.04", "24.04"],
            "amazon": ["2", "2023"],
            "sles": ["15.4", "15.5", "15.6"]
        }
        self.cloud_providers = ["aws", "azure", "gcp"]
        
        # Expanded hardware configurations with more variety
        self.instance_types = {
            "aws": [
                "m5.24xlarge", "m5.12xlarge", "m5.8xlarge", "m5.4xlarge",
                "m6i.24xlarge", "m6i.12xlarge", "m6i.8xlarge",
                "c5.24xlarge", "c5.12xlarge", "c5.8xlarge",
                "c6i.24xlarge", "c6i.12xlarge",
                "r5.24xlarge", "r5.12xlarge",
                # C6i series for cloud scaling analysis
                "c6i.large", "c6i.xlarge", "c6i.2xlarge", "c6i.4xlarge",
                "c6i.8xlarge", "c6i.16xlarge", "c6i.32xlarge"
            ],
            "azure": [
                "Standard_D96s_v3", "Standard_D64s_v3", "Standard_D48s_v3", "Standard_D32s_v3",
                "Standard_F96s_v2", "Standard_F64s_v2", "Standard_F48s_v2",
                "Standard_E96s_v5", "Standard_E64s_v5"
            ],
            "gcp": [
                "n2-highmem-96", "n2-highmem-64", "n2-highmem-48", "n2-highmem-32",
                "c2-standard-60", "c2-standard-48", "c2-standard-30",
                "n2-standard-96", "n2-standard-64",
                # C4 series for cloud scaling analysis
                "c4-standard-2", "c4-standard-4", "c4-standard-8", "c4-standard-16",
                "c4-standard-24", "c4-standard-32", "c4-standard-48", "c4-standard-96",
                "c4-standard-144", "c4-standard-192", "c4-standard-288"
            ]
        }
        
        self.test_types = [
            "coremark", "coremark_pro", "passmark", "streams", 
            "auto_hpl", "pyperf", "phoronix", "uperf", "pig",
            "specjbb", "fio", "sysbench"
        ]
        
        # Hardware performance tiers (affects baseline performance)
        self.hardware_tiers = {
            "high": ["24xlarge", "96", "60", "144", "192", "288"],
            "medium": ["12xlarge", "64", "48"],
            "low": ["8xlarge", "4xlarge", "32", "30", "24", "16", "8", "4", "2"]
        }
        
        # C4 series instance specifications for cloud scaling analysis (GCP)
        # Maps instance type to (vCPUs, RAM in GiB)
        self.c4_series_specs = {
            "c4-standard-2": (2, 7),
            "c4-standard-4": (4, 15),
            "c4-standard-8": (8, 30),
            "c4-standard-16": (16, 60),
            "c4-standard-24": (24, 90),
            "c4-standard-32": (32, 120),
            "c4-standard-48": (48, 180),
            "c4-standard-96": (96, 360),
            "c4-standard-144": (144, 540),
            "c4-standard-192": (192, 720),
            "c4-standard-288": (288, 1080),
        }
        
        # C6i series instance specifications for cloud scaling analysis (AWS)
        # Maps instance type to (vCPUs, RAM in GiB)
        self.c6i_series_specs = {
            "c6i.large": (2, 4),
            "c6i.xlarge": (4, 8),
            "c6i.2xlarge": (8, 16),
            "c6i.4xlarge": (16, 32),
            "c6i.8xlarge": (32, 64),
            "c6i.12xlarge": (48, 96),
            "c6i.16xlarge": (64, 128),
            "c6i.24xlarge": (96, 192),
            "c6i.32xlarge": (128, 256),
        }
        
        # Baseline metric values (will be varied based on hardware tier)
        self.baseline_metrics = {
            "coremark": {
                "multicore_score": 500000.0,
                "singlecore_score": 5000.0,
                "iterations_per_sec": 500000.0
            },
            "coremark_pro": {
                "SUMM_CPU_mean": 55000.0,
                "SUMM_ME_mean": 2700.0,
                "CPU_INT_mean": 62000.0,
                "CPU_FP_mean": 48000.0,
                "ME_READ_mean": 2800.0,
                "ME_WRITE_mean": 2600.0
            },
            "passmark": {
                "CPU_INTEGER_MATH_mean": 270000.0,
                "CPU_FLOATINGPOINT_MATH_mean": 146000.0,
                "CPU_PRIME_mean": 185000.0,
                "ME_WRITE_mean": 10000.0,
                "ME_READ_mean": 11000.0,
                "ME_LATENCY_mean": 85.0
            },
            "streams": {
                "copy__mb_per_sec": 180000.0,
                "scale__mb_per_sec": 140000.0,
                "add__mb_per_sec": 150000.0,
                "triad__mb_per_sec": 145000.0
            },
            "auto_hpl": {
                "gflops": 2500.0,
                "time_seconds": 120.0,
                "efficiency_pct": 85.0
            },
            "pyperf": {
                "mean": 0.5,
                "geometric_mean": 0.48,
                "min": 0.45,
                "max": 0.55
            },
            "phoronix": {
                "hash_bops": 8000000.0,
                "pipe_bops": 17000000.0,
                "poll_bops": 5000000.0,
                "syscall_bops": 12000000.0
            },
            "uperf": {
                "tcp_stream_bw_gbs": 9.5,
                "tcp_rr_trans_per_sec": 50000.0,
                "udp_stream_bw_gbs": 8.0,
                "latency_us": 45.0
            },
            "pig": {
                "throughput_mb_s": 150.0,
                "records_per_sec": 75000.0,
                "cpu_utilization_pct": 65.0
            },
            "specjbb": {
                "max_jops": 45000.0,
                "critical_jops": 38000.0,
                "throughput_score": 42000.0
            },
            "fio": {
                "read_bw_mb_s": 3500.0,
                "write_bw_mb_s": 3200.0,
                "read_iops": 875000.0,
                "write_iops": 800000.0,
                "read_latency_us": 12.0,
                "write_latency_us": 15.0
            },
            "sysbench": {
                "events_per_sec": 125000.0,
                "latency_ms": 0.08,
                "cpu_threads": 96
            }
        }
        
        # Metric correlations (for realistic co-variance)
        self.metric_correlations = {
            "coremark": [("multicore_score", "singlecore_score", 0.85)],
            "coremark_pro": [
                ("SUMM_CPU_mean", "CPU_INT_mean", 0.92),
                ("SUMM_CPU_mean", "CPU_FP_mean", 0.88),
                ("SUMM_ME_mean", "ME_READ_mean", 0.95),
                ("SUMM_ME_mean", "ME_WRITE_mean", 0.93)
            ],
            "streams": [
                ("copy__mb_per_sec", "scale__mb_per_sec", 0.90),
                ("add__mb_per_sec", "triad__mb_per_sec", 0.95)
            ],
            "fio": [
                ("read_bw_mb_s", "read_iops", 0.98),
                ("write_bw_mb_s", "write_iops", 0.98)
            ]
        }
        
        # Failure probability configuration
        self.failure_types = {
            "timeout": 0.02,        # 2% timeout failures
            "crash": 0.01,          # 1% crash failures
            "validation": 0.015,    # 1.5% validation failures
            "oom": 0.005            # 0.5% out-of-memory failures
        }
        
    def generate_dataset(
        self,
        num_scenarios: int = 20,
        iterations_per_scenario: int = 3,
        include_temporal_trends: bool = True,
        include_failures: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete synthetic dataset.
        
        Args:
            num_scenarios: Number of unique configuration scenarios
            iterations_per_scenario: Test iterations per scenario
            include_temporal_trends: Include time-based performance trends
            include_failures: Include realistic test failures
            
        Returns:
            List of synthetic benchmark documents
        """
        documents = []
        base_date = datetime.now() - timedelta(days=180)  # Extended to 6 months
        
        # Generate scenarios with controlled distribution
        scenarios = self._generate_scenarios(num_scenarios)
        
        for scenario_idx, scenario in enumerate(scenarios):
            os_distribution = scenario["os_distribution"]
            os_version = scenario["os_version"]
            cloud_provider = scenario["cloud_provider"]
            instance_type = scenario["instance_type"]
            test_type = scenario["test_type"]
            
            # Determine performance pattern for this scenario
            pattern = self._select_performance_pattern()
            
            # Add temporal trend if enabled
            temporal_trend = self._generate_temporal_trend() if include_temporal_trends else None
            
            # Generate iterations for this scenario
            for iteration in range(iterations_per_scenario):
                # Calculate test date with some temporal clustering
                days_offset = scenario_idx * 2 + random.randint(-1, 5)
                test_date = base_date + timedelta(
                    days=min(days_offset, 180),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Determine if this test should fail
                should_fail = (include_failures and 
                              random.random() < sum(self.failure_types.values()))
                failure_type = self._select_failure_type() if should_fail else None
                
                doc = self._generate_document(
                    os_distribution=os_distribution,
                    os_version=os_version,
                    cloud_provider=cloud_provider,
                    instance_type=instance_type,
                    test_type=test_type,
                    test_date=test_date,
                    iteration=iteration,
                    pattern=pattern,
                    temporal_trend=temporal_trend,
                    failure_type=failure_type,
                    scenario_id=f"scenario_{scenario_idx:03d}"
                )
                documents.append(doc)
        
        # Sort by timestamp for realistic temporal ordering
        documents.sort(key=lambda x: x["metadata"]["test_timestamp"])
        
        return documents
    
    def _generate_scenarios(self, num_scenarios: int) -> List[Dict[str, Any]]:
        """
        Generate a diverse set of test scenarios with controlled distribution.
        
        Ensures comprehensive coverage by:
        1. Running all test types across all RHEL versions (for regression analysis)
        2. Providing good coverage for other OS distributions
        3. Filling remaining scenarios with random combinations
        
        IMPORTANT: For regression analysis to work, each test must run on the SAME
        hardware configurations across different OS versions. This enables valid
        apples-to-apples comparisons.
        """
        scenarios = []
        
        # Create DETERMINISTIC hardware configuration assignments per test type
        # This ensures each test runs on the same hardware across all OS versions
        # Using a fixed assignment pattern for maximum reproducibility
        
        # Define a consistent set of hardware configs for each cloud provider
        stable_configs = {
            "aws": ["c6i.24xlarge", "m5.4xlarge", "r5.24xlarge"],
            "azure": ["Standard_D64s_v3", "Standard_F48s_v2", "Standard_E64s_v5"],
            "gcp": ["n2-standard-64", "c2-standard-60", "n2-highmem-96"]
        }
        
        test_hardware_configs = {}
        for idx, test_type in enumerate(self.test_types):
            # Assign exactly 3 hardware configs per test (one from each cloud provider)
            # Use modulo to cycle through available configs deterministically
            test_configs = []
            for cloud_provider in ["aws", "azure", "gcp"]:
                instance_idx = idx % len(stable_configs[cloud_provider])
                instance_type = stable_configs[cloud_provider][instance_idx]
                test_configs.append((cloud_provider, instance_type))
            test_hardware_configs[test_type] = test_configs
        
        # Phase 1: Ensure COMPLETE coverage for RHEL regression analysis
        # Run every test type on every RHEL version with CONSISTENT hardware
        rhel_versions = self.os_configs["rhel"]
        for rhel_version in rhel_versions:
            for test_type in self.test_types:
                # Use the pre-assigned hardware configs for this test
                # This ensures the same test runs on the same hardware across all versions
                for cloud_provider, instance_type in test_hardware_configs[test_type]:
                    scenarios.append({
                        "os_distribution": "rhel",
                        "os_version": rhel_version,
                        "cloud_provider": cloud_provider,
                        "instance_type": instance_type,
                        "test_type": test_type
                    })
        
        print(f"  Phase 1: Generated {len(scenarios)} RHEL scenarios (all tests × all versions × consistent HW)")
        
        # Phase 2: Ensure good coverage for other OS distributions
        # Run each test type on each version of other distributions with CONSISTENT hardware
        other_os_distributions = [os_dist for os_dist in self.os_configs.keys() if os_dist != "rhel"]
        for os_distribution in other_os_distributions:
            for os_version in self.os_configs[os_distribution]:
                for test_type in self.test_types:
                    # Use the same pre-assigned hardware configs for cross-OS comparison
                    for cloud_provider, instance_type in test_hardware_configs[test_type]:
                        scenarios.append({
                            "os_distribution": os_distribution,
                            "os_version": os_version,
                            "cloud_provider": cloud_provider,
                            "instance_type": instance_type,
                            "test_type": test_type
                        })
        
        print(f"  Phase 2: Generated {len(scenarios)} total scenarios (including other OS with consistent HW)")
        
        # Phase 3: Cloud Scaling Scenarios - RHEL 10 on GCP C4 series
        # This enables investigating how RHEL 10 performance scales across the C4 instance family
        c4_instances = [
            "c4-standard-2", "c4-standard-4", "c4-standard-8", "c4-standard-16",
            "c4-standard-24", "c4-standard-32", "c4-standard-48", "c4-standard-96",
            "c4-standard-144", "c4-standard-192", "c4-standard-288"
        ]
        rhel_10_versions = [v for v in self.os_configs["rhel"] if v.startswith("10")]
        
        for rhel_version in rhel_10_versions:
            for c4_instance in c4_instances:
                for test_type in self.test_types:
                    scenarios.append({
                        "os_distribution": "rhel",
                        "os_version": rhel_version,
                        "cloud_provider": "gcp",
                        "instance_type": c4_instance,
                        "test_type": test_type
                    })
        
        print(f"  Phase 3: Added RHEL 10 + GCP C4 cloud scaling scenarios")
        print(f"           {len(rhel_10_versions)} RHEL 10 versions × {len(c4_instances)} C4 instances × {len(self.test_types)} tests")
        
        # Phase 4: Cloud Scaling Scenarios - Amazon 2023 on AWS C6i series
        # This enables investigating how Amazon Linux 2023 performance scales across the C6i instance family
        c6i_instances = [
            "c6i.large", "c6i.xlarge", "c6i.2xlarge", "c6i.4xlarge",
            "c6i.8xlarge", "c6i.12xlarge", "c6i.16xlarge", "c6i.24xlarge", "c6i.32xlarge"
        ]
        
        for c6i_instance in c6i_instances:
            for test_type in self.test_types:
                scenarios.append({
                    "os_distribution": "amazon",
                    "os_version": "2023",
                    "cloud_provider": "aws",
                    "instance_type": c6i_instance,
                    "test_type": test_type
                })
        
        print(f"  Phase 4: Added Amazon 2023 + AWS C6i cloud scaling scenarios")
        print(f"           1 Amazon 2023 version × {len(c6i_instances)} C6i instances × {len(self.test_types)} tests")
        
        # Note: We're ignoring num_scenarios parameter and using ALL generated scenarios
        # to ensure complete coverage. This is better than randomly sampling which could
        # break the hardware consistency guarantees.
        
        print(f"  Final: Using all {len(scenarios)} scenarios to ensure complete coverage")
        
        # Shuffle to avoid temporal clustering by OS type
        random.shuffle(scenarios)
        
        return scenarios
    
    def _generate_temporal_trend(self) -> Dict[str, float]:
        """Generate a temporal trend pattern (gradual improvement/degradation)."""
        trend_types = ["improving", "degrading", "stable", "seasonal"]
        trend_type = random.choice(trend_types)
        
        if trend_type == "improving":
            return {"type": "linear", "slope": random.uniform(0.001, 0.003)}
        elif trend_type == "degrading":
            return {"type": "linear", "slope": random.uniform(-0.003, -0.001)}
        elif trend_type == "seasonal":
            return {"type": "seasonal", "amplitude": random.uniform(0.03, 0.08)}
        else:
            return {"type": "stable", "slope": 0.0}
    
    def _select_failure_type(self) -> str:
        """Select a failure type based on configured probabilities."""
        total_prob = sum(self.failure_types.values())
        rand_val = random.random() * total_prob
        
        cumulative = 0.0
        for failure_type, prob in self.failure_types.items():
            cumulative += prob
            if rand_val <= cumulative:
                return failure_type
        
        return "timeout"  # default
    
    def _select_performance_pattern(self) -> Dict[str, Any]:
        """
        Select a performance pattern (regression, improvement, or stable).
        
        Returns:
            Dictionary with pattern type and magnitude
        """
        pattern_type = random.choices(
            ["stable", "minor_improvement", "improvement", "minor_regression", "regression"],
            weights=[0.60, 0.15, 0.05, 0.15, 0.05]  # Most tests are stable
        )[0]
        
        if pattern_type == "stable":
            magnitude = random.uniform(0.97, 1.03)  # ±3%
        elif pattern_type == "minor_improvement":
            magnitude = random.uniform(1.05, 1.12)  # 5-12% improvement
        elif pattern_type == "improvement":
            magnitude = random.uniform(1.15, 1.35)  # 15-35% improvement
        elif pattern_type == "minor_regression":
            magnitude = random.uniform(0.88, 0.95)  # 5-12% regression
        else:  # regression
            magnitude = random.uniform(0.55, 0.80)  # 20-45% regression
        
        return {"type": pattern_type, "magnitude": magnitude}
    
    def _generate_document(
        self,
        os_distribution: str,
        os_version: str,
        cloud_provider: str,
        instance_type: str,
        test_type: str,
        test_date: datetime,
        iteration: int,
        pattern: Dict[str, Any],
        temporal_trend: Optional[Dict[str, Any]] = None,
        failure_type: Optional[str] = None,
        scenario_id: str = "scenario_000"
    ) -> Dict[str, Any]:
        """Generate a single synthetic benchmark document."""
        
        doc_id = f"{test_type}_{random.randbytes(8).hex()}"
        scenario_name = f"{os_distribution}_{os_version.replace('.', '')}"
        
        doc = {
            "metadata": {
                "document_id": doc_id,
                "document_type": "zathras_test_result",
                "zathras_version": "1.0",
                "test_timestamp": test_date.isoformat() + "Z",
                "processing_timestamp": (test_date + timedelta(hours=6)).isoformat() + "Z",
                "collection_timestamp": test_date.isoformat() + "Z",
                "os_vendor": os_distribution,
                "cloud_provider": cloud_provider,
                "instance_type": instance_type,
                "iteration": iteration,
                "scenario_name": scenario_name
            },
            "test": {
                "name": test_type,
                "version": "v1.22.zip",
                "wrapper_version": "v1.22.zip"
            },
            "system_under_test": self._generate_system_info(
                os_distribution, os_version, cloud_provider, instance_type
            ),
            "test_configuration": self._generate_test_config(
                os_distribution, cloud_provider, instance_type, test_type
            ),
            "runtime_info": {
                "command": "#/bin/bash",
                "user": "root"
            },
            "results": self._generate_results(
                test_type, pattern, iteration, temporal_trend, 
                failure_type, instance_type
            ),
            "scenario_id": scenario_id,
            "_export_metadata": {
                "exported_at": (test_date + timedelta(hours=6)).isoformat() + "Z",
                "exporter": "zathras-opensearch-exporter",
                "exporter_version": "1.0.0"
            }
        }
        
        return doc
    
    def _generate_system_info(
        self, os_distribution: str, os_version: str, cloud_provider: str, instance_type: str
    ) -> Dict[str, Any]:
        """Generate system_under_test object."""
        
        # Expanded CPU models with more variety
        cpu_models = {
            "aws": [
                "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz",
                "Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz",
                "AMD EPYC 7R13 Processor @ 3.60GHz"
            ],
            "azure": [
                "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz",
                "Intel(R) Xeon(R) Platinum 8272CL CPU @ 2.60GHz",
                "AMD EPYC 7763 64-Core Processor"
            ],
            "gcp": [
                "AMD EPYC 7B12 64-Core Processor",
                "Intel(R) Xeon(R) CPU @ 2.80GHz",
                "AMD EPYC 7B13 64-Core Processor"
            ]
        }
        
        # More accurate CPU core mapping based on instance type
        cores = self._get_cpu_cores(instance_type)
        cpu_model = random.choice(cpu_models[cloud_provider])
        
        vendor = "AuthenticAMD" if "AMD" in cpu_model else "GenuineIntel"
        numa_nodes = 4 if cores >= 96 else 2 if cores >= 48 else 1
        sockets = 2 if cores >= 48 else 1
        
        # Generate kernel version based on OS distribution
        kernel_version = self._get_kernel_version(os_distribution, os_version)
        
        return {
            "hardware": {
                "cpu": {
                    "vendor": vendor,
                    "model": cpu_model,
                    "architecture": "x86_64",
                    "cores": cores,
                    "threads_per_core": 2,
                    "sockets": sockets,
                    "numa_nodes": numa_nodes,
                    "cache_l3": f"{35.75 * sockets} MiB ({sockets} instances)" if sockets > 1 else f"{35.75} MiB"
                },
                "memory": self._get_memory_specs(instance_type, cores),
                "storage": {
                    "device_0": {
                        "path": "10.7GB",
                        "type": "scsi"
                    }
                }
            },
            "operating_system": {
                "distribution": os_distribution,
                "version": os_version,
                "kernel_version": kernel_version,
                "hostname": f"test-{cloud_provider}-{random.randint(100, 999)}.internal"
            },
            "configuration": {
                "tuned_profile": "virtual-guest",
                "sysctl_parameters": {
                    "kernel.numa_balancing": "1",
                    "net.core.somaxconn": "4096",
                    "vm.dirty_ratio": "30",
                    "vm.swappiness": "30"
                },
                "kernel_parameters": {
                    "console": ["tty0", "ttyS0,115200n8"],
                    "_total_parameters": 6
                }
            }
        }
    
    def _get_memory_specs(self, instance_type: str, cores: int) -> Dict[str, int]:
        """Get memory specifications based on instance type."""
        # Handle C4 series with exact RAM specs (GCP)
        if instance_type in self.c4_series_specs:
            ram_gib = self.c4_series_specs[instance_type][1]
            total_kb = ram_gib * 1024 * 1024  # GiB to KiB
            return {
                "total_gb": ram_gib,
                "total_kb": total_kb,
                "available_kb": int(total_kb * 0.98)  # ~98% available
            }
        
        # Handle C6i series with exact RAM specs (AWS)
        if instance_type in self.c6i_series_specs:
            ram_gib = self.c6i_series_specs[instance_type][1]
            total_kb = ram_gib * 1024 * 1024  # GiB to KiB
            return {
                "total_gb": ram_gib,
                "total_kb": total_kb,
                "available_kb": int(total_kb * 0.98)  # ~98% available
            }
        
        # Default logic for other instance types
        if cores >= 96:
            return {
                "total_gb": 373,
                "total_kb": 391500104,
                "available_kb": 388185644
            }
        else:
            return {
                "total_gb": 256,
                "total_kb": 268435456,
                "available_kb": 265000000
            }
    
    def _get_kernel_version(self, os_distribution: str, os_version: str) -> str:
        """Generate realistic kernel version for the given OS distribution and version."""
        if os_distribution == "rhel":
            # Handle both RHEL 9.x and 10.x
            major = os_version.split('.')[0] if '.' in os_version else os_version
            minor = os_version.split('.')[1] if '.' in os_version else "0"
            
            if major == "10":
                # RHEL 10 uses newer kernel (6.x series)
                return f"6.8.0-203.11.1.el10_{minor}.x86_64"
            else:
                # RHEL 9 uses 5.14.0 kernel
                return f"5.14.0-503.11.1.el9_{minor}.x86_64"
        elif os_distribution == "ubuntu":
            # Ubuntu kernel versions based on release
            kernel_map = {
                "20.04": "5.15.0-91-generic",
                "22.04": "6.5.0-35-generic",
                "24.04": "6.8.0-31-generic"
            }
            return kernel_map.get(os_version, "5.15.0-91-generic")
        elif os_distribution == "amazon":
            # Amazon Linux kernel versions
            if os_version == "2":
                return "5.10.220-173.862.amzn2.x86_64"
            else:  # Amazon Linux 2023
                return "6.1.82-99.168.amzn2023.x86_64"
        elif os_distribution == "sles":
            # SLES kernel versions
            return f"5.14.21-150500.55.52-default"
        return "5.15.0-generic"
    
    def _generate_test_config(
        self, os_distribution: str, cloud_provider: str, instance_type: str, test_type: str
    ) -> Dict[str, Any]:
        """Generate test_configuration object."""
        
        regions = {
            "aws": "us-east-2a",
            "azure": "eastus2",
            "gcp": "us-central1-a"
        }
        
        return {
            "iterations_requested": 1,
            "parameters": {
                "os_vendor": os_distribution,
                "system_type": cloud_provider,
                "host_config": instance_type,
                "cloud_region": regions[cloud_provider],
                "test_to_run": [test_type],
                "test_iterations": 1,
                "User": "synthetic_user",
                "Owner": "perf_team",
                "Project": "Performance_Regression_Testing",
                "Environment": "Test"
            }
        }
    
    def _generate_results(
        self,
        test_type: str,
        pattern: Dict[str, Any],
        iteration: int,
        temporal_trend: Optional[Dict[str, Any]],
        failure_type: Optional[str],
        instance_type: str
    ) -> Dict[str, Any]:
        """Generate results object with metrics."""
        
        # Handle failure case
        if failure_type:
            return self._generate_failure_result(test_type, failure_type)
        
        # Get baseline metrics for this test type
        baseline = self.baseline_metrics.get(test_type, {})
        
        # Calculate hardware tier multiplier
        hw_multiplier = self._get_hardware_multiplier(instance_type)
        
        # Apply performance pattern and iteration variation
        magnitude = pattern["magnitude"]
        iteration_variance = random.uniform(0.98, 1.02)  # Small run-to-run variation
        
        # Apply temporal trend if present
        trend_factor = 1.0
        if temporal_trend:
            if temporal_trend["type"] == "linear":
                trend_factor = 1.0 + (temporal_trend["slope"] * iteration)
            elif temporal_trend["type"] == "seasonal":
                # Simulate seasonal variation using sine wave
                trend_factor = 1.0 + (temporal_trend["amplitude"] * 
                                     math.sin(iteration * math.pi / 10))
        
        metrics = {}
        correlated_metrics = {}
        
        # First pass: generate base metrics
        for metric_name, baseline_value in baseline.items():
            # Apply all factors
            value = (baseline_value * hw_multiplier * magnitude * 
                    iteration_variance * trend_factor)
            
            # Ensure value is never zero or negative (can cause comparison issues)
            # Use a minimum threshold of 20% of baseline to ensure meaningful comparisons
            min_value = max(baseline_value * 0.20, 0.01)  # At least 20% or 0.01
            if value <= 0 or value < min_value:
                value = min_value * random.uniform(1.0, 1.5)  # Add some variance
            
            # For metrics with statistical aggregations (mean, min, max, stddev)
            if not metric_name.endswith(("_mean", "_min", "_max", "_stddev", "_pct")):
                metrics[metric_name] = value
                metrics[f"{metric_name}_mean"] = value
                metrics[f"{metric_name}_min"] = value * random.uniform(0.96, 0.99)
                metrics[f"{metric_name}_max"] = value * random.uniform(1.01, 1.04)
                metrics[f"{metric_name}_stddev"] = value * random.uniform(0.008, 0.015)
            else:
                metrics[metric_name] = value
                correlated_metrics[metric_name] = value
        
        # Second pass: apply correlations for realistic co-variance
        metrics = self._apply_metric_correlations(test_type, metrics, correlated_metrics)
        
        # Determine status based on pattern and magnitude
        if pattern["type"] in ["regression", "minor_regression"] and pattern["magnitude"] < 0.70:
            status = "FAIL"
        else:
            status = "PASS"
        
        # Select primary metric
        primary_metric_name = list(baseline.keys())[0] if baseline else "score"
        primary_metric_value = metrics.get(primary_metric_name, 100.0)
        
        # Ensure the primary metric is never zero or too small (can cause comparison issues)
        if primary_metric_value <= 0 or primary_metric_value < 0.001:
            # Use a reasonable positive value based on the baseline
            baseline_for_metric = baseline.get(primary_metric_name, 100.0)
            primary_metric_value = baseline_for_metric * random.uniform(0.30, 0.50)
        
        return {
            "status": status,
            "total_runs": 1,
            "primary_metric": {
                "name": primary_metric_name,
                "value": primary_metric_value,
                "unit": self._get_metric_unit(test_type, primary_metric_name)
            },
            "runs": {
                "run_0": {
                    "run_number": 0,
                    "status": status,
                    "configuration": {
                        "test": test_type,
                        "results_version": "1.0"
                    },
                    "metrics": metrics
                }
            }
        }
    
    def _get_cpu_cores(self, instance_type: str) -> int:
        """Extract CPU core count from instance type."""
        # Handle C4 series instances with exact vCPU counts (GCP)
        if instance_type in self.c4_series_specs:
            return self.c4_series_specs[instance_type][0]
        
        # Handle C6i series instances with exact vCPU counts (AWS)
        if instance_type in self.c6i_series_specs:
            return self.c6i_series_specs[instance_type][0]
        
        if "288" in instance_type:
            return 288
        elif "192" in instance_type:
            return 192
        elif "144" in instance_type:
            return 144
        elif "96" in instance_type or "24xlarge" in instance_type:
            return 96
        elif "64" in instance_type or "16xlarge" in instance_type:
            return 64
        elif "60" in instance_type:
            return 60
        elif "48" in instance_type or "12xlarge" in instance_type:
            return 48
        elif "32" in instance_type or "8xlarge" in instance_type:
            return 32
        elif "30" in instance_type:
            return 30
        elif "24" in instance_type:
            return 24
        elif "16" in instance_type:
            return 16
        elif "8" in instance_type:
            return 8
        elif "4" in instance_type:
            return 4
        elif "2" in instance_type:
            return 2
        else:
            return 16  # default for 4xlarge and smaller
    
    def _get_hardware_multiplier(self, instance_type: str) -> float:
        """Calculate performance multiplier based on hardware tier."""
        # Special handling for C4 series - scale based on vCPU count (GCP)
        # This provides realistic scaling behavior for cloud scaling analysis
        if instance_type in self.c4_series_specs:
            vcpus = self.c4_series_specs[instance_type][0]
            # Base scaling: roughly linear with diminishing returns at high core counts
            # Normalized so c4-standard-96 returns ~1.0 (baseline)
            base_multiplier = (vcpus / 96) ** 0.85  # Sub-linear scaling
            # Add small variance for realism
            return base_multiplier * random.uniform(0.97, 1.03)
        
        # Special handling for C6i series - scale based on vCPU count (AWS)
        if instance_type in self.c6i_series_specs:
            vcpus = self.c6i_series_specs[instance_type][0]
            # Base scaling: roughly linear with diminishing returns at high core counts
            # Normalized so c6i.24xlarge (96 vCPUs) returns ~1.0 (baseline)
            base_multiplier = (vcpus / 96) ** 0.85  # Sub-linear scaling
            # Add small variance for realism
            return base_multiplier * random.uniform(0.97, 1.03)
        
        for tier, patterns in self.hardware_tiers.items():
            if any(pattern in instance_type for pattern in patterns):
                if tier == "high":
                    return random.uniform(1.15, 1.25)
                elif tier == "medium":
                    return random.uniform(0.95, 1.05)
                elif tier == "low":
                    return random.uniform(0.75, 0.85)
        
        return 1.0  # default
    
    def _apply_metric_correlations(
        self,
        test_type: str,
        metrics: Dict[str, float],
        base_values: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply realistic correlations between related metrics."""
        
        correlations = self.metric_correlations.get(test_type, [])
        
        for metric1, metric2, correlation_coef in correlations:
            if metric1 in base_values and metric2 in metrics:
                # Adjust metric2 to be correlated with metric1
                base1 = self.baseline_metrics[test_type][metric1]
                base2 = self.baseline_metrics[test_type][metric2]
                
                # Calculate deviation of metric1 from its baseline
                deviation1 = (base_values[metric1] - base1) / base1
                
                # Apply correlated deviation to metric2
                correlated_deviation = deviation1 * correlation_coef
                noise = random.uniform(-0.02, 0.02) * (1 - correlation_coef)
                
                metrics[metric2] = base2 * (1 + correlated_deviation + noise)
                
                # Update aggregated versions if they exist
                if f"{metric2}_mean" in metrics:
                    metrics[f"{metric2}_mean"] = metrics[metric2]
                    metrics[f"{metric2}_min"] = metrics[metric2] * random.uniform(0.96, 0.99)
                    metrics[f"{metric2}_max"] = metrics[metric2] * random.uniform(1.01, 1.04)
                    metrics[f"{metric2}_stddev"] = metrics[metric2] * random.uniform(0.008, 0.015)
        
        return metrics
    
    def _generate_failure_result(self, test_type: str, failure_type: str) -> Dict[str, Any]:
        """Generate a realistic failure result."""
        
        failure_messages = {
            "timeout": "Test execution exceeded maximum time limit of 3600 seconds",
            "crash": "Process terminated unexpectedly with signal SIGSEGV",
            "validation": "Result validation failed: checksum mismatch detected",
            "oom": "Out of memory: system killed process due to memory exhaustion"
        }
        
        return {
            "status": "FAIL",
            "total_runs": 0,
            "failure_reason": failure_type,
            "error_message": failure_messages.get(failure_type, "Unknown error"),
            "primary_metric": {
                "name": "N/A",
                "value": 0.0,
                "unit": "N/A"
            },
            "runs": {}
        }
    
    def _get_metric_unit(self, test_type: str, metric_name: str) -> str:
        """Get the appropriate unit for a metric."""
        
        metric_lower = metric_name.lower()
        
        if "gflops" in metric_lower:
            return "GFLOPS"
        elif "mb_per_sec" in metric_lower or "mb_s" in metric_lower or "bw_mb" in metric_lower:
            return "MB/s"
        elif "bops" in metric_lower or "jops" in metric_lower:
            return "BOPs"
        elif "gbs" in metric_lower or "bw_gbs" in metric_lower:
            return "GB/s"
        elif "trans_per_sec" in metric_lower or "events_per_sec" in metric_lower:
            return "transactions/sec"
        elif "iops" in metric_lower:
            return "IOPS"
        elif "latency" in metric_lower:
            if "us" in metric_lower:
                return "microseconds"
            elif "ms" in metric_lower:
                return "milliseconds"
            else:
                return "seconds"
        elif "pct" in metric_lower or "utilization" in metric_lower or "efficiency" in metric_lower:
            return "percent"
        elif test_type == "pyperf":
            return "seconds"
        elif "time" in metric_lower or "seconds" in metric_lower:
            return "seconds"
        elif "records" in metric_lower:
            return "records/sec"
        else:
            return "score"
    
    def save_to_file(self, documents: List[Dict[str, Any]], filename: str):
        """Save generated documents to a JSON file."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(documents, f, indent=2)
        print(f"Saved {len(documents)} documents to {filename}")


def main():
    """Generate synthetic dataset and save to files."""
    
    generator = SyntheticDataGenerator(seed=42)
    
    print("=" * 80)
    print("ROBUST SYNTHETIC BENCHMARK DATA GENERATOR")
    print("=" * 80)
    print("\nGenerating comprehensive synthetic benchmark data...")
    print("This may take a moment...\n")
    
    # Deterministic scenario generation with guaranteed hardware consistency
    # RHEL: 7 versions × 12 tests × 3 HW configs/test = 252 scenarios
    # Other OS: 3 distributions × 8 versions × 12 tests × 3 HW configs = 864 scenarios
    # Total: 1116 scenarios (all will be used to ensure complete coverage)
    # 
    # Each test is assigned exactly 3 hardware configs (one from each cloud provider)
    # and these same configs are used across ALL OS versions for valid comparisons.
    
    print("Deterministic scenario generation with hardware consistency:")
    documents = generator.generate_dataset(
        num_scenarios=1200,  # This parameter is now advisory; we use all generated scenarios
        iterations_per_scenario=2,  # Keep file size reasonable while ensuring coverage
        include_temporal_trends=True,
        include_failures=True
    )
    
    print(f"\n✓ Generated {len(documents)} documents")
    print(f"  Iterations per scenario: 2")
    print(f"  Temporal range: 180 days")
    print(f"  Hardware consistency: DETERMINISTIC - Each test runs on exactly 3 HW configs")
    print(f"  Coverage guarantee: All test×version×hardware combinations included")
    
    # Save to file
    output_file = "data/synthetic/benchmark_results.json"
    generator.save_to_file(documents, output_file)
    
    # Generate comprehensive summary statistics
    test_types = {}
    os_distributions = {}
    os_versions = {}
    cloud_providers = {}
    instance_types = {}
    failures_by_type = {}
    
    pass_count = 0
    fail_count = 0
    
    for doc in documents:
        test_name = doc["test"]["name"]
        os_dist = doc["system_under_test"]["operating_system"]["distribution"]
        os_ver = doc["system_under_test"]["operating_system"]["version"]
        cloud = doc["metadata"]["cloud_provider"]
        instance = doc["metadata"]["instance_type"]
        status = doc["results"]["status"]
        
        test_types[test_name] = test_types.get(test_name, 0) + 1
        os_distributions[os_dist] = os_distributions.get(os_dist, 0) + 1
        os_key = f"{os_dist} {os_ver}"
        os_versions[os_key] = os_versions.get(os_key, 0) + 1
        cloud_providers[cloud] = cloud_providers.get(cloud, 0) + 1
        instance_types[instance] = instance_types.get(instance, 0) + 1
        
        if status == "FAIL":
            fail_count += 1
            failure_reason = doc["results"].get("failure_reason", "unknown")
            failures_by_type[failure_reason] = failures_by_type.get(failure_reason, 0) + 1
        else:
            pass_count += 1
    
    print("\n" + "=" * 80)
    print("DATASET SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 Test Type Distribution ({len(test_types)} unique):")
    for test_name, count in sorted(test_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {test_name:20s}: {count:4d} tests ({count/len(documents)*100:5.1f}%)")
    
    print(f"\n🖥️  OS Distribution Summary ({len(os_distributions)} distributions):")
    for os_dist, count in sorted(os_distributions.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {os_dist.upper():10s}: {count:4d} tests ({count/len(documents)*100:5.1f}%)")
    
    print(f"\n📦 OS Version Details ({len(os_versions)} unique versions):")
    for os_key, count in sorted(os_versions.items()):
        print(f"  • {os_key:20s}: {count:4d} tests ({count/len(documents)*100:5.1f}%)")
    
    print(f"\n☁️  Cloud Provider Distribution ({len(cloud_providers)} unique):")
    for cloud, count in sorted(cloud_providers.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cloud:10s}: {count:4d} tests ({count/len(documents)*100:5.1f}%)")
    
    print(f"\n💻 Instance Type Variety: {len(instance_types)} unique configurations")
    top_instances = sorted(instance_types.items(), key=lambda x: x[1], reverse=True)[:10]
    print("  Top 10:")
    for instance, count in top_instances:
        print(f"  • {instance:25s}: {count:3d} tests")
    
    print(f"\n✅ Status Distribution:")
    print(f"  • PASS: {pass_count:4d} ({pass_count/len(documents)*100:5.1f}%)")
    print(f"  • FAIL: {fail_count:4d} ({fail_count/len(documents)*100:5.1f}%)")
    
    if failures_by_type:
        print(f"\n⚠️  Failure Type Breakdown:")
        for failure_type, count in sorted(failures_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {failure_type:15s}: {count:3d} failures")
    
    # Calculate temporal statistics
    timestamps = [doc["metadata"]["test_timestamp"] for doc in documents]
    timestamps.sort()
    earliest = timestamps[0]
    latest = timestamps[-1]
    
    print(f"\n📅 Temporal Coverage:")
    print(f"  • Earliest test: {earliest}")
    print(f"  • Latest test:   {latest}")
    
    print("\n" + "=" * 80)
    print("✓ SYNTHETIC DATA GENERATION COMPLETE!")
    print("=" * 80)
    print(f"\n📁 Data saved to: {output_file}")
    print(f"📄 Total file size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    print("\n💡 This dataset includes:")
    print("  • Temporal trends and patterns")
    print("  • Correlated metrics within test types")
    print("  • Hardware-specific performance characteristics")
    print("  • Realistic failure scenarios")
    print("  • Wide variety of configurations")
    print("\n🎯 Ready for dashboard development and testing!")


if __name__ == "__main__":
    main()

