import argparse
import yaml
import os
import pandas as pd

def function_name(input, output):
    """
    Parses the pivot from the MLR config and outputs it as a TXT file.
    """
    data = pd.read_csv(input, sep="\t")

    with open(input) as file:
        config_data = yaml.safe_load(file)
        pivot = config_data["model"]["pivot"]

        # Write the pivot value to the output file
        with open(output, "w") as f:
            f.write(str(pivot))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--input_file", required=True, help="Path to MLR config with pivot.")
    parser.add_argument("--output_file", required=True, help="Output path to pivot TXT file.")
    args = parser.parse_args()
    function_name(args.input_file, args.output_file)
