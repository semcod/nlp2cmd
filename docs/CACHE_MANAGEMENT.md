# Cache Management Guide

## Overview

NLP2CMD uses intelligent caching to improve performance and reduce external dependencies. This guide covers cache management, configuration, and optimization strategies.

## Cache Types

### 1. Playwright Browser Cache

Location: `~/.cache/external/playwright/browsers`

Stores downloaded browser binaries for web schema extraction.

```bash
# Cache location
ls -la ~/.cache/external/playwright/browsers/

# Cache size
du -sh ~/.cache/external/playwright/
```

### 2. Model Cache

Location: `~/.cache/huggingface/hub`

Stores downloaded NLP models and embeddings.

```bash
# Model cache location
ls -la ~/.cache/huggingface/hub/

# Cache size
du -sh ~/.cache/huggingface/
```

### 3. Schema Cache

Location: `command_schemas/sites/`

Stores extracted web schemas for fast access.

```bash
# Schema cache
ls -la command_schemas/sites/

# Schema count
find command_schemas/sites/ -name "*.json" | wc -l
```

### 4. Semantic Index Cache

In-memory cache for precomputed embeddings.

```python
# Built during initialization
detector._build_semantic_index()

# Cached in memory for fast access
detector.semantic_index
```

## Configuration

### Environment Variables

```bash
# Playwright cache location
export PLAYWRIGHT_BROWSERS_PATH=/custom/cache/playwright

# HuggingFace cache location
export HF_HOME=/custom/cache/huggingface

# NLP2CMD cache directory
export NLP2CMD_CACHE_DIR=/custom/cache/nlp2cmd
```

### Cache Configuration

```yaml
# config.yaml
cache:
  enabled: true
  max_size_gb: 10
  ttl_hours: 24
  cleanup_interval_hours: 6
  
playwright:
  headless: true
  timeout_ms: 30000
  browser_cache_path: "~/.cache/external/playwright/browsers"
  
models:
  cache_dir: "~/.cache/huggingface/hub"
  download_timeout_ms: 300000
  max_cache_size_gb: 5
  
schemas:
  auto_refresh: true
  refresh_interval_hours: 24
  backup_enabled: true
```

## Cache Management Commands

### Full cache reset (recommended for troubleshooting)

Use this when cached multi-step plans or old runtime state cause unexpected behavior.

```bash
# 1) Remove NLP2CMD runtime cache (includes learned_schemas.json, action_plans.json, browser profile)
rm -rf ~/.nlp2cmd

# 2) Remove repo-local external cache (Playwright manifest/browsers used by this repo)
rm -rf .cache

# 2b) Optional: remove global Playwright browser cache
rm -rf ~/.cache/ms-playwright

# 3) Optional: clear extracted site schema cache
rm -rf command_schemas/sites
mkdir -p command_schemas/sites

# 4) Optional: clear HuggingFace model cache (forces model redownloads)
rm -rf ~/.cache/huggingface
```

Quick verification:

```bash
ls -ld ~/.nlp2cmd 2>/dev/null || echo "~/.nlp2cmd removed"
ls -ld .cache 2>/dev/null || echo ".cache removed"
ls -ld ~/.cache/ms-playwright 2>/dev/null || echo "~/.cache/ms-playwright removed"
ls -ld command_schemas/sites
ls -ld ~/.cache/huggingface 2>/dev/null || echo "~/.cache/huggingface removed"
```

CLI helper (external cache only):

```bash
nlp2cmd cache clear --all --yes
```

### View Cache Status

```bash
# Overall cache status
nlp2cmd cache status

# Detailed cache information
nlp2cmd cache status --verbose

# Cache by type
nlp2cmd cache status --type playwright
nlp2cmd cache status --type models
nlp2cmd cache status --type schemas
```

### Clean Cache

