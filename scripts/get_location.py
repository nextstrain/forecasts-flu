import pandas as pd
import argparse
import os

def get_location(data, min_seq, out_dir):
    """ Returns <location>.lst (country or region) of countries with a month with a peak greater than the <threshold> of sequences per month."""
    data = pd.read_csv(data, sep="\t")

    seq_by_group = data.groupby(["location"])["sequences"].sum().reset_index()
    filter_val = seq_by_group[seq_by_group["sequences"] >= min_seq]
    min_seq_df = filter_val.sort_values("sequences", ascending=False)
    locations = min_seq_df["location"].values.tolist()

    # write locations into list file
    with open(out_dir, "w", encoding="utf-8") as lst_file:
        print("location", file=lst_file)
        for location in locations:
            print(location, file=lst_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get locations with min mean seq per month")
    parser.add_argument("-i", "--input_seqs", type=str, required=True, help="Variant sequence counts TSV file")
    parser.add_argument("-t", "--threshold", type=float, required=True, default=20, help="Threshold for sequences per month per location")
    parser.add_argument("-o", "--output", type=str, required=True, help="Path to location.lst")
    args = parser.parse_args()
    get_location(args.input_seqs, args.threshold, args.output)
