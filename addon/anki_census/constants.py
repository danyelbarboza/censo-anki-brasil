ADDON_NAME = "Anki Census"
LEGACY_ADDON_NAME = "Anki Census"
ADDON_VERSION = "0.1.12"
SCHEMA_VERSION = "1.0.0"
AUTHOR = "Danyel Barboza - Anki Community"
DEFAULT_API_BASE_URL = "https://anki-census-api.danyelbarboza.workers.dev"
DEV_PASSWORD = "4599"
USER_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
USER_ID_LENGTH = 10
SUPPORTED_SCHEMA_VERSIONS = [SCHEMA_VERSION]

PRIMARY_AREAS = [
    "", "Medicine", "Nursing", "Dentistry", "Psychology", "Pharmacy", "Physiotherapy",
    "Other health fields", "Languages", "English", "Spanish", "French", "German",
    "Japanese", "Korean", "Chinese", "Other languages", "Public service exams", "Law",
    "Bar exam", "College entrance exams", "School/College", "Programming/IT", "Engineering",
    "Mathematics", "Statistics", "Data science", "Economics/Finance", "History",
    "Philosophy", "Theology/Religious studies", "Music", "Chess", "Personal studies",
    "Other", "Prefer not to say",
]

COUNTRIES = [
    "", "Brazil", "Portugal", "Angola", "Mozambique", "Cape Verde", "Guinea-Bissau",
    "Sao Tome and Principe", "Timor-Leste", "United States", "Canada", "United Kingdom",
    "Germany", "France", "Spain", "Italy", "Argentina", "Chile", "Uruguay",
    "Paraguay", "Other country", "Prefer not to say",
]

BRAZIL_STATES = [
    "", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    "Prefer not to say",
]

EXPERIENCE_BUCKETS = [
    "", "Less than 1 month", "1 to 6 months", "6 months to 1 year", "1 to 3 years",
    "3 to 5 years", "More than 5 years", "Prefer not to say",
]

LEVELS = [
    "", "Beginner", "Intermediate", "Advanced", "Technical user",
    "I build templates/scripts/add-ons", "Prefer not to say",
]

AGE_BUCKETS = ["", "Under 18", "18-24", "25-34", "35-44", "45-54", "55+", "Prefer not to say"]

PLATFORMS = ["Anki Desktop", "AnkiDroid", "AnkiMobile iOS", "AnkiWeb"]
