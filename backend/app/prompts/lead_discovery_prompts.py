"""
Optimized prompts for lead discovery agent
"""

def get_discovery_prompt(
    domain: str,
    keywords: list,
    location: str,
    min_employees: int,
    max_employees: int,
    min_funding: float,
    max_funding: float,
    funding_stages: list
) -> str:
    """Generate optimized search prompt for lead discovery"""
    
    return f"""Find {min_employees}-{max_employees} employee companies in {location} working on {domain}.

KEY REQUIREMENTS:
- Domain/Technology: {', '.join(keywords)}
- Location: {location}
- Company Size: {min_employees}-{max_employees} employees
- Funding: ${min_funding}M - ${max_funding}M (Stages: {', '.join(funding_stages)})
- Active/Operating businesses only
- Must have discoverable contact information

SEARCH STRATEGY:
Search for companies that:
1. Recently raised funding in target range
2. Are hiring for relevant roles (AI engineers, data scientists, etc.)
3. Have launched products in the past 2 years
4. Are featured in tech news/industry publications

EXCLUDE:
- Companies with >$50M total funding (too large)
- Enterprises with >100 employees
- Companies in stealth mode (no public info)
- Defunct or acquired companies

OUTPUT FORMAT:
For each company found, provide:
- Company name
- Website URL
- Brief description (1-2 sentences)
- Employee count (estimate)
- Funding stage and amount
- Location (city, country)
- Founded year
- Key technology focus
- Recent news or achievements

Find 10-15 highly relevant companies. Prioritize quality over quantity - only include companies that are excellent fits for the criteria."""


def get_regional_context_prompt(region: str, economic_tier: str) -> str:
    """Get regional context for more targeted searches"""
    
    contexts = {
        "tier1": {
            "focus": "innovation, cutting-edge tech, first movers",
            "pain_points": "scaling challenges, talent acquisition, market differentiation",
            "approach": "value proposition, innovation partnership, premium solutions"
        },
        "tier2": {
            "focus": "proven solutions, ROI, market expansion",
            "pain_points": "cost optimization, market entry, operational efficiency",
            "approach": "cost-benefit analysis, case studies, proven results"
        },
        "tier3": {
            "focus": "cost-effective, scalable, local market fit",
            "pain_points": "budget constraints, local compliance, rapid growth",
            "approach": "competitive pricing, localization, quick wins"
        }
    }
    
    context = contexts.get(economic_tier, contexts["tier1"])
    
    return f"""
REGIONAL CONTEXT FOR {region} ({economic_tier.upper()}):

Market Focus: {context['focus']}
Common Pain Points: {context['pain_points']}
Recommended Approach: {context['approach']}

Adjust search to find companies that align with these regional characteristics.
"""


def get_industry_specific_prompt(industry: str) -> str:
    """Get industry-specific search refinements"""
    
    industry_prompts = {
        "healthcare": """
Healthcare Industry Focus:
- Look for companies dealing with: medical records automation, clinical decision support, patient data management
- Key pain points: HIPAA compliance, data interoperability, administrative burden
- Decision makers: Chief Medical Information Officer (CMIO), VP of Operations, CTO
- Recent trends: Telemedicine adoption, AI diagnostics, administrative automation
        """,
        
        "finance": """
Financial Services Focus:
- Look for companies dealing with: fraud detection, process automation, risk assessment, compliance
- Key pain points: Regulatory compliance, fraud losses, manual processes, data security
- Decision makers: Chief Risk Officer, VP of Technology, Head of Innovation
- Recent trends: Open banking, real-time fraud detection, automated underwriting
        """,
        
        "manufacturing": """
Manufacturing Focus:
- Look for companies dealing with: supply chain optimization, predictive maintenance, quality control
- Key pain points: Supply chain disruptions, equipment downtime, quality issues, manual tracking
- Decision makers: VP of Operations, Supply Chain Director, Plant Manager
- Recent trends: Industry 4.0, IoT integration, predictive analytics
        """,
        
        "retail": """
Retail/E-commerce Focus:
- Look for companies dealing with: personalization, inventory optimization, customer analytics
- Key pain points: Cart abandonment, inventory management, customer retention, thin margins
- Decision makers: Head of E-commerce, CMO, VP of Operations
- Recent trends: AI personalization, omnichannel, dynamic pricing
        """,
        
        "default": """
Technology/SaaS Focus:
- Look for companies building innovative software solutions
- Key pain points: Customer acquisition, product-market fit, scaling challenges
- Decision makers: CEO, CTO, VP of Product
- Recent trends: AI integration, automation, API-first products
        """
    }
    
    return industry_prompts.get(industry.lower(), industry_prompts["default"])


