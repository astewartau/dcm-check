import sys
import json
import argparse
import pandas as pd
from tabulate import tabulate
from ..io import read_dicom_session, read_json_session
from ..models import load_ref_dict
from ..compliance import check_session_compliance
from ..mapping import map_session, interactive_mapping

def main():
    parser = argparse.ArgumentParser(description="Generate compliance summaries for a DICOM session based on JSON reference.")
    parser.add_argument("--json_ref", required=True, help="Path to the JSON reference file.")
    parser.add_argument("--in_session", required=True, help="Directory path for the DICOM session.")
    parser.add_argument("--out_json", default="compliance_report.json", help="Path to save the JSON compliance summary report.")
    parser.add_argument("--auto_yes", action="store_true", help="Automatically map acquisitions to series.")
    args = parser.parse_args()

    acquisition_fields, reference_fields, ref_session = read_json_session(json_ref=args.json_ref)
    ref_session = load_ref_dict(ref_session)
    in_session = read_dicom_session(session_dir=args.in_session, acquisition_fields=acquisition_fields, reference_fields=reference_fields)
    session_map = map_session(in_session, ref_session)
    if not args.auto_yes and sys.stdin.isatty():
        session_map = interactive_mapping(in_session, ref_session, initial_mapping=session_map)
    compliance_summary = check_session_compliance(in_session, ref_session, session_map)
    compliance_df = pd.DataFrame(compliance_summary)

    # if compliance_df is empty, print message and exit
    if compliance_df.empty:
        print("Session is fully compliant with the reference model.")
        return
    
    print(tabulate(compliance_df, headers="keys", tablefmt="simple"))

    # Save compliance_summary (which is a dict) to JSON file
    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(compliance_summary, f)

if __name__ == "__main__":
    main()

