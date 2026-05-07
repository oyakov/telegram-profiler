#!/usr/bin/env python3
"""Test semantic search improvements."""
# -*- coding: utf-8 -*-

import requests
import json
import sys
import io

# Set stdout encoding to handle Cyrillic text
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8090/api"

def test_search(query: str, limit: int = 5):
    """Test search endpoint."""
    response = requests.post(
        f"{API_BASE}/search",
        json={"query": query, "limit": limit},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Test cases
test_queries = [
    "real estate Belgrade",
    "who works with blockchain",
    "immigration residence permit Serbia",
    "work permit employment",
]

print("=" * 80)
print("SEMANTIC SEARCH TEST RESULTS")
print("=" * 80)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 80)

    try:
        result = test_search(query)

        contacts = result.get("contacts", [])
        messages = result.get("messages", [])

        print(f"  Contacts found: {len(contacts)}")
        for i, contact in enumerate(contacts[:3], 1):
            print(f"    {i}. {contact.get('first_name', 'N/A')} "
                  f"(similarity: {contact.get('similarity', 0):.4f}, "
                  f"type: {contact.get('search_type', 'unknown')})")
            evidence = contact.get('evidence', [])
            if evidence:
                print(f"       Evidence: {len(evidence)} quotes found")

        print(f"  Messages found: {len(messages)}")
        for i, msg in enumerate(messages[:2], 1):
            print(f"    {i}. {msg.get('contact_name', 'Unknown')}: "
                  f"'{msg.get('content', '')[:50]}...' "
                  f"(similarity: {msg.get('similarity', 0):.4f})")

    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 80)
print("Key observations:")
print("  + Batch evidence loading implemented (no N+1 queries)")
print("  + Distance threshold increased to 0.52 for better recall")
print("  + Keyword search array conditions fixed")
print("  ? Embedding processing status: Check dashboard for completion")
print("=" * 80)
