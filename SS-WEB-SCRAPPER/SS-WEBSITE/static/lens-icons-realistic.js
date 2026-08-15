// Realistic SVG lens icons based on actual lens designs
// Proportions, colors, and details match real lenses

const lensIcons = {
    // Canon EF 70-200mm f/2.8L IS III USM - White telephoto zoom (V-SHAPE - tapered at front)
    'Canon_70-200': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c70200Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f8f8f8"/>
      <stop offset="20%" style="stop-color:#f0f0f0"/>
      <stop offset="50%" style="stop-color:#e8e8e8"/>
      <stop offset="80%" style="stop-color:#f0f0f0"/>
      <stop offset="100%" style="stop-color:#f8f8f8"/>
    </linearGradient>
    <linearGradient id="c70200Red" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#c41e3a"/>
      <stop offset="100%" style="stop-color:#a01830"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - V-SHAPE: wider at rear (mount), narrower at front -->
  <!-- Using polygon to create tapered/V-shape -->
  <polygon points="12,15 88,15 76,85 24,85" fill="url(#c70200Body)" stroke="#ddd" stroke-width="0.5"/>
  <!-- Red L ring at front (narrower end of V) -->
  <polygon points="12,15 88,15 87,19 13,19" fill="url(#c70200Red)"/>
  <!-- Focus ring (wide, textured) -->
  <polygon points="15,24 85,24 82,42 18,42" fill="#e0e0e0" stroke="#ccc" stroke-width="0.3"/>
  <line x1="18" y1="29" x2="82" y2="29" stroke="#d0d0d0" stroke-width="0.5"/>
  <line x1="17" y1="33" x2="83" y2="33" stroke="#d0d0d0" stroke-width="0.5"/>
  <line x1="17" y1="37" x2="83" y2="37" stroke="#d0d0d0" stroke-width="0.5"/>
  <!-- Distance window -->
  <rect x="38" y="46" width="24" height="8" rx="1" fill="#1a1a1a"/>
  <!-- Zoom ring -->
  <polygon points="17,58 83,58 81,70 19,70" fill="#d8d8d8" stroke="#bbb" stroke-width="0.3"/>
  <!-- Tripod collar area -->
  <polygon points="32,64 68,64 67,72 33,72" fill="#c0c0c0" opacity="0.5"/>
  <!-- Rear mount (wider) -->
  <polygon points="22,78 78,78 77,85 23,85" fill="#333"/>
  <!-- Front element (larger, at narrow end) -->
  <ellipse cx="50" cy="12" rx="38" ry="11" fill="#111" stroke="#999" stroke-width="2"/>
  <!-- Canon logo area -->
  <text x="50" y="50" font-size="5" fill="#333" text-anchor="middle" font-weight="bold">70-200</text>
</svg>`,

    // Nikon AF-S 70-200mm f/2.8E FL ED VR - Black telephoto (V-SHAPE)
    'Nikon_70-200': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="n70200Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="30%" style="stop-color:#111"/>
      <stop offset="70%" style="stop-color:#111"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
    <linearGradient id="n70200Gold" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#d4af37"/>
      <stop offset="100%" style="stop-color:#b8941f"/>
    </linearGradient>
  </defs>
  <!-- V-SHAPE: wider at rear, narrower at front -->
  <polygon points="10,18 90,18 80,82 20,82" fill="url(#n70200Body)"/>
  <!-- Nikon gold ring at rear (wider end) -->
  <polygon points="20,76 80,76 80,82 20,82" fill="url(#n70200Gold)"/>
  <!-- Focus ring -->
  <polygon points="14,24 86,24 83,40 17,40" fill="#222"/>
  <!-- VR switch area -->
  <rect x="22" y="42" width="12" height="6" rx="0.5" fill="#2a2a2a"/>
  <!-- Distance window -->
  <rect x="42" y="44" width="16" height="6" rx="0.5" fill="#0a0a0a"/>
  <!-- Zoom ring -->
  <polygon points="15,54 85,54 83,68 17,68" fill="#1a1a1a"/>
  <!-- Tripod collar foot -->
  <polygon points="38,62 62,62 61,68 39,68" fill="#333" opacity="0.5"/>
  <!-- Front element (at narrow end) -->
  <ellipse cx="50" cy="14" rx="40" ry="12" fill="#080808" stroke="#d4af37" stroke-width="2"/>
  <text x="50" y="48" font-size="5" fill="#d4af37" text-anchor="middle">70-200</text>
</svg>`,

    // Sony FE 70-200mm f/2.8 GM OSS II - G Master telephoto (V-SHAPE)
    'Sony_70-200': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="s70200Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="50%" style="stop-color:#111"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
    <linearGradient id="s70200Orange" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ff6b00"/>
      <stop offset="100%" style="stop-color:#e55e00"/>
    </linearGradient>
  </defs>
  <!-- V-SHAPE: wider at rear -->
  <polygon points="12,18 88,18 78,82 22,82" fill="url(#s70200Body)"/>
  <!-- Orange G ring at rear -->
  <polygon points="22,76 78,76 78,82 22,82" fill="url(#s70200Orange)"/>
  <!-- Focus ring -->
  <polygon points="16,24 84,24 81,38 19,38" fill="#222"/>
  <!-- Function buttons -->
  <rect x="22" y="40" width="10" height="5" rx="0.5" fill="#2a2a2a"/>
  <rect x="38" y="40" width="10" height="5" rx="0.5" fill="#2a2a2a"/>
  <rect x="54" y="40" width="10" height="5" rx="0.5" fill="#2a2a2a"/>
  <!-- Zoom ring -->
  <polygon points="17,52 83,52 81,68 19,68" fill="#1a1a1a"/>
  <!-- Tripod foot -->
  <polygon points="36,62 64,62 63,68 37,68" fill="#333" opacity="0.5"/>
  <!-- Front element -->
  <ellipse cx="50" cy="14" rx="38" ry="12" fill="#080808" stroke="#ff6b00" stroke-width="2"/>
  <text x="50" y="46" font-size="4" fill="#fff" text-anchor="middle" font-weight="bold">G MASTER</text>
</svg>`,

    // Tamron SP 70-200mm f/2.8 Di VC USD G2 (V-SHAPE)
    'Tamron_70-200': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="t70200Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="50%" style="stop-color:#111"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
    <linearGradient id="t70200Gold" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#d4af37"/>
      <stop offset="100%" style="stop-color:#b8941f"/>
    </linearGradient>
  </defs>
  <!-- V-SHAPE -->
  <polygon points="12,20 88,20 80,80 20,80" fill="url(#t70200Body)"/>
  <!-- Gold band at rear -->
  <polygon points="20,74 80,74 80,80 20,80" fill="url(#t70200Gold)"/>
  <!-- Focus ring -->
  <polygon points="16,26 84,26 81,40 19,40" fill="#222"/>
  <!-- Distance window -->
  <rect x="40" y="44" width="20" height="6" rx="0.5" fill="#0a0a0a"/>
  <!-- Zoom ring -->
  <polygon points="17,52 83,52 81,64 19,64" fill="#1a1a1a"/>
  <!-- Tripod collar -->
  <polygon points="36,60 64,60 63,66 37,66" fill="#333" opacity="0.5"/>
  <!-- Front element -->
  <ellipse cx="50" cy="16" rx="38" ry="11" fill="#080808" stroke="#d4af37" stroke-width="2"/>
  <text x="50" y="48" font-size="5" fill="#d4af37" text-anchor="middle" font-weight="bold">SP</text>
</svg>`,

    // Canon RF 24-70mm f/2.8L IS USM - Black standard zoom (TUBE shape)
    'Canon_24-70': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c2470Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2a2a2a"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
    <linearGradient id="c2470Red" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#c41e3a"/>
      <stop offset="100%" style="stop-color:#a01830"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - TUBE shape (uniform width) -->
  <rect x="22" y="22" width="56" height="56" rx="2" fill="url(#c2470Body)"/>
  <!-- Red L ring -->
  <rect x="22" y="22" width="56" height="4" fill="url(#c2470Red)"/>
  <!-- Control ring -->
  <rect x="24" y="30" width="52" height="6" rx="0.5" fill="#333"/>
  <!-- Focus ring (wide) -->
  <rect x="24" y="40" width="52" height="14" rx="1" fill="#252525" stroke="#444" stroke-width="0.3"/>
  <!-- Zoom ring -->
  <rect x="24" y="58" width="52" height="10" rx="1" fill="#222"/>
  <!-- Function buttons -->
  <rect x="28" y="62" width="8" height="4" rx="0.5" fill="#444"/>
  <rect x="40" y="62" width="8" height="4" rx="0.5" fill="#444"/>
  <!-- Rear -->
  <rect x="24" y="72" width="52" height="6" rx="1" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="82" rx="28" ry="9" fill="#111" stroke="#c41e3a" stroke-width="2"/>
  <text x="50" y="55" font-size="5" fill="#c41e3a" text-anchor="middle" font-weight="bold">24-70</text>
</svg>`,

    // Nikon AF-S 24-70mm f/2.8E ED VR - Standard zoom (TUBE)
    'Nikon_24-70': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="n2470Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#222"/>
      <stop offset="50%" style="stop-color:#151515"/>
      <stop offset="100%" style="stop-color:#222"/>
    </linearGradient>
    <linearGradient id="n2470Gold" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#d4af37"/>
      <stop offset="100%" style="stop-color:#b8941f"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - TUBE -->
  <rect x="22" y="26" width="56" height="48" rx="2" fill="url(#n2470Body)"/>
  <!-- Gold ring -->
  <rect x="22" y="70" width="56" height="3" fill="url(#n2470Gold)"/>
  <!-- Focus ring -->
  <rect x="24" y="32" width="52" height="12" rx="1" fill="#2a2a2a"/>
  <!-- Zoom ring -->
  <rect x="24" y="48" width="52" height="12" rx="1" fill="#222"/>
  <!-- Switches -->
  <rect x="28" y="52" width="10" height="4" rx="0.5" fill="#333"/>
  <rect x="42" y="52" width="10" height="4" rx="0.5" fill="#333"/>
  <!-- Rear -->
  <rect x="24" y="74" width="52" height="4" rx="1" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="82" rx="28" ry="9" fill="#111" stroke="#666" stroke-width="1"/>
  <text x="50" y="44" font-size="5" fill="#d4af37" text-anchor="middle">24-70</text>
</svg>`,

    // Sony FE 24-70mm f/2.8 GM - Standard zoom (TUBE)
    'Sony_24-70': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="s2470Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#222"/>
      <stop offset="50%" style="stop-color:#151515"/>
      <stop offset="100%" style="stop-color:#222"/>
    </linearGradient>
    <linearGradient id="s2470Orange" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ff6b00"/>
      <stop offset="100%" style="stop-color:#e55e00"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - TUBE -->
  <rect x="22" y="26" width="56" height="48" rx="2" fill="url(#s2470Body)"/>
  <!-- Orange ring -->
  <rect x="22" y="70" width="56" height="3" fill="url(#s2470Orange)"/>
  <!-- Focus ring -->
  <rect x="24" y="32" width="52" height="12" rx="1" fill="#2a2a2a"/>
  <!-- Zoom ring -->
  <rect x="24" y="48" width="52" height="12" rx="1" fill="#222"/>
  <!-- Rear -->
  <rect x="24" y="74" width="52" height="4" rx="1" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="82" rx="28" ry="9" fill="#111" stroke="#666" stroke-width="1"/>
  <text x="50" y="44" font-size="4" fill="#ff6b00" text-anchor="middle">GM</text>
</svg>`,

    // Canon EF 50mm f/1.8 STM - Compact "nifty fifty" (TUBE but compact)
    'Canon_50mm': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c50Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#333"/>
      <stop offset="50%" style="stop-color:#252525"/>
      <stop offset="100%" style="stop-color:#333"/>
    </linearGradient>
  </defs>
  <!-- Small compact body - TUBE -->
  <rect x="30" y="32" width="40" height="36" rx="1" fill="url(#c50Body)"/>
  <!-- Silver ring -->
  <rect x="30" y="32" width="40" height="3" fill="#c0c0c0"/>
  <!-- Focus ring (small) -->
  <rect x="32" y="38" width="36" height="8" rx="0.5" fill="#2a2a2a"/>
  <!-- STM label area -->
  <rect x="35" y="50" width="30" height="6" rx="0.5" fill="#222"/>
  <!-- Rear mount -->
  <rect x="32" y="62" width="36" height="4" rx="0.5" fill="#1a1a1a"/>
  <!-- Front element (small) -->
  <ellipse cx="50" cy="72" rx="18" ry="6" fill="#111" stroke="#666" stroke-width="1"/>
  <text x="50" y="48" font-size="5" fill="#999" text-anchor="middle">STM</text>
</svg>`,

    // Nikon AF-S 50mm f/1.8G - Compact prime (TUBE)
    'Nikon_50mm': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="n50Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2a2a2a"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
  </defs>
  <!-- Compact body - TUBE -->
  <rect x="28" y="34" width="44" height="32" rx="1" fill="url(#n50Body)"/>
  <!-- Silver accent -->
  <rect x="28" y="34" width="44" height="2" fill="#c0c0c0"/>
  <!-- Focus ring -->
  <rect x="30" y="40" width="40" height="8" rx="0.5" fill="#333"/>
  <!-- Rear -->
  <rect x="30" y="56" width="40" height="4" rx="0.5" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="68" rx="20" ry="6" fill="#111" stroke="#888" stroke-width="1"/>
  <text x="50" y="50" font-size="4" fill="#888" text-anchor="middle">AF-S</text>
</svg>`,

    // Canon EF 40mm f/2.8 STM - PANCAKE lens (very flat)
    'Canon_40mm_Pancake': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c40PancakeBody" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#333"/>
      <stop offset="50%" style="stop-color:#252525"/>
      <stop offset="100%" style="stop-color:#333"/>
    </linearGradient>
  </defs>
  <!-- PANCAKE - very short/flat, wider diameter -->
  <rect x="26" y="38" width="48" height="18" rx="1" fill="url(#c40PancakeBody)"/>
  <!-- Silver ring -->
  <rect x="26" y="38" width="48" height="2" fill="#c0c0c0"/>
  <!-- Focus ring (thin) -->
  <rect x="28" y="42" width="44" height="5" rx="0.5" fill="#2a2a2a"/>
  <!-- STM text area -->
  <rect x="32" y="50" width="36" height="4" rx="0.5" fill="#222"/>
  <!-- Rear -->
  <rect x="28" y="50" width="44" height="4" rx="0.5" fill="#1a1a1a"/>
  <!-- Front element (wide, shallow) -->
  <ellipse cx="50" cy="58" rx="22" ry="5" fill="#111" stroke="#888" stroke-width="1"/>
  <text x="50" y="47" font-size="4" fill="#888" text-anchor="middle">40mm Pancake</text>
</svg>`,

    // Canon EF 24mm f/2.8 STM - Wide pancake
    'Canon_24mm_Pancake': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c24PancakeBody" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#333"/>
      <stop offset="50%" style="stop-color:#252525"/>
      <stop offset="100%" style="stop-color:#333"/>
    </linearGradient>
  </defs>
  <!-- PANCAKE -->
  <rect x="26" y="38" width="48" height="18" rx="1" fill="url(#c24PancakeBody)"/>
  <!-- Silver ring -->
  <rect x="26" y="38" width="48" height="2" fill="#c0c0c0"/>
  <!-- Focus ring -->
  <rect x="28" y="42" width="44" height="5" rx="0.5" fill="#2a2a2a"/>
  <!-- Rear -->
  <rect x="28" y="50" width="44" height="4" rx="0.5" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="58" rx="24" ry="5" fill="#111" stroke="#888" stroke-width="1"/>
  <text x="50" y="47" font-size="4" fill="#888" text-anchor="middle">24mm Pancake</text>
</svg>`,

    // Canon EF 16-35mm f/2.8L III USM - Wide angle (BULBOUS front - slight taper)
    'Canon_16-35': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c1635Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2a2a2a"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
    <linearGradient id="c1635Red" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#c41e3a"/>
      <stop offset="100%" style="stop-color:#a01830"/>
    </linearGradient>
  </defs>
  <!-- Wide angle - REVERSE V: wider at front (bulbous) -->
  <polygon points="18,28 82,28 88,72 12,72" fill="url(#c1635Body)"/>
  <!-- Red L ring at front (wider) -->
  <polygon points="18,28 82,28 81,32 19,32" fill="url(#c1635Red)"/>
  <!-- Focus ring -->
  <polygon points="20,36 80,36 82,48 18,48" fill="#252525"/>
  <!-- Bulbous front section -->
  <polygon points="16,52 84,52 86,68 14,68" fill="#1a1a1a" stroke="#333" stroke-width="1"/>
  <!-- Rear -->
  <polygon points="15,70 85,70 84,76 16,76" fill="#1a1a1a"/>
  <!-- Bulbous front element -->
  <ellipse cx="50" cy="26" rx="36" ry="10" fill="#111" stroke="#c41e3a" stroke-width="2"/>
  <text x="50" y="46" font-size="5" fill="#c41e3a" text-anchor="middle">16-35</text>
</svg>`,

    // Canon EF 100mm f/2.8L Macro IS USM - Macro lens (TUBE, medium length)
    'Canon_100mm_Macro': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="c100MacroBody" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2a2a2a"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
    <linearGradient id="c100MacroRed" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#c41e3a"/>
      <stop offset="100%" style="stop-color:#a01830"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - TUBE, medium length -->
  <rect x="24" y="25" width="52" height="50" rx="2" fill="url(#c100MacroBody)"/>
  <!-- Red L ring -->
  <rect x="24" y="25" width="52" height="4" fill="url(#c100MacroRed)"/>
  <!-- Focus ring -->
  <rect x="26" y="33" width="48" height="12" rx="1" fill="#252525" stroke="#333" stroke-width="0.3"/>
  <!-- Distance scale window -->
  <rect x="38" y="48" width="24" height="6" rx="0.5" fill="#1a1a1a"/>
  <!-- Macro range indicator -->
  <rect x="30" y="55" width="40" height="4" rx="0.5" fill="#c41e3a" opacity="0.3"/>
  <!-- Rear -->
  <rect x="26" y="65" width="48" height="6" rx="1" fill="#1a1a1a"/>
  <!-- Front element -->
  <ellipse cx="50" cy="80" rx="26" ry="8" fill="#111" stroke="#c41e3a" stroke-width="2"/>
  <text x="50" y="53" font-size="4" fill="#c41e3a" text-anchor="middle">MACRO</text>
</svg>`,

    // Sigma Art 35mm f/1.4 DG HSM - Large prime (TUBE, large diameter)
    'Sigma_Art_35': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="sigma35Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="50%" style="stop-color:#0a0a0a"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
  </defs>
  <!-- Main barrel - TUBE, large diameter -->
  <rect x="18" y="24" width="64" height="52" rx="2" fill="url(#sigma35Body)"/>
  <!-- Silver ring at front -->
  <rect x="18" y="24" width="64" height="4" fill="#c0c0c0"/>
  <!-- Focus ring -->
  <rect x="21" y="32" width="58" height="14" rx="1" fill="#222"/>
  <!-- A markings -->
  <text x="50" y="42" font-size="6" fill="#c0c0c0" text-anchor="middle" font-weight="bold">A</text>
  <!-- Rear -->
  <rect x="21" y="70" width="58" height="6" rx="1" fill="#151515"/>
  <!-- Large front element -->
  <ellipse cx="50" cy="82" rx="32" ry="10" fill="#080808" stroke="#c0c0c0" stroke-width="2"/>
  <text x="50" y="55" font-size="5" fill="#c0c0c0" text-anchor="middle">35mm ART</text>
</svg>`,

    // Sigma Art 85mm f/1.4 DG HSM - Portrait telephoto (TUBE, longer)
    'Sigma_Art_85': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="sigma85Body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="50%" style="stop-color:#0a0a0a"/>
      <stop offset="100%" style="stop-color:#1a1a1a"/>
    </linearGradient>
  </defs>
  <!-- Longer barrel - TUBE -->
  <rect x="22" y="22" width="56" height="56" rx="2" fill="url(#sigma85Body)"/>
  <!-- Silver ring -->
  <rect x="22" y="22" width="56" height="4" fill="#c0c0c0"/>
  <!-- Focus ring -->
  <rect x="24" y="30" width="52" height="16" rx="1" fill="#222"/>
  <text x="50" y="41" font-size="7" fill="#c0c0c0" text-anchor="middle" font-weight="bold">A</text>
  <!-- Rear -->
  <rect x="24" y="74" width="52" height="6" rx="1" fill="#151515"/>
  <!-- Front element -->
  <ellipse cx="50" cy="84" rx="28" ry="9" fill="#080808" stroke="#c0c0c0" stroke-width="2"/>
  <text x="50" y="58" font-size="5" fill="#c0c0c0" text-anchor="middle">85mm ART</text>
</svg>`,

    // Wide angle fisheye - bulbous front
    'Fisheye_Bulbous': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="fishBody" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2a2a2a"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
  </defs>
  <!-- Short but very bulbous front -->
  <polygon points="15,35 85,35 90,70 10,70" fill="url(#fishBody)"/>
  <!-- Extra bulbous front element section -->
  <ellipse cx="50" cy="28" rx="38" ry="14" fill="#111" stroke="#c41e3a" stroke-width="2"/>
  <ellipse cx="50" cy="26" rx="30" ry="10" fill="#222" opacity="0.5"/>
  <!-- Rear -->
  <polygon points="15,68 85,68 84,75 16,75" fill="#1a1a1a"/>
  <text x="50" y="50" font-size="5" fill="#c41e3a" text-anchor="middle">Fisheye</text>
</svg>`,

    // Default generic lens
    'default': `<svg viewBox="0 0 100 100" class="lens-icon">
  <defs>
    <linearGradient id="genericLens" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#333"/>
      <stop offset="50%" style="stop-color:#222"/>
      <stop offset="100%" style="stop-color:#333"/>
    </linearGradient>
  </defs>
  <rect x="25" y="30" width="50" height="40" rx="2" fill="url(#genericLens)"/>
  <rect x="25" y="32" width="50" height="4" fill="#444"/>
  <rect x="28" y="40" width="44" height="12" rx="1" fill="#2a2a2a"/>
  <rect x="30" y="56" width="40" height="8" rx="1" fill="#333"/>
  <ellipse cx="50" cy="78" rx="20" ry="7" fill="#111" stroke="#555" stroke-width="1"/>
  <text x="50" y="50" font-size="5" fill="#666" text-anchor="middle">Lens</text>
</svg>`
};

