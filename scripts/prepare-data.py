"""
Prepare case counts and clade counts data for analysis by subsetting to
specific date range and locations, pruning recent clade counts, and collapsing clades.
"""
import argparse
import pandas as pd
import sys

import re
from datetime import datetime, timedelta

SEQ_COUNTS_DTYPES = {
    'location': 'string',
    'clade': 'string',
    'sequences': 'int64',
}

# Use these as your defaults for relative or absolute dates
DEFAULT_MIN_DATE = "1Y"  # 1 year ago
DEFAULT_MAX_DATE = "1D"  # 1 day ago

def positive_int(value):
    """
    Custom argparse type function to verify only
    positive integers are provided as arguments
    """
    int_value = int(value)
    if int_value <= 0:
        print(f"ERROR: {int_value} is not a positive integer.", file=sys.stderr)
        sys.exit(1)
    return int_value

def parse_relative_or_absolute_date(date_str: str) -> datetime:
    """
    Parse a date string that may be:
      - Absolute in ISO format: e.g. "2024-02-01"
      - Relative with suffix D/M/Y: e.g. "7D", "6M", "1Y"

    We interpret:
      - 'D' => days
      - 'M' => months (30 days)
      - 'Y' => years  (365 days)

    Returns a datetime object (time zeroed out).
    """
    match = re.match(r'^(\d+)([DMY])$', date_str.strip())
    if match:
        quantity = int(match.group(1))
        unit = match.group(2)

        ref_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if unit == "D":
            delta = timedelta(days=quantity)
        elif unit == "M":
            # Approximate 1 month as 30 days
            delta = timedelta(days=30 * quantity)
        elif unit == "Y":
            # Approximate 1 year as 365 days
            delta = timedelta(days=365 * quantity)
        else:
            raise ValueError(f"Unrecognized time unit in {date_str}. Must be D, M, or Y.")

        return ref_date - delta
    else:
        # Otherwise assume YYYY-MM-DD
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(
                f"Could not parse date string: {date_str}. "
                "Must be either YYYY-MM-DD or a pattern like 7D, 6M, 1Y."
            )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "--seq-counts",
        metavar="TSV",
        required=True,
        help="Path to clade counts TSV with columns: 'location','clade','date','sequences'"
    )

    parser.add_argument(
        "--min-date",
        default=DEFAULT_MIN_DATE,
        help=(
            "The minimum cutoff for date (inclusive). Can be:\n"
            "  - 'YYYY-MM-DD'\n"
            "  - A relative date like '7D' (7 days ago), '6M' (6 months ago), or '1Y' (1 year ago)\n"
            "(default: %(default)s)"
        )
    )

    parser.add_argument(
        "--max-date",
        default=DEFAULT_MAX_DATE,
        help=(
            "The maximum cutoff for date (inclusive). Can be:\n"
            "  - 'YYYY-MM-DD'\n"
            "  - A relative date like '7D', '6M', or '1Y'\n"
            "(default: %(default)s)"
        )
    )

    parser.add_argument(
        "--location-min-seq",
        type=positive_int,
        default=1,
        help=(
            "The minimum number of sequences a location must have in the overall analysis "
            "date range to be included in analysis.\n"
            "(default: %(default)s)"
        )
    )

    parser.add_argument(
        "--excluded-locations",
        help="File with a list of locations to exclude from analysis (one per line)."
    )

    parser.add_argument(
        "--clade-min-seq",
        type=positive_int,
        help=(
            "The minimum number of sequences a clade must have (over the entire analysis date range) "
            "to be included as its own variant. Clades below this threshold are collapsed into 'other'."
        )
    )

    parser.add_argument(
        "--force-include-clades",
        nargs="*",
        help="Clades to force-include in the output regardless of sequence counts."
    )

    parser.add_argument(
        "--force-exclude-clades",
        nargs="*",
        help="Clades to force-exclude in the output regardless of sequence counts."
    )

    parser.add_argument(
        "--output-seq-counts",
        required=True,
        help="Path to output TSV file for the prepared variants data."
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Convert min_date and max_date from string to datetime
    # -------------------------------------------------------------------------
    min_date = parse_relative_or_absolute_date(args.min_date)
    max_date = parse_relative_or_absolute_date(args.max_date)

    print(f"Setting min date (inclusive) as {min_date.strftime('%Y-%m-%d')}.")
    print(f"Setting max date (inclusive) as {max_date.strftime('%Y-%m-%d')}.")

    # -------------------------------------------------------------------------
    # Read in seq_counts data
    # -------------------------------------------------------------------------
    # Read the file without automatic date parsing
    seq_counts = pd.read_csv(
        args.seq_counts,
        sep='\t',
        dtype=SEQ_COUNTS_DTYPES
    )

    # Strip whitespace in case of formatting issues
    seq_counts['date'] = seq_counts['date'].str.strip()

    # Convert to datetime and check for parsing issues
    seq_counts['date'] = pd.to_datetime(seq_counts['date'], errors='coerce')

    # Print any problematic rows
    if seq_counts['date'].isna().any():
        print("ERROR: Some dates could not be parsed. Showing first few problematic rows:", file=sys.stderr)
        print(seq_counts[seq_counts['date'].isna()].head(), file=sys.stderr)
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Filter locations: Only include those that have >= location-min-seq
    #    sequences within the [min_date, max_date] range.
    # -------------------------------------------------------------------------
    print(f"Only including locations that have at least {args.location_min_seq} sequence(s) in the analysis date range.")

    # Subset to date range for location-based counting
    location_sub = seq_counts.loc[
        (seq_counts['date'] >= min_date) &
        (seq_counts['date'] <= max_date),
        ['location', 'sequences']
    ]
    seqs_per_location = location_sub.groupby('location', as_index=False).sum()

    # Locations meeting the threshold
    locations_with_min_seq = set(
        seqs_per_location.loc[seqs_per_location['sequences'] >= args.location_min_seq, 'location']
    )

    # Excluded locations (optional file)
    excluded_locations = set()
    if args.excluded_locations:
        with open(args.excluded_locations, 'r') as f:
            excluded_locations = {line.strip() for line in f}
        print(f"Excluding the following requested locations: {sorted(excluded_locations)}.")

    # Final set of locations to include
    locations_to_include = locations_with_min_seq - excluded_locations
    print(f"Locations that will be included: {sorted(locations_to_include)}.")

    assert len(locations_to_include) > 0, (
        "All locations have been excluded. Try again with different options, "
        "e.g. lowering the `--location-min-seq` cutoff.\n"
        f"Here's a summary of available sequences per location:\n"
        f"{seqs_per_location.to_dict(orient='records')}"
    )

    # -------------------------------------------------------------------------
    # Filter / Collapse Clades
    # -------------------------------------------------------------------------
    seq_counts['variant'] = seq_counts['clade']

    force_included_clades = set(args.force_include_clades) if args.force_include_clades else set()
    force_excluded_clades = set(args.force_exclude_clades) if args.force_exclude_clades else set()

    if force_included_clades:
        print(f"Force-including these clades: {sorted(force_included_clades)}")
    if force_excluded_clades:
        print(f"Force-excluding these clades: {sorted(force_excluded_clades)}")

    # Collapse small clades if clade_min_seq is given
    if args.clade_min_seq:
        print(
            f"Collapsing clades that have fewer than {args.clade_min_seq} sequence(s) "
            f"in the analysis date range (inclusive) into 'other'."
        )
        # Subset to [min_date, max_date] for clade-based counting
        clade_sub = seq_counts.loc[
            (seq_counts['date'] >= min_date) &
            (seq_counts['date'] <= max_date),
            ['clade', 'sequences']
        ]
        seqs_per_clade = clade_sub.groupby(['clade'], as_index=False).sum()
        clades_with_min_seq = set(
            seqs_per_clade.loc[seqs_per_clade['sequences'] >= args.clade_min_seq, 'clade']
        )

        # Exclude forcibly excluded from the keep set
        clades_to_keep = clades_with_min_seq - force_excluded_clades

        # Anything not forced included and not in clades_to_keep -> 'other'
        mask_other = ~seq_counts['clade'].isin(force_included_clades | clades_to_keep)
        seq_counts.loc[mask_other, 'variant'] = 'other'

    # Replace "recombinant" with 'other'
    seq_counts.loc[seq_counts['clade'] == 'recombinant', 'variant'] = 'other'

    # If variant is NaN, label it 'other'
    seq_counts.loc[pd.isna(seq_counts['variant']), 'variant'] = 'other'

    # Group by location, variant, date
    seq_counts = seq_counts.groupby(['location', 'variant', 'date'], as_index=False).sum(numeric_only=False)
    seq_counts.drop(columns=['clade'], inplace=True)

    # -------------------------------------------------------------------------
    # Final subsetting by date and location
    # -------------------------------------------------------------------------
    seq_counts = seq_counts.loc[
        (seq_counts['date'] >= min_date) &
        (seq_counts['date'] <= max_date) &
        (seq_counts['location'].isin(locations_to_include))
    ]

    included_variants = seq_counts['variant'].unique()
    print(f"Variants that will be included: {sorted(included_variants)}.")

    assert len(included_variants) > 0, (
        "All variants have been excluded. Try again with different options, "
        "e.g. lowering the `--clade-min-seq` cutoff."
    )

    # Sort and output
    seq_counts.sort_values(['location', 'variant', 'date']).to_csv(
        args.output_seq_counts, sep='\t', index=False
    )
