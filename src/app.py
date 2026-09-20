import os
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from src.analyzer import run_analysis_pipeline
from src.organizer import execute_organization

st.set_page_config(page_title="AI Archive Organizer", layout="wide")

st.title("AI-Powered Digital Archive Organizer")
st.markdown("Automated analysis and organization for Doğrusal Mühendislik.")

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'rels' not in st.session_state:
    st.session_state.rels = []

# --- 1. IMPORT ---
st.header("1. Import & Analysis")
source_dir = st.text_input("Enter path to the messy archive directory:", value="mock_archive")

if st.button("Analyze Content"):
    if os.path.exists(source_dir):
        with st.spinner("Parsing files and analyzing content..."):
            df, rels = run_analysis_pipeline(source_dir)
            st.session_state.df = df
            st.session_state.rels = rels
        st.success(f"Analyzed {len(df)} files successfully.")
    else:
        st.error("Directory not found.")

if not st.session_state.df.empty:
    df = st.session_state.df
    rels = st.session_state.rels

    # --- 2. RELATIONSHIP DISCOVERY & DUPLICATES ---
    st.header("2. Discovered Relationships & Duplicates")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Duplicates and Versions")
        dupes = [r for r in rels if r['type'] in ["Exact Duplicate", "Version / Near Duplicate"]]
        if dupes:
            st.dataframe(pd.DataFrame(dupes))
        else:
            st.info("No duplicates found.")

    with col2:
        st.subheader("Visual Relationship Map")
        if rels:
            G = nx.Graph()
            for r in rels:
                # Add nodes and edges based on relationships
                G.add_edge(r['source'], r['target'], weight=r['similarity'])

            fig, ax = plt.subplots(figsize=(8, 6))
            pos = nx.spring_layout(G, k=0.5)
            nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=8, ax=ax)
            st.pyplot(fig)
        else:
            st.info("Not enough data to map relationships.")

    # --- 3. ORPHANS / UNCLEAR FILES ---
    st.header("3. Unresolved Files")
    orphans = df[df['proposed_category'] == '99_AYIKLANACAKLAR']
    if not orphans.empty:
        st.warning("The following files could not be confidently categorized and need review:")
        st.dataframe(orphans[['filename', 'text']])
    else:
        st.success("All files successfully categorized.")

    # --- 4. REVIEW BEFORE CHANGES ---
    st.header("4. Proposed Architecture & Review")
    st.markdown("Review and edit the proposed categories below. **Original files will not be touched.**")

    # Editable dataframe
    edited_df = st.data_editor(
        df[['filename', 'project', 'doc_type', 'proposed_category']],
        key="data_editor",
        use_container_width=True
    )

    # Update main DF with user edits
    df['proposed_category'] = edited_df['proposed_category']

    # Tree visualization
    st.subheader("Proposed Folder Structure Preview")
    tree = {}
    for cat in df['proposed_category'].unique():
        parts = cat.split('/')
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    def display_tree(d, indent=0):
        for k, v in d.items():
            st.markdown("&nbsp;" * indent * 4 + f"📂 **{k}**")
            display_tree(v, indent + 1)

    display_tree(tree)

    # --- 5. SAFE ORGANIZATION ---
    st.header("5. Execute Safe Organization")
    target_dir = st.text_input("Target Organized Archive Directory:", value="Organized_Archive")

    if st.button("Confirm and Organize"):
        with st.spinner("Copying files to new architecture..."):
            log_df = execute_organization(df, source_dir, target_base_dir=target_dir, rels=rels)
            st.success("Organization complete! Master Index and reports have been generated in the target directory.")
            st.dataframe(log_df)
