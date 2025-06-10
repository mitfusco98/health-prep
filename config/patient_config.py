"""Patient domain configuration"""

# Validation constants
PATIENT_VALIDATION = {
    "name_max_length": 100,
    "mrn_max_length": 20,
    "phone_max_length": 20,
    "email_max_length": 254,
    "address_max_length": 200,
    "insurance_max_length": 100,
}

# Search configuration
PATIENT_SEARCH = {"max_results": 50, "min_search_length": 2}

# Gender options
GENDER_OPTIONS = [
    ("Male", "Male"),
    ("Female", "Female"),
    ("Other", "Other"),
    ("Prefer not to say", "Prefer not to say"),
]

# Insurance providers (can be expanded)
COMMON_INSURANCES = [
    "Medicare",
    "Medicaid",
    "Blue Cross Blue Shield",
    "Aetna",
    "Cigna",
    "UnitedHealth",
    "Humana",
    "Kaiser Permanente",
    "Self-Pay",
    "Other",
]

# Age groups for reporting
AGE_GROUPS = [
    (0, 17, "Pediatric"),
    (18, 39, "Young Adult"),
    (40, 64, "Middle Age"),
    (65, 120, "Senior"),
]
