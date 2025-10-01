"""
Конфигурация источников для фактчекинга
"""

from typing import Dict, List, Optional
import json
import os

class SourcesConfig:
    """Умная система управления источниками для фактчекинга"""
    
    def __init__(self):
        self.config_file = "sources.json"
        self.sources = self._load_sources()
    
    def _load_sources(self) -> Dict:
        """Загружает конфигурацию источников"""
        default_sources = {
            "general_news": {
                "description": "Общие новостные источники",
                "domains": [
                    "reuters.com",
                    "bbc.com", 
                    "cnn.com",
                    "tass.ru",
                    "ria.ru",
                    "kommersant.ru",
                    "vedomosti.ru",
                    "gazeta.ru",
                    "rbc.ru",
                    "interfax.ru"
                ]
            },
            "technology": {
                "description": "Технологические компании и их официальные источники",
                "domains": [
                    "techcrunch.com",
                    "theverge.com",
                    "arstechnica.com",
                    "wired.com",
                    "venturebeat.com",
                    # Официальные сайты компаний
                    "blog.discord.com",
                    "discord.com",
                    "blog.google.com",
                    "microsoft.com",
                    "apple.com",
                    "meta.com",
                    "openai.com",
                    "github.blog",
                    "stackoverflow.blog",
                    "reddit.com",
                    "twitter.com",
                    "x.com"
                ]
            },
            "finance": {
                "description": "Финансовые источники",
                "domains": [
                    "bloomberg.com",
                    "reuters.com",
                    "wsj.com",
                    "ft.com",
                    "marketwatch.com",
                    "investing.com",
                    "yahoo.com",
                    "cbr.ru",
                    "moex.com"
                ]
            },
            "science": {
                "description": "Научные источники",
                "domains": [
                    "nature.com",
                    "science.org",
                    "pubmed.ncbi.nlm.nih.gov",
                    "arxiv.org",
                    "who.int",
                    "cdc.gov",
                    "fda.gov",
                    "nih.gov"
                ]
            },
            "entertainment": {
                "description": "Развлечения и медиа",
                "domains": [
                    "variety.com",
                    "hollywoodreporter.com",
                    "deadline.com",
                    "entertainment.com",
                    "imdb.com",
                    "rottentomatoes.com"
                ]
            },
            "company_specifics": {
                "description": "Автоматически определяемые официальные сайты",
                "auto_detect": True,
                "patterns": {
                    "discord": ["blog.discord.com", "discord.com", "support.discord.com"],
                    "google": ["blog.google.com", "support.google.com", "developers.google.com"],
                    "microsoft": ["microsoft.com", "techcommunity.microsoft.com", "devblogs.microsoft.com"],
                    "apple": ["apple.com", "developer.apple.com", "support.apple.com"],
                    "meta": ["meta.com", "about.fb.com", "blog.whatsapp.com"],
                    "openai": ["openai.com", "help.openai.com"],
                    "github": ["github.blog", "github.com", "docs.github.com"],
                    "reddit": ["reddit.com", "redditinc.com"],
                    "twitter": ["blog.twitter.com", "help.twitter.com", "x.com"],
                    "telegram": ["telegram.org", "core.telegram.org"],
                    "youtube": ["youtube.com", "creators.youtube.com"],
                    "netflix": ["about.netflix.com", "media.netflix.com"],
                    "amazon": ["press.aboutamazon.com", "aws.amazon.com"],
                    "tesla": ["tesla.com", "ir.tesla.com"]
                }
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        self._save_sources(default_sources)
        return default_sources
    
    def _save_sources(self, sources: Dict):
        """Сохраняет конфигурацию источников"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(sources, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения источников: {e}")
    
    def get_sources_for_topic(self, text: str, category: str = None) -> List[str]:
        """
        Умный выбор источников на основе содержания сообщения
        """
        text_lower = text.lower()
        selected_domains = set()
        
        # Всегда добавляем общие новостные источники
        selected_domains.update(self.sources["general_news"]["domains"])
        
        # Определяем тематику по ключевым словам
        if any(word in text_lower for word in [
            "discord", "google", "microsoft", "apple", "meta", "openai", 
            "github", "reddit", "twitter", "telegram", "youtube", "netflix",
            "amazon", "tesla", "facebook", "instagram", "whatsapp"
        ]):
            # Ищем упоминания конкретных компаний
            for company, domains in self.sources["company_specifics"]["patterns"].items():
                if company in text_lower:
                    selected_domains.update(domains)
            
            # Добавляем технологические источники
            selected_domains.update(self.sources["technology"]["domains"])
        
        if any(word in text_lower for word in [
            "курс", "доллар", "рубль", "биткоин", "акции", "биржа", "банк",
            "инфляция", "экономика", "финансы", "инвестиции"
        ]):
            selected_domains.update(self.sources["finance"]["domains"])
        
        if any(word in text_lower for word in [
            "исследование", "наука", "ученые", "медицина", "вакцина", "лечение",
            "covid", "вирус", "болезнь", "препарат"
        ]):
            selected_domains.update(self.sources["science"]["domains"])
        
        if any(word in text_lower for word in [
            "фильм", "сериал", "актер", "режиссер", "кино", "голливуд",
            "премия", "оскар", "спектакль", "концерт"
        ]) or category == "развлечения":
            selected_domains.update(self.sources["entertainment"]["domains"])
        
        return list(selected_domains)
    
    def add_custom_source(self, category: str, domain: str, description: str = ""):
        """Добавляет пользовательский источник"""
        if category not in self.sources:
            self.sources[category] = {
                "description": description or f"Пользовательская категория: {category}",
                "domains": []
            }
        
        if domain not in self.sources[category]["domains"]:
            self.sources[category]["domains"].append(domain)
            self._save_sources(self.sources)
            return True
        return False
    
    def remove_source(self, category: str, domain: str):
        """Удаляет источник"""
        if category in self.sources and domain in self.sources[category]["domains"]:
            self.sources[category]["domains"].remove(domain)
            self._save_sources(self.sources)
            return True
        return False
    
    def get_all_categories(self) -> Dict[str, str]:
        """Возвращает все категории с описаниями"""
        return {
            category: info.get("description", "")
            for category, info in self.sources.items()
            if not info.get("auto_detect", False)
        }
    
    def get_category_domains(self, category: str) -> List[str]:
        """Возвращает домены для конкретной категории"""
        return self.sources.get(category, {}).get("domains", [])

# Глобальный экземпляр
sources_config = SourcesConfig()