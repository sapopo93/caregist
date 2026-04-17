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
    photos: list[str] | None = Field(None, max_length=15)
    virtual_tour_url: str | None = Field(None, max_length=500)
    inspection_response: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=500)
    funding_types: list[str] | None = None
    fee_guidance: str | None = Field(None, max_length=500)
    min_visit_duration: str | None = Field(None, max_length=100)
    contract_types: list[str] | None = None
    age_ranges: list[str] | None = None


PROFILE_TIERS = {
    "claimed": {"photos": 0, "description": False, "virtual_tour": False, "inspection_response": True, "logo": True, "funding": True, "practical": True},
    "enhanced": {"photos": 5, "description": True, "virtual_tour": True, "inspection_response": True, "logo": True, "funding": True, "practical": True},
    "premium": {"photos": 10, "description": True, "virtual_tour": True, "inspection_response": True, "logo": True, "funding": True, "practical": True},
    "sponsored": {"photos": 15, "description": True, "virtual_tour": True, "inspection_response": True, "logo": True, "funding": True, "practical": True},
}


@router.get("/{slug}/profile")
async def get_profile(slug: str, _auth: dict = Depends(validate_api_key)) -> dict:
    """Get the enhanced profile for a provider."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, slug, profile_description, profile_photos,
                      virtual_tour_url, inspection_response, profile_tier,
                      profile_updated_at, is_claimed,
                      logo_url, funding_types, fee_guidance,
                      min_visit_duration, contract_types, age_ranges
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
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

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

    tier_config = PROFILE_TIERS.get(tier, PROFILE_TIERS["claimed"]) if tier else PROFILE_TIERS["claimed"]

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
    if req.logo_url is not None:
        updates.append(f"logo_url = ${i}")
        params.append(req.logo_url)
        i += 1
    if req.funding_types is not None:
        updates.append(f"funding_types = ${i}::text[]")
        params.append(req.funding_types)
        i += 1
    if req.fee_guidance is not None:
        updates.append(f"fee_guidance = ${i}")
        params.append(req.fee_guidance)
        i += 1
    if req.min_visit_duration is not None:
        updates.append(f"min_visit_duration = ${i}")
        params.append(req.min_visit_duration)
        i += 1
    if req.contract_types is not None:
        updates.append(f"contract_types = ${i}::text[]")
        params.append(req.contract_types)
        i += 1
    if req.age_ranges is not None:
        updates.append(f"age_ranges = ${i}::text[]")
        params.append(req.age_ranges)
        i += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    updates.append(f"profile_updated_at = NOW()")
    sql = f"UPDATE care_providers SET {', '.join(updates)} WHERE slug = ${i}"
    params.append(slug)

    async with get_connection() as conn:
        await conn.execute(sql, *params)
        await conn.execute(
            """
            UPDATE care_providers
            SET profile_completeness = calculate_profile_completeness(
                profile_description,
                profile_photos,
                virtual_tour_url,
                inspection_response,
                is_claimed,
                profile_tier
            )
            WHERE slug = $1
            """,
            slug,
        )

    logger.info("Profile updated for %s by user %s", slug, user_id)
    return {"message": "Profile updated successfully."}