```bash
# Clean all cache
nlp2cmd cache clean

# Clean specific cache type
nlp2cmd cache clean --type playwright
nlp2cmd cache clean --type models
nlp2cmd cache clean --type schemas

# Force clean (remove even if in use)
nlp2cmd cache clean --force

# Clean old cache (older than TTL)
nlp2cmd cache clean --old-only
```

### Refresh Cache

```bash
# Refresh all cache
nlp2cmd cache refresh

# Refresh specific cache type
nlp2cmd cache refresh --type schemas
nlp2cmd cache refresh --type models

# Refresh specific schema
nlp2cmd cache refresh --schema github.com
nlp2cmd cache refresh --schema google.com
```

### Backup Cache

```bash
# Backup all cache
nlp2cmd cache backup --output /backup/nlp2cmd-cache

# Backup specific cache type
nlp2cmd cache backup --type schemas --output /backup/schemas

# Restore from backup
nlp2cmd cache restore --input /backup/nlp2cmd-cache
```

## Performance Optimization

### Cache Warming

```bash
# Warm up all cache
nlp2cmd cache warm

# Warm up specific cache
nlp2cmd cache warm --type models
nlp2cmd cache warm --type schemas

# Warm up with specific queries
nlp2cmd cache warm --queries "wyszukaj w google,znajdź na github"
```

### Preloading Models

```python
# Preload NLP models
from nlp2cmd.generation.enhanced_context import get_enhanced_detector

# This loads and caches models
detector = get_enhanced_detector()

# Models are now cached for fast access
```

### Schema Precomputation

```python
# Precompute semantic index
detector._build_semantic_index()

# Index is cached in memory for fast similarity calculations
```

## Cache Monitoring

### Cache Statistics

```bash
# Real-time cache statistics
nlp2cmd cache monitor

# Historical cache usage
nlp2cmd cache monitor --history

# Cache hit rates
nlp2cmd cache monitor --hit-rates
```

### Cache Analytics

```python
# Cache performance metrics
from nlp2cmd.utils.cache import get_cache_stats

stats = get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
print(f"Cache size: {stats['size_mb']} MB")
print(f"Cache entries: {stats['entries']}")
```

### Alerting

```yaml
# config.yaml
cache:
  alerts:
    enabled: true
    max_size_gb: 10
    hit_rate_threshold: 0.8
    notification_webhook: "https://hooks.slack.com/..."
```

## Troubleshooting

### Common Issues

#### 1. Cache Corruption

**Problem**: Cache files corrupted or invalid

**Solution**: Clean and rebuild cache:

```bash
# Clean corrupted cache
nlp2cmd cache clean --force

# Rebuild cache
nlp2cmd cache refresh

# Verify cache integrity
nlp2cmd cache status --verify
```

#### 2. Slow Cache Performance

**Problem**: Cache access is slow

**Solution**: Optimize cache configuration:

```yaml
cache:
  enabled: true
  max_size_gb: 5  # Reduce size
  ttl_hours: 12   # Reduce TTL
  cleanup_interval_hours: 3
```

#### 3. Out of Memory

**Problem**: Cache using too much memory

**Solution**: Limit cache size and enable cleanup:

```python
# Limit semantic index size
detector.max_cache_entries = 1000

# Enable periodic cleanup
detector.enable_auto_cleanup = True
```

#### 4. Cache Misses

**Problem**: High cache miss rate

**Solution**: Warm up cache and adjust TTL:

```bash
# Warm up cache
nlp2cmd cache warm

# Increase TTL
nlp2cmd cache config --ttl-hours 48

# Monitor hit rate
nlp2cmd cache monitor --hit-rates
```

### Debug Mode

Enable debug mode for cache operations:

```bash
# Enable cache debugging
export NLP2CMD_CACHE_DEBUG=1

# Run with debug output
nlp2cmd --query "test" --debug

# Check cache logs
tail -f ~/.nlp2cmd/logs/cache.log
```

## Advanced Configuration

### Custom Cache Backend

