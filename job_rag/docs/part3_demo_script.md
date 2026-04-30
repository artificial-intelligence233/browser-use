# Part 3 Demo Script

## 30-60 Second Narration

This module is responsible for turning candidate job pages into explainable job
recommendations. First, it reads candidate URLs or local demo HTML files and
extracts visible page text. Then it converts the text into structured
`JobPosting` JSON, including title, company, location, salary, responsibilities,
requirements, and skills.

After extraction, the module normalizes city, salary, and skills, removes
duplicates, and writes the jobs into a local vector index. A structured resume
profile is converted into a retrieval query, which recalls top-k jobs from the
index. Finally, the scorer combines retrieval similarity, skill overlap, target
role alignment, and city preference to produce a match score, matched skills,
missing skills, match reasons, mismatch reasons, and resume edit focus.

The current demo can be run with:

```bash
python job_rag/examples/run_demo.py
```

Even if some pages fail to crawl, the pipeline keeps the failure records and
continues producing recommendations from successful pages.

