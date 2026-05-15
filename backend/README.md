# DeepLeads AI - Intelligent Lead Generation & Outreach System

## 🎯 Overview

An AI-powered lead generation system that intelligently discovers, enriches, and engages with businesses in high-value tech domains using multi-agent architecture.

## ✨ Key Features

### 1. **Smart Lead Discovery Agent**
- Multi-domain targeting (AI/ML, Cybersecurity, Automation, etc.)
- Geographic & economic filtering
- Company size & funding stage filtering
- Industry-specific search strategies

### 2. **Lead Enrichment Agent**
- Company data collection
- Decision-maker identification
- Technology stack analysis
- Pain point identification

### 3. **Email Campaign Agent**
- Personalized email generation
- A/B testing capabilities
- Campaign performance tracking
- Follow-up automation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Lead       │  │   Lead       │  │   Email      │ │
│  │  Discovery   │→ │  Enrichment  │→ │  Campaign    │ │
│  │   Agent      │  │   Agent      │  │   Agent      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         ↓                 ↓                  ↓          │
│  ┌─────────────────────────────────────────────────┐  │
│  │          PostgreSQL Database                    │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Target Market Strategy

### Company Size Focus
- **Employees**: 10-100
- **Funding**: $500K - $10M (Series A, Seed, or Bootstrapped)
- **Revenue**: $1M - $50M ARR

### Geographic Priorities
1. **Tier 1**: US (SF, NYC, Austin, Boston), UK, Germany
2. **Tier 2**: Canada, France, Netherlands, Singapore
3. **Tier 3**: India (Bangalore, Mumbai), Australia, UAE

### Industry Domains
- AI/ML/Data Science applications
- Agentic AI & Automation
- Cybersecurity & Privacy tech
- Environmental & Sustainable tech
- Industry-specific AI (Healthcare, Finance, Manufacturing)

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
1. Copy `.env.example` to `.env`
2. Add your API keys:
   - Google Gemini API key
   - Database credentials
   - Email service credentials

### Run the Server
```bash
uvicorn app.main:app --reload
```

## 📊 API Endpoints

### Lead Discovery
- `POST /api/leads/discover` - Start lead discovery campaign
- `GET /api/leads` - List discovered leads
- `GET /api/leads/{id}` - Get lead details

### Lead Enrichment
- `POST /api/leads/{id}/enrich` - Enrich specific lead
- `POST /api/leads/batch-enrich` - Batch enrichment

### Email Campaigns
- `POST /api/campaigns` - Create email campaign
- `GET /api/campaigns/{id}` - Campaign status & metrics
- `POST /api/campaigns/{id}/send` - Launch campaign

## 🧠 Intelligent Filtering Strategy

The system uses a multi-stage filtering approach:

1. **Pre-Search Filtering**: Define search parameters based on domain, location, size
2. **AI-Powered Filtering**: Gemini evaluates relevance and fit
3. **Post-Search Validation**: Verify company data and contact quality
4. **Scoring System**: Rank leads by likelihood to convert

## 📈 Success Metrics

- **Lead Discovery Rate**: 50-100 qualified leads per hour
- **Enrichment Accuracy**: 80%+ data completeness
- **Email Open Rate Target**: 25-35%
- **Response Rate Target**: 3-8%

## 🔒 Best Practices

1. **Avoid Over-Funded Companies**: Filter out companies with >$50M funding
2. **Geographic Relevance**: Match offerings to regional needs
3. **Timing**: Research company growth signals (new funding, hiring, product launches)
4. **Personalization**: Use AI to craft unique messages per lead
5. **Compliance**: Respect GDPR, CAN-SPAM, and local regulations

## 📝 License

MIT License - See LICENSE file for details

