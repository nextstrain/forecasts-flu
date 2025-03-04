#!/usr/bin/env python3
# from ChatGPT
import argparse
import csv

def main():
    parser = argparse.ArgumentParser(
        description="Update the variant column based on mapping rules defined in a TSV."
    )
    parser.add_argument(
        "--input-metadata",
        required=True,
        help="Input metadata TSV file containing 'proposedSubclade' and 'aaSubstitutions' columns."
    )
    parser.add_argument(
        "--input-mapping",
        required=True,
        help="Mapping TSV file with columns: old_label, new_label, and optional comma-separated mutations."
    )
    parser.add_argument(
        "--variant-column",
        required=True,
        help="Column in metadata TSV with variant information to update")
    parser.add_argument(
        "--output",
        required=True,
        help="Output updated metadata TSV file."
    )
    args = parser.parse_args()

    # 1. Read the mapping from the TSV file
    #    Each line: old_label, new_label, required_substitutions (optional)
    mapping = []
    with open(args.input_mapping, "r", encoding="utf-8") as mapping_file:
        for line in mapping_file:
            line = line.strip()
            if not line:
                # Skip empty lines
                continue
            parts = line.split("\t")

            # Expect at least old_label, new_label
            if len(parts) < 2:
                raise ValueError(
                    f"Each line in mapping file must have at least 2 columns. Found: {line}"
                )

            old_label = parts[0].strip()  # e.g. "J.2"
            new_label = parts[1].strip()  # e.g. "J.2:158K-189R"

            if len(parts) > 2 and parts[2].strip():
                # If there is a third column and it's not empty
                required_subs = {
                    s.strip() for s in parts[2].split(",") if s.strip()
                }
            else:
                # No required substitutions (unconditional update)
                required_subs = set()

            mapping.append((old_label, new_label, required_subs))

    # 2. Process the metadata TSV
    with open(args.input_metadata, "r", newline="", encoding="utf-8") as infile, \
         open(args.output, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile, delimiter="\t")
        fieldnames = reader.fieldnames

        # Ensure required columns exist
        if args.variant_column not in fieldnames or 'aaSubstitutions' not in fieldnames:
            raise ValueError(
                "Input metadata TSV must contain args.variant_column and 'aaSubstitutions' columns."
            )

        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            current_label = row[args.variant_column]
            aa_subs = row['aaSubstitutions'].split(",")
            aa_subs_set = {sub.strip() for sub in aa_subs if sub.strip()}

            # Check the mapping in the order they appear
            for old_label, new_label, required_subs in mapping:
                if current_label == old_label:
                    # If no required subs, update unconditionally
                    if not required_subs:
                        row[args.variant_column] = new_label
                        break
                    # If required_subs is a subset of aa_subs_set
                    if required_subs.issubset(aa_subs_set):
                        row[args.variant_column] = new_label
                        break

            writer.writerow(row)

if __name__ == "__main__":
    main()
