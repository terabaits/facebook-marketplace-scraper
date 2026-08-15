// Detailed SVG lens icons that represent actual lens characteristics
// Lens length varies by focal length, aperture affects front element size

const lensIcons = {
    // Canon L-series telephoto (70-200mm style) - white body, red ring
    'Canon_Telephoto_L': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="canonL" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#f5f5f5"/><stop offset="50%" style="stop-color:#e8e8e8"/><stop offset="100%" style="stop-color:#f5f5f5"/></linearGradient><linearGradient id="canonLRed" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#c41e3a"/><stop offset="100%" style="stop-color:#a01830"/></linearGradient></defs><rect x="15" y="20" width="70" height="60" rx="3" fill="url(#canonL)" stroke="#ccc" stroke-width="1"/><rect x="15" y="22" width="70" height="6" fill="url(#canonLRed)"/><rect x="20" y="32" width="60" height="8" rx="1" fill="#ddd"/><rect x="22" y="44" width="10" height="12" rx="1" fill="#333"/><rect x="35" y="44" width="10" height="12" rx="1" fill="#333"/><rect x="20" y="60" width="60" height="15" rx="1" fill="#e0e0e0"/><ellipse cx="50" cy="80" rx="30" ry="10" fill="#1a1a1a" stroke="#c41e3a" stroke-width="3"/><text x="50" y="55" font-size="7" fill="#333" text-anchor="middle" font-weight="bold">Canon L</text></svg>`,

    // Canon standard zoom (24-70mm style) - black body, red ring
    'Canon_Standard_L': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="canonStd" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2a2a2a"/><stop offset="50%" style="stop-color:#1a1a1a"/><stop offset="100%" style="stop-color:#2a2a2a"/></linearGradient></defs><rect x="20" y="25" width="60" height="50" rx="2" fill="url(#canonStd)"/><rect x="20" y="27" width="60" height="5" fill="#c41e3a"/><rect x="22" y="35" width="56" height="10" rx="1" fill="#333"/><rect x="25" y="48" width="12" height="8" rx="1" fill="#444"/><rect x="42" y="48" width="12" height="8" rx="1" fill="#444"/><rect x="22" y="60" width="56" height="10" rx="1" fill="#222"/><ellipse cx="50" cy="78" rx="25" ry="8" fill="#111" stroke="#c41e3a" stroke-width="2"/><text x="50" y="56" font-size="6" fill="#c41e3a" text-anchor="middle" font-weight="bold">L</text></svg>`,

    // Canon compact prime (35mm/50mm style) - small, black
    'Canon_Prime_Compact': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="canonPrime" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#333"/><stop offset="50%" style="stop-color:#222"/><stop offset="100%" style="stop-color:#333"/></linearGradient></defs><rect x="30" y="30" width="40" height="40" rx="2" fill="url(#canonPrime)"/><rect x="30" y="32" width="40" height="4" fill="#555"/><rect x="32" y="40" width="36" height="8" rx="1" fill="#444"/><rect x="35" y="52" width="30" height="6" rx="1" fill="#333"/><ellipse cx="50" cy="75" rx="18" ry="6" fill="#111" stroke="#666" stroke-width="1"/><text x="50" y="58" font-size="6" fill="#999" text-anchor="middle">STM</text></svg>`,

    // Canon macro lens (with macro switch)
    'Canon_Macro': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="canonMacro" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2a2a2a"/><stop offset="50%" style="stop-color:#1a1a1a"/><stop offset="100%" style="stop-color:#2a2a2a"/></linearGradient></defs><rect x="22" y="25" width="56" height="50" rx="2" fill="url(#canonMacro)"/><rect x="22" y="27" width="56" height="5" fill="#c41e3a"/><rect x="25" y="35" width="50" height="12" rx="1" fill="#333"/><rect x="28" y="50" width="44" height="8" rx="1" fill="#3a3a3a" stroke="#c41e3a" stroke-width="0.5"/><rect x="25" y="62" width="50" height="8" rx="1" fill="#444"/><ellipse cx="50" cy="78" rx="22" ry="7" fill="#111" stroke="#c41e3a" stroke-width="2"/><text x="50" y="57" font-size="5" fill="#c41e3a" text-anchor="middle">MACRO</text></svg>`,

    // Canon wide angle (16-35mm style) - bulbous front
    'Canon_Wide_L': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="canonWide" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2a2a2a"/><stop offset="50%" style="stop-color:#1a1a1a"/><stop offset="100%" style="stop-color:#2a2a2a"/></linearGradient></defs><rect x="20" y="28" width="60" height="44" rx="2" fill="url(#canonWide)"/><rect x="20" y="30" width="60" height="5" fill="#c41e3a"/><rect x="22" y="38" width="56" height="10" rx="1" fill="#333"/><rect x="25" y="52" width="50" height="14" rx="2" fill="#1a1a1a" stroke="#333" stroke-width="1"/><ellipse cx="50" cy="78" rx="28" ry="12" fill="#111" stroke="#c41e3a" stroke-width="2"/><text x="50" y="50" font-size="6" fill="#c41e3a" text-anchor="middle">L USM</text></svg>`,

    // Nikon professional (70-200mm style) - black with gold ring
    'Nikon_Telephoto_Pro': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="nikonPro" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#1a1a1a"/><stop offset="50%" style="stop-color:#0a0a0a"/><stop offset="100%" style="stop-color:#1a1a1a"/></linearGradient><linearGradient id="nikonGold" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#d4af37"/><stop offset="100%" style="stop-color:#b8941f"/></linearGradient></defs><rect x="15" y="22" width="70" height="56" rx="3" fill="url(#nikonPro)"/><rect x="15" y="24" width="70" height="5" fill="#333"/><rect x="15" y="70" width="70" height="6" fill="url(#nikonGold)"/><rect x="20" y="34" width="60" height="10" rx="1" fill="#222"/><rect x="22" y="48" width="10" height="10" rx="1" fill="#333"/><rect x="68" y="48" width="10" height="10" rx="1" fill="#333"/><rect x="20" y="62" width="60" height="6" rx="1" fill="#2a2a2a"/><ellipse cx="50" cy="82" rx="28" ry="9" fill="#111" stroke="#d4af37" stroke-width="2"/><text x="50" y="57" font-size="6" fill="#d4af37" text-anchor="middle" font-weight="bold">N</text></svg>`,

    // Nikon standard zoom (24-70mm style)
    'Nikon_Standard_Zoom': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="nikonStd" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#222"/><stop offset="50%" style="stop-color:#151515"/><stop offset="100%" style="stop-color:#222"/></linearGradient></defs><rect x="20" y="26" width="60" height="48" rx="2" fill="url(#nikonStd)"/><rect x="20" y="28" width="60" height="4" fill="#333"/><rect x="20" y="68" width="60" height="4" fill="#d4af37"/><rect x="22" y="36" width="56" height="10" rx="1" fill="#2a2a2a"/><rect x="25" y="50" width="50" height="14" rx="1" fill="#1a1a1a"/><ellipse cx="50" cy="80" rx="25" ry="8" fill="#111" stroke="#666" stroke-width="1"/><text x="50" y="45" font-size="6" fill="#d4af37" text-anchor="middle">VR</text></svg>`,

    // Nikon prime lens (small, compact)
    'Nikon_Prime': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="nikonPrime" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2a2a2a"/><stop offset="50%" style="stop-color:#1a1a1a"/><stop offset="100%" style="stop-color:#2a2a2a"/></linearGradient></defs><rect x="28" y="32" width="44" height="36" rx="2" fill="url(#nikonPrime)"/><rect x="28" y="34" width="44" height="4" fill="#333"/><rect x="30" y="42" width="40" height="8" rx="1" fill="#222"/><rect x="32" y="54" width="36" height="8" rx="1" fill="#333"/><ellipse cx="50" cy="75" rx="18" ry="6" fill="#111" stroke="#555" stroke-width="1"/><text x="50" y="50" font-size="5" fill="#999" text-anchor="middle">AF-S</text></svg>`,

    // Sony G Master (white text on black, orange ring)
    'Sony_GM': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="sonyGM" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#1a1a1a"/><stop offset="50%" style="stop-color:#0a0a0a"/><stop offset="100%" style="stop-color:#1a1a1a"/></linearGradient><linearGradient id="sonyOrange" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#ff6b00"/><stop offset="100%" style="stop-color:#e55e00"/></linearGradient></defs><rect x="20" y="25" width="60" height="50" rx="2" fill="url(#sonyGM)"/><rect x="20" y="27" width="60" height="5" fill="#333"/><rect x="20" y="68" width="60" height="5" fill="url(#sonyOrange)"/><rect x="22" y="36" width="56" height="12" rx="1" fill="#222"/><rect x="25" y="52" width="50" height="12" rx="1" fill="#2a2a2a" stroke="#ff6b00" stroke-width="0.5"/><ellipse cx="50" cy="80" rx="26" ry="9" fill="#111" stroke="#ff6b00" stroke-width="2"/><text x="50" y="49" font-size="5" fill="#fff" text-anchor="middle" font-weight="bold">G MASTER</text></svg>`,

    // Sony standard (silver/white body for some models)
    'Sony_Standard': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="sonyStd" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#333"/><stop offset="50%" style="stop-color:#222"/><stop offset="100%" style="stop-color:#333"/></linearGradient></defs><rect x="22" y="28" width="56" height="44" rx="2" fill="url(#sonyStd)"/><rect x="22" y="30" width="56" height="4" fill="#333"/><rect x="22" y="66" width="56" height="4" fill="#ff6b00"/><rect x="25" y="38" width="50" height="10" rx="1" fill="#2a2a2a"/><rect x="28" y="52" width="44" height="10" rx="1" fill="#333"/><ellipse cx="50" cy="78" rx="24" ry="8" fill="#111" stroke="#666" stroke-width="1"/><text x="50" y="48" font-size="5" fill="#ccc" text-anchor="middle">OSS</text></svg>`,

    // Sigma Art (black with silver A, larger body)
    'Sigma_Art': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="sigmaArt" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#1a1a1a"/><stop offset="50%" style="stop-color:#0a0a0a"/><stop offset="100%" style="stop-color:#1a1a1a"/></linearGradient></defs><rect x="18" y="24" width="64" height="52" rx="2" fill="url(#sigmaArt)"/><rect x="18" y="26" width="64" height="5" fill="#c0c0c0"/><rect x="22" y="35" width="56" height="12" rx="1" fill="#222"/><rect x="25" y="52" width="50" height="18" rx="1" fill="#1a1a1a" stroke="#c0c0c0" stroke-width="0.5"/><ellipse cx="50" cy="82" rx="28" ry="10" fill="#111" stroke="#c0c0c0" stroke-width="2"/><text x="50" y="60" font-size="7" fill="#c0c0c0" text-anchor="middle" font-weight="bold">A</text></svg>`,

    // Sigma Contemporary (smaller, C badge)
    'Sigma_Contemporary': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="sigmaCont" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2a2a2a"/><stop offset="50%" style="stop-color:#1a1a1a"/><stop offset="100%" style="stop-color:#2a2a2a"/></linearGradient></defs><rect x="24" y="28" width="52" height="44" rx="2" fill="url(#sigmaCont)"/><rect x="24" y="30" width="52" height="4" fill="#c0c0c0"/><rect x="27" y="38" width="46" height="10" rx="1" fill="#333"/><rect x="30" y="52" width="40" height="14" rx="1" fill="#222"/><ellipse cx="50" cy="78" rx="24" ry="8" fill="#111" stroke="#888" stroke-width="1"/><text x="50" y="48" font-size="5" fill="#c0c0c0" text-anchor="middle">C</text></svg>`,

    // Tamron SP (black with gold band at rear)
    'Tamron_SP': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="tamronSP" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#1a1a1a"/><stop offset="50%" style="stop-color:#0a0a0a"/><stop offset="100%" style="stop-color:#1a1a1a"/></linearGradient><linearGradient id="tamronGold" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#d4af37"/><stop offset="100%" style="stop-color:#b8941f"/></linearGradient></defs><rect x="20" y="25" width="60" height="50" rx="2" fill="url(#tamronSP)"/><rect x="20" y="70" width="60" height="5" fill="url(#tamronGold)"/><rect x="23" y="32" width="54" height="12" rx="1" fill="#222"/><rect x="25" y="48" width="50" height="18" rx="1" fill="#1a1a1a"/><ellipse cx="50" cy="80" rx="26" ry="9" fill="#111" stroke="#d4af37" stroke-width="2"/><text x="50" y="45" font-size="5" fill="#d4af37" text-anchor="middle" font-weight="bold">SP</text></svg>`,

    // Tamron standard (black with silver)
    'Tamron_Standard': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="tamronStd" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#222"/><stop offset="50%" style="stop-color:#151515"/><stop offset="100%" style="stop-color:#222"/></linearGradient></defs><rect x="22" y="28" width="56" height="44" rx="2" fill="url(#tamronStd)"/><rect x="22" y="68" width="56" height="4" fill="#c0c0c0"/><rect x="25" y="35" width="50" height="12" rx="1" fill="#2a2a2a"/><rect x="28" y="52" width="44" height="12" rx="1" fill="#222"/><ellipse cx="50" cy="78" rx="24" ry="8" fill="#111" stroke="#888" stroke-width="1"/><text x="50" y="48" font-size="5" fill="#888" text-anchor="middle">VC</text></svg>`,

    // Default generic lens
    'default': `<svg viewBox="0 0 100 100" class="lens-icon"><defs><linearGradient id="genericLens" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#333"/><stop offset="50%" style="stop-color:#222"/><stop offset="100%" style="stop-color:#333"/></linearGradient></defs><rect x="25" y="30" width="50" height="40" rx="2" fill="url(#genericLens)"/><rect x="25" y="32" width="50" height="4" fill="#444"/><rect x="28" y="40" width="44" height="12" rx="1" fill="#2a2a2a"/><rect x="30" y="56" width="40" height="8" rx="1" fill="#333"/><ellipse cx="50" cy="78" rx="20" ry="7" fill="#111" stroke="#555" stroke-width="1"/><text x="50" y="50" font-size="5" fill="#666" text-anchor="middle">Lens</text></svg>`
};

