# Image Handling with Listing Versioning

## Overview

Images are stored using the **BASE listing ID** (without version suffixes), so all versions of the same listing share the same image storage. This prevents duplicate downloads and wasted disk space.

## How It Works

### Example Scenario:

| Listing | Database ID | Image URL | Stored As |
|---------|-------------|-----------|-----------|
| Original Gaming PC | `gexxm` | https://.../image1.jpg | `images/gexxm_a1b2c3d4.jpg` |
| Same PC, price drop | `gexxm` (v1) | https://.../image1.jpg | *(already exists, skipped)* |
| ID reused for Laptop | `gexxm_v2` | https://.../laptop.jpg | `images/gexxm_e5f6g7h8.jpg` |
| Laptop price drop | `gexxm_v2` (v2) | https://.../laptop.jpg | *(already exists, skipped)* |

**Key Points:**
- Images are stored by **base ID** (gexxm), not versioned ID (gexxm_v2)
- Each unique image URL gets its own file (hash prevents collisions)
- All versions can reference the same physical image file
- No duplicate downloads of the same image

## Storage Structure

```
images/
├── computers/
│   ├── gexxm_a1b2c3d4.jpg      # Original Gaming PC
│   ├── gexxm_e5f6g7h8.jpg      # Laptop (v2)
│   ├── abcde_f1g2h3i4.jpg     # Another listing
│   └── ...
├── consoles/
│   └── ...
└── listings/  (for GPU/CPU listings)
    └── ...
```

## Database Schema

Each listing version stores its own `image_url`:

```sql
-- listings table
listing_id      | version_number | image_url                    | image_local_path
----------------|------------------|------------------------------|------------------
gexxm           | 1                | https://ss.com/img1.jpg    | images/gexxm_a1b2c3d4.jpg
gexxm_v2        | 2                | https://ss.com/laptop.jpg  | images/gexxm_e5f6g7h8.jpg
gexxm_v3        | 3                | https://ss.com/desktop.jpg | images/gexxm_i9j0k1l2.jpg
```

## Code Changes

### ImageDownloader._get_base_listing_id()

```python
def _get_base_listing_id(self, listing_id: str) -> str:
    """Extract base listing ID without version suffix."""
    if "_v" in listing_id:
        parts = listing_id.rsplit("_v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
    return listing_id
```

This ensures:
- `gexxm` → `gexxm`
- `gexxm_v2` → `gexxm`
- `gexxm_v3` → `gexxm`

### Filename Generation

```python
base_id = self._get_base_listing_id(listing_id)  # "gexxm_v2" -> "gexxm"
url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
filename = f"{base_id}_{url_hash}{ext}"  # "gexxm_abc123.jpg"
```

## Benefits

1. **No Duplicate Storage**
   - Same image across versions = one file on disk
   - Different images for same ID = separate files (hash ensures uniqueness)

2. **Easy Cleanup**
   - When a listing ID is completely removed, all its images are in one place
   - Images are named by base ID, making them easy to find

3. **Version History**
   - Each version stores its own `image_url`
   - If images change between versions, both are preserved
   - Database tracks which image belonged to which version

4. **Backwards Compatible**
   - Existing images (without versions) continue to work
   - Old listings use same naming scheme

## Edge Cases Handled

### Case 1: Same image across versions
- **Input:** gexxm_v2 has same image as gexxm
- **Result:** File already exists, skipped download
- **Database:** Each version references same local path

### Case 2: Different images across versions
- **Input:** gexxm_v2 has different image than gexxm
- **Result:** New file created (different hash)
- **Database:** Each version references different local path

### Case 3: Image URL changes but content same
- **Input:** Same image uploaded to different URL
- **Result:** New download (different hash)
- **Database:** Both versions exist, old one may be orphaned

## Migration Notes

**No migration needed for existing images!**

- Existing images use base listing ID already
- New versions will share the same storage location
- Orphaned images (from deleted listings) can be cleaned up separately

## Future Improvements

Potential enhancements:
- Periodic cleanup of orphaned images
- Image deduplication across different listing IDs
- WebP conversion for better compression
- CDN integration for faster serving