```python
# Custom cache implementation
from nlp2cmd.utils.cache import CacheBackend

class CustomCacheBackend(CacheBackend):
    def __init__(self, config):
        self.config = config
        self.redis_client = redis.Redis()
    
    def get(self, key: str) -> Any:
        return self.redis_client.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        return self.redis_client.setex(key, ttl, value)
    
    def delete(self, key: str):
        return self.redis_client.delete(key)

# Register custom backend
cache_backend = CustomCacheBackend(config)
```

### Distributed Cache

```yaml
# config.yaml
cache:
  backend: "redis"
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: null
    ssl: false
  
  distributed:
    enabled: true
    sync_interval: 60
    conflict_resolution: "last_write_wins"
```

### Cache Partitioning

```python
# Partition cache by domain
def get_cache_key(domain: str, intent: str, query: str) -> str:
    return f"{domain}:{intent}:{hash(query) % 1000}"

# Use partitioned cache
cache_key = get_cache_key("browser", "web_action", "wyszukaj w google")
cached_result = cache.get(cache_key)
```

## Best Practices

### Cache Design

1. **Appropriate TTL**: Set TTL based on data volatility
2. **Size Limits**: Monitor and limit cache size
3. **Cleanup Strategy**: Regular cleanup of expired entries
4. **Hit Rate Monitoring**: Track cache effectiveness
5. **Backup Strategy**: Backup important cache data

### Performance Optimization

1. **Cache Warming**: Preload frequently used data
2. **Batch Operations**: Group cache operations
3. **Async Updates**: Update cache asynchronously
4. **Compression**: Compress large cache entries
5. **Partitioning**: Partition cache by access patterns

### Security Considerations

1. **Access Control**: Limit cache access permissions
2. **Data Encryption**: Encrypt sensitive cache data
3. **Audit Logging**: Log cache access and modifications
4. **Secure Storage**: Use secure storage for cache
5. **Regular Cleanup**: Remove sensitive data from cache

## Cache API Reference

### Cache Manager

```python
from nlp2cmd.utils.cache import CacheManager

# Initialize cache manager
cache = CacheManager(config)

# Basic operations
cache.set("key", "value", ttl=3600)
value = cache.get("key")
cache.delete("key")

# Batch operations
cache.set_many({"key1": "value1", "key2": "value2"})
values = cache.get_many(["key1", "key2"])
cache.delete_many(["key1", "key2"])

# Statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

### Cache Decorators

```python
from nlp2cmd.utils.cache import cached

# Cache function results
@cached(ttl=3600, key_prefix="nlp2cmd")
def expensive_operation(query: str) -> dict:
    # Expensive computation
    return result

# Cache with custom key
@cached(key=lambda args: f"search:{args[0]}")
def search_query(query: str) -> list:
    return search_results
```

### Cache Context Manager

```python
from nlp2cmd.utils.cache import cache_context

# Use cache context
with cache_context(ttl=3600):
    result1 = expensive_operation("query1")
    result2 = expensive_operation("query2")
    # Results cached automatically
```

## Migration Guide

### From v1 to v2

```bash
# Backup v1 cache
nlp2cmd cache backup --output /backup/v1-cache

# Migrate to v2
nlp2cmd cache migrate --from-version 1 --to-version 2

# Verify migration
nlp2cmd cache status --verify

# Clean up v1 cache
nlp2cmd cache clean --version 1
```

### Cache Format Changes

```python
# Handle cache format migration
def migrate_cache_format(old_cache_path: str, new_cache_path: str):
    old_cache = load_old_format(old_cache_path)
    new_cache = convert_to_new_format(old_cache)
    save_new_format(new_cache, new_cache_path)
```

## Conclusion

Effective cache management is crucial for NLP2CMD performance:

- **Improved Performance**: Faster response times with cached data
- **Reduced Dependencies**: Fewer external API calls
- **Better Reliability**: Graceful handling of external failures
- **Cost Optimization**: Reduced bandwidth and compute costs

Proper cache management ensures NLP2CMD runs efficiently while maintaining data freshness and accuracy.
