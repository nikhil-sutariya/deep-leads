"""
Prompts for email campaign generation
"""

def get_email_generation_prompt(
    lead_data: dict,
    campaign_goal: str,
    email_template: dict | None = None,
) -> str:
    """Generate personalized email content from the available lead facts."""

    template_section = ""
    if email_template:
        template_section = f"""
USER EMAIL TEMPLATE (use as tone/structure guide; personalize with lead facts):
Subject template: {email_template.get('subject_line', '')}
Body template: {email_template.get('body', '')}

Substitute placeholders like {{company_name}}, {{contact_name}}, {{industry}} with real values from LEAD INFORMATION.
"""

    return f"""Write a highly personalized cold outreach email based on this lead.
{template_section}

The lead may be any type of business (startup, restaurant, manufacturer, retailer,
agency, non-profit, etc.). Personalize using ONLY the facts below — do NOT invent
pain points, recent news, or funding details that aren't listed.

LEAD INFORMATION:
Company: {lead_data.get('company_name')}
Industry / type: {lead_data.get('industry')}
Location: {lead_data.get('location')}
Employees (estimate): {lead_data.get('employee_count')}
Funding stage: {lead_data.get('funding_stage')}
What they do: {lead_data.get('description')}
Capabilities / tech stack: {lead_data.get('tech_stack')}
Contact: {lead_data.get('contact_name')} - {lead_data.get('contact_title')}

CAMPAIGN GOAL: {campaign_goal}

EMAIL REQUIREMENTS:

1. SUBJECT LINE (Critical):
   - Personalized with a company / contact / industry specific detail
   - Curiosity-driven or value-driven
   - Under 60 characters
   - NO generic phrases like "Quick question" or "Following up"
   - Good patterns:
     * "[Outcome] for [Company]"
     * "[Company] + [capability]"
     * "How [similar business in their industry] achieved [outcome]"

2. OPENING LINE (Critical):
   - Reference something SPECIFIC and verifiable about them (their industry,
     location, what they do — whatever is in the LEAD INFORMATION above)
   - Create immediate relevance
   - NO generic "I hope this email finds you well"

3. VALUE PROPOSITION (Important):
   - Lead with the outcome they care about, inferred from their industry / what they do
   - Be specific to their situation
   - Use numbers / metrics when possible

4. SOCIAL PROOF (Important):
   - Brief mention of a similar business's success
   - Relevant to their industry / situation
   - Concrete results / metrics

5. CALL TO ACTION (Important):
   - Low commitment ask (15-min call, specific question)
   - Make it easy to respond
   - Suggest specific time / approach

6. TONE & STYLE:
   - Professional but conversational
   - Confident not pushy
   - Helpful not salesy
   - Short and scannable (under 150 words)

7. STRUCTURE:
   - 3-4 short paragraphs
   - Lots of white space
   - Easy to read on mobile
   - One clear CTA

AVOID:
- Inventing facts (pain points, news, funding) that aren't in LEAD INFORMATION
- Generic templates that could go to anyone
- Talking too much about your company / product
- Multiple CTAs or questions
- Jargon or buzzwords
- Being too long (>200 words)
- Markdown formatting (no **, #, bullets)
- Multiple variations or A/B options

OUTPUT FORMAT — return exactly ONE email in plain text (no markdown):

SUBJECT: <subject line under 60 characters>
BODY:
<email body, 3-4 short paragraphs, under 200 words>

Do NOT include Variation A/B, multiple options, or explanatory notes. Only the subject and body above."""


def get_follow_up_email_prompt(
    original_email: str,
    lead_data: dict,
    days_since_first: int,
    follow_up_number: int,
    campaign_goal: str = "",
) -> str:
    """Generate follow-up email prompt"""

    goal_line = f"\nCAMPAIGN GOAL: {campaign_goal}\n" if campaign_goal else ""

    angles = {
        1: "Add additional value/insight",
        2: "Different pain point or use case",
        3: "Breakup email / permission to close"
    }
    
    angle = angles.get(follow_up_number, "Add value")
    
    return f"""Write a follow-up email (follow-up #{follow_up_number}, {days_since_first} days after first email):
{goal_line}
ORIGINAL EMAIL:
{original_email}

LEAD INFO:
{lead_data}

FOLLOW-UP STRATEGY: {angle}

REQUIREMENTS:

1. DO NOT:
   - Say "just following up" or "bumping this"
   - Repeat the same value prop
   - Sound desperate or pushy
   - Ask "did you see my email?"

2. DO:
   - Bring new value or information
   - Reference something new (if available)
   - Make it standalone (assume they didn't see first email)
   - Keep it even shorter than original

3. ANGLE FOR FOLLOW-UP {follow_up_number}:
   {get_follow_up_angle_guidance(follow_up_number)}

Keep it under 100 words. Make it scannable."""


