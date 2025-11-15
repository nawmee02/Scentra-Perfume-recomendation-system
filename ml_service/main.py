from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import faiss, numpy as np
from sentence_transformers import SentenceTransformer
import os

# Paths
DATA_CSV   = "data/fra_cleaned.csv"
INDEX_FILE = "data/faiss.index"
EMB_FILE   = "data/embeddings.npy"

# 1) Read CSV with semicolon delimiter
df = pd.read_csv(
    DATA_CSV,
    sep=';',                # use semicolon
    engine='python',
    on_bad_lines='skip',
    encoding='ISO-8859-1'
)

# Debug: confirm columns
print("Loaded columns:", df.columns.tolist())

# Map columns
name_col  = 'Perfume'
brand_col = 'Brand'
# Combine top/middle/base into single 'notes' field
note_cols = ['Top', 'Middlee', 'Base']

# Convert DataFrame to list of dicts
perfumes = df.to_dict(orient="records")

# Pre-build text list for embedding
texts = []
for p in perfumes:
    notes = ' '.join(str(p.get(c, '')) for c in note_cols)
    desc  = str(p.get('Perfumer1', '')) + ' ' + str(p.get('Perfumer2', ''))
    texts.append(f"{p.get(name_col, '')} {p.get(brand_col, '')} {notes} {desc}")

# 2) Load or build FAISS index with MiniLM
model = SentenceTransformer("all-MiniLM-L6-v2")
if os.path.exists(EMB_FILE) and os.path.exists(INDEX_FILE):
    emb = np.load(EMB_FILE)
    index = faiss.read_index(INDEX_FILE)
    print("Loaded existing index")
else:
    emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    # normalize embeddings
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    np.save(EMB_FILE, emb)
    faiss.write_index(index, INDEX_FILE)
    print("Built new FAISS index")

app = FastAPI()

class Query(BaseModel):
    query: str
    k: int = 5

@app.post("/recommend")
def recommend(req: Query):
    if not req.query:
        raise HTTPException(400, "query is required")

    # Embed and normalize the query
    q_emb = model.encode([req.query], convert_to_numpy=True)
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
    D, I = index.search(q_emb, req.k)

    recs = []
    for score, idx in zip(D[0], I[0]):
        p = perfumes[idx]

        # Safely build notes string
        notes_list = []
        for col in ['Top', 'Middle', 'Base']:
            val = p.get(col, "")
            if val is not None:
                notes_list.append(str(val))
        notes = " ".join(notes_list)

        # Safely build description from Perfumer1/2
        perf1 = str(p.get('Perfumer1', "") or "")
        perf2 = str(p.get('Perfumer2', "") or "")
        desc = f"{perf1} {perf2}".strip()

        recs.append({
            "name":        str(p.get('Perfume', "") or ""),
            "brand":       str(p.get('Brand', "") or ""),
            
        })

    return {"recommendations": recs}