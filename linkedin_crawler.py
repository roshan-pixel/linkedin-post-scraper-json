#!/usr/bin/env python3
"""
================================================================================
🚀 LinkedIn Post Crawler & Structured JSON Extractor
================================================================================
Author: Roshan Singh (roshan-pixel)
Repository: https://github.com/roshan-pixel/LINKED-IN-SACRAWLLER-FOR-EXTRACTING-POST-JSON
Description:
    Autonomous LinkedIn post crawler that hooks into an active, authenticated
    browser session (via Kimi WebBridge / Chrome CDP) and harvests posts into
    structured JSON. Handles single queries or multi-topic research with
    infinite virtual scroll support.
================================================================================
"""

import urllib.request
import urllib.parse
import json
import time
import os
import sys
import argparse

DEFAULT_BRIDGE_URL = "http://127.0.0.1:10086/command"
DEFAULT_SESSION = "linkedin-live-session"

DEFAULT_TOPICS = [
    "cybersecurity",
    "ransomware",
    "threat intelligence",
    "zero day vulnerability",
    "malware analysis",
    "CISA advisory",
    "cloud security AWS",
    "EDR bypass",
    "SOC detection engineering",
    "AI security prompt injection",
    "Active Directory Kerberos",
    "DevSecOps CI CD",
    "Kubernetes security",
    "incident response",
    "FIDO2 passkeys"
]

class LinkedInCrawler:
    def __init__(self, bridge_url=DEFAULT_BRIDGE_URL, session=DEFAULT_SESSION, output_file="linkedin_posts.json"):
        self.bridge_url = bridge_url
        self.session = session
        self.output_file = output_file
        self.posts_by_id = {}
        self._load_existing()

    def _load_existing(self):
        """Loads previously saved posts to prevent duplicates."""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    for post in json.load(f):
                        pid = post.get("post_id")
                        if pid:
                            self.posts_by_id[pid] = post
                print(f"📦 Loaded {len(self.posts_by_id)} existing posts from {self.output_file}")
            except Exception as e:
                print(f"⚠️ Could not load existing JSON: {e}")

    def api_call(self, action, args=None):
        """Sends a command to the local browser bridge daemon."""
        payload = json.dumps({"action": action, "args": args or {}, "session": self.session}).encode('utf-8')
        req = urllib.request.Request(self.bridge_url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"❌ Bridge Communication Error ({action}): {e}")
            return {"ok": False, "error": str(e)}

    def cdp_eval(self, js_code):
        """Evaluates JavaScript inside the target browser tab."""
        res = self.api_call("evaluate", {"code": js_code})
        if res.get("ok"):
            return res.get("data", {}).get("value")
        return None

    def connect_tab(self):
        """Hooks into the user's active LinkedIn tab."""
        print("🔗 Connecting to active LinkedIn browser tab...")
        res = self.api_call("find_tab", {"url": "https://www.linkedin.com", "active": True})
        if res.get("ok"):
            print("✅ Successfully hooked into LinkedIn session!")
            return True
        else:
            print("⚠️ Active tab not found. Navigating to LinkedIn...")
            self.api_call("navigate", {"url": "https://www.linkedin.com", "newTab": False})
            time.sleep(2)
            return True

    def crawl_query(self, query, sort_by="date_posted", max_scrolls=5):
        """Crawls a specific search query with smooth virtual scrolling on <main>."""
        encoded_q = urllib.parse.quote(query)
        if sort_by == "date_posted":
            url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_q}&sortBy=%22date_posted%22"
        else:
            url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_q}"

        print(f"\n🔍 Navigating to: '{query}' (Sort: {sort_by})")
        self.api_call("navigate", {"url": url, "newTab": False})
        time.sleep(2.0)

        # In-page virtual DOM harvester
        harvest_script = """
        (async function() {
            let main = document.querySelector('main') || document.body;
            let results = [];
            
            for (let s = 0; s < 4; s++) {
                main.scrollTop = main.scrollHeight;
                window.scrollBy(0, 1000);
                await new Promise(r => setTimeout(r, 700));
            }

            let divs = Array.from(document.querySelectorAll('div, li, article')).filter(d => (d.innerText||'').startsWith('Feed post'));
            let leaves = divs.filter(fp => !divs.some(other => other !== fp && fp.contains(other)));

            leaves.forEach(leaf => {
                let text = (leaf.innerText || '').trim();
                if (text.length > 50) {
                    let lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    let author = lines.length > 1 ? lines[1] : 'Unknown';
                    let hash = 'post_' + Math.abs(text.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0));
                    
                    results.push({
                        post_id: hash,
                        author: author,
                        full_text: text.substring(0, 2000),
                        preview: text.substring(0, 200),
                        collected_at: new Date().toISOString()
                    });
                }
            });
            return results;
        })()
        """

        raw_posts = self.cdp_eval(harvest_script)
        new_count = 0
        if isinstance(raw_posts, list):
            for post in raw_posts:
                pid = post.get("post_id")
                if pid and pid not in self.posts_by_id:
                    self.posts_by_id[pid] = {
                        "post_id": pid,
                        "query": query,
                        "sort_by": sort_by,
                        "author": post.get("author"),
                        "preview": post.get("preview"),
                        "full_text": post.get("full_text"),
                        "collected_at": post.get("collected_at")
                    }
                    new_count += 1

        print(f"   📥 Extracted: {len(raw_posts) if isinstance(raw_posts, list) else 0} | New Added: +{new_count} | Total Stored: {len(self.posts_by_id)}")
        self.save()

    def save(self):
        """Saves current database to JSON file."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(list(self.posts_by_id.values()), f, indent=2)

    def run(self, topics=None, target_count=100):
        """Runs the crawler over a list of topics until target count is met."""
        self.connect_tab()
        topics = topics or DEFAULT_TOPICS

        print(f"\n🚀 Starting Crawler: Target = {target_count} Posts across {len(topics)} Topics")
        for i, topic in enumerate(topics, 1):
            if len(self.posts_by_id) >= target_count:
                break
            
            print(f"\n--- [Topic {i}/{len(topics)}]: {topic} ---")
            self.crawl_query(topic, sort_by="date_posted")
            
            if len(self.posts_by_id) >= target_count:
                break
            
            self.crawl_query(topic, sort_by="relevance")
            time.sleep(1.0)

        print(f"\n🎉 Finished! Total unique posts collected: {len(self.posts_by_id)}")
        print(f"📁 Data saved to: {os.path.abspath(self.output_file)}")

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Post Extractor & Crawler")
    parser.add_argument("--query", "-q", type=str, help="Specific search keyword or topic")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Target number of posts to collect")
    parser.add_argument("--output", "-o", type=str, default="scraped_posts.json", help="Output JSON file name")
    args = parser.parse_args()

    crawler = LinkedInCrawler(output_file=args.output)
    if args.query:
        crawler.run(topics=[args.query], target_count=args.limit)
    else:
        crawler.run(target_count=args.limit)

if __name__ == "__main__":
    main()
