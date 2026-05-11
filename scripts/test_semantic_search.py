#!/usr/bin/env python3
"""
Comprehensive semantic search testing.
Tests search functionality with various queries and metrics.
"""

import asyncio
import sys
from datetime import datetime, timezone
import json
import structlog
from typing import List, Dict, Any

logger = structlog.get_logger()


async def run_search_tests(db_name: str = "crm"):
    """Run comprehensive semantic search tests."""
    from src.api.schemas import SearchRequest
    from src.db.database import get_session
    from src.db.models import MessageEmbedding, Message
    from sqlalchemy import func, select
    from src.ai.analysis import generate_embedding
    from collections import defaultdict
    import sqlalchemy as sa

    print("=" * 70)
    print("SEMANTIC SEARCH TESTING")
    print("=" * 70)

    # Check coverage first
    async with get_session(db_name=db_name) as session:
        msgs = await session.execute(select(func.count(Message.id)))
        embs = await session.execute(
            select(func.count(MessageEmbedding.message_id.distinct()))
        )
        total_msgs = msgs.scalar() or 0
        total_embs = embs.scalar() or 0
        coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0

    print(f"\nDatabase Coverage: {total_embs:,} / {total_msgs:,} ({coverage:.2f}%)")
    print(
        f"Note: Search coverage depends on embeddings. More embeddings = better results.\n"
    )

    # Define inline search function
    async def perform_search(session, query_text: str, limit: int = 10):
        """Perform semantic + keyword search."""
        from src.db.models import Contact
        from src.api.routers.contacts import _contact_to_response

        query_embedding = await generate_embedding(query_text)

        # 1. Semantic search
        msg_results = await session.execute(
            select(
                MessageEmbedding,
                Message,
                MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(Message, Message.id == MessageEmbedding.message_id)
            .options(sa.orm.joinedload(Message.contact))
            .order_by("distance")
            .limit(limit * 5)
        )

        semantic_contacts = defaultdict(list)
        for me, msg, distance in msg_results:
            if msg.contact and distance < 0.52:
                if not (msg.contact.id in semantic_contacts and len(semantic_contacts[msg.contact.id]) >= 5):
                    semantic_contacts[msg.contact.id].append((msg.contact, me, distance))

        # 2. Keyword search
        from src.api.routers.search import _keyword_search
        keyword_contacts = {}
        if len(semantic_contacts) < limit:
            kw_results = await _keyword_search(session, query_text, limit * 2)
            for contact, msg_count in kw_results:
                if contact.id not in semantic_contacts:
                    keyword_contacts[contact.id] = (contact, None, 0.5)

        # 3. Combine results
        all_contacts = {}
        for contact_id, msg_list in semantic_contacts.items():
            contact, best_me, best_distance = msg_list[0]
            all_contacts[contact_id] = (contact, best_distance, "semantic")

        for contact_id, (contact, _, _) in keyword_contacts.items():
            if contact_id not in all_contacts:
                all_contacts[contact_id] = (contact, 0.5, "keyword")

        # Get final contacts list
        contact_list = list(all_contacts.values())[:limit]
        contacts = []
        for contact, distance, search_type in contact_list:
            try:
                contacts.append({
                    **_contact_to_response(contact),
                    "similarity": round(1 - distance, 4) if search_type == "semantic" else 0.5,
                    "evidence": [],
                    "search_type": search_type,
                })
            except:
                pass

        return {"query": query_text, "contacts": contacts, "messages": []}

    # Test queries covering different domains
    test_queries = [
        # Business/Professional
        {
            "query": "machine learning AI technology",
            "category": "Technology",
            "description": "Tech industry discussion",
        },
        {
            "query": "investment startup funding",
            "category": "Business",
            "description": "Investment and business opportunities",
        },
        {
            "query": "product management development",
            "category": "Work",
            "description": "Product development discussion",
        },
        # General networking
        {
            "query": "networking community collaboration",
            "category": "Networking",
            "description": "Collaboration and networking",
        },
        {
            "query": "marketing sales business growth",
            "category": "Sales",
            "description": "Sales and marketing topics",
        },
        # Specific technical topics
        {
            "query": "Python JavaScript programming",
            "category": "Development",
            "description": "Programming languages",
        },
        {
            "query": "data analysis analytics insights",
            "category": "Data",
            "description": "Data science and analytics",
        },
        # General conversation
        {
            "query": "hello meeting discussion chat",
            "category": "General",
            "description": "General conversation",
        },
    ]

    results_summary = {
        "total_queries": 0,
        "avg_contacts_found": 0,
        "avg_messages_found": 0,
        "queries_with_results": 0,
        "semantic_vs_keyword": {"semantic": 0, "keyword": 0, "mixed": 0},
        "results": [],
    }

    print("Running search tests...\n")
    print(f"{'Query':<30} {'Category':<12} {'Contacts':<10} {'Messages':<10} {'Type':<15}")
    print("-" * 77)

    async with get_session(db_name=db_name) as session:
        for test in test_queries:
            try:
                result = await perform_search(session, test["query"], limit=10)

                contacts_found = len(result.get("contacts", []))
                messages_found = len(result.get("messages", []))

                # Determine search type
                search_types = set()
                for contact in result.get("contacts", []):
                    search_types.add(contact.get("search_type", "unknown"))
                for msg in result.get("messages", []):
                    search_types.add(msg.get("search_type", "unknown"))

                if len(search_types) > 1:
                    search_type = "mixed"
                    results_summary["semantic_vs_keyword"]["mixed"] += 1
                elif "semantic" in search_types:
                    search_type = "semantic"
                    results_summary["semantic_vs_keyword"]["semantic"] += 1
                else:
                    search_type = "keyword"
                    results_summary["semantic_vs_keyword"]["keyword"] += 1

                results_summary["total_queries"] += 1
                results_summary["avg_contacts_found"] += contacts_found
                results_summary["avg_messages_found"] += messages_found

                if contacts_found > 0 or messages_found > 0:
                    results_summary["queries_with_results"] += 1

                # Store detailed result
                results_summary["results"].append(
                    {
                        "query": test["query"],
                        "category": test["category"],
                        "contacts": contacts_found,
                        "messages": messages_found,
                        "type": search_type,
                        "top_contact": (
                            {
                                "name": f"{result['contacts'][0]['first_name']} {result['contacts'][0]['last_name']}",
                                "similarity": result["contacts"][0]["similarity"],
                            }
                            if contacts_found > 0
                            else None
                        ),
                    }
                )

                print(
                    f"{test['query']:<30} {test['category']:<12} {contacts_found:<10} {messages_found:<10} {search_type:<15}"
                )

            except Exception as e:
                print(f"{test['query']:<30} {'ERROR':<12} - {str(e)[:20]}")
                logger.error("search_test_failed", query=test["query"], error=str(e))

    # Print summary
    print("\n" + "=" * 70)
    print("SEARCH TESTING SUMMARY")
    print("=" * 70)

    if results_summary["total_queries"] > 0:
        avg_contacts = (
            results_summary["avg_contacts_found"] / results_summary["total_queries"]
        )
        avg_messages = (
            results_summary["avg_messages_found"] / results_summary["total_queries"]
        )
    else:
        avg_contacts = 0
        avg_messages = 0

    print(f"Queries tested: {results_summary['total_queries']}")
    print(f"Queries with results: {results_summary['queries_with_results']}")
    print(f"Success rate: {(results_summary['queries_with_results'] / results_summary['total_queries'] * 100) if results_summary['total_queries'] > 0 else 0:.1f}%")
    print(f"Avg contacts per query: {avg_contacts:.2f}")
    print(f"Avg messages per query: {avg_messages:.2f}")
    print()
    print("Search type distribution:")
    print(f"  Semantic: {results_summary['semantic_vs_keyword']['semantic']}")
    print(f"  Keyword fallback: {results_summary['semantic_vs_keyword']['keyword']}")
    print(f"  Mixed: {results_summary['semantic_vs_keyword']['mixed']}")

    print("\n" + "=" * 70)
    print("DETAILED RESULTS")
    print("=" * 70)

    for result in results_summary["results"]:
        print(f"\nQuery: \"{result['query']}\"")
        print(f"  Category: {result['category']}")
        print(f"  Type: {result['type']}")
        print(f"  Contacts: {result['contacts']}")
        if result["top_contact"]:
            print(
                f"    Top: {result['top_contact']['name']} (similarity: {result['top_contact']['similarity']:.4f})"
            )
        print(f"  Messages: {result['messages']}")

    print("\n" + "=" * 70)

    # Save results to file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results_file = f"search_test_results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results_summary, f, indent=2, default=str)
    print(f"Results saved to: {results_file}")

    return 0


async def main():
    """Main entry point."""
    try:
        return await run_search_tests(db_name="crm")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
