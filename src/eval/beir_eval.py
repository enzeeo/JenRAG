"""
Run retrieval against a previously ingested BEIR collection and compute
standard IR metrics: NDCG@K, Recall@K, Precision@K, MRR@K, Hit Rate@K.

Ingest the dataset first with:  uv run beir-ingest --dataset scifact

Usage:
    uv run beir-eval                                  # scifact, embedding only
    uv run beir-eval --use-reranker --rerank-top-k 5  # with BGE reranker
    uv run beir-eval --dataset nfcorpus --top-k 20
"""

import argparse
import json
import logging
import math
import os
import time
from collections import defaultdict

import chromadb
from tqdm import tqdm

from src.pipeline.embedder import embed_queries
from src.pipeline.retriever import rerank
from src.pipeline.config import CHROMA_DB_PATH, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BEIR_DIR = os.path.join(DATA_DIR, "beir")
K_VALUES = [1, 3, 5, 10]


# ---------------------------------------------------------------------------
# Data loading (queries + ground truth only — corpus lives in ChromaDB)
# ---------------------------------------------------------------------------

def load_queries(dataset_dir: str) -> dict[str, str]:
    queries = {}
    with open(os.path.join(dataset_dir, "queries.jsonl")) as f:
        for line in f:
            entry = json.loads(line)
            queries[entry["_id"]] = entry["text"]
    log.info(f"Loaded {len(queries)} queries")
    return queries


def load_qrels(dataset_dir: str, split: str = "test") -> dict[str, dict[str, int]]:
    qrels_path = os.path.join(dataset_dir, "qrels", f"{split}.tsv")
    qrels: dict[str, dict[str, int]] = defaultdict(dict)

    with open(qrels_path) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split("\t")
            qid, did, score = parts[0], parts[1], int(parts[2])
            if score > 0:
                qrels[qid][did] = score

    log.info(f"Loaded qrels for {len(qrels)} queries ({split} split)")
    return dict(qrels)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

CHROMA_QUERY_BATCH = 64


