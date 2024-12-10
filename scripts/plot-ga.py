import altair as alt
import argparse
from collections import defaultdict
import json
import math
from matplotlib import pyplot as plt
import pandas as pd

def plot_ga(input_file, virus, color_file, out_var, out_loc, loc_lst, var_lst, pivot_file, auspice_config_file=None, coloring_field=None):
    # Read in GA file.
    df = pd.read_csv(input_file, sep="\t")

    # If a location/variant list is specified, subset the GA.
    if loc_lst:
        loc_filter = list(pd.read_csv(loc_lst)["location"].values)
    else:
        loc_filter = list(df["location"].unique())

    loc_filter.insert(0, "hierarchical")

    if var_lst:
        var_filter = pd.read_csv(var_lst)["variant"].values
    else:
        var_filter = df["variant"].unique()

    df = df[df["location"].isin(loc_filter)]
    df = df[df["variant"].isin(var_filter)]
    base_chart = alt.Chart(df)

    # Parse pivot from file
    for line in open(pivot_file):
        pivot = line.strip()

    # Load color map for locations.
    colors_by_n = {}
    with open(color_file, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            colors_by_n[n + 1] = line.rstrip().split("\t")

    # Add color codes by location
    locations = sorted(df["location"].drop_duplicates().values, key=lambda x: (x != "hierarchical", x))
    color_by_location = dict(zip(locations, colors_by_n[len(locations)]))
    df["location_color"] = df["location"].map(color_by_location)

    # Load color map from Auspice config. Otherwise, build a new map for variant
    # colors if one is not provided through an Auspice config.
    variants = sorted(df["variant"].drop_duplicates().values)
    if auspice_config_file:
        with open(auspice_config_file, "r", encoding="utf-8") as fh:
            auspice_config = json.load(fh)

            if "colorings" in auspice_config:
                for coloring in auspice_config["colorings"]:
                    if coloring["key"] == coloring_field:
                        if "scale" in coloring:
                            print(f"Using color map defined in {auspice_config_file}")
                            color_by_variant = defaultdict(lambda: "#CCCCCC")
                            for clade, color in coloring["scale"]:
                                if clade != pivot and clade in variants:
                                    color_by_variant[clade] = color

                        break
    else:
        color_by_variant = dict(zip(variants, colors_by_n[len(variants)]))

    # Add color codes by variant
    df["variant_color"] = df["variant"].map(color_by_variant)

    # Do column layout
    n_loc = len(locations)
    n_var = len(variants)
    max_col_loc = min(n_loc, 5)
    max_col_var = min(n_var, 4)

    ### Plot GA by location
    tooltip_attributes = [
        "variant",
        "HDI_95_lower",
        "median",
        "HDI_95_upper"
        ]

    points = base_chart.mark_circle(size=35).encode(
        x=alt.X("median:Q", title="Growth advantage"),
        y=alt.Y("variant:N", title=f"Variant (pivot {pivot})", sort=locations),
        color=alt.Color("variant:N", scale=alt.Scale(domain=list(color_by_variant.keys()), range=list(color_by_variant.values()))),
        tooltip=tooltip_attributes
        )

    error_bars = base_chart.mark_line().encode(
        x="HDI_95_lower:Q",
        x2="HDI_95_upper:Q",
        y="variant:N",
        color=alt.Color("variant:N", scale=alt.Scale(domain=list(color_by_variant.keys()), range=list(color_by_variant.values()))),
        tooltip=tooltip_attributes
        )

    ga_threshold = base_chart.mark_rule(
        strokeWidth=0.25,
        strokeDash=[8, 8],
        ).encode(
            x=alt.datum(1.0),
            color=alt.ColorValue("gray")
            )

    location_chart = (ga_threshold + points + error_bars).properties(
        width=150,
        height=150,
        ).facet(
            alt.Column(
                "location:N",
                title="",
                sort=locations,
                header=alt.Header(labelOrient="top", titleOrient="top", labels=True)
                ),
            columns=max_col_loc
            )
    location_chart.save(out_loc)

    # ### Plot GA by variant
    tooltip_attributes = [
        "location",
        "HDI_95_lower",
        "median",
        "HDI_95_upper"
        ]
    points = base_chart.mark_circle(size=35).encode(
        x=alt.X("median:Q", title="Growth advantage"),
        y=alt.Y("location:N", title="Location", sort=locations),
        color=alt.Color("location:N", scale=alt.Scale(domain=list(color_by_location.keys()), range=list(color_by_location.values()))),
        tooltip=tooltip_attributes,
        )

    error_bars = base_chart.mark_line().encode(
        x="HDI_95_lower:Q",
        x2="HDI_95_upper:Q",
        y=alt.Color("location:N", sort=locations),
        color=alt.Color("location:N", scale=alt.Scale(domain=list(color_by_location.keys()), range=list(color_by_location.values()))),
        tooltip=tooltip_attributes
        )

    ga_threshold = base_chart.mark_rule(
        strokeWidth=0.25,
        strokeDash=[8, 8],
        ).encode(
            x=alt.datum(1.0),
            color=alt.ColorValue("gray")
            )

    variant_chart = (ga_threshold + points + error_bars).properties(
        width=150,
        height=150,
        ).facet(
            alt.Column(
                "variant:N",
                title=f"{virus}: Variant (pivot {pivot})",
                sort=locations,
                header=alt.Header(labelOrient="top", titleOrient="top", labels=True)

            ),
            columns=max_col_var
        )
    variant_chart.save(out_var)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot GA plots by location and variant.")
    parser.add_argument("-i", "--input_ga", type=str, help="Parsed MLR growth advantage file (<name>_ga.tsv)")
    parser.add_argument("-v", "--virus", help="Virus type ['H3N2', 'H1N1pdm', 'B_Vic']")
    parser.add_argument("-c", "--colors", help="Path to Nextstrain color scheme (color_schemes.tsv)]")
    parser.add_argument("--auspice-config", help="Auspice config JSON with custom colorings for clades defined in a scale")
    parser.add_argument("--coloring-field", default="subclade", help="name of the coloring field in the given Auspice config JSON to use for the color scale")
    parser.add_argument("-ov", "--out_variant", help="GA by variant PDF")
    parser.add_argument("-ol", "--out_location", help="GA by location PDF")
    parser.add_argument("-ll", "--location_list", required=False, help="Location list TXT file to include in GA plot")
    parser.add_argument("-vl", "--variant_list", required=False, help="Variant list TXT file to include in GA plot")
    parser.add_argument("-p", "--pivot", type=str, required=False, help="Pivot for MLR run")
    args = parser.parse_args()
    plot_ga(args.input_ga, args.virus, args.colors, args.out_variant, args.out_location, args.location_list, args.variant_list, args.pivot, args.auspice_config, args.coloring_field)
