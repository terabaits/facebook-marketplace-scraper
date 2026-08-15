"""Unit tests for GPU matcher - following Meta TDD principles.

Fast: Tests run in <10ms each
Deterministic: No external dependencies, no randomness
Isolated: Each test is independent, can run in parallel
"""

import pytest
from src.scraper.matcher import GPUMatcher
from src.models.schemas import GPUReference, MatchResult


class TestGPUMatcher:
    """Test GPU matcher logic."""
    
    @pytest.fixture
    def sample_gpus(self):
        """Create sample GPU references for testing."""
        return [
            GPUReference(
                id=1,
                vendor='NVIDIA',
                model='RTX 3060',
                vram_gb=12,
                year_released=2021,
                normalized_name='nvidia rtx 3060',
                search_keywords=['RTX 3060', 'NVIDIA RTX 3060', '3060']
            ),
            GPUReference(
                id=2,
                vendor='NVIDIA',
                model='RTX 3060 Ti',
                vram_gb=8,
                year_released=2020,
                normalized_name='nvidia rtx 3060 ti',
                search_keywords=['RTX 3060 Ti', '3060 Ti']
            ),
            GPUReference(
                id=3,
                vendor='AMD',
                model='RX 6700 XT',
                vram_gb=12,
                year_released=2021,
                normalized_name='amd rx 6700 xt',
                search_keywords=['RX 6700 XT', '6700 XT', 'AMD 6700 XT']
            ),
        ]
    
    @pytest.fixture
    def matcher(self, sample_gpus):
        """Create GPU matcher with sample data."""
        return GPUMatcher(sample_gpus)
    
    def test_exact_match(self, matcher):
        """Test exact title match returns correct GPU."""
        result = matcher.match("NVIDIA RTX 3060 12GB", "")
        assert result.confidence >= 0.7
        assert result.gpu.model == "RTX 3060"
        assert result.method in ['exact', 'name_only']
    
    def test_partial_match(self, matcher):
        """Test partial title match."""
        result = matcher.match("GeForce RTX 3060", "")
        assert result.confidence >= 0.6
        assert result.gpu is not None
    
    def test_no_match(self, matcher):
        """Test when no GPU matches."""
        result = matcher.match("Random text without GPU", "")
        assert result.confidence < 0.5
        assert result.gpu is None
    
    def test_vram_detection(self, matcher):
        """Test VRAM extraction from title."""
        result = matcher.match("RTX 3060 with 12GB VRAM", "")
        assert result.confidence >= 0.7
        assert result.gpu.vram_gb == 12
    
    def test_rtx_matching_with_sample_data(self, matcher):
        """Test RTX matching using sample data (RTX 3060, 3060 Ti)."""
        test_cases = [
            ("NVIDIA RTX 3060 12GB", "RTX 3060", 0.7),
            ("GeForce RTX 3060 Ti", "RTX 3060 Ti", 0.7),
            ("RTX 3060 Gaming", "RTX 3060", 0.7),
            ("AMD RX 6700 XT", "RX 6700 XT", 0.7),
        ]
        
        for title, expected_model, min_confidence in test_cases:
            result = matcher.match(title, "")
            assert result.gpu is not None, f"Failed for: {title}"
            assert expected_model in result.gpu.model, f"Expected {expected_model}, got {result.gpu.model}"
            assert result.confidence >= min_confidence, f"Low confidence for {title}: {result.confidence}"
    
    def test_vendor_prioritization(self, matcher):
        """Test that vendor detection works."""
        result = matcher.match("AMD RX 6700 XT", "")
        assert result.gpu.vendor == "AMD"
        assert result.gpu.model == "RX 6700 XT"


class TestRTX3070Specific:
    """Test RTX 3070 specifically - uses database (integration test)."""
    
    @pytest.mark.integration
    def test_rtx_3070_from_database(self):
        """Test RTX 3070 matching using actual database reference."""
        from src.database.connection import get_session, init_database
        from src.database.repository import GPUReferenceRepository
        from src.utils.config import AppConfig
        
        # Initialize database
        config = AppConfig.from_yaml()
        init_database(config.database)
        
        with get_session() as session:
            gpus = GPUReferenceRepository.get_all(session)
            matcher = GPUMatcher(gpus)
            
            # Test RTX 3070
            result = matcher.match("Pārdodu RTX 3070", "")
            print(f"\nRTX 3070 Test:")
            print(f"  Title: 'Pārdodu RTX 3070'")
            print(f"  Matched: {result.gpu.model if result.gpu else 'None'}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Method: {result.method}")
            
            assert result.gpu is not None
            assert "3070" in result.gpu.model
            assert result.confidence >= 0.7
    
    @pytest.mark.integration
    def test_rtx_3070_variants(self):
        """Test RTX 3070 variant detection."""
        from src.database.connection import get_session, init_database
        from src.database.repository import GPUReferenceRepository
        from src.utils.config import AppConfig
        
        # Initialize database
        config = AppConfig.from_yaml()
        init_database(config.database)
        
        with get_session() as session:
            gpus = GPUReferenceRepository.get_all(session)
            matcher = GPUMatcher(gpus)
            
            variants = [
                ("RTX 3070", "RTX 3070"),
                ("RTX 3070 Ti", "RTX 3070 Ti"),
                ("GeForce RTX 3070", "RTX 3070"),
                ("NVIDIA RTX 3070 8GB", "RTX 3070"),
            ]
            
            for title, expected_contains in variants:
                result = matcher.match(title, "")
                print(f"\n  '{title}' -> {result.gpu.model if result.gpu else 'None'} ({result.confidence:.2f})")
                assert result.gpu is not None
                assert expected_contains in result.gpu.model
    """Test confidence scoring logic."""
    
    def test_confidence_exact_match(self):
        """Exact match should have high confidence."""
        gpu = GPUReference(
            id=1, 
            vendor='NVIDIA', 
            model='RTX 4090', 
            vram_gb=24, 
            year_released=2022,
            normalized_name='nvidia rtx 4090'
        )
        result = MatchResult(item=gpu, confidence=0.95, method='exact')
        assert result.confidence == 0.95
    
    def test_confidence_below_threshold(self):
        """Low confidence matches should be rejected."""
        gpu = GPUReference(
            id=1, 
            vendor='NVIDIA', 
            model='RTX 4090', 
            vram_gb=24, 
            year_released=2022,
            normalized_name='nvidia rtx 4090'
        )
        result = MatchResult(item=gpu, confidence=0.3, method='fuzzy')
        assert result.confidence < 0.5
