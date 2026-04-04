"""Provider profile management — claimed providers can update their listing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key

logger = logging.getLogger("caregist.profile")
router = APIRouter(prefix="/api/v1/providers", tags=["provider-profile"])


class ProfileUpdateRequest(BaseModel):
    description: str | None = Field(None, max_length=2000)
    photos: list[str] | None = Field(None, max_items=10)
    virtual_tour_url: str | None = Field(None, max_length=500)
    inspection_response: str | None = Field(None, max_length=2000)


PROFILE_TIERS = {
    "basic": {"photos": 3, "description": True, "virtual_tour": False, "inspection_response": False},
    "standard": {"photos": 5, "description": True, "virtual_tour": True, "inspection_response": True},
    "premium": {"photos": 10, "description": True, "virtual_tour": True, "inspection_response": True},
}


@router.get("/{slug}/profile")
async def get_profile(slug: str, _auth: dict = Depends(validate_api_key)) -> dict:
    """Get the enhanced profile for a provider."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, slug, profile_description, profile_photos,
                      virtual_tour_url, inspection_response, profile_tier,
                      profile_updated_at, is_claimed
               FROM care_providers WHERE slug = $1""",
            slug,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found.")

    return {"data": dict(row)}


@router.patch("/{slug}/profile")
async def update_profile(
    slug: str,
    req: ProfileUpdateRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Update the enhanced profile. Requires claimed + active profile subscription."""
    # Resolve user from API key
    async with get_connection() as conn:
        key_row = await conn.fetchrow(
            "SELECT user_id FROM api_keys WHERE name = $1 AND is_active = true",
            _auth.get("name", ""),
        )
    if not key_row or not key_row["user_id"]:
        raise HTTPException(status_code=401, detail="User account required.")
    user_id = key_row["user_id"]

    async with get_connection() as conn:
        provider = await conn.fetchrow(
            "SELECT id, is_claimed, profile_tier FROM care_providers WHERE slug = $1",
            slug,
        )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if not provider["is_claimed"]:
        raise HTTPException(status_code=403, detail="You must claim this provider first.")

    # Verify the user owns the claim
    async with get_connection() as conn:
        claim = await conn.fetchrow(
            """SELECT id FROM provider_claims
               WHERE provider_id = $1 AND status = 'approved'
               AND claimant_email = (SELECT email FROM users WHERE id = $2)""",
            provider["id"], user_id,
        )
    if not claim:
        raise HTTPException(status_code=403, detail="You don't have an approved claim for this provider.")

    tier = provider["profile_tier"]

    # Inspection response is free for all claimed providers (provider acquisition tool)
    # Other features (photos, description, virtual tour) require paid tier
    if not tier:
        if req.description is not None or req.photos is not None or req.virtual_tour_url is not None:
            raise HTTPException(
                status_code=403,
                detail="Photos, description, and virtual tour require an enhanced profile subscription. Inspection response is free. Visit /pricing to upgrade.",
            )

    tier_config = PROFILE_TIERS.get(tier, PROFILE_TIERS["basic"]) if tier else {"photos": 0, "description": False, "virtual_tour": False, "inspection_response": True}

    # Enforce tier limits
    if req.photos and len(req.photos) > tier_config["photos"]:
        raise HTTPException(
            status_code=400,
            detail=f"Your {tier} plan allows up to {tier_config['photos']} photos.",
        )
    if req.virtual_tour_url and not tier_config["virtual_tour"]:
        raise HTTPException(status_code=403, detail="Virtual tour requires Standard plan or above.")
    if req.inspection_response and not tier_config["inspection_response"]:
        raise HTTPException(status_code=403, detail="Inspection response requires Standard plan or above.")

    # Update profile
    updates = []
    params = []
    i = 1

    if req.description is not None:
        updates.append(f"profile_description = ${i}")
        params.append(req.description)
        i += 1
    if req.photos is not None:
        import json
        updates.append(f"profile_photos = ${i}::jsonb")
        params.append(json.dumps(req.photos))
        i += 1
    if req.virtual_tour_url is not None:
        updates.append(f"virtual_tour_url = ${i}")
        params.append(req.virtual_tour_url)
        i += 1
    if req.inspection_response is not None:
        updates.append(f"inspection_response = ${i}")
        params.append(req.inspection_response)
        i += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    updates.append(f"profile_updated_at = NOW()")
    sql = f"UPDATE care_providers SET {', '.join(updates)} WHERE slug = ${i}"
    params.append(slug)

    async with get_connection() as conn:
        await conn.execute(sql, *params)

    logger.info("Profile updated for %s by user %s", slug, user_id)
    return {"message": "Profile updated successfully."}
