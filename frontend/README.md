# ELYSIUM – AI-Driven Drug Discovery Toolkit

ELYSIUM is a modular, agentic toolkit for early-stage drug discovery.  
It generates candidate molecules for a target, scores them with AI models,
annotates them with ADMET properties, and links them to a small knowledge
graph of known drugs for repurposing / similarity analysis.

The goal is not to be a full production pipeline, but a **starter framework**
that shows how DeepPurpose, RDKit, chemBERTa and a graph store can work together
end-to-end.

---

## Architecture

Text diagram of the system:

- **FastAPI backend**
  - `/discover` – orchestrates the discovery pipeline
  - `/runs` + `/runs/{id}` – access historical runs
  - `/graph/target/{id}` – knowledge-graph view by target
  - `/graph/drug/{name}` – knowledge-graph view by known drug

- **Core pipeline**
  - **Generator** – library / model that proposes candidate SMILES
  - **DeepPurpose** – drug–target interaction scoring (binding affinity proxy)
  - **RDKit**
    - ADMET-like descriptors (MW, logP, HBD/HBA, TPSA, rotatable bonds)
    - Lipinski rule-of-five pass / fail
    - Morgan fingerprints for similarity (Tanimoto)
  - **chemBERTa**
    - SMILES embeddings
    - semantic similarity between molecules (cosine distance)

- **Knowledge graph (SQLite)**
  - `kq_nodes` – targets, known drugs, generated molecules
  - `kq_edges` – `BINDS` and `SIMILAR_TO` relationships
  - Exposed via `/graph/*` endpoints

- **Frontend (React + Vite + Tailwind)**
  - Discovery dashboard – run `/discover` and inspect candidates
  - Runs view – browse history via `/runs`, view details via `/runs/{id}`
  - Graph explorer – simple UI over `/graph/target/{id}` and `/graph/drug/{name}`
