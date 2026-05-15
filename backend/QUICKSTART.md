# 🚀 DeepLeads AI - 5 Minute Quickstart

## Step 1: Get Your API Key (2 minutes)

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key

## Step 2: Setup (2 minutes)

```bash
cd /Users/nikhil/Desktop/DeepLeads

# Install dependencies
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
GOOGLE_API_KEY=paste_your_key_here
DATABASE_URL=sqlite:///./leadfinder.db
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF

# Initialize database
python -c "from app.core.database import init_db; init_db()"
```

## Step 3: Start Server (1 minute)

```bash
# Start the API server
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

## Step 4: Test It! (Try in another terminal)

### Option A: Use the Example Script
```bash
# In a new terminal
python example_usage.py
```

This will:
- ✅ Discover 10 leads in AI/ML domain
- ✅ Enrich 3 of them with intelligence
- ✅ Create a personalized email campaign
- ✅ Show you the results

### Option B: Try the API Manually

Open http://localhost:8000/docs in your browser and try:

**1. Discover Leads:**
```json
POST /api/leads/discover

{
  "domains": ["AI & Machine Learning"],
  "geographic_tier": "tier1",
  "specific_locations": ["San Francisco, USA"],
  "min_employees": 10,
  "max_employees": 100,
  "min_funding_millions": 0.5,
  "max_funding_millions": 10.0,
  "funding_stages": ["Seed", "Series A"],
  "max_results": 10
}
```

**2. View Your Leads:**
```
GET /api/leads
```

**3. Enrich a Lead:**
```
POST /api/leads/1/enrich
```

**4. Create Campaign:**
```json
POST /api/campaigns

{
  "name": "Test Campaign",
  "lead_ids": [1, 2, 3],
  "email_template": {
    "subject_line": "Quick question about {company_name}",
    "body": "Hi {contact_name},\n\nI noticed..."
  },
  "send_from_email": "you@company.com",
  "send_from_name": "Your Name"
}
```

## 🎯 What Just Happened?

### The System:
1. **Discovered** companies matching your criteria using AI + Google Search
2. **Enriched** them with decision makers, pain points, recent news
3. **Generated** personalized emails for each company
4. **Stored** everything in a database for tracking

### The AI Agents Did:
- 🤖 **Discovery Agent**: Searched Google for matching companies
- 🤖 **Enrichment Agent**: Researched each company in depth  
- 🤖 **Email Agent**: Wrote custom emails for each lead

## 📊 Check Your Results

### In the API Docs (http://localhost:8000/docs):
- See all your leads
- View enrichment data
- Review generated emails

### In the Database:
```bash
sqlite3 leadfinder.db
sqlite> SELECT name, industry, score FROM leads;
```

## 🎉 Success! What's Next?

### Immediate Next Steps:
1. ✅ Review the discovered leads
2. ✅ Check the generated emails
3. ✅ Adjust search criteria in the API
4. ✅ Try different domains and locations

### This Week:
1. Read `STRATEGY_GUIDE.md` for best practices
2. Customize prompts for your use case
3. Test with 50-100 leads
4. Refine based on results

### Production Ready:
1. Read `DEPLOYMENT.md` for deployment options
2. Set up PostgreSQL database
3. Integrate email service (SendGrid/AWS SES)
4. Scale to 1000+ leads/month

## 🆘 Troubleshooting

### "Cannot connect to API"
```bash
# Make sure server is running
uvicorn app.main:app --reload
```

### "API key not valid"
- Check your .env file
- Make sure GOOGLE_API_KEY is set correctly
- Try regenerating key at https://makersuite.google.com/app/apikey

### "No leads found"
- Try broader search criteria
- Increase max_results
- Try different geographic tier
- Check different domains

### "Import errors"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## 📚 Learn More

- **API Documentation**: http://localhost:8000/docs
- **Getting Started Guide**: `GETTING_STARTED.md`
- **Strategy Guide**: `STRATEGY_GUIDE.md` (READ THIS!)
- **Deployment Guide**: `DEPLOYMENT.md`
- **Project Summary**: `PROJECT_SUMMARY.md`

## 🎯 Key Files

```
DeepLeads/
├── app/main.py              # Start here for code
├── example_usage.py         # Run this to test
├── STRATEGY_GUIDE.md        # READ THIS for strategy
├── GETTING_STARTED.md       # Detailed setup
├── requirements.txt         # Dependencies
└── .env                     # Your API keys
```

## 💡 Pro Tips

1. **Start Small**: Test with 10-20 leads first
2. **Quality Check**: Review AI-generated content before scaling
3. **Iterate**: Adjust prompts based on results
4. **Track Metrics**: Monitor response rates and optimize
5. **Scale Gradually**: Go from 50 → 200 → 1000 leads/month

## 🚀 You're Ready!

The system is running and ready to find leads. 

**Go discover some companies and see what the AI can do!**

```bash
# Try this now:
python example_usage.py
```

---

**Questions?** Check the documentation or review the code - it's well commented!

**Ready to scale?** Read `STRATEGY_GUIDE.md` next!

