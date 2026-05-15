"""
Email Campaign Agent - Generates personalized emails and manages campaigns
"""
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
from google import genai
from google.genai import types
from loguru import logger

from app.core.config import get_settings
from app.schemas.lead import Lead, EmailTemplate, Campaign, CampaignStatus
from app.prompts.email_prompts import (
    get_email_generation_prompt,
    get_follow_up_email_prompt,
    get_email_subject_variants_prompt
)


class EmailCampaignAgent:
    """AI Agent for generating personalized email campaigns"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = genai.Client(api_key=self.settings.google_api_key)
    
    async def generate_personalized_email(
        self, 
        lead: Lead, 
        campaign_goal: str = "Schedule discovery call"
    ) -> Dict[str, str]:
        """
        Generate a highly personalized email for a specific lead
        
        Args:
            lead: Lead to generate email for
            campaign_goal: Goal of the email campaign
            
        Returns:
            Dict with 'subject' and 'body' keys containing email content
        """
        logger.info(f"Generating personalized email for {lead.company_info.name}")
        
        try:
            # Prepare lead data for prompt
            lead_data = self._prepare_lead_data(lead)
            
            # Generate email content
            prompt = get_email_generation_prompt(lead_data, campaign_goal)
            response = await self._call_gemini_async(prompt)
            
            # Parse response into subject and body
            email_content = self._parse_email_response(response)
            
            # Validate and refine
            if not self._validate_email_quality(email_content, lead):
                logger.warning(f"Email quality check failed for {lead.company_info.name}, regenerating...")
                # Try one more time with more specific guidance
                email_content = await self._regenerate_email(lead, campaign_goal, response)
            
            logger.info(f"Generated email for {lead.company_info.name}")
            return email_content
            
        except Exception as e:
            logger.error(f"Error generating email for {lead.company_info.name}: {e}")
            # Return fallback template
            return self._get_fallback_email(lead)
    
    async def generate_follow_up_email(
        self,
        lead: Lead,
        original_email: str,
        follow_up_number: int,
        days_since_first: int
    ) -> Dict[str, str]:
        """
        Generate a follow-up email
        
        Args:
            lead: Lead to follow up with
            original_email: Original email sent
            follow_up_number: Which follow-up this is (1, 2, 3, etc.)
            days_since_first: Days since first email
            
        Returns:
            Dict with 'subject' and 'body' keys
        """
        logger.info(f"Generating follow-up #{follow_up_number} for {lead.company_info.name}")
        
        try:
            lead_data = self._prepare_lead_data(lead)
            
            prompt = get_follow_up_email_prompt(
                original_email=original_email,
                lead_data=lead_data,
                days_since_first=days_since_first,
                follow_up_number=follow_up_number
            )
            
            response = await self._call_gemini_async(prompt)
            email_content = self._parse_email_response(response)
            
            return email_content
            
        except Exception as e:
            logger.error(f"Error generating follow-up for {lead.company_info.name}: {e}")
            return self._get_fallback_followup(lead, follow_up_number)
    
    async def generate_subject_line_variants(
        self,
        email_body: str,
        lead: Lead,
        num_variants: int = 5
    ) -> List[Dict[str, str]]:
        """
        Generate multiple subject line variants for A/B testing
        
        Args:
            email_body: Email body content
            lead: Lead information
            num_variants: Number of variants to generate
            
        Returns:
            List of dicts with 'subject' and 'rationale' keys
        """
        logger.info(f"Generating {num_variants} subject line variants")
        
        try:
            lead_data = self._prepare_lead_data(lead)
            
            prompt = get_email_subject_variants_prompt(email_body, lead_data)
            response = await self._call_gemini_async(prompt)
            
            # Parse variants
            variants = self._parse_subject_variants(response)
            
            return variants[:num_variants]
            
        except Exception as e:
            logger.error(f"Error generating subject variants: {e}")
            return self._get_fallback_subjects(lead)
    
    async def batch_generate_campaign_emails(
        self,
        leads: List[Lead],
        campaign_goal: str = "Schedule discovery call"
    ) -> List[Dict]:
        """
        Generate personalized emails for multiple leads
        
        Args:
            leads: List of leads to generate emails for
            campaign_goal: Campaign goal
            
        Returns:
            List of dicts with lead_id, subject, body, and lead data
        """
        import asyncio
        
        logger.info(f"Generating campaign emails for {len(leads)} leads")
        
        results = []
        
        # Process in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i+batch_size]
            
            tasks = [
                self.generate_personalized_email(lead, campaign_goal) 
                for lead in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for lead, email_content in zip(batch, batch_results):
                if isinstance(email_content, Exception):
                    logger.error(f"Failed to generate email for {lead.company_info.name}: {email_content}")
                    email_content = self._get_fallback_email(lead)
                
                results.append({
                    'lead_id': lead.id,
                    'lead_name': lead.company_info.name,
                    'subject': email_content.get('subject', ''),
                    'body': email_content.get('body', ''),
                    'personalization_data': self._prepare_lead_data(lead)
                })
            
            # Rate limiting delay
            await asyncio.sleep(2)
        
        logger.info(f"Generated {len(results)} campaign emails")
        return results
    
    def _prepare_lead_data(self, lead: Lead) -> Dict:
        """Prepare lead data for email generation."""

        primary_contact = None
        if lead.enrichment_data and lead.enrichment_data.decision_makers:
            primary_contact = lead.enrichment_data.decision_makers[0]

        funding_stage = lead.company_info.funding_stage
        if funding_stage is not None and hasattr(funding_stage, "value"):
            funding_stage = funding_stage.value

        return {
            'company_name': lead.company_info.name,
            'industry': lead.company_info.industry or 'their industry',
            'location': lead.company_info.location or lead.company_info.city or 'their location',
            'employee_count': lead.company_info.employee_count,
            'funding_stage': funding_stage,
            'description': lead.company_info.description,
            'tech_stack': lead.company_info.tech_stack or [],
            'contact_name': primary_contact.name if primary_contact else 'there',
            'contact_title': primary_contact.title if primary_contact else None,
        }
    
    async def _call_gemini_async(self, prompt: str) -> str:
        """Call Gemini API for email generation"""
        
        config = types.GenerateContentConfig(
            temperature=0.8,  # Slightly higher for creativity
            max_output_tokens=1024,
            top_p=0.9
        )
        
        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=config
        )
        
        return response.text
    
    def _parse_email_response(self, response: str) -> Dict[str, str]:
        """Parse email content from response"""
        
        email_content = {}
        
        # Try to extract subject line
        subject_patterns = [
            r'Subject(?:\s+Line)?[:\s]+(.+?)(?:\n|$)',
            r'SUBJECT[:\s]+(.+?)(?:\n|$)',
            r'\*\*Subject\*\*[:\s]+(.+?)(?:\n|$)'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                email_content['subject'] = match.group(1).strip().strip('"').strip("'")
                break
        
        # Try to extract body
        body_patterns = [
            r'Body[:\s]+(.*?)(?:\n\n---|\n\nVariation|$)',
            r'BODY[:\s]+(.*?)(?:\n\n---|\n\nVariation|$)',
            r'\*\*Body\*\*[:\s]+(.*?)(?:\n\n---|\n\nVariation|$)'
        ]
        
        for pattern in body_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                email_content['body'] = match.group(1).strip()
                break
        
        # If structured parsing failed, try to intelligently split
        if not email_content.get('subject') or not email_content.get('body'):
            email_content = self._fallback_parse_email(response)
        
        return email_content
    
    def _fallback_parse_email(self, response: str) -> Dict[str, str]:
        """Fallback parsing if structured extraction fails"""
        
        lines = response.strip().split('\n')
        
        # First non-empty line is likely subject
        subject = None
        body_start = 0
        
        for i, line in enumerate(lines):
            if line.strip() and not subject:
                subject = line.strip().strip('"').strip("'")
                subject = re.sub(r'^Subject[:\s]+', '', subject, flags=re.IGNORECASE)
                body_start = i + 1
                break
        
        # Rest is body
        body_lines = [l for l in lines[body_start:] if l.strip()]
        body = '\n\n'.join(body_lines)
        
        # Clean up body
        body = re.sub(r'^Body[:\s]+', '', body, flags=re.IGNORECASE)
        
        return {
            'subject': subject or 'Regarding your automation needs',
            'body': body or 'I wanted to reach out regarding your company.'
        }
    
    def _parse_subject_variants(self, response: str) -> List[Dict[str, str]]:
        """Parse subject line variants from response"""
        
        variants = []
        
        # Try JSON parsing first
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Parse text format
        variant_blocks = re.split(r'\n\d+[\.)]\s+', response)
        
        for block in variant_blocks:
            if len(block.strip()) < 10:
                continue
            
            # Extract subject and rationale
            lines = block.strip().split('\n')
            subject = lines[0].strip().strip('"').strip("'")
            rationale = ' '.join(lines[1:]).strip() if len(lines) > 1 else "Personalized subject line"
            
            # Clean up
            subject = re.sub(r'^(?:SUBJECT|Subject)[:\s]+', '', subject, flags=re.IGNORECASE)
            rationale = re.sub(r'^(?:RATIONALE|Rationale)[:\s]+', '', rationale, flags=re.IGNORECASE)
            
            if subject:
                variants.append({
                    'subject': subject,
                    'rationale': rationale
                })
        
        return variants
    
    def _validate_email_quality(self, email_content: Dict[str, str], lead: Lead) -> bool:
        """Validate email quality"""
        
        subject = email_content.get('subject', '')
        body = email_content.get('body', '')
        
        # Check subject line
        if not subject or len(subject) < 10 or len(subject) > 100:
            return False
        
        # Check for generic phrases
        generic_phrases = [
            'hope this email finds you well',
            'i hope this message finds you',
            'just reaching out',
            'quick question'
        ]
        
        body_lower = body.lower()
        if any(phrase in body_lower for phrase in generic_phrases):
            return False
        
        # Check if company name is mentioned
        if lead.company_info.name.lower() not in body_lower:
            return False
        
        # Check length (should be concise)
        if len(body) < 100 or len(body) > 1500:
            return False
        
        # Check for clear CTA
        cta_indicators = ['call', 'chat', 'discuss', 'meet', 'talk', 'explore', 'demo']
        if not any(indicator in body_lower for indicator in cta_indicators):
            return False
        
        return True
    
    async def _regenerate_email(
        self,
        lead: Lead,
        campaign_goal: str,
        previous_attempt: str
    ) -> Dict[str, str]:
        """Regenerate email with more specific guidance"""
        
        lead_data = self._prepare_lead_data(lead)
        
        improved_prompt = get_email_generation_prompt(lead_data, campaign_goal)
        improved_prompt += f"\n\nPREVIOUS ATTEMPT (had issues):\n{previous_attempt}\n\n"
        improved_prompt += "IMPROVEMENTS NEEDED: Be more specific, mention company name, add clear CTA, keep it under 200 words."
        
        response = await self._call_gemini_async(improved_prompt)
        return self._parse_email_response(response)
    
    def _get_fallback_email(self, lead: Lead) -> Dict[str, str]:
        """Get fallback email template if generation fails"""
        
        company_name = lead.company_info.name
        contact_name = "there"
        
        if lead.enrichment_data and lead.enrichment_data.decision_makers:
            contact_name = lead.enrichment_data.decision_makers[0].name or "there"
        
        return {
            'subject': f"Quick question about {company_name}'s automation",
            'body': f"""Hi {contact_name},

