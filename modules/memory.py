"""ChromaDB persistent memory for news, scores, and filings."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
import chromadb


class Memory:
    def __init__(self, db_path: str = "data/chromadb"):
        self.client  = chromadb.PersistentClient(path=db_path)
        self.news    = self.client.get_or_create_collection("news")
        self.scores  = self.client.get_or_create_collection("scores")
        self.filings = self.client.get_or_create_collection("filings")

    def add_news(self, ticker: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        ids, docs, metas = [], [], []
        for item in items:
            uid = hashlib.md5(item.get("url", item["title"]).encode()).hexdigest()
            ids.append(uid)
            docs.append(f"{item['title']} {item.get('snippet', '')}")
            metas.append({
                "ticker":       ticker,
                "date":         item.get("date", ""),
                "title":        item.get("title", ""),
                "snippet":      item.get("snippet", "")[:500],
                "source":       item.get("source", ""),
                "url":          item.get("url", ""),
                "category":     item.get("category", "other"),
                "significance": int(item.get("significance", 5)),
            })
        self.news.upsert(ids=ids, documents=docs, metadatas=metas)

    def search(self, query: str, ticker: str | None = None, k: int = 10) -> list[dict[str, Any]]:
        where  = {"ticker": ticker} if ticker else None
        kwargs: dict = {"query_texts": [query], "n_results": k}
        if where:
            kwargs["where"] = where
        try:
            res = self.news.query(**kwargs)
        except Exception:
            return []
        return [{**meta, "distance": dist}
                for meta, dist in zip(res["metadatas"][0], res["distances"][0])]

    def add_score(self, ticker: str, date: str, scored: dict[str, Any]) -> None:
        uid = f"{ticker}_{date}"
        doc = (f"{ticker} score {scored.get('total_score', 0):.0f} on {date}. "
               f"{scored.get('reasoning', '')} {scored.get('narrative', '')}")
        self.scores.upsert(
            ids=[uid], documents=[doc],
            metadatas=[{
                "ticker":      ticker,
                "date":        date,
                "total_score": float(scored.get("total_score", 0)),
                "reasoning":   str(scored.get("reasoning", ""))[:500],
                "narrative":   str(scored.get("narrative", ""))[:500],
            }]
        )

    def get_score_history(self, ticker: str, days: int = 90) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            # Filter by ticker only, then filter dates in Python
            # (ChromaDB string $gte comparator unreliable across versions)
            res = self.scores.get(where={"ticker": ticker})
        except Exception:
            return []
        rows = [m for m in res["metadatas"] if m.get("date", "") >= cutoff]
        rows.sort(key=lambda x: x.get("date", ""), reverse=True)
        return rows

    def add_filing(self, ticker: str, date: str, form_type: str, content: str) -> None:
        uid = hashlib.md5(f"{ticker}_{date}_{form_type}".encode()).hexdigest()
        self.filings.upsert(
            ids=[uid], documents=[content[:2000]],
            metadatas=[{"ticker": ticker, "date": date, "form_type": form_type}],
        )
