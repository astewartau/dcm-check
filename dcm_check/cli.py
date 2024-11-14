#!/usr/bin/env python

import argparse
import pandas as pd
import json
import sys
import os

from tabulate import tabulate

from dcm_check.dcm_check import load_ref_json, load_ref_dicom, load_ref_pydantic, get_compliance_summary, load_dicom

def infer_type_from_extension(ref_path):
    """Infer the reference type based on the file extension."""
    _, ext = os.path.splitext(ref_path.lower())
    if ext == ".json":
        return "json"
    elif ext == ".dcm":
        return "dicom"
    elif ext == ".py":
        return "pydantic"
    else:
        print("Error: Could not determine the reference type. Please specify '--type'.", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Check DICOM compliance against a reference model.")
    parser.add_argument("--ref", required=True, help="Reference JSON file, DICOM file, or Python module to use for compliance.")
    parser.add_argument("--type", choices=["json", "dicom", "pydantic"], help="Reference type: 'json', 'dicom', or 'pydantic'.")
    parser.add_argument("--scan", required=False, help="Scan type when using a JSON or Pydantic reference.")
    parser.add_argument("--in", dest="in_file", required=True, help="Path to the DICOM file to check.")
    parser.add_argument("--fields", nargs="*", help="Optional: List of DICOM fields to include in validation for DICOM reference.")
    parser.add_argument("--out", required=False, help="Path to save the compliance report in JSON format.")
    args = parser.parse_args()

    # Determine the reference type if not provided
    ref_type = args.type or infer_type_from_extension(args.ref)

    if ref_type == "json":
        reference_model = load_ref_json(args.ref, args.scan)
    elif ref_type == "dicom":
        ref_dicom_values = load_dicom(args.ref)
        reference_model = load_ref_dicom(ref_dicom_values, args.fields)
    elif ref_type == "pydantic":
        reference_model = load_ref_pydantic(args.ref, args.scan)
    else:
        print(f"Error: Unsupported reference type '{ref_type}'", file=sys.stderr)
        sys.exit(1)

    in_dicom_values = load_dicom(args.in_file)
    results = get_compliance_summary(reference_model, in_dicom_values)

    df = pd.DataFrame(results)

    if len(df) == 0:
        print("DICOM file is compliant with the reference model.")
    else:
        print(tabulate(df, headers="keys", tablefmt="simple"))

    if args.out:
        with open(args.out, 'w') as outfile:
            json.dump(results, outfile, indent=4)
        print(f"Compliance report saved to {args.out}")

if __name__ == "__main__":
    main()