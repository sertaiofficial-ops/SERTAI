import os
import shutil
import pandas as pd

def execute_organization(df, source_dir, target_base_dir="Organized_Archive", rels=None):
    """
    Safely copies files to the new architecture based on the DataFrame.
    Never deletes or moves the original files.
    Also exports duplicate and unresolved reports.
    """
    if not os.path.exists(target_base_dir):
        os.makedirs(target_base_dir)

    log = []

    for idx, row in df.iterrows():
        # Get proposed category / path
        category_path = row['proposed_category']

        # Build full target directory path
        target_dir = os.path.join(target_base_dir, os.path.normpath(category_path))
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        source_path = row['filepath']
        filename = row['filename']
        target_path = os.path.join(target_dir, filename)

        try:
            # COPY only. Never move.
            shutil.copy2(source_path, target_path)
            log.append({"status": "SUCCESS", "file": filename, "target": target_path})
        except Exception as e:
            log.append({"status": "ERROR", "file": filename, "target": target_path, "error": str(e)})

    # Generate Master Index in the root of the new archive
    master_index_path = os.path.join(target_base_dir, "MASTER_INDEX.csv")
    df.to_csv(master_index_path, index=False)

    # Export Duplicate/Relationships Report
    if rels:
        dupes_df = pd.DataFrame([r for r in rels if r['type'] in ["Exact Duplicate", "Version / Near Duplicate"]])
        if not dupes_df.empty:
            dupes_df.to_csv(os.path.join(target_base_dir, "DUPLICATES_REPORT.csv"), index=False)

    # Export Unresolved Report
    orphans = df[df['proposed_category'] == '99_AYIKLANACAKLAR']
    if not orphans.empty:
        orphans[['filename', 'text']].to_csv(os.path.join(target_base_dir, "UNRESOLVED_FILES.csv"), index=False)

    return pd.DataFrame(log)
