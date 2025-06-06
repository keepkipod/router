from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import os
import hashlib

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# In production, store these in a secret manager
VALID_API_KEYS = {
    hashlib.sha256(key.encode()).hexdigest(): name 
    for name, key in {
        "client1": os.getenv("API_KEY_CLIENT1", "demo-key-1"),
        "client2": os.getenv("API_KEY_CLIENT2", "demo-key-2"),
    }.items()
}

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    if key_hash not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return VALID_API_KEYS[key_hash]
