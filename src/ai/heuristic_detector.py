"""Heuristic-based ad and lead detection (No LLM required)."""

import re
from typing import Optional, List
from pydantic import BaseModel

class HeuristicAdResult(BaseModel):
    is_ad: bool
    username: Optional[str] = None
    summary: str = ""
    evidence: str = ""
    confidence: float = 0.0

# Keywords indicating commercial activity
AD_KEYWORDS = [
    r"реклам[аыу]", r"продам", r"услуги", r"предлагаю", r"ищу", r"куплю", 
    r"цена", r"прайс", r"стоимость", r"контакты", r"пишите", r"в лс", 
    r"директ", r"заказ", r"аренда", r"сдам", r"обучение", r"курс",
    r"подбор", r"помощь", r"viber", r"whatsapp", r"телефон", r"номер"
]

# High value business keywords
BUSINESS_KEYWORDS = [
    r"dev", r"software", r"ai", r"agency", r"invest", r"partnership", r"hiring",
    r"разработка", r"программист", r"инвестиции", r"партнерство", r"вакансия"
]

def detect_ad_heuristically(text: str) -> Optional[HeuristicAdResult]:
    if not text or len(text) < 20:
        return None
        
    text_lower = text.lower()
    
    # 1. Look for @username or t.me links
    usernames = re.findall(r"@([a-zA-Z0-9_]{5,32})", text)
    links = re.findall(r"t\.me/([a-zA-Z0-9_]{5,32})", text)
    
    contacts = list(set(usernames + links))
    primary_contact = contacts[0] if contacts else None
    
    # 2. Count keyword hits
    ad_matches = [kw for kw in AD_KEYWORDS if re.search(kw, text_lower)]
    biz_matches = [kw for kw in BUSINESS_KEYWORDS if re.search(kw, text_lower)]
    
    # 3. Decision Logic
    # An ad usually has a contact AND at least 2 ad keywords OR 1 biz keyword
    if (primary_contact and len(ad_matches) >= 1) or (len(ad_matches) >= 3):
        confidence = 0.5 + (0.1 * len(ad_matches)) + (0.2 * len(biz_matches))
        if primary_contact: confidence += 0.2
        
        confidence = min(0.95, confidence)
        
        # Build summary
        summary = " ".join(ad_matches[:3]) + (" (Business)" if biz_matches else "")
        evidence = text[:100] + "..."
        
        return HeuristicAdResult(
            is_ad=True,
            username=primary_contact,
            summary=f"Heuristic Match: {summary}",
            evidence=evidence,
            confidence=confidence
        )
        
    return None
