from urllib.parse import urlparse

DOMAIN_RULES = {
    "www.healthdirect.gov.au": {
        "source_name": "healthdirect",
        "country": "AU",
        "trust_weight": 1.0,
        "allowed_path_keywords": [
            "/health-topics/",
            "/symptom-checker",
            "/abdominal-pain",
            "/diarrhoea",
            "/shortness-of-breath",
            "/chest-pain",
            "/cough",
            "/headache",
            "/fatigue",
        ],
        "blocked_path_keywords": [
            "/app/",
            "/about/",
            "/news/",
            "/contact-",
        ],
    },
    "www.nhs.uk": {
        "source_name": "nhs",
        "country": "UK",
        "trust_weight": 0.95,
        "allowed_path_keywords": [
            "/symptoms/",
            "/conditions/",
            "/health-a-to-z/",
            "/mental-health/feelings-symptoms-behaviours/",
        ],
        "blocked_path_keywords": [
            "/service-search/",
            "/conditions/?page=",
            "/live-well/",
            "/vaccinations/",
        ],
    },
    "www.cdc.gov": {
        "source_name": "cdc",
        "country": "US",
        "trust_weight": 0.9,
        "allowed_path_keywords": [
            "/health-topics",
            "/covid/signs-symptoms/",
            "/port-health/",
            "/patients/symptoms",
        ],
        "blocked_path_keywords": [
            "/media/",
            "/about/",
            "/other/",
            "/tools/",
        ],
    },
}