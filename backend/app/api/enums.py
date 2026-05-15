from fastapi import APIRouter, Depends
from app.core.constants import TARGET_DOMAINS, GEOGRAPHIC_TIERS, FUNDING_STAGES
from fastapi.responses import JSONResponse
from app.messages.enums import InfoMessage
from app.api.deps.auth_deps import get_current_user
from app.schemas.user import CurrentUser

router = APIRouter()

@router.get("/domains")
def get_domains(current_user: CurrentUser = Depends(get_current_user)):
	"""
	Return available target domains by name and full objects.
	"""
	domain_names = [d.get("name") for d in TARGET_DOMAINS]
	return JSONResponse(
		status_code=200,
		content={"success": True, "message": InfoMessage.domains_fetched, "data": {"names": domain_names, "items": TARGET_DOMAINS}},
	)


@router.get("/funding-stages")
def get_funding_stages(current_user: CurrentUser = Depends(get_current_user)):
	"""
	Return funding stages, both categorized and flattened unique list.
	"""
	preferred = FUNDING_STAGES.get("preferred", [])
	acceptable = FUNDING_STAGES.get("acceptable", [])
	avoid = FUNDING_STAGES.get("avoid", [])
	# preserve order: preferred -> acceptable -> avoid, unique
	seen = set()
	all_stages: list[str] = []
	for stage in preferred + acceptable + avoid:
		if stage not in seen:
			seen.add(stage)
			all_stages.append(stage)
            
	return JSONResponse(
		status_code=200,
		content={
			"success": True,
			"message": InfoMessage.funding_stages_fetched,
			"data": {"all": all_stages, "categories": {"preferred": preferred, "acceptable": acceptable, "avoid": avoid}},
		},
	)


@router.get("/geographic-tiers")
def get_geographic_tiers(current_user: CurrentUser = Depends(get_current_user)):
	"""
	Return available geographic tiers and their region/city details.
	"""
	tiers = list(GEOGRAPHIC_TIERS.keys())
	return JSONResponse(
		status_code=200,
		content={"success": True, "message": InfoMessage.geographic_tiers_fetched, "data": {"tiers": tiers, "details": GEOGRAPHIC_TIERS}},
	)
