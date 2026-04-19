"""Test fixtures and unit tests for the parser."""
import pytest
from src.scraper.parser import ListingParser
from src.scraper.matcher import GPUMatcher


# Mock HTML fixture for a typical ss.com listing
SAMPLE_LISTING_HTML = '''
<!DOCTYPE html>
<html>
<head><title>RTX 3080 - Test Listing</title></head>
<body>
<h2>Nvidia Geforce RTX 3080 10GB Gaming X Trio - Kā jauna</h2>
<div class="ads_price">€ 450.00</div>
<div id="msg_div_msg">
    <p>Pārdodu lietotu RTX 3080 video karti.</p>
    <p>Kartīte darbojas ideāli, temperatūras normas.</p>
    <table>...</table>
</div>
<img class="pic_thumbnail" src="/upload/2024/01/pic123.jpg">
<td class="msg_footer">Datums: 11.04.2026 14:30</td>
<td class="ads_contacts_name">Vieta:</td>
<td class="ads_contacts">Rīga</td>
</body>
</html>
'''

# Category page fixture
SAMPLE_CATEGORY_HTML = '''
<!DOCTYPE html>
<html>
<body>
<table>
<tr>
    <td class="msg_icon"></td>
    <td class="pmsg"><a href="/msg/lv/electronics/computers/completing-pc/video/123.html">RTX 3080</a></td>
    <td>€450</td>
</tr>
<tr>
    <td class="msg_icon"></td>
    <td class="pmsg"><a href="/msg/lv/electronics/computers/completing-pc/video/124.html">GTX 1060 6GB</a></td>
    <td>€120</td>
</tr>
</table>
<a href="/lv/electronics/computers/completing-pc/video/page2.html">Nākošie</a>
</body>
</html>
'''


class TestListingParser:
    """Tests for the HTML parser."""
    
    def test_extract_listing_id_from_url(self):
        """Test listing ID extraction from URL."""
        parser = ListingParser("", "https://www.ss.com/msg/.../sell/123.html")
        assert parser.listing_id == "123"
    
    def test_parse_title(self):
        """Test title extraction."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert "RTX 3080" in listing.title
    
    def test_parse_price(self):
        """Test price extraction and conversion."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert listing.price_eur == 450.00
    
    def test_parse_description(self):
        """Test description extraction (table removed)."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert "RTX 3080" in listing.description
        assert "table" not in listing.description.lower()
    
    def test_parse_date(self):
        """Test date extraction in Latvian format."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert listing.date_posted is not None
        assert listing.date_posted.year == 2026
        assert listing.date_posted.month == 4
        assert listing.date_posted.day == 11
    
    def test_parse_location(self):
        """Test location extraction."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert "Rīga" in listing.seller_location
    
    def test_get_category_links(self):
        """Test category page link extraction."""
        parser = ListingParser(SAMPLE_CATEGORY_HTML, "https://www.ss.com/category.html")
        links = parser.get_category_links()
        
        assert len(links) == 2
        assert "123.html" in links[0]
        assert "124.html" in links[1]
    
    def test_has_next_page(self):
        """Test pagination detection."""
        parser = ListingParser(SAMPLE_CATEGORY_HTML, "https://www.ss.com/category.html")
        next_url = parser.has_next_page()
        
        assert next_url is not None
        assert "page2.html" in next_url
    
    def test_content_hash_generation(self):
        """Test content hash for duplicate detection."""
        parser = ListingParser(SAMPLE_LISTING_HTML, "https://www.ss.com/test.html")
        listing = parser.parse()
        
        assert listing is not None
        assert listing.content_hash is not None
        assert len(listing.content_hash) == 64  # SHA256 hex


class TestGPUMatcher:
    """Tests for GPU matching."""
    
    def setup_method(self):
        """Set up GPU matcher with test data."""
        test_gpus = [
            type('GPU', (), {
                'id': 1,
                'vendor': 'NVIDIA',
                'model': 'GeForce RTX 3080',
                'search_keywords': ['rtx3080', 'geforce rtx 3080', 'g rtx 3080'],
                'normalized_name': 'rtx3080'
            })(),
            type('GPU', (), {
                'id': 2,
                'vendor': 'NVIDIA',
                'model': 'GeForce GTX 1060 6GB',
                'search_keywords': ['gtx1060', 'gtx10606gb', 'geforce gtx 1060'],
                'normalized_name': 'gtx10606gb'
            })(),
            type('GPU', (), {
                'id': 3,
                'vendor': 'AMD',
                'model': 'Radeon RX 580',
                'search_keywords': ['rx580', 'radeon rx 580', 'amdrx580'],
                'normalized_name': 'rx580'
            })(),
        ]
        self.matcher = GPUMatcher(test_gpus)
    
    def test_exact_match(self):
        """Test exact token matching."""
        result = self.matcher.match("Pārdodu RTX 3080", "")
        
        assert result.gpu is not None
        assert result.confidence == 1.0
        assert result.method == "exact"
    
    def test_fuzzy_match(self):
        """Test fuzzy matching."""
        result = self.matcher.match("Nvidia RTX 3080 Gaming", "")
        
        assert result.gpu is not None
        assert result.confidence > 0.7
        assert result.gpu.vendor == "NVIDIA"
    
    def test_no_match(self):
        """Test when no GPU is found."""
        result = self.matcher.match("Random computer parts", "")
        
        assert result.gpu is None
        assert result.confidence == 0.0
        assert result.method == "none"
    
    def test_latvian_title_normalization(self):
        """Test matching with Latvian diacritics."""
        result = self.matcher.match("Radeon RX 580 - kā jauna", "")
        
        # 'kā' contains ā which should be normalized to 'a'
        assert result.gpu is not None
        assert result.gpu.model == "Radeon RX 580"
    
    def test_cyrillic_text(self):
        """Test matching with Cyrillic text."""
        # Some sellers use Cyrillic
        result = self.matcher.match("Видеокарта GTX 1060", "")
        
        assert result.gpu is not None
        assert "1060" in result.gpu.model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
