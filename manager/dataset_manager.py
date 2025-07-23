import os
import shutil
import json
from datetime import datetime

def createMirroredDataset(session_info: dict, scan_info: dict, primary_save_path: str) -> str:
    """
    Creates a BIDS-inspired dataset structure, copies scan files into it, and saves metadata.

    This function takes the session and scan information and organizes the output files
    from the primary acquisition directory into a clean, structured dataset directory.

    Args:
        session_info (dict): The fully populated session dictionary from the GUI.
                             Expected keys: 'subject_id', 'study_id', etc.
        scan_info (dict): The mapVals dictionary from the completed sequence run.
                          Expected keys: 'seqName', 'fileName', 'name_string', etc.
        primary_save_path (str): The original save path where the .mat, .csv, etc.,
                                 were initially saved (e.g., 'experiments/acquisitions/...').

    Returns:
        str: The absolute path to the newly created session directory in the mirrored dataset.
             Returns None if a critical error occurs.
    """
    try:
        # --- 1. Define Paths and Labels ---

        # Define the root directory for the entire dataset.
        # It's good practice to make this configurable, but we'll hardcode it for now.
        dataset_root = '/home/bryant/Desktop/mri_dataset'

        # Sanitize the subject_id to use in a folder name (replaces spaces, etc.).
        subject_label = session_info.get('subject_id', 'UnknownSubject').replace(" ", "_")
        subject_folder = f"sub-{subject_label}"

        # Create a session label from the acquisition timestamp for chronological sorting.
        # The 'name_string' from mapVals is the unique scan identifier.
        timestamp_str = scan_info.get('name_string')
        if not timestamp_str:
            raise ValueError("'name_string' (unique timestamp) is missing from scan_info.")
            
        # Parse the timestamp to create a datetime object for formatting.
        dt_object = datetime.strptime(timestamp_str, "%Y.%m.%d.%H.%M.%S.%f")
        session_label = f"ses-{dt_object.strftime('%Y%m%dT%H%M%S')}"

        # Construct the full path for the new session directory.
        dataset_session_path = os.path.join(dataset_root, subject_folder, session_label)

        # --- 2. Create Directory Structure ---

        # Define the subdirectories for each file type.
        subfolders = ["mat", "csv", "dcm", "raw", "seq"]
        for subfolder in subfolders:
            os.makedirs(os.path.join(dataset_session_path, subfolder), exist_ok=True)

        # --- 3. Identify Source Files and Copy Them ---

        # The base filename is the unique part, without the extension.
        base_filename = os.path.splitext(scan_info.get('fileName', ''))[0]
        if not base_filename:
            raise ValueError("'fileName' is missing from scan_info.")

        # Define a map of file extensions to their source and destination subdirectories.
        file_map = {
            ".mat": ("mat", "mat"),
            ".csv": ("csv", "csv"),
            ".dcm": ("dcm", "dcm"),
            ".h5": ("ismrmrd", "raw"), # Source is 'ismrmrd', destination is 'raw'
        }

        # Helper function to safely copy a file if it exists.
        def _try_copy(src_path, dest_path):
            if os.path.exists(src_path):
                shutil.copy(src_path, dest_path)
                print(f"  - Copied: {os.path.basename(src_path)}")
            else:
                print(f"  - Skipped (not found): {os.path.basename(src_path)}")

        print(f"Mirroring files for scan: {base_filename}")
        
        # Copy the main data files.
        for ext, (src_subdir, dest_subdir) in file_map.items():
            source_file = os.path.join(primary_save_path, src_subdir, f"{base_filename}{ext}")
            dest_file = os.path.join(dataset_session_path, dest_subdir, f"{base_filename}{ext}")
            _try_copy(source_file, dest_file)

        # Copy the sequence (.seq) files, which are handled differently.
        primary_seq_dir = os.path.join(primary_save_path, 'seq')
        dest_seq_dir = os.path.join(dataset_session_path, 'seq')
        if os.path.exists(primary_seq_dir):
            for seq_file in os.listdir(primary_seq_dir):
                if seq_file.startswith(base_filename) and seq_file.endswith(".seq"):
                    source_file = os.path.join(primary_seq_dir, seq_file)
                    dest_file = os.path.join(dest_seq_dir, seq_file)
                    _try_copy(source_file, dest_file)
        
        # --- 4. Save Metadata ---

        # Combine session and scan parameters into a single comprehensive metadata dictionary.
        full_metadata = {
            "session_info": session_info,
            "scan_parameters": {key: str(value) for key, value in scan_info.items()} # Convert numpy arrays etc. to strings
        }
        
        metadata_path = os.path.join(dataset_session_path, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(full_metadata, f, indent=4)
        print(f"  - Saved: metadata.json")

        return dataset_session_path

    except Exception as e:
        print(f"CRITICAL ERROR in create_mirrored_dataset: {e}")
        return None