def retrieve_for_queries(
    queries: dict[str, str],
    qrels: dict[str, dict[str, int]],
    collection_name: str,
    top_k: int,
    use_reranker: bool,
    rerank_top_k: int,
    retrieve_k: int = 50,
) -> dict[str, list[str]]:
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(name=collection_name)
    log.info(f"Collection '{collection_name}' has {collection.count()} docs")

    eval_qids = [qid for qid in queries if qid in qrels]
    eval_texts = [queries[qid] for qid in eval_qids]
    log.info(f"Evaluating {len(eval_qids)} queries with qrels")

    if not use_reranker:
        retrieve_k = top_k

    # --- Phase 1: batch-embed all queries at once ---
    log.info("Phase 1/3: embedding all queries …")
    all_embeddings = embed_queries(eval_texts)

    # --- Phase 2: batch ChromaDB lookups ---
    log.info("Phase 2/3: querying ChromaDB …")
    all_ids: list[list[str]] = []
    all_docs: list[list[str]] = []
    all_metas: list[list[dict]] = []

    for i in tqdm(range(0, len(all_embeddings), CHROMA_QUERY_BATCH),
                  desc="ChromaDB", unit="batch"):
        batch_embs = all_embeddings[i : i + CHROMA_QUERY_BATCH]
        res = collection.query(query_embeddings=batch_embs, n_results=retrieve_k)
        all_ids.extend(res["ids"])
        all_docs.extend(res["documents"])
        all_metas.extend(res["metadatas"])

    # --- Phase 3: optional reranking (the bottleneck) ---
    results: dict[str, list[str]] = {}

    if use_reranker:
        log.info("Phase 3/3: reranking …")
        for i, qid in enumerate(tqdm(eval_qids, desc="Reranking", unit="query")):
            _, reranked_metas = rerank(eval_texts[i], all_docs[i], all_metas[i], rerank_top_k)
            results[qid] = [m["doc_id"] for m in reranked_metas]
    else:
        log.info("Phase 3/3: collecting results (no reranker) …")
        for i, qid in enumerate(eval_qids):
            results[qid] = all_ids[i][:top_k]

    return results


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _dcg(relevances: list[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(retrieved: list[str], qrel: dict[str, int], k: int) -> float:
    rels = [qrel.get(doc_id, 0) for doc_id in retrieved[:k]]
    dcg = _dcg(rels, k)
    ideal = sorted(qrel.values(), reverse=True)[:k]
    idcg = _dcg(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(retrieved: list[str], qrel: dict[str, int], k: int) -> float:
    relevant = set(qrel.keys())
    if not relevant:
        return 0.0
    return sum(1 for d in retrieved[:k] if d in relevant) / len(relevant)


def precision_at_k(retrieved: list[str], qrel: dict[str, int], k: int) -> float:
    if k == 0:
        return 0.0
    relevant = set(qrel.keys())
    return sum(1 for d in retrieved[:k] if d in relevant) / k


def mrr_at_k(retrieved: list[str], qrel: dict[str, int], k: int) -> float:
    relevant = set(qrel.keys())
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def hit_rate_at_k(retrieved: list[str], qrel: dict[str, int], k: int) -> float:
    relevant = set(qrel.keys())
    return 1.0 if any(d in relevant for d in retrieved[:k]) else 0.0


METRIC_FNS = {
    "NDCG": ndcg_at_k,
    "Recall": recall_at_k,
    "Precision": precision_at_k,
    "MRR": mrr_at_k,
    "Hit Rate": hit_rate_at_k,
}


# ---------------------------------------------------------------------------
# Evaluation & reporting
# ---------------------------------------------------------------------------

def compute_metrics(
    results: dict[str, list[str]],
    qrels: dict[str, dict[str, int]],
) -> dict[str, dict[int, float]]:
    scores: dict[str, dict[int, list[float]]] = {
        name: {k: [] for k in K_VALUES} for name in METRIC_FNS
    }

    for qid, retrieved in results.items():
        qrel = qrels.get(qid, {})
        for name, fn in METRIC_FNS.items():
            for k in K_VALUES:
                scores[name][k].append(fn(retrieved, qrel, k))

    return {
        name: {k: sum(vals) / len(vals) if vals else 0.0 for k, vals in k_scores.items()}
        for name, k_scores in scores.items()
    }


def print_results(metrics: dict, dataset: str, n_queries: int, use_reranker: bool,
                   elapsed: float | None = None):
    print(f"\n{'=' * 70}")
    print(f"BEIR EVALUATION — {dataset.upper()}")
    print(f"{'=' * 70}")
    print(f"  Queries evaluated: {n_queries}")
    print(f"  Reranker:          {'BGE v2 M3' if use_reranker else 'None'}")
    if elapsed is not None:
        print(f"  Wall time:         {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print()

    header = f"  {'Metric':<14}" + "".join(f"{'@' + str(k):>10}" for k in K_VALUES)
    print(header)
    print(f"  {'-' * 14}" + "".join(f"  {'-' * 8}" for _ in K_VALUES))

    for name in METRIC_FNS:
        row = f"  {name:<14}"
        for k in K_VALUES:
            row += f"{metrics[name][k]:>10.4f}"
        print(row)

    print(f"{'=' * 70}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BEIR retrieval evaluation")
    parser.add_argument(
        "--dataset",
        default="scifact",
        choices=["scifact", "nfcorpus", "fiqa", "arguana"],
        help="BEIR dataset (must be ingested first)",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Final retrieval depth")
    parser.add_argument("--use-reranker", action="store_true", help="Enable BGE reranker")
    parser.add_argument("--rerank-top-k", type=int, default=7, help="Chunks kept after reranking")
    parser.add_argument(
        "--retrieve-k", type=int, default=50,
        help="Candidates fetched from ChromaDB for reranking (lower = faster, default 50)",
    )
    args = parser.parse_args()

    dataset_dir = os.path.join(BEIR_DIR, args.dataset)
    if not os.path.isdir(dataset_dir):
        print(f"Dataset not found at {dataset_dir}. Run: uv run beir-ingest --dataset {args.dataset}")
        return

    collection_name = f"beir_{args.dataset}"
    queries = load_queries(dataset_dir)
    qrels = load_qrels(dataset_dir)

    t0 = time.time()
    results = retrieve_for_queries(
        queries, qrels, collection_name,
        top_k=args.top_k,
        use_reranker=args.use_reranker,
        rerank_top_k=args.rerank_top_k,
        retrieve_k=args.retrieve_k,
    )
    elapsed = time.time() - t0

    metrics = compute_metrics(results, qrels)
    print_results(metrics, args.dataset, len(results), args.use_reranker, elapsed)

    out_path = os.path.join(BEIR_DIR, f"{args.dataset}_results.json")
    with open(out_path, "w") as f:
        json.dump({"dataset": args.dataset, "metrics": metrics, "config": vars(args)}, f, indent=2)
    log.info(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
