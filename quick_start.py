#!/usr/bin/env python3
"""
================================================================================
⚡ 1-Click Quick Start Runner for Beginners
================================================================================
"""

import sys
from linkedin_crawler import LinkedInCrawler

def main():
    print("=" * 60)
    print("🕷️  LinkedIn Post Scraper & JSON Extractor (Quick Start)")
    print("=" * 60)
    print("Make sure your Chrome browser is open and logged into LinkedIn!\n")
    
    query = input("Enter a search topic (or press Enter for Cybersecurity): ").strip()
    if not query:
        query = "cybersecurity"
    
    limit_input = input("How many posts do you want to extract? [Default: 30]: ").strip()
    limit = int(limit_input) if limit_input.isdigit() else 30
    
    output = input("Enter output JSON filename [Default: my_linkedin_posts.json]: ").strip()
    if not output:
        output = "my_linkedin_posts.json"
    
    print("\n🚀 Starting crawler...")
    crawler = LinkedInCrawler(output_file=output)
    crawler.run(topics=[query], target_count=limit)

if __name__ == "__main__":
    main()
