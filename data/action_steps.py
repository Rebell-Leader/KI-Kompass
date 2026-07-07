from datetime import datetime

# Date this curated dataset was last reviewed against the official sources.
# Update it whenever the steps below are re-checked. Individual steps get a
# fresher last_verified automatically when 'flask refresh-knowledge' succeeds.
DATA_CURATED_AT = datetime(2025, 6, 29)

# Official online appointment booking (Terminvereinbarung) links for steps
# that require an appointment in Munich. Keyed by step title so existing
# databases can be backfilled too.
BOOKING_URLS = {
    # Buergerbuero appointments (Anmeldung and most citizen services)
    "Address Registration (Anmeldung)": "https://stadt.muenchen.de/buergerservice/terminvereinbarung.html",
    # Auslaenderbehoerde (foreigners office) appointment portal
    "Apply for Residence Permit": "https://terminvereinbarung.muenchen.de/abh/termin/",
}


def populate_action_steps(db):
    """
    Populate the database with predefined action steps for relocation to Munich.
    """
    from models import ActionStep

    # Define action steps
    action_steps = [
        # Pre-arrival planning
        {
            "title": "Research Visa Requirements",
            "description": "Determine which visa type you need based on your purpose of stay (work, study, family reunion, etc.).",
            "instructions": "Visit the German Federal Foreign Office website or contact the German consulate in your country for detailed visa requirements.",
            "category": "Pre-arrival",
            "priority": 1,
            "estimated_time": "1-2 weeks",
            "timeline_offset": -60,  # 60 days before arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.auswaertiges-amt.de/en/visa-service",
            "required_documents": ["Passport", "Visa application form", "Proof of financial means", "Travel insurance"],
        },
        
        {
            "title": "Apply for Visa",
            "description": "Submit your visa application at the German consulate or embassy in your home country.",
            "instructions": "Schedule an appointment at your local German consulate or embassy. Prepare all required documents and pay the visa fee.",
            "category": "Pre-arrival",
            "priority": 1,
            "estimated_time": "4-8 weeks",
            "timeline_offset": -90,  # 90 days before arrival
            "prerequisites": ["Research Visa Requirements"],
            "visa_types": ["work", "study", "family reunion", "job seeker"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.auswaertiges-amt.de/en/visa-service",
            "required_documents": ["Passport", "Visa application form", "Biometric photos", "Proof of financial means", "Travel insurance", "Accommodation details", "Employment contract (if applicable)"]
        },
        
        {
            "title": "Find Temporary Accommodation",
            "description": "Book temporary accommodation for your first few weeks in Munich while you look for a permanent home.",
            "instructions": "Look for short-term rentals, serviced apartments, or hotels in Munich. Areas like Maxvorstadt, Haidhausen, or Schwabing are central and convenient.",
            "category": "Pre-arrival",
            "priority": 1,
            "estimated_time": "1-2 weeks",
            "timeline_offset": -30,  # 30 days before arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.muenchen.de/int/en/living/finding-accommodation",
            "required_documents": []
        },
        
        {
            "title": "Arrange Health Insurance",
            "description": "Secure health insurance coverage before arriving in Germany, as it's mandatory for all residents.",
            "instructions": "If employed, your employer will typically assist with public health insurance registration. Self-employed individuals should research private options or voluntary public insurance.",
            "category": "Pre-arrival",
            "priority": 1,
            "estimated_time": "1-2 weeks",
            "timeline_offset": -14,  # 14 days before arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.krankenkassen.de/gesetzliche-krankenkassen/krankenkassen-liste/",
            "required_documents": ["Passport", "Visa or residence permit", "Employment contract (if applicable)"]
        },
        
        # First week tasks
        {
            "title": "Address Registration (Anmeldung)",
            "description": "Register your address at the local Bürgerbüro (citizen's office) within 14 days of arrival.",
            "instructions": "Book an appointment online at the Bürgerbüro. Bring your passport, visa, and Wohnungsgeberbestätigung (landlord confirmation) to your appointment.",
            "category": "First week",
            "priority": 1,
            "estimated_time": "1-2 hours",
            "timeline_offset": 7,  # 7 days after arrival
            "prerequisites": ["Find Temporary Accommodation"],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.muenchen.de/rathaus/home_en/Department-of-Public-Order/Residence-Registration",
            "address": "Kreisverwaltungsreferat (KVR), Ruppertstraße 19, 80466 München",
            "required_documents": ["Passport", "Visa", "Wohnungsgeberbestätigung (landlord confirmation)"]
        },
        
        {
            "title": "Open a Bank Account",
            "description": "Set up a German bank account to manage your finances, pay rent, and receive salary.",
            "instructions": "Visit a local bank branch with your passport and Anmeldung (registration certificate). Compare different banks for features and fees before deciding.",
            "category": "First week",
            "priority": 2,
            "estimated_time": "1-2 hours",
            "timeline_offset": 10,  # 10 days after arrival
            "prerequisites": ["Address Registration (Anmeldung)"],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "",
            "required_documents": ["Passport", "Registration certificate (Anmeldebestätigung)", "Residence permit (if applicable)"]
        },
        
        {
            "title": "Get a German SIM Card",
            "description": "Purchase a German SIM card or mobile phone plan for local connectivity.",
            "instructions": "Visit providers like Telekom, Vodafone, O2, or discount providers like Aldi Talk or Lidl Connect. Bring your passport for registration.",
            "category": "First week",
            "priority": 3,
            "estimated_time": "1 hour",
            "timeline_offset": 3,  # 3 days after arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "",
            "required_documents": ["Passport", "Credit card or cash for payment"]
        },
        
        # First month tasks
        {
            "title": "Apply for Residence Permit",
            "description": "Non-EU citizens must apply for a residence permit at the Foreign Office (Ausländerbehörde).",
            "instructions": "Book an appointment online at the Ausländerbehörde. Prepare all required documents based on your visa type.",
            "category": "First month",
            "priority": 1,
            "estimated_time": "2-3 hours",
            "timeline_offset": 21,  # 21 days after arrival
            "prerequisites": ["Address Registration (Anmeldung)"],
            "visa_types": ["work", "study", "family reunion", "job seeker"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.muenchen.de/rathaus/home_en/Department-of-Public-Order/Foreigners-Office",
            "address": "Ausländerbehörde, Ruppertstraße 19, 80466 München",
            "required_documents": ["Passport", "Visa", "Biometric photos", "Registration certificate", "Employment contract/university enrollment", "Proof of health insurance", "Proof of financial means"]
        },
        
        {
            "title": "Register with Tax Office",
            "description": "Register with the local tax office to receive your tax ID number and tax class assignment.",
            "instructions": "Visit your district's Finanzamt (tax office) with your registration certificate. If employed, your employer will typically assist with this process.",
            "category": "First month",
            "priority": 2,
            "estimated_time": "1-2 hours",
            "timeline_offset": 28,  # 28 days after arrival
            "prerequisites": ["Address Registration (Anmeldung)"],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": True,
            "url": "https://www.finanzamt.bayern.de/",
            "required_documents": ["Passport", "Registration certificate", "Employment contract (if applicable)"]
        },
        
        {
            "title": "Find Permanent Housing",
            "description": "Search for and secure long-term accommodation in Munich.",
            "instructions": "Use websites like ImmobilienScout24, WG-Gesucht, or work with real estate agents. Prepare for high competition by having all documents ready.",
            "category": "First month",
            "priority": 1,
            "estimated_time": "4-8 weeks",
            "timeline_offset": 14,  # 14 days after arrival
            "prerequisites": ["Open a Bank Account"],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.immobilienscout24.de/",
            "required_documents": ["Passport", "Registration certificate", "Proof of income/employment", "SCHUFA credit report", "Previous landlord reference"]
        },
        
        {
            "title": "Register Children in School/Daycare",
            "description": "Enroll your children in local schools or daycare centers (Kindergarten).",
            "instructions": "Contact the Schulamt (school office) or visit local Kindergartens to inquire about availability and registration procedures.",
            "category": "First month",
            "priority": 1,
            "estimated_time": "2-4 weeks",
            "timeline_offset": 14,  # 14 days after arrival
            "prerequisites": ["Address Registration (Anmeldung)"],
            "visa_types": ["all"],
            "family_required": True,
            "employment_required": False,
            "url": "https://www.muenchen.de/rathaus/Stadtverwaltung/Referat-fuer-Bildung-und-Sport/Schule.html",
            "required_documents": ["Child's passport", "Birth certificate", "Registration certificate", "Vaccination records", "Previous school records"]
        },
        
        # Settling in tasks
        {
            "title": "Register for German Language Course",
            "description": "Enroll in a German language course to improve your integration and job prospects.",
            "instructions": "Contact the Volkshochschule München (VHS) or private language schools like Goethe-Institut for course options and schedules.",
            "category": "Settling in",
            "priority": 2,
            "estimated_time": "ongoing",
            "timeline_offset": 30,  # 30 days after arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.mvhs.de/programm/deutsch-als-fremdsprache",
            "required_documents": ["Passport", "Registration certificate"]
        },
        
        {
            "title": "Get Public Transportation Pass",
            "description": "Purchase a monthly or annual pass for Munich's public transportation system (MVV).",
            "instructions": "Visit an MVV customer center or use the MVG app to buy an IsarCard or IsarCard12 for unlimited travel.",
            "category": "Settling in",
            "priority": 2,
            "estimated_time": "1 hour",
            "timeline_offset": 5,  # 5 days after arrival
            "prerequisites": [],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.mvg.de/tickets-tarife/abonnement.html",
            "required_documents": ["Passport", "Bank account details for subscription"]
        },
        
        {
            "title": "Register for Integration Course",
            "description": "Enroll in an integration course covering German language and culture (often mandatory for non-EU citizens).",
            "instructions": "Contact the Federal Office for Migration and Refugees (BAMF) or authorized language schools to register for an integration course.",
            "category": "Settling in",
            "priority": 2,
            "estimated_time": "ongoing (600-900 hours)",
            "timeline_offset": 45,  # 45 days after arrival
            "prerequisites": ["Apply for Residence Permit"],
            "visa_types": ["family reunion", "work", "humanitarian"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.bamf.de/EN/Themen/Integration/ZugewanderteTeilnehmende/Integrationskurse/integrationskurse-node.html",
            "required_documents": ["Passport", "Residence permit", "Registration certificate"]
        },
        
        {
            "title": "Set Up Utilities and Internet",
            "description": "Arrange electricity, water, heating, and internet services for your permanent accommodation.",
            "instructions": "Contact local utility providers like Stadtwerke München for electricity/water and providers like Telekom, Vodafone, or O2 for internet.",
            "category": "Settling in",
            "priority": 1,
            "estimated_time": "1-2 weeks",
            "timeline_offset": 1,  # 1 day after finding permanent housing
            "prerequisites": ["Find Permanent Housing"],
            "visa_types": ["all"],
            "family_required": False,
            "employment_required": False,
            "url": "https://www.swm.de/",
            "required_documents": ["Passport", "Registration certificate", "Rental contract", "Bank account details"]
        }
    ]
    
    # Add steps to database, stamping data provenance: the step's url doubles
    # as the information source until a dedicated source_url is curated
    for step_data in action_steps:
        step_data.setdefault("source_url", step_data.get("url") or None)
        step_data.setdefault("last_verified", DATA_CURATED_AT)
        step_data.setdefault("booking_url", BOOKING_URLS.get(step_data["title"]))

        # Check if step already exists
        existing_step = ActionStep.query.filter_by(title=step_data["title"]).first()
        if not existing_step:
            step = ActionStep(**step_data)
            db.session.add(step)

    db.session.commit()


def backfill_provenance(db):
    """Stamp source_url/last_verified on rows created before those columns existed"""
    from models import ActionStep

    updated = 0
    for step in ActionStep.query.filter(ActionStep.source_url.is_(None)).all():
        if step.url:
            step.source_url = step.url
        if step.last_verified is None:
            step.last_verified = DATA_CURATED_AT
        updated += 1

    for title, booking_url in BOOKING_URLS.items():
        step = ActionStep.query.filter_by(title=title).first()
        if step and not step.booking_url:
            step.booking_url = booking_url
            updated += 1

    if updated:
        db.session.commit()
    return updated
