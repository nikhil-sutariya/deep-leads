from enum import Enum

email_regex = r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,4})+$"

class Environment(str, Enum):
    development = "development"
    production = "production"


class WsResponseMsgType(str, Enum):
    notification = "notification"


class WsStatusType(str, Enum):
    success = "success"
    failed = "failed"


class NotificationType(str, Enum):
    error = "error"
    success = "success"


# Target domains configuration
TARGET_DOMAINS = [
    {
        "name": "Accounting",
        "keywords": ["accounting", "accounting automation", "CPA", "document automation", "bookkeeping", "tax"],
        "industries": ["accounting", "professional services", "finance"]
    },
    {
        "name": "Agri Business",
        "keywords": ["agri business", "agriculture", "agtech", "farming technology", "agribusiness"],
        "industries": ["agriculture", "food", "environment"]
    },
    {
        "name": "AgriTech",
        "keywords": ["agtech", "agriculture technology", "farming technology", "precision agriculture", "agri tech"],
        "industries": ["agriculture", "technology", "food"]
    },
    {
        "name": "Artifical Intelligence",
        "keywords": ["AI", "artificial intelligence", "machine learning", "deep learning", "neural networks", "computer vision", "NLP", "AI consulting", "AI strategy"],
        "industries": ["technology", "software", "saas", "consulting"]
    },
    {
        "name": "Biomedical",
        "keywords": ["biomedical", "biomedical engineering", "medical devices", "biomedical research", "clinical"],
        "industries": ["healthcare", "medical", "biotech"]
    },
    {
        "name": "Biotechnology",
        "keywords": ["biotechnology", "biotech", "life sciences", "genomics", "pharmaceutical", "bioengineering"],
        "industries": ["biotech", "healthcare", "pharmaceutical", "life sciences"]
    },
    {
        "name": "Blockchain Development",
        "keywords": ["blockchain", "blockchain development", "cryptocurrency", "distributed ledger", "smart contracts"],
        "industries": ["technology", "finance", "fintech"]
    },
    {
        "name": "Cosmetics",
        "keywords": ["cosmetics", "beauty", "skincare", "personal care", "cosmetic products"],
        "industries": ["retail", "consumer", "fashion", "e-commerce"]
    },
    {
        "name": "Cyber Security",
        "keywords": ["cybersecurity", "cyber security", "data privacy", "infosec", "security automation", "zero trust", "data security"],
        "industries": ["security", "technology", "fintech", "healthcare"]
    },
    {
        "name": "Data analytics",
        "keywords": ["data analytics", "business intelligence", "data analysis", "predictive analytics", "data science"],
        "industries": ["technology", "consulting", "enterprise", "finance"]
    },
    {
        "name": "Digital marketing",
        "keywords": ["digital marketing", "marketing automation", "head of digital", "social media marketing", "SEO", "content marketing"],
        "industries": ["marketing", "consulting", "enterprise", "technology"]
    },
    {
        "name": "Digital transformation",
        "keywords": ["digital transformation", "digital strategy", "digitalization", "digital initiatives"],
        "industries": ["consulting", "enterprise", "technology"]
    },
    {
        "name": "DevOps",
        "keywords": ["DevOps", "CI/CD", "cloud infrastructure", "containerization", "automation"],
        "industries": ["technology", "software", "saas"]
    },
    {
        "name": "E commerce",
        "keywords": ["e-commerce", "ecommerce", "retail", "online store", "e-commerce websites", "e-commerce apps", "online shopping"],
        "industries": ["retail", "e-commerce", "consumer"]
    },
    {
        "name": "EdTech",
        "keywords": ["EdTech", "education technology", "e-learning", "online education", "learning management"],
        "industries": ["education", "technology", "saas"]
    },
    {
        "name": "Environmental technology",
        "keywords": ["environmental technology", "climate tech", "clean tech", "carbon tracking", "green tech", "environment tech"],
        "industries": ["energy", "environment", "manufacturing"]
    },
    {
        "name": "Fashion",
        "keywords": ["fashion", "apparel", "clothing", "lingerie", "fashion retail"],
        "industries": ["retail", "fashion", "e-commerce", "consumer"]
    },
    {
        "name": "Financial Services",
        "keywords": ["financial services", "retail banking", "banking", "investment", "wealth management", "financial advisory"],
        "industries": ["finance", "banking", "fintech"]
    },
    {
        "name": "Fintech",
        "keywords": ["fintech", "financial technology", "payment processing", "banking automation", "financial AI"],
        "industries": ["finance", "fintech", "technology"]
    },
    {
        "name": "Food Processing",
        "keywords": ["food processing", "food manufacturing", "food production", "food industry"],
        "industries": ["food", "manufacturing", "retail"]
    },
    {
        "name": "Fraud Detection",
        "keywords": ["fraud detection", "fraud prevention", "anti-fraud", "fraud analytics", "compliance"],
        "industries": ["fintech", "finance", "security"]
    },
    {
        "name": "Healthcare",
        "keywords": ["healthcare", "medical", "hospital management", "patient care", "telemedicine", "health services"],
        "industries": ["healthcare", "medical"]
    },
    {
        "name": "Healthtech",
        "keywords": ["healthtech", "healthcare AI", "medical AI", "patient portal", "health technology", "digital health"],
        "industries": ["healthcare", "healthtech", "technology"]
    },
    {
        "name": "IoT Solution",
        "keywords": ["IoT", "IoT solution", "internet of things", "IoT-based monitoring", "connected devices"],
        "industries": ["technology", "manufacturing", "healthcare", "retail"]
    },
    {
        "name": "Machine Learning",
        "keywords": ["machine learning", "ML", "deep learning", "predictive modeling", "AI/ML"],
        "industries": ["technology", "software", "saas"]
    },
    {
        "name": "Manufacturing",
        "keywords": ["manufacturing", "manufacturing 4.0", "industrial", "MES systems", "automation", "predictive maintenance"],
        "industries": ["manufacturing", "industrial"]
    },
    {
        "name": "Metaverse",
        "keywords": ["metaverse", "virtual reality", "VR", "AR", "augmented reality", "immersive technology"],
        "industries": ["technology", "gaming", "retail", "entertainment"]
    },
    {
        "name": "Non Profit Organization",
        "keywords": ["non profit", "nonprofit", "non-profit organization", "NGO", "charity", "non-profit"],
        "industries": ["non-profit", "social impact", "various"]
    },
    {
        "name": "Payment Gateway",
        "keywords": ["payment gateway", "payment processing", "online payments", "payment API"],
        "industries": ["fintech", "e-commerce", "retail", "finance"]
    },
    {
        "name": "Payment Integrator",
        "keywords": ["payment integrator", "payment integration", "payment solutions", "payment API integration"],
        "industries": ["fintech", "e-commerce", "technology", "finance"]
    },
    {
        "name": "POS Solution",
        "keywords": ["POS", "point of sale", "POS solution", "POS system", "retail POS"],
        "industries": ["retail", "e-commerce", "hospitality", "finance"]
    },
    {
        "name": "Restaurant",
        "keywords": ["restaurant", "food service", "hospitality", "dining", "restaurant management"],
        "industries": ["hospitality", "food", "retail"]
    },
    {
        "name": "RPA & ETL",
        "keywords": ["RPA", "robotic process automation", "ETL", "data pipeline", "process automation", "workflow automation"],
        "industries": ["technology", "enterprise", "software"]
    },
    {
        "name": "Software Development",
        "keywords": ["software development", "CTO", "engineering", "software engineering", "application development"],
        "industries": ["technology", "software", "saas"]
    },
    {
        "name": "Supply Chain",
        "keywords": ["supply chain", "logistics", "procurement", "inventory management", "distribution"],
        "industries": ["manufacturing", "logistics", "retail"]
    },
    {
        "name": "Sustainable technology",
        "keywords": ["sustainable technology", "sustainability", "green technology", "sustainable solutions", "eco-friendly tech"],
        "industries": ["energy", "environment", "manufacturing"]
    },
    {
        "name": "Textile",
        "keywords": ["textile", "textiles", "fabric", "apparel manufacturing", "garment", "textile industry"],
        "industries": ["manufacturing", "fashion", "retail"]
    },
    {
        "name": "Wearable technology",
        "keywords": ["wearable technology", "wearables", "smart wearables", "fitness trackers", "wearable devices"],
        "industries": ["technology", "healthcare", "retail", "consumer"]
    }
]