I came across {company_name} and was impressed by what you're building in {lead.company_info.industry or 'your space'}.

I work with similar companies to automate workflows and reduce manual processes. Given your growth stage, I thought you might find value in a quick conversation.

Would you be open to a 15-minute call next week?

Best regards"""
        }
    
    def _get_fallback_followup(self, lead: Lead, follow_up_number: int) -> Dict[str, str]:
        """Get fallback follow-up template"""
        
        company_name = lead.company_info.name
        
        if follow_up_number == 1:
            return {
                'subject': f"Re: {company_name} automation",
                'body': f"""Hi,

Following up on my previous email about automation opportunities for {company_name}.

Happy to share a quick case study of how we helped a similar company.

Interested?"""
            }
        else:
            return {
                'subject': f"Closing your file - {company_name}",
                'body': f"""Hi,

I'll take the silence as a no and stop reaching out.

If timing changes or you'd like to explore automation in the future, feel free to reply.

Best of luck!"""
            }
    
    def _get_fallback_subjects(self, lead: Lead) -> List[Dict[str, str]]:
        """Get fallback subject lines"""
        
        company_name = lead.company_info.name
        
        return [
            {'subject': f"Automate workflows at {company_name}", 'rationale': 'Direct value proposition'},
            {'subject': f"Quick question about {company_name}", 'rationale': 'Curiosity-driven'},
            {'subject': f"{company_name} + AI automation", 'rationale': 'Technology focus'},
            {'subject': f"Scaling {company_name}'s operations", 'rationale': 'Growth-focused'},
            {'subject': f"Thought you'd find this interesting", 'rationale': 'Intrigue-based'}
        ]

