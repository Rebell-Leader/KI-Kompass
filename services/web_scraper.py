import logging
import requests
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MunichGovScraper:
    """
    Scraper for Munich government services to extract real-time information
    """
    
    def __init__(self):
        self.base_url = "https://stadt.muenchen.de"
        self.services_url = "https://stadt.muenchen.de/infos/online-services.html"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_services_links(self) -> List[Dict[str, str]]:
        """
        Extract service links from the main services page
        """
        try:
            logger.info("Fetching Munich government services page")
            response = self.session.get(self.services_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            services = []
            
            # Find service links - look for common patterns
            service_links = soup.find_all('a', href=True)
            
            for link in service_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Filter relevant services for relocation
                if self._is_relocation_relevant(text.lower()):
                    full_url = urljoin(self.base_url, href)
                    services.append({
                        'title': text,
                        'url': full_url,
                        'description': self._extract_description(link)
                    })
            
            logger.info(f"Found {len(services)} relevant services")
            return services
            
        except Exception as e:
            logger.error(f"Error fetching services: {str(e)}")
            return []
    
    def _is_relocation_relevant(self, text: str) -> bool:
        """
        Check if service is relevant for relocation
        """
        relevant_keywords = [
            'anmeldung', 'registration', 'bürgerbüro', 'citizen',
            'residence', 'aufenthalt', 'visa', 'permit',
            'steuer', 'tax', 'id', 'ausweis', 'passport',
            'wohnung', 'housing', 'address', 'adresse',
            'kindergarten', 'school', 'schule', 'kita',
            'insurance', 'versicherung', 'health', 'gesundheit',
            'bank', 'konto', 'account', 'arbeit', 'work',
            'employment', 'job', 'integration', 'deutsch',
            'german', 'language', 'sprache'
        ]
        
        return any(keyword in text for keyword in relevant_keywords)
    
    def _extract_description(self, link_element) -> str:
        """
        Extract description from surrounding elements
        """
        try:
            # Look for description in parent or sibling elements
            parent = link_element.parent
            if parent:
                # Try to find description text near the link
                description_text = parent.get_text(strip=True)
                if len(description_text) > len(link_element.get_text(strip=True)):
                    return description_text[:200] + "..." if len(description_text) > 200 else description_text
            return ""
        except:
            return ""
    
    def get_service_details(self, service_url: str) -> Dict[str, str]:
        """
        Get detailed information from a specific service page
        """
        try:
            logger.debug(f"Fetching details for: {service_url}")
            
            # Use trafilatura to extract clean text content
            downloaded = trafilatura.fetch_url(service_url)
            if not downloaded:
                return {}
            
            text_content = trafilatura.extract(downloaded)
            if not text_content:
                return {}
            
            # Extract structured information
            details = {
                'content': text_content,
                'url': service_url,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Try to extract specific information patterns
            lines = text_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if 'öffnungszeiten' in line.lower() or 'opening hours' in line.lower():
                    details['opening_hours'] = line
                elif 'adresse' in line.lower() or 'address' in line.lower():
                    details['address'] = line
                elif 'telefon' in line.lower() or 'phone' in line.lower():
                    details['phone'] = line
                elif 'email' in line.lower() or '@' in line:
                    details['email'] = line
            
            return details
            
        except Exception as e:
            logger.error(f"Error fetching service details from {service_url}: {str(e)}")
            return {}
    
    def get_updated_knowledge_base(self) -> List[Dict[str, str]]:
        """
        Get updated knowledge base from Munich government services
        """
        try:
            services = self.get_services_links()
            knowledge_base = []
            
            # Limit to prevent timeout issues
            max_services = 10
            
            for i, service in enumerate(services[:max_services]):
                if i > 0:  # Rate limiting
                    time.sleep(1)
                
                details = self.get_service_details(service['url'])
                if details and details.get('content'):
                    knowledge_base.append({
                        'title': service['title'],
                        'content': details['content'],
                        'url': service['url'],
                        'source': 'munich_gov',
                        'last_updated': details.get('last_updated', '')
                    })
            
            logger.info(f"Successfully scraped {len(knowledge_base)} service pages")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Error building knowledge base: {str(e)}")
            return []

def get_website_text_content(url: str) -> str:
    """
    Extract text content from a website URL using trafilatura
    Currently returns empty string - actual implementation disabled for MVP
    """
    logger.info(f"get_website_text_content called for {url} (returning empty - stub implementation)")
    return ""
