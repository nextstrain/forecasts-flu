#!/usr/bin/env python3
# from ChatGPT
# This should be cleaned up to have a structured list of AA substitutions
# mapped to a list of variant names
import argparse
import csv

def main():
    parser = argparse.ArgumentParser(
        description="Update the 'proposedSubclade' column based on specific AA substitutions."
    )
    parser.add_argument("--input", required=True, help="Input metadata TSV file.")
    parser.add_argument("--output", required=True, help="Output updated metadata TSV file.")
    args = parser.parse_args()

    # Define patterns for relabeling
    # Condition 1: If 'HA1:N158K' and 'HA1:K189R' are present.
    # Also include 'HA1:N122D' and 'HA1:K276E' to demarcate J.2
    condition1 = {"HA1:N158K", "HA1:K189R", "HA1:N122D", "HA1:K276E"}
    new_label1 = "J.2:158K-189R"

    # Condition 2: If 'HA1:T135A' and 'HA1:S145N' are present.
    # Also include 'HA1:N122D' and 'HA1:K276E' to demarcate J.2
    condition2 = {"HA1:T135A", "HA1:S145N", "HA1:N122D", "HA1:K276E"}
    new_label2 = "J.2:135A-145N"

    with open(args.input, "r", newline="", encoding="utf-8") as infile, \
         open(args.output, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile, delimiter="\t")
        fieldnames = reader.fieldnames

        # If for some reason these columns are not in the file, you may want to handle that gracefully.
        if 'proposedSubclade' not in fieldnames or 'aaSubstitutions' not in fieldnames:
            raise ValueError("Input TSV must contain 'proposedSubclade' and 'aaSubstitutions' columns.")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            aa_subs = row['aaSubstitutions'].split(",")
            aa_subs_set = set([sub.strip() for sub in aa_subs])

            # Check the two conditions in sequence:
            if condition1.issubset(aa_subs_set):
                # If Condition 1 is satisfied
                row['proposedSubclade'] = new_label1
            elif condition2.issubset(aa_subs_set):
                # Else if Condition 2 is satisfied
                row['proposedSubclade'] = new_label2

            writer.writerow(row)

if __name__ == "__main__":
    main()