// Map lens names to icon types
function getLensIconType(lensName) {
    const name = lensName.toLowerCase();
    
    // Canon
    if (name.includes('canon')) {
        if (name.includes('70-200') || name.includes('100-400') || name.includes('200-')) return 'Canon_Telephoto_L';
        if (name.includes('24-70') || name.includes('16-35') || name.includes('24-105')) return 'Canon_Standard_L';
        if (name.includes('macro') || name.includes('100mm') && name.includes('macro')) return 'Canon_Macro';
        if (name.includes('135mm') || name.includes('85mm')) return 'Canon_Standard_L';
        if (name.includes('35mm') || name.includes('50mm') || name.includes('40mm')) return 'Canon_Prime_Compact';
        if (name.includes('16mm') || name.includes('14mm') || name.includes('11-')) return 'Canon_Wide_L';
        return 'Canon_Standard_L';
    }
    
    // Nikon
    if (name.includes('nikon')) {
        if (name.includes('70-200') || name.includes('100-400') || name.includes('200-')) return 'Nikon_Telephoto_Pro';
        if (name.includes('24-70') || name.includes('24-120') || name.includes('28-')) return 'Nikon_Standard_Zoom';
        if (name.includes('50mm') || name.includes('35mm') || name.includes('85mm')) return 'Nikon_Prime';
        return 'Nikon_Standard_Zoom';
    }
    
    // Sony
    if (name.includes('sony')) {
        if (name.includes('gm') || name.includes('g master')) return 'Sony_GM';
        return 'Sony_Standard';
    }
    
    // Sigma
    if (name.includes('sigma')) {
        if (name.includes('art')) return 'Sigma_Art';
        if (name.includes('contemporary') || name.includes('c ')) return 'Sigma_Contemporary';
        return 'Sigma_Art';
    }
    
    // Tamron
    if (name.includes('tamron')) {
        if (name.includes('sp') || name.includes('g2')) return 'Tamron_SP';
        return 'Tamron_Standard';
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
