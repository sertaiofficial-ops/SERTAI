import os
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.parsers import extract_text_from_file

def analyze_directory(dir_path):
    """
    Scans a directory, extracts text from all supported files,
    and returns a DataFrame containing the raw data and basic metadata.
    """
    data = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            text = extract_text_from_file(file_path)

            # Skip empty files or unsupported formats
            if not text:
                continue

            data.append({
                "filename": file,
                "filepath": file_path,
                "text": text,
                "size_bytes": os.path.getsize(file_path)
            })

    return pd.DataFrame(data)

def extract_entities_and_keywords(df):
    """
    Heuristically extracts potential projects, categories, and document types based on text and filename.
    (In a fully productionized system, an LLM call or NER model would be used here. We use regex/keyword matching for speed and determinism locally.)
    """
    # Keywords dictionaries
    project_keywords = ["luleburgaz", "izmir", "kampus", "santiye"]
    doc_types = {
        "hakedis": "Hakedis", "kesin hesap": "Kesin Hesap", "test": "Test Raporu",
        "rapor": "Rapor", "sozlesme": "Sozlesme", "personel": "IK / Personel",
        "onay": "Onay Belgesi", "belediye": "Resmi Evrak / Belediye", "ruhsat": "Resmi Evrak / Belediye",
        "profil": "Kurumsal", "vizyon": "Kurumsal"
    }

    assigned_projects = []
    assigned_types = []
    assigned_categories = []

    for idx, row in df.iterrows():
        combined_content = (row['filename'] + " " + row['text']).lower()

        # 1. Project Assignment
        proj = "Unresolved"
        for pk in project_keywords:
            if pk in combined_content:
                proj = pk.capitalize()
                if proj == "Kampus": proj = "Izmir Kampus" # Normalization
                break
        assigned_projects.append(proj)

        # 2. Document Type Assignment
        dt = "Diger"
        for k, v in doc_types.items():
            if k in combined_content:
                dt = v
                break
        assigned_types.append(dt)

        # 3. Category Generation
        if proj == "Unresolved":
            if dt in ["Kurumsal", "IK / Personel"]:
                assigned_categories.append(f"00_MERKEZ_OFIS/{dt}")
            else:
                assigned_categories.append("99_AYIKLANACAKLAR")
        else:
            cat = f"01_PROJELER/{proj}/{dt}"
            assigned_categories.append(cat)

    df['project'] = assigned_projects
    df['doc_type'] = assigned_types
    df['proposed_category'] = assigned_categories
    return df

def detect_relationships(df, similarity_threshold=0.3):
    """
    Uses TF-IDF and Cosine Similarity to find related documents.
    Returns a list of edge dictionaries for graph building.
    """
    if len(df) < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words=None) # We could use Turkish stop words here if available
    tfidf_matrix = vectorizer.fit_transform(df['text'])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    relationships = []
    for i in range(len(df)):
        for j in range(i+1, len(df)):
            sim_score = cosine_sim[i][j]
            if sim_score >= similarity_threshold:
                rel_type = "Related Content"

                # Check for duplicates/versions
                if sim_score > 0.95:
                    rel_type = "Exact Duplicate"
                elif sim_score > 0.8:
                    rel_type = "Version / Near Duplicate"

                relationships.append({
                    "source": df.iloc[i]['filename'],
                    "target": df.iloc[j]['filename'],
                    "similarity": sim_score,
                    "type": rel_type
                })

    return relationships

def run_analysis_pipeline(dir_path):
    """
    Runs the full analysis pipeline and returns the annotated DataFrame and relationships.
    """
    df = analyze_directory(dir_path)
    if df.empty:
        return df, []

    df = extract_entities_and_keywords(df)
    relationships = detect_relationships(df)

    return df, relationships