# Geographic targeting by tier
GEOGRAPHIC_TIERS = {
    "tier1": {
        "priority": "high",
        "regions": [
            {
                "country": "USA",
                "cities": [
                    "Austin", "Houston", "Dallas", "Baltimore", "Irvine", "New York", "Boston",
                    "Chicago", "San Francisco", "San Diego", "San Jose", "Sacramento", "Miami",
                    "Seattle", "Los Angeles", "Denver", "Columbia", "Phoenix", "Pittsburgh",
                    "Washington", "Tampa", "Orlando", "Richmond", "Rochester", "Sunnyvale"
                ]
            },
            {
                "country": "Germany",
                "cities": ["Munich", "Hamburg", "Düsseldorf", "Berlin", "Hanover"]
            },
            {
                "country": "Switzerland",
                "cities": ["Zurich", "Geneva", "Basel", "Lausanne", "Bern"]
            },
            {
                "country": "Singapore",
                "cities": ["Singapore"]
            }
        ],
        "economic_context": "High innovation, high cost, mature markets"
    },
    "tier2": {
        "priority": "medium",
        "regions": [
            {
                "country": "France",
                "cities": ["Paris", "Nice", "Lyon", "Lille", "Toulouse"]
            },
            {
                "country": "Netherlands",
                "cities": ["Amsterdam", "Rotterdam"]
            },
            {
                "country": "Denmark",
                "cities": ["Copenhagen"]
            },
            {
                "country": "Finland",
                "cities": ["Helsinki", "Turku"]
            },
            {
                "country": "New Zealand",
                "cities": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Dunedin", "Tauranga", "Nelson", "Queenstown", "Rotorua"]
            }
        ],
        "economic_context": "Growing markets, moderate costs"
    },
    "tier3": {
        "priority": "selective",
        "regions": [
            {
                "country": "Poland",
                "cities": ["Warsaw", "Kraków"]
            }
        ],
        "economic_context": "Emerging markets, cost-sensitive, high growth"
    }
}

# Funding stage preferences
FUNDING_STAGES = {
    "preferred": ["Seed", "Series A", "Bootstrapped", "Pre-Seed"],
    "acceptable": ["Series B"],
    "avoid": ["Series C+", "Public", "Corporate"]
}

