"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime
from src.models.schemas import Listing, GPUReference, CPUReference


@pytest.fixture
def sample_listing():
    """Create a sample listing for testing."""
    return Listing(
        listing_id="test_001",
        title="NVIDIA RTX 3060 12GB",
        description="Great condition GPU",
        price_eur=350.0,
        seller_location="Riga",
        listing_url="https://test.com/1",
        date_posted=datetime.now(),
        category="gpu",
        source="test",
        is_active=True,
        matched_gpu_id=1,
        confidence_score=0.95
    )


@pytest.fixture
def mock_gpu_reference():
    """Create a mock GPU reference."""
    return GPUReference(
        id=1,
        vendor="NVIDIA",
        model="RTX 3060",
        vram_gb=12,
        year_released=2021
    )


@pytest.fixture
def mock_cpu_reference():
    """Create a mock CPU reference."""
    return CPUReference(
        id=1,
        producer="Intel",
        cpu_name="Core i5-12400F",
        processor_number="i5-12400F",
        cores=6,
        threads=12,
        socket="LGA1700"
    )
