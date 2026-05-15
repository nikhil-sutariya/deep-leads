"""
Example usage script for DeepLeads AI

This script demonstrates how to use the DeepLeads API programmatically.
Run the server first: uvicorn app.main:app --reload
"""

import httpx
import asyncio
import json
from typing import List, Dict

# API base URL
BASE_URL = "http://localhost:8000"


async def discover_leads(
    domains: List[str],
    locations: List[str],
    max_results: int = 20
) -> Dict:
    """Discover leads using AI-powered search"""
    
    print(f"\n🔍 Discovering leads in domains: {', '.join(domains)}")
    print(f"   Locations: {', '.join(locations)}")
    
    payload = {
        "domains": domains,
        "geographic_tier": "tier1",
        "specific_locations": locations,
        "min_employees": 10,
        "max_employees": 100,
        "min_funding_millions": 0.5,
        "max_funding_millions": 10.0,
        "funding_stages": ["Seed", "Series A"],
        "max_results": max_results
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/leads/discover",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
    
    print(f"✅ Found {data['total']} qualified leads")
    return data


async def enrich_lead(lead_id: int) -> Dict:
    """Enrich a specific lead with intelligence"""
    
    print(f"\n📊 Enriching lead #{lead_id}...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/leads/{lead_id}/enrich"
        )
        response.raise_for_status()
        data = response.json()
    
    lead = data['lead']
    enrichment = lead.get('enrichment_data', {})
    
    print(f"✅ Enriched: {lead['company_info']['name']}")
    print(f"   Score: {lead['score']:.1f}/100")
    
    if enrichment.get('pain_points'):
        print(f"   Pain Points: {len(enrichment['pain_points'])} identified")
    
    if enrichment.get('decision_makers'):
        print(f"   Decision Makers: {len(enrichment['decision_makers'])} found")
    
    return data


async def create_campaign(
    name: str,
    lead_ids: List[int],
    from_email: str,
    from_name: str
) -> Dict:
    """Create personalized email campaign"""
    
    print(f"\n📧 Creating campaign: {name}")
    print(f"   Leads: {len(lead_ids)}")
    
    payload = {
        "name": name,
        "lead_ids": lead_ids,
        "email_template": {
            "subject_line": "Automating {pain_point} at {company_name}",
            "body": "Hi {contact_name},\n\nI noticed {company_name} is doing interesting work in {industry}..."
        },
        "send_from_email": from_email,
        "send_from_name": from_name,
        "follow_up_days": [3, 7, 14]
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/campaigns",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
    
    print(f"✅ Campaign created successfully")
    print(f"   {data.get('message', 'Ready to launch')}")
    
    return data


async def get_campaign_details(campaign_id: int) -> Dict:
    """Get campaign details"""
    
    print(f"\n📈 Fetching campaign #{campaign_id} details...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}"
        )
        response.raise_for_status()
        data = response.json()
    
    campaign = data['campaign']
    
    print(f"✅ Campaign: {campaign['name']}")
    print(f"   Status: {campaign['status']}")
    print(f"   Total Leads: {campaign['total_leads']}")
    print(f"   Emails Sent: {campaign['emails_sent']}")
    
    return data


async def main():
    """Main workflow demonstration"""
    
    print("=" * 60)
    print("DeepLeads AI - Example Usage")
    print("=" * 60)
    
    try:
        # Check API health
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ API is healthy and ready\n")
            else:
                print("❌ API health check failed")
                return
    except Exception as e:
        print(f"❌ Cannot connect to API. Is the server running?")
        print(f"   Error: {e}")
        print(f"\n   Start the server with: uvicorn app.main:app --reload")
        return
    
    # ============ Step 1: Discover Leads ============
    
    print("\n" + "=" * 60)
    print("STEP 1: Lead Discovery")
    print("=" * 60)
    
    # Define search criteria
    domains = [
        "AI & Machine Learning",
        "Agentic AI & Automation"
    ]
    
    locations = [
        "San Francisco, USA",
        "New York, USA",
        "Austin, USA"
    ]
    
    # Discover leads
    discovery_result = await discover_leads(domains, locations, max_results=10)
    
    leads = discovery_result['leads']
    
    if not leads:
        print("\n⚠️  No leads found. Try adjusting search criteria.")
        return
    
    # Display discovered leads
    print(f"\n📋 Discovered Leads:")
    for i, lead in enumerate(leads[:5], 1):
        company = lead['company_info']
        print(f"\n   {i}. {company['name']}")
        print(f"      Industry: {company.get('industry', 'N/A')}")
        print(f"      Location: {company.get('location', 'N/A')}")
        print(f"      Employees: {company.get('employee_count', 'N/A')}")
        print(f"      Funding: {company.get('funding_stage', 'N/A')}")
        print(f"      Score: {lead.get('score', 0):.1f}/100")
    
    # ============ Step 2: Enrich Leads ============
    
    print("\n" + "=" * 60)
    print("STEP 2: Lead Enrichment")
    print("=" * 60)
    
    # Enrich first 3 leads
    enriched_leads = []
    for lead in leads[:3]:
        try:
            enriched = await enrich_lead(lead['id'])
            enriched_leads.append(enriched['lead'])
            
            # Small delay to avoid rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"   ⚠️  Failed to enrich lead {lead['id']}: {e}")
    
    # Display enrichment results
    if enriched_leads:
        print(f"\n📊 Enrichment Summary:")
        for lead in enriched_leads:
            company = lead['company_info']
            enrichment = lead.get('enrichment_data', {})
            
            print(f"\n   {company['name']}:")
            
            if enrichment.get('pain_points'):
                print(f"   💡 Pain Points:")
                for pp in enrichment['pain_points'][:2]:
                    print(f"      - {pp}")
            
            if enrichment.get('decision_makers'):
                print(f"   👥 Decision Makers:")
                for dm in enrichment['decision_makers'][:2]:
                    print(f"      - {dm.get('name', 'N/A')} ({dm.get('title', 'N/A')})")
            
            if enrichment.get('recent_news'):
                print(f"   📰 Recent News:")
                for news in enrichment['recent_news'][:1]:
                    print(f"      - {news}")
    
    # ============ Step 3: Create Campaign ============
    
    print("\n" + "=" * 60)
    print("STEP 3: Email Campaign Creation")
    print("=" * 60)
    
    # Create campaign with enriched leads
    lead_ids = [lead['id'] for lead in enriched_leads]
    
    campaign_result = await create_campaign(
        name="Example AI Automation Campaign",
        lead_ids=lead_ids,
        from_email="hello@yourcompany.com",
        from_name="Your Name"
    )
    
    campaign_id = campaign_result['campaign']['id']
    
    # Get campaign details
    await get_campaign_details(campaign_id)
    
    # ============ Summary ============
    
    print("\n" + "=" * 60)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   ✓ Discovered: {len(leads)} leads")
    print(f"   ✓ Enriched: {len(enriched_leads)} leads")
    print(f"   ✓ Campaign Created: #{campaign_id}")
    
    print(f"\n🚀 Next Steps:")
    print(f"   1. Review generated emails in the database")
    print(f"   2. Launch campaign: POST /api/campaigns/{campaign_id}/send")
    print(f"   3. Monitor metrics: GET /api/campaigns/{campaign_id}/metrics")
    
    print(f"\n📖 Documentation: {BASE_URL}/docs")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

