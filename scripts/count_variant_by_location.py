#!/usr/bin/env python3
# Script from ChatGPT
import argparse
import sys
from typing import Optional, List
import pandas as pd

def count_clade_by_region(
    tsv_file: str,
    clade_name: Optional[str] = None,
    min_date: Optional[str] = None,
    min_total_count: int = 0,
) -> None:
    """
    Read a TSV with columns: location, clade, date (YYYY-MM-DD), sequences
    and print a per-region table of counts and percentages for the selected clade.

    Parameters
    ----------
    tsv_file : str
        Path to input TSV.
    clade_name : Optional[str]
        Clade to count (exact match). If None, counts will be zero in the clade column.
    min_date : Optional[str]
        If provided (YYYY-MM-DD), only include observations on/after this date
        in both numerator and denominator.
    min_total_count : int
        Minimum total sequences required for a region to be shown (after filters).
    """
    # Load
    df = pd.read_csv(tsv_file, sep="\t")
    required_cols = {"location", "clade", "date", "sequences"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"Error: TSV missing required columns: {', '.join(sorted(missing))}", file=sys.stderr)
        sys.exit(2)

    # Optional date filter
    if min_date:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        cutoff = pd.to_datetime(min_date, errors="coerce")
        if pd.isna(cutoff):
            print(f"Error: --min-date '{min_date}' is not a valid date (expected YYYY-MM-DD).", file=sys.stderr)
            sys.exit(2)
        df = df[df["date"] >= cutoff]

    if df.empty:
        print("No data after applying filters.")
        return

    # Compute counts
    if clade_name is not None:
        clade_df = df[df["clade"] == clade_name]
        clade_counts = clade_df.groupby("location")["sequences"].sum()
    else:
        clade_counts = pd.Series(dtype=float)

    total_counts = df.groupby("location")["sequences"].sum()

    # Apply min_total_count threshold to region list
    regions = [loc for loc, total in total_counts.items() if int(total) >= min_total_count]
    regions.sort()

    if not regions:
        print("No regions meet the --min-total-count threshold after filters.")
        return

    # Column widths
    region_w = 15
    clade_w = 12
    total_w = 7
    perc_w = 10  # includes the % sign, e.g., '35.8%'

    # Header
    label = clade_name if clade_name is not None else "clade"
    print(f"| {'Region':<{region_w}} | {label:<{clade_w}} | {'Total':<{total_w}} | {'Percentage':<{perc_w}} |")
    print(f"|{'-'*(region_w+1)}|{'-'*(clade_w+2)}|{'-'*(total_w+2)}|{'-'*(perc_w+2)}|")

    # Rows
    for region in regions:
        clade_count = int(clade_counts.get(region, 0))
        total_count = int(total_counts.get(region, 0))
        percentage = (clade_count / total_count * 100) if total_count > 0 else 0.0
        perc_str = f"{percentage:.1f}%"
        print(f"| {region:<{region_w}} | {clade_count:<{clade_w}} | {total_count:<{total_w}} | {perc_str:<{perc_w}} |")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Count a clade by region from a TSV of sequence counts."
    )
    parser.add_argument("tsv_file", help="Path to TSV (with columns: location, clade, date, sequences)")
    parser.add_argument(
        "--clade",
        dest="clade",
        default=None,
        help='Clade to count (exact match). Example: "D.3.1:157L"',
    )
    parser.add_argument(
        "--min-date",
        dest="min_date",
        default=None,
        help="Only include observations on/after this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--min-total-count",
        dest="min_total_count",
        type=int,
        default=0,
        help="Only show regions with at least this many total sequences after filters (default: 0).",
    )
    args = parser.parse_args(argv)
    count_clade_by_region(
        args.tsv_file,
        clade_name=args.clade,
        min_date=args.min_date,
        min_total_count=args.min_total_count,
    )


if __name__ == "__main__":
    main()
