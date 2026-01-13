"""Collapse low-count haplotype counts into parent clades."""
import argparse
import pandas as pd


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        __doc__,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--seq-counts",
        metavar="TSV",
        required=True,
        help="Path to clade counts TSV with columns: 'location','clade','date','sequences'"
    )

    parser.add_argument(
        "--haplotype-min-seq",
        type=positive_int,
        help=(
            "The minimum number of sequences a haplotype must have "
            "to be included as its own variant. Derived haplotypes below this threshold are collapsed "
            "into their parental clade. For example, a low-count haplotype 'K:S145N' would be collapsed "
            "into a haplotype 'K'."
        )
    )

    parser.add_argument(
        "--output-seq-counts",
        required=True,
        help="Path to output TSV file for the prepared variants data."
    )

    args = parser.parse_args()

    seq_counts = pd.read_csv(
        args.seq_counts,
        sep='\t',
    )

    seqs_per_haplotype = seq_counts.groupby(['clade'], as_index=False).aggregate(
        sequence_count=("sequences", "sum")
    )

    low_count_haplotypes = set(
        seqs_per_haplotype.loc[
            (
                (seqs_per_haplotype["clade"].str.contains(":")) &
                (seqs_per_haplotype["sequence_count"] < args.haplotype_min_seq)
            ),
            "clade"
        ].values
    )
    seq_counts_with_low_count_haplotypes = seq_counts["clade"].isin(low_count_haplotypes)
    seq_counts.loc[seq_counts_with_low_count_haplotypes, "clade"] = seq_counts.loc[
        seq_counts_with_low_count_haplotypes,
        "clade"
    ].apply(
        lambda haplotype: haplotype.split(":")[0]
    )

    seq_counts = seq_counts.groupby(
        [
            'location',
            'clade',
            'date',
        ],
        as_index=False,
    ).sum(numeric_only=False)

    seq_counts.to_csv(
        args.output_seq_counts,
        sep='\t',
        index=False,
    )