def get_follow_up_angle_guidance(follow_up_number: int) -> str:
    """Get specific guidance for each follow-up"""
    
    if follow_up_number == 1:
        return """
        - Share a relevant case study or resource
        - Mention a new insight about their industry/company
        - Offer specific value (article, tool, introduction)
        - Keep door open but add something new
        """
    elif follow_up_number == 2:
        return """
        - Take a completely different angle
        - Address a different pain point
        - Share a surprising statistic or insight
        - More direct ask: "Is this even relevant to you?"
        """
    else:  # 3+
        return """
        - "Breakup" email approach
        - "I'll take that as a no and stop bothering you"
        - Give them easy out: "Should I close your file?"
        - Often highest response rate paradoxically
        - Make it friendly and brief
        """


def get_email_subject_variants_prompt(email_body: str, lead_data: dict) -> str:
    """Generate multiple subject line options for A/B testing."""

    return f"""Generate 5 different subject line variants for this email.

EMAIL BODY:
{email_body}

LEAD CONTEXT:
Company: {lead_data.get('company_name')}
Industry / type: {lead_data.get('industry')}
Location: {lead_data.get('location')}
What they do: {lead_data.get('description')}

SUBJECT LINE STYLES TO GENERATE:

1. CURIOSITY-DRIVEN
   - Creates intrigue, makes them want to open
   - Example: "A small idea for {lead_data.get('company_name')}"

2. VALUE-FORWARD
   - Leads with a specific benefit relevant to their industry
   - Example: "Cut X time for {lead_data.get('industry')} teams"

3. PERSONALIZED-REFERENCE
   - References something specific from the LEAD CONTEXT
   - Example: "{lead_data.get('company_name')} + [capability]"

4. QUESTION-BASED
   - Asks a relevant, engaging question
   - Example: "Is [common workflow in their industry] slowing {lead_data.get('company_name')}?"

5. DIRECT-BENEFIT
   - Clear, simple value statement
   - Example: "[Outcome] for {lead_data.get('company_name')}"

REQUIREMENTS:
- Under 60 characters each
- Use ONLY facts from the LEAD CONTEXT — do not invent pain points or news
- No spam trigger words (free, guarantee, limited time)
- Mobile-friendly (shows well on small screens)
- Each variant should test a different psychological trigger

Return as JSON array with subject line and rationale for each."""


EMAIL_BEST_PRACTICES = """
COLD EMAIL BEST PRACTICES:

1. PERSONALIZATION LEVELS:
   - Level 1: Use their name/company (minimum)
   - Level 2: Reference their industry/role
   - Level 3: Mention specific pain point
   - Level 4: Reference recent news/achievement (BEST)
   - Level 5: Custom insight about their situation (EXCEPTIONAL)

2. OPTIMAL TIMING:
   - Tuesday-Thursday best days
   - 10am-11am or 1pm-2pm optimal times (recipient's timezone)
   - Avoid Monday mornings and Friday afternoons

3. FOLLOW-UP CADENCE:
   - Day 0: Initial email
   - Day 3: First follow-up (add value)
   - Day 7: Second follow-up (different angle)
   - Day 14: Final follow-up (breakup email)

4. SUCCESS METRICS (Industry Benchmarks):
   - Open Rate: 25-35% (good)
   - Response Rate: 3-8% (good)
   - Meeting Booked: 1-3% (good)
   - Above these = excellent

5. RED FLAGS TO AVOID:
   - Attachments (often blocked)
   - Too many links (spam trigger)
   - ALL CAPS or excessive punctuation!!!
   - Images (tracking issues)
   - Overly long (>200 words)
   - Generic copy-paste feel
"""

