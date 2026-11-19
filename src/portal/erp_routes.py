"""
ERP OAuth 2.0 & Read-Only Synchronization Endpoints.
Provides 1-click connect, token vaulting, sync triggers, and disconnection
across Xero, QuickBooks Online, Zoho Books, NetSuite, and TallyPrime.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.erp import ERP_ADAPTERS
from src.portal.database import (
    ERPConnection,
    User,
    delete_tenant_erp_connection,
    encrypt_token,
    get_db,
    get_tenant_erp_connection,
    list_tenant_erp_connections,
    utc_now,
)
from src.portal.dependencies import get_verified_user
from src.portal.security import check_csrf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/erp", tags=["erp"])

PROVIDER_METADATA = {
    "tally": {
        "name": "TallyPrime / Tally ERP 9",
        "region": "India",
        "standard": "Ind AS / Schedule III",
        "description": "Read-only XML-over-HTTP / Relay Agent for Indian business ledgers.",
    },
    "zoho": {
        "name": "Zoho Books",
        "region": "Global / India / EU",
        "standard": "Ind AS / IFRS",
        "description": "OAuth 2.0 multi-DC read-only reports and accountant sync.",
    },
    "quickbooks": {
        "name": "QuickBooks Online",
        "region": "US / Global",
        "standard": "US GAAP / IFRS",
        "description": "OAuth 2.0 Intuit accounting read-only reports API.",
    },
    "xero": {
        "name": "Xero Accounting",
        "region": "UK / Australia / Global",
        "standard": "IFRS / GAAP",
        "description": "OAuth 2.0 read-only financial statement extraction.",
    },
    "netsuite": {
        "name": "Oracle NetSuite OneWorld",
        "region": "Enterprise Global",
        "standard": "US GAAP / Multi-GAAP",
        "description": "OAuth 2.0 + SuiteQL read-only subsidiary trial balances.",
    },
}


class ERPConnectResponse(BaseModel):
    provider: str
    authorize_url: str
    state: str


@router.get("/providers")
def list_providers(
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Lists all 5 institutional ERP providers and active connection state
    for the authenticated tenant under strict row isolation.
    """
    tenant_id = user.tenant_id
    active_connections = list_tenant_erp_connections(db, tenant_id=tenant_id)
    conn_map = {c.provider: c for c in active_connections}

    result = []
    for prov_key, meta in PROVIDER_METADATA.items():
        conn = conn_map.get(prov_key)
        result.append({
            "provider": prov_key,
            "name": meta["name"],
            "region": meta["region"],
            "standard": meta["standard"],
            "description": meta["description"],
            "connected": conn is not None and conn.status == "connected",
            "connection_id": conn.id if conn else None,
            "org_name": conn.org_name if conn else None,
            "last_synced_at": conn.last_synced_at.isoformat() if conn and conn.last_synced_at else None,
            "status": conn.status if conn else "not_connected",
        })

    return {"providers": result}


@router.get("/{provider}/connect")
def connect_erp_provider(
    provider: str,
    request: Request,
    user: User = Depends(get_verified_user),
) -> Dict[str, str]:
    """
    Generates a secure OAuth 2.0 state and returns the consent URL
    for the selected read-only ERP connector.
    """
    prov_key = provider.lower()
    adapter_cls = ERP_ADAPTERS.get(prov_key)
    if not adapter_cls:
        raise HTTPException(status_code=400, detail=f"Unsupported ERP provider '{provider}'.")

    state = f"{secrets.token_urlsafe(24)}:{user.tenant_id}:{prov_key}"
    adapter = adapter_cls()
    auth_url = adapter.get_authorize_url(state=state)

    return {
        "provider": prov_key,
        "authorize_url": auth_url,
        "state": state,
    }


@router.get("/{provider}/callback")
def erp_oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    OAuth 2.0 redirect callback. Exchanges authorization code,
    encrypts tokens with Fernet, and saves the connection.
    """
    prov_key = provider.lower()
    adapter_cls = ERP_ADAPTERS.get(prov_key)
    if not adapter_cls:
        raise HTTPException(status_code=400, detail="Invalid ERP provider.")

    parts = state.split(":")
    tenant_id = parts[1] if len(parts) >= 2 else "default_tenant"

    adapter = adapter_cls()
    token_data = adapter.exchange_code(code=code, redirect_uri="")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    org_name = token_data.get("company_name") or token_data.get("organization_id") or f"{prov_key.capitalize()} Connected Org"

    # Encrypt tokens before storing
    enc_access = encrypt_token(access_token)
    enc_refresh = encrypt_token(refresh_token) if refresh_token else None

    # Check if existing connection exists for this tenant and provider
    existing = (
        db.query(ERPConnection)
        .filter(ERPConnection.tenant_id == tenant_id, ERPConnection.provider == prov_key)
        .first()
    )
    if existing:
        existing.org_name = org_name
        existing.encrypted_access_token = enc_access
        existing.encrypted_refresh_token = enc_refresh
        existing.status = "connected"
        existing.last_synced_at = utc_now()
    else:
        new_conn = ERPConnection(
            tenant_id=tenant_id,
            provider=prov_key,
            org_name=org_name,
            external_realm_id=token_data.get("realmId"),
            encrypted_access_token=enc_access,
            encrypted_refresh_token=enc_refresh,
            status="connected",
            last_synced_at=utc_now(),
        )
        db.add(new_conn)

    db.commit()
    logger.info("Successfully established encrypted read-only ERP connection (%s) for tenant %s.", prov_key, tenant_id)

    return RedirectResponse(url="/#erps", status_code=303)


@router.post("/{connection_id}/sync")
def trigger_erp_sync(
    connection_id: str,
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Triggers an immediate read-only ledger pull, 3-statement solve,
    and board pack generation for the connected ERP.
    """
    check_csrf(request)
    tenant_id = user.tenant_id
    conn = get_tenant_erp_connection(db, connection_id=connection_id, tenant_id=tenant_id)
    if not conn:
        raise HTTPException(status_code=404, detail="ERP connection not found.")

    from src.workers.erp_sync_tasks import execute_erp_connection_sync
    result = execute_erp_connection_sync(conn.id, db_session=db)

    return {
        "status": "success",
        "message": f"Successfully synchronized {conn.provider.capitalize()} ledger.",
        "connection_id": conn.id,
        "provider": conn.provider,
        "sync_result": result,
    }


@router.delete("/{connection_id}")
def disconnect_erp_provider(
    connection_id: str,
    request: Request,
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Revokes and permanently purges encrypted ERP tokens cleanly.
    """
    check_csrf(request)
    tenant_id = user.tenant_id
    success = delete_tenant_erp_connection(db, connection_id=connection_id, tenant_id=tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="ERP connection not found or unauthorized.")

    return {
        "status": "success",
        "message": "ERP connection tokens revoked and purged.",
        "connection_id": connection_id,
    }
