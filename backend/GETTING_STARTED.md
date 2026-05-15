# Getting Started with DeepLeads AI

This guide will walk you through setting up and using the DeepLeads AI system.

## 📋 Prerequisites

- Python 3.9 or higher
- PostgreSQL database (or SQLite for development)
- Google Gemini API key
- (Optional) SendGrid or SMTP credentials for sending emails

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Copy the example
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Minimum required configuration:**
```env
GOOGLE_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./leadfinder.db
```

**Get your Gemini API key:**
1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy it to your `.env` file

### 3. Initialize Database

```bash
# Run the application once to create tables
python -c "from app.core.database import init_db; init_db()"
```

### 4. Start the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 📖 Usage Guide

### Step 1: Discover Leads

Use the lead discovery endpoint to find companies matching your criteria:

```bash
curl -X POST "http://localhost:8000/api/leads/discover" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["AI & Machine Learning", "Agentic AI & Automation"],
    "geographic_tier": "tier1",
    "specific_locations": ["San Francisco, USA", "New York, USA"],
    "min_employees": 10,
    "max_employees": 100,
    "min_funding_millions": 0.5,
    "max_funding_millions": 10.0,
    "funding_stages": ["Seed", "Series A"],
    "max_results": 20
  }'
```

**Response:**
```json
{
  "leads": [
    {
      "id": 1,
      "company_info": {
        "name": "Example AI Corp",
        "website": "https://example-ai.com",
        "description": "Building AI automation tools...",
        "employee_count": 45,
        "funding_stage": "Series A",
        "funding_amount_millions": 5.0,
        "location": "San Francisco, USA"
      },
      "status": "discovered",
      "score": 85.5
    }
  ],
  "total": 20
}
```

### Step 2: Enrich Leads

Gather detailed intelligence on a specific lead:

```bash
curl -X POST "http://localhost:8000/api/leads/1/enrich"
```

**What this does:**
- Finds decision makers (CEO, CTO, etc.)
- Identifies pain points and challenges
- Gathers recent news and growth signals
- Analyzes technology stack
- Prepares personalization data

**Response:**
```json
{
  "lead": {
    "id": 1,
    "company_info": {...},
    "enrichment_data": {
      "pain_points": [
        "Scaling data processing infrastructure",
        "Manual customer onboarding process"
      ],
      "recent_news": [
        "Raised $5M Series A led by Acme Ventures",
        "Launched new product feature for automation"
      ],
      "decision_makers": [
        {
          "name": "John Smith",
          "title": "CEO & Founder",
          "linkedin_url": "https://linkedin.com/in/johnsmith"
        }
      ],
      "growth_signals": [
        "Hiring 10 new engineers",
        "Expanding to European market"
      ]
    },
    "status": "enriched",
    "score": 92.0
  }
}
```

### Step 3: Create Email Campaign

Generate personalized emails for your leads:

```bash
curl -X POST "http://localhost:8000/api/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q1 2025 AI Automation Outreach",
    "lead_ids": [1, 2, 3, 4, 5],
    "email_template": {
      "subject_line": "Automate {pain_point} at {company_name}",
      "body": "Hi {contact_name},\n\nI noticed..."
    },
    "send_from_email": "hello@yourcompany.com",
    "send_from_name": "Your Name"
  }'
```

**What this does:**
- Generates unique, personalized emails for each lead
- Uses AI to incorporate company-specific details
- References pain points, recent news, and growth signals
- Creates compelling subject lines
- Maintains professional but conversational tone

### Step 4: Review and Launch

Review generated emails:

```bash
curl "http://localhost:8000/api/campaigns/1"
```

Launch the campaign:

```bash
curl -X POST "http://localhost:8000/api/campaigns/1/send"
```

**Note:** The current implementation simulates email sending. For production, integrate with SendGrid, AWS SES, or your preferred email service.

### Step 5: Track Performance

Monitor campaign metrics:

```bash
curl "http://localhost:8000/api/campaigns/1/metrics"
```

**Response:**
```json
{
  "campaign_id": 1,
  "open_rate": 32.5,
  "click_rate": 8.2,
  "response_rate": 4.1,
  "bounce_rate": 2.0,
  "conversion_rate": 4.1
}
```

## 🎯 Best Practices

### Lead Discovery

1. **Start Narrow**: Begin with specific domains and locations
2. **Quality > Quantity**: Use stricter filters (higher min_score)
3. **Test Different Tiers**: Try tier1, tier2, tier3 for different results
4. **Funding Sweet Spot**: $500K - $10M is often ideal
5. **Company Size**: 10-100 employees for best response rates

### Lead Enrichment

1. **Enrich Before Campaigns**: Always enrich leads before emailing
2. **Batch Processing**: Use batch-enrich for efficiency
3. **Manual Review**: Check high-value leads manually
4. **Update Regularly**: Re-enrich leads every 90 days

### Email Campaigns

1. **Personalization is Key**: Reference specific company details
2. **Short & Scannable**: Keep emails under 150 words
3. **Clear CTA**: One specific, low-commitment ask
4. **Timing Matters**: Tuesday-Thursday, 10am-2pm (recipient's timezone)
5. **Follow-Up Strategy**: 3-email sequence over 14 days

### Success Metrics

**Good benchmarks:**
- Open Rate: 25-35%
- Response Rate: 3-8%
- Meeting Booked: 1-3%

**If below these:**
- Improve subject lines (test variants)
- Increase personalization
- Refine target criteria
- Adjust value proposition

## 🔧 Advanced Configuration

### Custom Search Criteria

Modify `app/core/config.py` to add:
- New target domains
- Additional geographic tiers
- Custom funding stage preferences
- Industry-specific keywords

### Email Templates

Customize prompts in `app/prompts/email_prompts.py`:
- Subject line styles
- Body structure
- Follow-up strategies
- Tone and voice

### Database

**PostgreSQL (Recommended for Production):**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/leadfinder
```

**SQLite (Development Only):**
```env
DATABASE_URL=sqlite:///./leadfinder.db
```

## 🐛 Troubleshooting

### "API key not valid"
- Check your `GOOGLE_API_KEY` in `.env`
- Ensure you're using Gemini API (not PaLM or older keys)
- Visit Google AI Studio to verify/regenerate key

### "Database connection failed"
- Verify DATABASE_URL format
- Check PostgreSQL is running
- Ensure database exists

### "Rate limit exceeded"
- Reduce batch sizes
- Add delays between requests
- Check your API quota

### "No leads found"
- Broaden search criteria
- Try different geographic tiers
- Adjust funding/size ranges
- Check domain spelling

## 📚 Next Steps

1. **Integrate Email Service**: Connect SendGrid or AWS SES
2. **Add Scheduling**: Use Celery for background tasks
3. **Build Frontend**: Create React/Vue dashboard
4. **Add Analytics**: Implement detailed tracking
5. **Scale Up**: Deploy to cloud (AWS, GCP, Azure)

## 🤝 Support

- Check `/docs` endpoint for interactive API documentation
- Review code comments for implementation details
- Modify prompts to match your specific use case

## 📄 License

MIT License - See LICENSE file

