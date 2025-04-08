#!/usr/bin/env python3
import argparse
import json
import sys


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--model", required=True, help="JSON file of model to add colors to")
    parser.add_argument("--auspice-config", required=True, help="Auspice config JSON with a color scale to use to color variants in the given model")
    parser.add_argument("--coloring-field", required=True, help="name of the coloring field in the given Auspice config JSON where the color scale is stored")
    parser.add_argument("--output", required=True, help="JSON file of model with colors added")

    args = parser.parse_args()

    # Get color scale from Auspice config.
    with open(args.auspice_config, "r", encoding="utf-8") as fh:
        auspice_config = json.load(fh)

    color_scale = None
    for coloring in auspice_config["colorings"]:
        if coloring["key"] == args.coloring_field:
            color_scale = coloring["scale"]
            break

    if color_scale is None:
        print(
            f"ERROR: Could not find a color scale for the field '{args.coloring_field}' in the given Auspice config JSON.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load the model JSON.
    with open(args.model, "r", encoding="utf-8") as fh:
        model = json.load(fh)

    # Add the color scale to the model JSON.
    model["metadata"]["variantColors"] = color_scale

    # Save the modified model JSON.
    with open(args.output, "w", encoding="utf-8") as oh:
        json.dump(model, oh)
