# This map links Congressional Committees to the sectors they regulate.
# Used by Granite 3.3 to calculate the "Corruption Score".
#
# How it works:
# - When a member of Congress trades stocks in sectors their committee regulates,
#   it increases their "Corruption Score"
# - Committees have insider knowledge of upcoming legislation, contracts, and regulations
#   that directly impact these sectors

COMMITTEE_MAP = {
    # AGRICULTURE: Controls food prices, subsidies, and fertilizer regulation
    "House Committee on Agriculture": [
        "Consumer Defensive",
        "Basic Materials",  # Fertilizer companies like MOS/NTR
        "Food Distribution"
    ],
    "Senate Committee on Agriculture, Nutrition, and Forestry": [
        "Consumer Defensive",
        "Basic Materials",  # Fertilizer companies like MOS/NTR
        "Food Distribution"
    ],
    
    # ARMED SERVICES: The "War Machine" - Direct contracts to Lockheed, Raytheon
    "House Committee on Armed Services": [
        "Industrials", 
        "Aerospace & Defense", 
        "Technology"
    ],
    "Senate Committee on Armed Services": [
        "Industrials", 
        "Aerospace & Defense", 
        "Technology"
    ],
    
    # ENERGY & COMMERCE: Broad jurisdiction over energy, healthcare, and telecom
    "House Committee on Energy and Commerce": [
        "Energy",
        "Healthcare",
        "Technology",
        "Utilities",
        "Communication Services"
    ],
    "Senate Committee on Energy and Natural Resources": [
        "Energy",
        "Utilities",
        "Basic Materials",
        "Solar"
    ],
    
    # FINANCIAL SERVICES: Regulates banks, capital markets, and real estate
    "House Committee on Financial Services": [
        "Financial Services",
        "Real Estate",
        "Banks",
        "Capital Markets"
    ],
    "Senate Committee on Banking, Housing, and Urban Affairs": [
        "Financial Services",
        "Real Estate",
        "Banks"
    ],
    
    # TRANSPORTATION: Infrastructure spending and transportation contracts
    "House Committee on Transportation and Infrastructure": [
        "Industrials",
        "Engineering & Construction",
        "Railroads",
        "Airlines",
        "Logistics"
    ],
    "Senate Committee on Commerce, Science, and Transportation": [
        "Technology",
        "Communication Services",
        "Industrials",
        "Airlines",
        "Semiconductors"
    ],
    "Senate Committee on Environment and Public Works": [
        "Utilities",
        "Industrials",
        "Construction",
        "Waste Management"
    ],
    
    # FOREIGN AFFAIRS: International energy deals and defense exports
    "House Committee on Foreign Affairs": [
        "Energy",
        "Industrials",
        "Defense Contractors"
    ],
    "Senate Committee on Foreign Relations": [
        "Energy",
        "Industrials",
        "Defense Contractors"
    ],
    
    # HOMELAND SECURITY: Cybersecurity contracts (CrowdStrike, Palo Alto, Palantir)
    # This is where the contracts for CrowdStrike, Palo Alto Networks, and Palantir come from.
    "House Committee on Homeland Security": [
        "Technology",
        "Software - Infrastructure",
        "Cybersecurity"
    ],
    "Senate Committee on Homeland Security and Governmental Affairs": [
        "Technology",
        "Cybersecurity",
        "Industrials"
    ],
    
    # JUDICIARY: Handles Antitrust laws (breaking up Google/Facebook)
    # Why? Because the Judiciary committee handles Antitrust. When they sue Google or 
    # break up Facebook, they know about it first.
    "House Committee on the Judiciary": [
        "Technology",
        "Internet Content",
        "Communication Services"
    ],
    "Senate Committee on the Judiciary": [
        "Technology",
        "Internet Content",
        "Communication Services"
    ],
    
    # NATURAL RESOURCES: Mining, oil, and energy extraction
    "House Committee on Natural Resources": [
        "Energy",
        "Basic Materials",
        "Metals & Mining"
    ],
    
    # SCIENCE & TECHNOLOGY: R&D funding, semiconductors, space contracts
    "House Committee on Science, Space, and Technology": [
        "Technology",
        "Semiconductors",
        "Aerospace & Defense",
        "Clean Energy"
    ],
    
    # VETERANS AFFAIRS: Healthcare and pharmaceutical contracts for veterans
    "House Committee on Veterans' Affairs": [
        "Healthcare",
        "Pharmaceuticals"
    ],
    "Senate Committee on Veterans' Affairs": [
        "Healthcare",
        "Pharmaceuticals"
    ],
    
    # INTELLIGENCE: Classified contracts, defense tech, cybersecurity
    "House Permanent Select Committee on Intelligence": [
        "Technology",
        "Aerospace & Defense",
        "Cybersecurity"
    ],
    "Senate Select Committee on Intelligence": [
        "Technology",
        "Aerospace & Defense",
        "Cybersecurity"
    ],
    
    # WAYS & MEANS / FINANCE: Write Tax Law (Capital Gains) and Healthcare (Medicare)
    # These committees write Tax Law. They affect everyone, but specifically Healthcare 
    # (Medicare rules) and Finance (Capital Gains taxes).
    "House Committee on Ways and Means": [
        "Healthcare",
        "Financial Services",
        "Technology"
    ],
    "Senate Committee on Finance": [
        "Healthcare",
        "Financial Services",
        "Technology"
    ],
    
    # HEALTH, EDUCATION, LABOR: Healthcare regulation, biotech, education policy
    "Senate Committee on Health, Education, Labor, and Pensions": [
        "Healthcare",
        "Biotechnology",
        "Education"
    ],
    
    # JOINT COMMITTEES: Cross-chamber committees with specific jurisdictions
    # Note: Database may store as "Committee {CODE}" format, but full names are also mapped
    "Joint Committee on Taxation": [
        "Financial Services",
        "Healthcare",
        "Energy"
    ],
    "Committee JSTX": [  # Alias for database format
        "Financial Services",
        "Healthcare",
        "Energy"
    ],
    "Joint Economic Committee": [
        "Financial Services",
        "Basic Materials"
    ],
    "Committee JSEC": [  # Alias for database format
        "Financial Services",
        "Basic Materials"
    ],
    "Helsinki Commission (Security & Cooperation in Europe)": [
        "Defense",
        "Energy"
    ],
    "Committee JCSE": [  # Alias for database format
        "Defense",
        "Energy"
    ],
    "Joint Committee on Printing": [],  # No sector impact - manages Government Publishing Office
    "Committee JSPR": [],  # Alias for database format - No sector impact
    "Joint Committee on the Library": [],  # No sector impact - oversees Library of Congress
    "Committee JSLC": [],  # Alias for database format - No sector impact
    
    # HOUSE SELECT COMMITTEES: Special investigative committees
    "Select Committee on the CCP (China Committee)": [
        "Technology",
        "Semiconductors",
        "Defense"
    ],
    "Committee HSZS": [  # Alias for database format
        "Technology",
        "Semiconductors",
        "Defense"
    ],
    "Select Subcommittee on Weaponization": [
        "Communication Services",
        "Social Media"
    ],
    "Committee HSQJ": [  # Alias for database format
        "Communication Services",
        "Social Media"
    ],
    "Select Subcommittee on the Coronavirus Pandemic": [
        "Healthcare",
        "Biotech",
        "Pharmaceuticals"
    ],
    "Committee HSSO": [  # Alias for database format
        "Healthcare",
        "Biotech",
        "Pharmaceuticals"
    ],
    
    # ---------------------------------------------------------
    # THE "POWER OF THE PURSE" (Appropriations & Budget)
    # These control *how much* money companies get.
    # ---------------------------------------------------------
    "Senate Committee on Appropriations": [
        "Industrials",
        "Aerospace & Defense",
        "Healthcare",
        "Technology",
        "Construction"
    ],
    "House Committee on Appropriations": [
        "Industrials",
        "Aerospace & Defense",
        "Healthcare",
        "Technology",
        "Construction"
    ],
    "Senate Committee on the Budget": [
        "Financial Services",
        "Healthcare",
        "Defense"
    ],
    "House Committee on the Budget": [
        "Financial Services",
        "Healthcare",
        "Defense"
    ],
    
    # ---------------------------------------------------------
    # RULES & ADMIN (The Gatekeepers)
    # House Rules determines IF a bill gets a vote. High corruption risk.
    # ---------------------------------------------------------
    "House Committee on Rules": [
        "Financial Services",
        "Healthcare",
        "Energy",
        "Technology"
    ],
    "Senate Committee on Rules and Administration": [
        "Communication Services",
        "Technology"
    ],
    "House Committee on House Administration": [
        "Communication Services",
        "Technology"
    ],
    
    # ---------------------------------------------------------
    # SMALL BUSINESS & WORKFORCE
    # ---------------------------------------------------------
    "House Committee on Education and the Workforce": [
        "Consumer Defensive",
        "Financial Services",
        "Industrials"
    ],
    "Senate Committee on Small Business and Entrepreneurship": [
        "Financial Services",
        "Consumer Cyclical"
    ],
    "House Committee on Small Business": [
        "Financial Services",
        "Consumer Cyclical"
    ],
    
    # ---------------------------------------------------------
    # SPECIAL / OVERSIGHT (The Investigators)
    # ---------------------------------------------------------
    "House Committee on Oversight and Accountability": [
        "Technology",
        "Healthcare",
        "Financial Services"
    ],
    "Senate Special Committee on Aging": [
        "Healthcare",
        "Pharmaceuticals",
        "Financial Services"
    ],
    "Senate Committee on Indian Affairs": [
        "Consumer Cyclical",
        "Real Estate",
        "Energy"
    ],
    "Senate Caucus on International Narcotics Control": [
        "Pharmaceuticals",
        "Defense"
    ],
    
    # ---------------------------------------------------------
    # ETHICS (Internal Police - Low Trading Signal)
    # ---------------------------------------------------------
    "Senate Select Committee on Ethics": []  # They police the Senators, not the market
}