def get_validation_prompt(company_data: dict) -> str:
    """Prompt to validate if a discovered company is a good fit"""
    
    return f"""Analyze if this company is a good lead prospect:

Company: {company_data.get('name')}
Website: {company_data.get('website')}
Description: {company_data.get('description')}
Employees: {company_data.get('employee_count')}
Funding: {company_data.get('funding_stage')} - ${company_data.get('funding_amount')}M
Location: {company_data.get('location')}

EVALUATION CRITERIA:
1. Relevance (0-100): How well does this company fit the target domain?
2. Reachability (0-100): Can we find decision-makers and contact info?
3. Fit (0-100): Are they likely to need our solutions?
4. Timing (0-100): Are there growth signals indicating good timing?

PROVIDE:
- Overall score (0-100)
- Key strengths (why they're a good fit)
- Potential concerns (red flags)
- Recommended action (pursue, maybe, skip)

Be critical - we want quality leads only."""


# Query templates for different search strategies
SEARCH_QUERY_TEMPLATES = {
    "recent_funding": "{domain} companies {location} raised ${min_funding}M to ${max_funding}M funding {current_year} {previous_year}",
    
    "hiring_signals": "{domain} startups {location} hiring {role_keywords} {employee_range} employees",
    
    "product_launch": "{domain} companies {location} launched product {current_year} {funding_stage}",
    
    "news_mentions": "{industry} startups {location} featured TechCrunch VentureBeat news {employee_range} employees",
    
    "specific_tech": "companies using {technology_stack} {location} {funding_stage} {employee_range}",
    
    "competitor_analysis": "alternatives to {competitor_name} {location} smaller companies {employee_range}",
    
    "awards_recognition": "{industry} companies {location} won awards recognition innovation {current_year}",
}


def build_multi_angle_queries(params: dict) -> list:
    """Build multiple search queries from different angles for comprehensive discovery"""
    
    queries = []
    
    # Base search
    queries.append(
        f"{params['domain']} companies in {params['location']} "
        f"with {params['min_employees']}-{params['max_employees']} employees "
        f"recent funding {params['funding_stage']}"
    )
    
    # Hiring signals search
    queries.append(
        f"{params['domain']} startups in {params['location']} "
        f"hiring engineers developers recent jobs"
    )
    
    # Recent news search
    queries.append(
        f"{params['industry']} companies {params['location']} "
        f"announced product launch funding news 2024 2025"
    )
    
    # Technology-specific search
    if params.get('tech_keywords'):
        queries.append(
            f"companies using {params['tech_keywords']} "
            f"{params['location']} {params['funding_stage']}"
        )
    
    return queries



def build_extraction_prompt(discovery_response: str) -> str:
    return f"""
Extract structured company data from the following text.

Text to extract from:
\"\"\"
{discovery_response}
\"\"\"

Return ONLY a JSON array.
No commentary. No explanation.

Each company must follow this exact shape:

[
  {{
    "name": "",
    "website": "",
    "description": "",
    "industry": "",
    "employee_count": null,
    "phone": "",
    "email": "",
    "address": "",
    "location": "",
    "city": "",
    "country": "",
    "funding_stage": "",
    "funding_amount": null,
    "founded_year": null,
    "tech_stack": ""
  }}
]

Rules:
- Missing or unknown values must be null
- Keys must match exactly
- No additional fields
- Output must be valid JSON
- "phone" / "email" / "address" should only be filled in if publicly listed —
  never fabricate contact details
- "funding_stage" / "funding_amount" should be null when funding is not relevant
  to this business
"""
