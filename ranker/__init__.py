"""
Redrob Hackathon — Candidate Ranking Engine

A rule-based, multi-component ranker for the Intelligent Candidate
Discovery & Ranking Challenge. Ranks a 100K candidate pool against
a specific job description using:

  - Skill taxonomy matching
  - Career trajectory scoring
  - Experience bell-curve scoring
  - Education tier/field scoring
  - Behavioral signal scoring (23 Redrob platform signals)
  - Honeypot detection
  - Fact-grounded per-candidate reasoning

Compute constraints: CPU-only, ≤5 min, ≤16 GB RAM, no network.
"""
