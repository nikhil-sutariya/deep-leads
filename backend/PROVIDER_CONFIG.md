# AI Provider Configuration Guide

This guide explains how to configure and switch between Gemini and Perplexity AI providers.

## Overview

The lead finder application now supports two AI providers:
- **Gemini** (Google's AI with Google Search grounding)
- **Perplexity** (Perplexity's Sonar model with online search)

Both providers are used across:
- Lead Discovery Agent
- Lead Enrichment Agent

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# AI Provider Selection (options: "gemini" or "perplexity")
AI_PROVIDER=gemini

# API Keys
GOOGLE_API_KEY=your_google_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here  # Only required if using Perplexity
```

### Switching Providers

To switch between providers, simply change the `AI_PROVIDER` value in your `.env` file:

```bash
# Use Gemini
AI_PROVIDER=gemini

# OR use Perplexity
AI_PROVIDER=perplexity
```

## Provider Details

### Gemini Provider

- **Model**: `gemini-2.5-flash` (Discovery) / `gemini-2.0-flash-exp` (Enrichment)
- **Features**: Google Search grounding, real-time data
- **API Key**: Requires `GOOGLE_API_KEY`
- **Best for**: Comprehensive search results with Google's search index

### Perplexity Provider

- **Model**: `sonar`
- **Features**: Online search, real-time data
- **API Key**: Requires `PERPLEXITY_API_KEY`
- **Best for**: Alternative search perspective, competitive analysis

## Implementation Details

### Lead Discovery Agent

The agent automatically routes to the configured provider:

```python
from app.agents.lead_discovery_agent import LeadDiscoveryAgent

# Automatically uses the provider configured in .env
agent = LeadDiscoveryAgent()
leads = agent.discover_leads(request)
```

### Lead Enrichment Agent

Similarly, enrichment uses the configured provider:

```python
from app.agents.lead_enrichment_agent import LeadEnrichmentAgent

# Automatically uses the provider configured in .env
agent = LeadEnrichmentAgent()
enriched_lead = await agent.enrich_lead(lead)
```

## Error Handling

If you configure a provider without the required API key:

```python
# If AI_PROVIDER=perplexity but PERPLEXITY_API_KEY is not set
ValueError: Perplexity API key not configured
```

If you specify an unsupported provider:

```python
# If AI_PROVIDER=some_other_provider
ValueError: Unsupported AI provider: some_other_provider
```

## Testing Different Providers

You can test both providers to compare results:

```bash
# Test with Gemini
AI_PROVIDER=gemini python example_usage.py

# Test with Perplexity
AI_PROVIDER=perplexity python example_usage.py
```

## Configuration Object

The provider configuration is managed through the `Settings` class in `app/core/config.py`:

```python
class Settings(BaseSettings):
    # API Keys
    google_api_key: str
    perplexity_api_key: Optional[str] = None
    
    # Provider Configuration
    ai_provider: str = "gemini"  # Default provider
```

## API Endpoints

Both agents respect the provider configuration when called via API:

```bash
# Lead Discovery - uses configured provider
POST /api/v1/leads/discover

# Lead Enrichment - uses configured provider
POST /api/v1/leads/{lead_id}/enrich
```

## Best Practices

1. **Set Default Provider**: Configure `AI_PROVIDER` in your `.env` file
2. **Keep Both Keys**: Maintain both API keys for easy switching
3. **Monitor Costs**: Different providers have different pricing
4. **Test Both**: Compare results to find the best fit for your use case
5. **Rate Limits**: Be aware of rate limits for each provider

## Troubleshooting

### Import Errors

If you get import errors for `httpx`:

```bash
pip install httpx
```

### API Connection Issues

- Verify your API keys are correct
- Check your network connection
- Review provider status pages

### Rate Limiting

Both providers have rate limits. If you hit them:
- Add delays between requests
- Use batch processing
- Consider upgrading your API plan

## Example Usage

```python
from app.core.config import get_settings
from app.agents.lead_discovery_agent import LeadDiscoveryAgent
from app.agents.lead_enrichment_agent import LeadEnrichmentAgent

# Check current provider
settings = get_settings()
print(f"Current provider: {settings.ai_provider}")

# Discovery uses configured provider
discovery_agent = LeadDiscoveryAgent()
leads = discovery_agent.discover_leads(request)

# Enrichment uses configured provider
enrichment_agent = LeadEnrichmentAgent()
for lead in leads:
    enriched = await enrichment_agent.enrich_lead(lead)
```

## Support

For issues or questions:
- Gemini API: https://ai.google.dev/docs
- Perplexity API: https://docs.perplexity.ai