// Map lens names to specific icon types based on focal length, features, and lens shape
function getLensIconType(lensName) {
    const name = lensName.toLowerCase();
    
    // PANCAKE lenses - very flat, short
    if (name.includes('40mm') && name.includes('pancake') || 
        (name.includes('40mm') && name.includes('2.8') && name.includes('stm')) ||
        (name.includes('24mm') && name.includes('2.8') && name.includes('stm'))) {
        return 'Canon_40mm_Pancake';
    }
    if (name.includes('pancake')) {
        return 'Canon_40mm_Pancake';
    }
    
    // Fisheye lenses - bulbous front
    if (name.includes('fisheye') || name.includes('8mm') || name.includes('circular')) {
        return 'Fisheye_Bulbous';
    }
    
    // V-SHAPE telephoto zooms (70-200mm, 100-400mm, etc.)
    if (name.includes('70-200') || name.includes('100-400') || 
        name.includes('80-200') || name.includes('75-300')) {
        if (name.includes('canon')) return 'Canon_70-200';
        if (name.includes('nikon')) return 'Nikon_70-200';
        if (name.includes('sony')) return 'Sony_70-200';
        if (name.includes('tamron')) return 'Tamron_70-200';
        if (name.includes('sigma')) return 'Canon_70-200'; // Sigma telephotos similar
        return 'Canon_70-200'; // Default to Canon style
    }
    
    // BULBOUS wide angle zooms (tapered outward)
    if (name.includes('16-35') || name.includes('11-24') || 
        name.includes('14-24') || name.includes('17-40')) {
        return 'Canon_16-35';
    }
    
    // Standard zooms (TUBE shape)
    if (name.includes('24-70') || name.includes('24-105') || name.includes('24-120')) {
        if (name.includes('canon')) return 'Canon_24-70';
        if (name.includes('nikon')) return 'Nikon_24-70';
        if (name.includes('sony')) return 'Sony_24-70';
        if (name.includes('tamron') || name.includes('sigma')) return 'Canon_24-70';
        return 'Canon_24-70';
    }
    
    // Canon primes
    if (name.includes('canon')) {
        if (name.includes('50mm') || name.includes('40mm')) return 'Canon_50mm';
        if (name.includes('100mm') && name.includes('macro')) return 'Canon_100mm_Macro';
        if (name.includes('35mm') && !name.includes('24-35')) return 'Canon_50mm';
        if (name.includes('85mm')) return 'Canon_50mm';
        return 'Canon_24-70';
    }
    
    // Nikon primes
    if (name.includes('nikon')) {
        if (name.includes('50mm') || name.includes('35mm') || name.includes('85mm')) return 'Nikon_50mm';
        return 'Nikon_24-70';
    }
    
    // Sony lenses
    if (name.includes('sony')) {
        if (name.includes('24-70')) return 'Sony_24-70';
        if (name.includes('50mm') || name.includes('35mm') || name.includes('85mm')) return 'Nikon_50mm'; // Similar
        return 'Sony_24-70';
    }
    
    // Sigma Art lenses
    if (name.includes('sigma')) {
        if (name.includes('35mm') && name.includes('art')) return 'Sigma_Art_35';
        if (name.includes('85mm') && name.includes('art')) return 'Sigma_Art_85';
        if (name.includes('50mm') && name.includes('art')) return 'Sigma_Art_35';
        return 'Sigma_Art_35';
    }
    
    // Tamron lenses
    if (name.includes('tamron')) {
        if (name.includes('70-200')) return 'Tamron_70-200';
        return 'Tamron_70-200';
    }
    
    // Default - check for clues
    if (name.includes('70-200') || name.includes('100-')) {
        return 'Canon_70-200'; // V-shape telephoto
    }
    if (name.includes('16-') || name.includes('14-') || name.includes('11-')) {
        return 'Canon_16-35'; // Bulbous wide
    }
    
    return 'default';
}

function getLensIcon(lensName) {
    const iconType = getLensIconType(lensName);
    return lensIcons[iconType] || lensIcons['default'];
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { lensIcons, getLensIcon, getLensIconType };
}

// Make functions globally available for browser
if (typeof window !== 'undefined') {
    window.getLensIcon = getLensIcon;
    window.getLensIconType = getLensIconType;
    window.lensIcons = lensIcons;
}