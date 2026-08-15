        """
        Match listing text to best console reference.
        
        Args:
            title: Listing title
            description: Listing description
            price: Listing price in EUR (for default model selection)
        
        Returns ConsoleMatchResult with matched console, variant, and edition
        """
        full_text = f"{title} {description}".strip()
        if not full_text:
            return ConsoleMatchResult()
        
        normalized_title = normalize_text(title)
        normalized_full = normalize_text(full_text)
        
        # Step 1: Match console - prioritize title matches
        console_match, console_confidence = self._match_console(normalized_title, title)
        
        # If no confident match from title, try with full text
        if not console_match or console_confidence < 0.7:
            console_match_full, console_confidence_full = self._match_console(normalized_full, full_text)
            if console_match_full:
                console_match = console_match_full
                console_confidence = console_confidence_full * 0.9  # Lower confidence for description-based match
        
        if not console_match:
            # Try fallback matching for common patterns
            console_match, console_confidence = self._fallback_console_match(normalized_title)
            if not console_match:
                console_match, console_confidence = self._fallback_console_match(normalized_full)
            if not console_match:
                return ConsoleMatchResult(confidence=0.0, method="none")
        
        # Step 2: Match variant (if console matched)
        variant_match = None
        variant_confidence = 0.0
        if console_match:
            # Try title first for variant matching
            variant_match, variant_confidence = self._match_variant(
                normalized_title, title, console_match.id
            )
            
            # If no variant from title, try full text
            if not variant_match:
                variant_match, variant_confidence = self._match_variant(
                    normalized_full, full_text, console_match.id
                )
