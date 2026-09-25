import os
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import unicodedata
from src.parsers import extract_text_from_file

def normalize_text(text):
    """Normalize Turkish characters and lower case text for better matching."""
    text = text.lower()
    text = text.replace("ü", "u").replace("ö", "o").replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ç", "c")
    return text

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

            # Use filename as fallback if text extraction fails or is empty
            if not text:
                text = file

            data.append({
                "filename": file,
                "filepath": file_path,
                "text": text,
                "size_bytes": os.path.getsize(file_path)
            })

    return pd.DataFrame(data)

def extract_entities_and_keywords(df):
    """
    Enhanced heuristic extraction using extensive construction terminology.
    """
    # Comprehensive project and keyword dictionaries
    project_keywords = {
        "luleburgaz": "Luleburgaz", "lüleburgaz": "Luleburgaz",
        "izmir": "Izmir_Kampus", "kampus": "Izmir_Kampus", "kampüs": "Izmir_Kampus",
        "merkez": "Merkez_Ofis", "santiye": "Genel_Santiye", "şantiye": "Genel_Santiye"
    }

    doc_types = {
        # Finance
        "hakedis": "03_HAKEDISLER", "hakediş": "03_HAKEDISLER",
        "kesin hesap": "02_MALI_ISLER", "fatura": "02_MALI_ISLER",
        "gider": "02_MALI_ISLER", "maliyet": "02_MALI_ISLER", "odeme": "02_MALI_ISLER",

        # Engineering / Technical
        "beton": "04_BETON_TESTLERI", "test": "04_BETON_TESTLERI",
        "zemin": "06_MUHENDISLIK_ETUD", "etud": "06_MUHENDISLIK_ETUD",
        "mimari": "06_MUHENDISLIK_ETUD", "proje": "06_MUHENDISLIK_ETUD",
        "vinc": "07_OPERASYON", "vinç": "07_OPERASYON", "ekipman": "07_OPERASYON",

        # Official / Legal
        "belediye": "05_BELEDIYE_ISLEMLERI", "ruhsat": "05_BELEDIYE_ISLEMLERI",
        "sozlesme": "08_RESMI_BELGELER", "sözleşme": "08_RESMI_BELGELER",

        # Corporate / HR
        "personel": "09_IK_VE_PERSONEL", "ik ": "09_IK_VE_PERSONEL", "is plani": "09_IK_VE_PERSONEL",
        "guvenlik": "10_IS_GUVENLIGI", "hse": "10_IS_GUVENLIGI",
        "vizyon": "01_KURUMSAL", "profil": "01_KURUMSAL", "rehber": "01_KURUMSAL",
        "toplanti": "11_YONETIM", "notlar": "11_YONETIM", "rapor": "11_YONETIM"
    }

    assigned_projects = []
    assigned_types = []
    assigned_categories = []

    for idx, row in df.iterrows():
        # Combine filename and content, then normalize
        combined_content = normalize_text(row['filename'] + " " + row['text'])

        # 1. Project Assignment
        proj = "Belirsiz"
        for k, v in project_keywords.items():
            if k in combined_content:
                proj = v
                break
        assigned_projects.append(proj)

        # 2. Document Type Assignment
        dt = "12_DIGER_EVRAKLAR"
        for k, v in doc_types.items():
            if k in combined_content:
                dt = v
                break
        assigned_types.append(dt)

        # 3. Category Generation
        if proj == "Belirsiz" and dt == "12_DIGER_EVRAKLAR":
            assigned_categories.append("99_AYIKLANACAKLAR")
        else:
            # Structure: PROJECT / DOC_TYPE
            if proj == "Belirsiz":
                assigned_categories.append(f"GENEL_ARSIV/{dt}")
            else:
                assigned_categories.append(f"{proj}/{dt}")

    df['project'] = assigned_projects
    df['doc_type'] = assigned_types
    df['proposed_category'] = assigned_categories
    return df

def detect_relationships(df, similarity_threshold=0.3):
    """
    Uses TF-IDF, Cosine Similarity, file sizes, and regex to find related documents.
    """
    if len(df) < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words=None)
    tfidf_matrix = vectorizer.fit_transform(df['text'])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    relationships = []
    for i in range(len(df)):
        for j in range(i+1, len(df)):
            sim_score = cosine_sim[i][j]
            file_i = df.iloc[i]['filename']
            file_j = df.iloc[j]['filename']
            size_i = df.iloc[i]['size_bytes']
            size_j = df.iloc[j]['size_bytes']

            # File name heuristic checks for versions
            name_i_norm = normalize_text(file_i)
            name_j_norm = normalize_text(file_j)

            version_keywords = ['son', 'yedek', 'kopya', 'v2', 'rev', 'draft', 'taslak']
            has_version_flag = any(vk in name_i_norm or vk in name_j_norm for vk in version_keywords)

            rel_type = "Related Content"

            # If files are identical in size and highly similar in text
            if sim_score > 0.98 and size_i == size_j:
                rel_type = "Exact Duplicate"
            # If similarity is very high, or high with version keywords in filename
            elif sim_score > 0.80 or (sim_score > 0.50 and has_version_flag):
                rel_type = "Version / Near Duplicate"

            if sim_score >= similarity_threshold:
                relationships.append({
                    "source": file_i,
                    "target": file_j,
                    "similarity": round(sim_score, 3),
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
