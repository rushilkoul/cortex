"""
for caliberation of retrieval threshold
Threshold calibration script.

Run a batch of queries you've labeled as "relevant" or "irrelevant" against
your indexed vault, and log the raw distance scores to a CSV so you can sort
and compare them.

USAGE:
    1. Edit the QUERIES list below with your own test queries.
    2. Run: python3 calibrate_threshold.py
    3. Open scores.csv in Excel/Sheets/LibreOffice, sort by the "score" column.
"""
import csv
from cortex.retrieval.search import search_text, search_image

# label: "relevant"   -> you expect this query to match something in your vault
# label: "irrelevant" -> you expect this query to match NOTHING in your vault
QUERIES = [

    # RELEVANT

    ("what is chmod used for", "relevant"),
    ("how does git help developers collaborate", "relevant"),
    ("what is sql injection", "relevant"),
    ("what is machine learning", "relevant"),
    ("what is the purpose of the united nations", "relevant"),
    ("what does article 5 of nato state", "relevant"),
    ("why is the indo-pacific strategically important", "relevant"),
    ("why is the arctic becoming geopolitically important", "relevant"),
    ("what are rare earth minerals used for", "relevant"),
    ("what is global governance", "relevant"),
    ("what do worker bees do", "relevant"),
    ("what equipment is needed for cave exploration", "relevant"),
    ("how does an automatic watch work", "relevant"),
    ("what are urban forests", "relevant"),
    ("what technologies are used in modern navigation", "relevant"),


    # PARTIALLY RELEVANT

    ("where are linux system settings usually stored", "partial"),
    ("how can multiple programmers work on the same project safely", "partial"),
    ("why might an ai model produce unfair predictions", "partial"),
    ("what happens if a website trusts user input too much", "partial"),
    ("which international organization sends peacekeeping forces", "partial"),
    ("if one member of a military alliance is attacked what happens", "partial"),
    ("why do governments care about shipping routes in asia", "partial"),
    ("how is melting ice changing international politics", "partial"),
    ("why are lithium and cobalt strategically important", "partial"),
    ("why do countries form international institutions", "partial"),
    ("why are bees important besides making honey", "partial"),
    ("what dangers do explorers face underground", "partial"),
    ("why do some wristwatches never need batteries", "partial"),
    ("how can cities naturally reduce heat during summers", "partial"),
    ("how did sailors travel long distances before gps", "partial"),


    # IRRELEVANT

    ("who is the prime minister of india", "irrelevant"),
    ("best butter chicken recipe", "irrelevant"),
    ("weather forecast for tomorrow", "irrelevant"),
    ("history of the roman empire", "irrelevant"),
    ("how to fix a flat tire", "irrelevant"),
    ("what is quantum entanglement", "irrelevant"),
    ("how does bitcoin mining work", "irrelevant"),
    ("best chest workout for muscle growth", "irrelevant"),
    ("capital city of brazil", "irrelevant"),
    ("explain photosynthesis", "irrelevant"),

]

# k=40 and threshold=999 so NOTHING gets filtered out -- we want raw scores
K = 40
THRESHOLD = 999


def run():
    rows = []

    for query, label in QUERIES:
        text_results = search_text(query, k=K, threshold=THRESHOLD)
        image_results = search_image(query, k=K, threshold=THRESHOLD)

        if not text_results and not image_results:
            # no chunks in the DB at all matched -- still log it as a row
            # so you notice the gap, rather than it silently vanishing
            rows.append({
                "query": query,
                "label": label,
                "type": "none",
                "file_path": "",
                "score": "",
                "snippet": "",
            })
            continue

        for r in text_results:
            rows.append({
                "query": query,
                "label": label,
                "type": "text",
                "file_path": r["file_path"],
                "score": round(r["score"], 4),
                "snippet": r["content"][:80].replace("\n", " "),
            })

        for r in image_results:
            rows.append({
                "query": query,
                "label": label,
                "type": "image",
                "file_path": r["file_path"],
                "score": round(r["score"], 4),
                "snippet": "",
            })

    with open("scores.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "label", "type", "file_path", "score", "snippet"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to scores.csv")
    print("Open it, sort by the 'score' column, and compare where 'relevant' rows")
    print("stop and 'irrelevant' rows start -- your threshold goes in that gap.")


if __name__ == "__main__":
    run()