"""
Download a BEIR dataset and embed its corpus into a dedicated ChromaDB collection.

Run this once per dataset. The embedding model (Nomic) is the only dependency —
LLM and reranker choices don't matter here.

Usage:
    uv run beir-ingest                    # defaults to scifact
    uv run beir-ingest --dataset nfcorpus
"""

import argparse
import json
import logging
import os
import urllib.request
import zipfile

import chromadb

from src.pipeline.embedder import embed_chunks
from src.pipeline.config import CHROMA_DB_PATH, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BEIR_BASE_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets"
BEIR_DIR = os.path.join(DATA_DIR, "beir")

SUPPORTED_DATASETS = {
    "scifact": {"docs": "~5K", "queries": "300 test"},
    "nfcorpus": {"docs": "~3.6K", "queries": "323 test"},
    "fiqa": {"docs": "~57K", "queries": "648 test"},
    "arguana": {"docs": "~8.7K", "queries": "1406 test"},
}


def download_dataset(name: str) -> str:
    dataset_dir = os.path.join(BEIR_DIR, name)
    if os.path.isdir(dataset_dir):
        log.info(f"Dataset '{name}' already downloaded at {dataset_dir}")
        return dataset_dir

    os.makedirs(BEIR_DIR, exist_ok=True)
    url = f"{BEIR_BASE_URL}/{name}.zip"
    zip_path = os.path.join(BEIR_DIR, f"{name}.zip")

    log.info(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, zip_path)

    log.info(f"Extracting to {BEIR_DIR} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(BEIR_DIR)
    os.remove(zip_path)

    log.info(f"Dataset ready at {dataset_dir}")
    return dataset_dir


def load_corpus(dataset_dir: str) -> dict[str, dict]:
    corpus = {}
    with open(os.path.join(dataset_dir, "corpus.jsonl")) as f:
        for line in f:
            entry = json.loads(line)
            corpus[entry["_id"]] = {
                "title": entry.get("title", ""),
                "text": entry.get("text", ""),
            }
    log.info(f"Loaded {len(corpus)} corpus documents")
    return corpus


def ingest_corpus(corpus: dict[str, dict], collection_name: str):
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=collection_name)

    existing = collection.count()
    if existing >= len(corpus):
        log.info(
            f"Collection '{collection_name}' already has {existing} docs "
            f"(corpus has {len(corpus)}), skipping ingest"
        )
        return

    if existing > 0:
        log.info(f"Collection has {existing} docs, will upsert remaining")

    doc_ids = list(corpus.keys())
    texts = [f"{corpus[d]['title']}\n{corpus[d]['text']}" for d in doc_ids]
    metadatas = [{"doc_id": d, "title": corpus[d]["title"]} for d in doc_ids]

    log.info(f"Embedding {len(texts)} documents ...")
    embeddings = embed_chunks(texts)

    BATCH = 5000
    for i in range(0, len(doc_ids), BATCH):
        end = min(i + BATCH, len(doc_ids))
        collection.upsert(
            ids=doc_ids[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings[i:end],
        )
        log.info(f"Upserted {end}/{len(doc_ids)} docs")

    log.info(f"Ingest complete: {collection.count()} docs in '{collection_name}'")


def main():
    parser = argparse.ArgumentParser(description="Download and ingest a BEIR dataset")
    parser.add_argument(
        "--dataset",
        default="scifact",
        choices=list(SUPPORTED_DATASETS.keys()),
        help="BEIR dataset to ingest",
    )
    args = parser.parse_args()

    dataset_dir = download_dataset(args.dataset)
    corpus = load_corpus(dataset_dir)
    ingest_corpus(corpus, f"beir_{args.dataset}")


if __name__ == "__main__":
    main()
