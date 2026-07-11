"""Static reference pools used by the seed script — kept separate from
run_seed.py so the generation logic isn't buried under data."""

DEPARTMENTS = [
    ("Engineering", "ENG"),
    ("Data Science", "DS"),
    ("Product", "PRD"),
    ("Design", "DSN"),
    ("Quality Assurance", "QA"),
    ("DevOps", "DEVOPS"),
    ("Human Resources", "HR"),
    ("Finance", "FIN"),
    ("Sales", "SALES"),
    ("Marketing", "MKT"),
    ("Customer Success", "CS"),
    ("Legal & Compliance", "LEGAL"),
]

DESIGNATIONS_BY_DEPT = {
    "ENG": ["Software Engineer I", "Software Engineer II", "Senior Software Engineer", "Staff Engineer", "Engineering Manager", "Principal Engineer"],
    "DS": ["Data Analyst", "Data Scientist", "Senior Data Scientist", "ML Engineer", "AI Engineer", "Data Science Manager"],
    "PRD": ["Associate Product Manager", "Product Manager", "Senior Product Manager", "Group Product Manager"],
    "DSN": ["UI/UX Designer", "Senior Designer", "Design Lead", "Product Designer"],
    "QA": ["QA Engineer", "Senior QA Engineer", "SDET", "QA Lead"],
    "DEVOPS": ["DevOps Engineer", "Site Reliability Engineer", "Senior DevOps Engineer", "Infrastructure Lead"],
    "HR": ["HR Executive", "HR Business Partner", "Talent Acquisition Specialist", "HR Manager"],
    "FIN": ["Financial Analyst", "Accountant", "Finance Manager", "Controller"],
    "SALES": ["Sales Executive", "Account Executive", "Sales Manager", "Regional Sales Head"],
    "MKT": ["Marketing Executive", "Content Strategist", "Marketing Manager", "Brand Manager"],
    "CS": ["Customer Success Executive", "Customer Success Manager", "Support Lead"],
    "LEGAL": ["Legal Associate", "Compliance Officer", "Legal Counsel"],
}

BUILDINGS = ["Ethara Tower A", "Ethara Tower B"]

ZONE_NAMES = ["Zone A", "Zone B", "Zone C", "Zone D"]

CLIENTS = [
    "Atlas Retail Group", "Nimbus Financial", "Vertex Healthcare", "Orbit Logistics",
    "Sterling Bank", "Quantum Robotics", "Horizon Media", "Cascade Energy",
    "Meridian Insurance", "Foundry Manufacturing", "Beacon Telecom", "Summit Airlines",
]

PROJECT_NAME_TEMPLATES = [
    "Project {word}", "{word} Platform Revamp", "{word} Data Migration",
    "{word} Mobile App", "{word} Analytics Suite", "{word} Cloud Migration",
]
PROJECT_CODE_WORDS = [
    "Atlas", "Nova", "Zenith", "Orion", "Falcon", "Nimbus", "Vertex", "Titan",
    "Phoenix", "Comet", "Aurora", "Pulse", "Cascade", "Beacon", "Summit",
    "Horizon", "Quantum", "Meridian", "Catalyst", "Odyssey", "Nexus", "Vantage",
    "Ember", "Solstice", "Prism", "Voyager", "Apex", "Frontier", "Lumen", "Echo",
]

LOCATIONS = ["Bangalore", "Hyderabad", "Pune", "Gurugram", "Noida"]
