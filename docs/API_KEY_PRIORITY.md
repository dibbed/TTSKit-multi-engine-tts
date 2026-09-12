# 🔑 API Key Priority System

## Overview

TTSKit uses a priority-based API key verification system that ensures flexibility and backward compatibility.

## Priority Order

### 1. **Config Settings (Highest Priority)**

API keys defined in environment variables or `.env` file:

```bash
# Single API key
API_KEY=CHANGE_ME_ADMIN_KEY

# Multiple API keys (JSON format)
API_KEYS={"admin": "CHANGE_ME_ADMIN_KEY", "user1": "CHANGE_ME_USER1_KEY", "readonly_user": "CHANGE_ME_READONLY_KEY"}
```

### 2. **Database Storage (Lower Priority)**

API keys stored in the database with enhanced security (hash-only storage).

## How It Works

### Verification Process

```python
async def verify_api_key(api_key: str) -> APIKeyAuth:
    # 1. Check config settings first (from env)
    if api_key in settings.api_keys:
        return APIKeyAuth(user_id="admin", permissions=["read", "write", "admin"])

    # 2. Check single API key from config
    if api_key == settings.api_key:
        return APIKeyAuth(user_id="demo-user", permissions=["read", "write"])

    # 3. Check database (hash-based verification)
    user_info = await user_service.verify_api_key(api_key)
    if user_info:
        return APIKeyAuth(user_id=user_info["user_id"], permissions=user_info["permissions"])

    # 4. Invalid key
    raise HTTPException(status_code=401, detail="Invalid API key")
```

### Permission Mapping

#### From Config:

- `admin` → `["read", "write", "admin"]`
- `readonly_*` → `["read"]`
- Others → `["read", "write"]`

#### From Database:

- Permissions stored as JSON in database
- Admin users get `admin` permission automatically

## Examples

### Environment Configuration

```bash
# .env file
API_KEY=my-secret-key
API_KEYS={"admin": "admin-key", "user1": "user1-key", "readonly_test": "readonly-key"}
```

### Usage Examples

```python
# Admin key from config
headers = {"Authorization": "Bearer admin-key"}
# Result: user_id="admin", permissions=["read", "write", "admin"]

# Regular user key from config
headers = {"Authorization": "Bearer user1-key"}
# Result: user_id="user1", permissions=["read", "write"]

# Readonly key from config
headers = {"Authorization": "Bearer readonly-key"}
# Result: user_id="readonly_test", permissions=["read"]

# Database key (if not in config)
headers = {"Authorization": "Bearer ttskit_abc123..."}
# Result: user_id from database, permissions from database
```

## Security Features

### Config Keys (Plain Text)

- ✅ Fast verification
- ✅ Easy to manage
- ⚠️ Stored in plain text
- ⚠️ Visible in environment

### Database Keys (Hash-Only)

- ✅ Secure hash storage
- ✅ Usage tracking
- ✅ Expiration support
- ✅ Detailed permissions
- ⚠️ Requires database access

## Best Practices

### For Development

```bash
# Use config keys for quick testing
API_KEY=dev-key
API_KEYS={"admin": "admin-dev", "test": "test-key"}
```

### For Production

```bash
# Use database keys for security
API_KEY=  # Leave empty to force database usage
API_KEYS={"admin": "admin-prod-key"}  # Only for super admin
```

### Migration Strategy

1. **Phase 1**: Use config keys for existing users
2. **Phase 2**: Create database keys for new users
3. **Phase 3**: Gradually migrate config keys to database
4. **Phase 4**: Remove config keys (optional)

## Configuration Examples

### Simple Setup

```bash
# Single admin key
API_KEY=CHANGE_ME_ADMIN_KEY
```

### Multi-User Setup

```bash
# Multiple users with different permissions
API_KEYS={
  "admin": "CHANGE_ME_ADMIN_KEY",
  "api_user": "CHANGE_ME_API_USER_KEY",
  "readonly_monitor": "CHANGE_ME_MONITOR_KEY"
}
```

### Production Setup

```bash
# Only super admin in config, others in database
API_KEY=CHANGE_ME_SUPER_ADMIN_KEY
API_KEYS={"admin": "CHANGE_ME_SUPER_ADMIN_KEY"}
```

## Troubleshooting

### Common Issues

1. **Key Not Found**

   - Check if key exists in config or database
   - Verify key format (no extra spaces)
   - Check JSON format for API_KEYS

2. **Permission Denied**

   - Verify user has required permissions
   - Check if user is active in database
   - Confirm admin status

3. **Database Errors**
   - Ensure database is accessible
   - Check database connection settings
   - Verify migration has been run

### Debug Mode

Enable debug logging to see verification process:

```bash
LOG_LEVEL=DEBUG
```

This will show which source (config/database) was used for verification.

## Migration Commands

```bash
# Check current security status
python -m ttskit.database.migration

# Run security migration
python -m ttskit.database.migration

# Test API key verification
python test_security.py
```

---

**Note**: Config keys take priority over database keys to ensure backward compatibility and allow easy admin access even when database is unavailable.
