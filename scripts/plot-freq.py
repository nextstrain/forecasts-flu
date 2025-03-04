import argparse
from collections import defaultdict
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import sys
import matplotlib.ticker as mticker

# Set global default fontsizes
mpl.rcParams["legend.title_fontsize"] = 12
mpl.rcParams["axes.labelsize"] = 12
mpl.rcParams["xtick.labelsize"] = 10
mpl.rcParams["ytick.labelsize"] = 10
mpl.rcParams["legend.fontsize"] = 10


def plot_freq(df_file, raw_file, color_file, output_plot, cases_file=None, loc_lst=None, var_lst=None, auspice_config_file=None, coloring_field=None):
    df = pd.read_csv(df_file, sep="\t", parse_dates=["date"])
    raw = pd.read_csv(raw_file, sep="\t", parse_dates=["date"])

    # If a location/variant list is specified, subset the GA.
    if loc_lst:
        loc_filter = pd.read_csv(loc_lst)["location"].values
    else:
        loc_filter = df["location"].unique()

    if var_lst:
        var_filter = pd.read_csv(var_lst)["variant"].values
    else:
        var_filter = df["variant"].unique()

    df = df[(df["location"].isin(loc_filter)) & (df["variant"].isin(var_filter))].copy()
    raw = raw[(raw["location"].isin(loc_filter)) & (raw["variant"].isin(var_filter))].copy()

    variants = sorted(df["variant"].drop_duplicates().values)

    # Load color map from Auspice config. Otherwise, build a new map if one is
    # not provided through an Auspice config.
    if auspice_config_file:
        color_by_variant = None

        with open(auspice_config_file, "r", encoding="utf-8") as fh:
            auspice_config = json.load(fh)

            if "colorings" in auspice_config:
                for coloring in auspice_config["colorings"]:
                    if coloring["key"] == coloring_field:
                        if "scale" in coloring:
                            print(f"Using color map defined in {auspice_config_file}")
                            color_by_variant = defaultdict(lambda: "#999999")
                            for clade, color in coloring["scale"]:
                                if clade in variants:
                                    color_by_variant[clade] = color

                        break

        if color_by_variant is None:
            print(f"ERROR: Could not find coloring field {coloring_field!r} in the Auspice config JSON {auspice_config_file!r}.", file=sys.stderr)
            sys.exit(1)
    else:
        colors_by_n = {}
        with open(color_file, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                colors_by_n[n + 1] = line.rstrip().split("\t")

        # Add color codes by variant
        color_by_variant = dict(zip(variants, colors_by_n[len(variants)]))

    print(variants)
    print(color_by_variant)
    df["variant_color"] = df["variant"].map(color_by_variant)

    fig = sns.FacetGrid(
        data=df,
        col="location",
        hue="variant",
        col_wrap=4,
        height=4,
        palette=color_by_variant,
        hue_order=variants,
    ).set_axis_labels(
        x_var="Date",
        y_var="Frequency"
    ).set_titles(
        col_template="{col_name}"
    ).tick_params(
        axis="x",
        rotation=45
    )

    # Plot the CIs
    def plot_with_ci(data, **kwargs):
        sns.lineplot(data=data, x="date", y="median", linewidth=2, **kwargs)
        plt.fill_between(data["date"], data["HDI_95_lower"], data["HDI_95_upper"], alpha=0.4, color=kwargs["color"])
    fig.map_dataframe(plot_with_ci)

    # Plot the weekly_raw_freq
    def plot_with_raw(data, **kwargs):
        raw_data = raw[(raw["location"] == data["location"].iloc[0]) & (raw["variant"] == data["variant"].iloc[0])]
        sns.scatterplot(data=raw_data, x="date", y="raw_freq", **kwargs, s=35, alpha = 1.0, legend=False)
    fig.map_dataframe(plot_with_raw)

    fig.add_legend(title="Variants")
    sns.move_legend(
        fig,
        loc="upper right",
        bbox_to_anchor=(1.0, 0.92),
        markerscale=2.25,
    )

    if cases_file:
        cases = pd.read_csv(
            cases_file,
            sep="\t",
            parse_dates=["date"],
        )
        cases = cases[cases["date"] >= df["date"].min()].copy()

        for (i, j, k), facet_df in fig.facet_data():
            if k == 0:
                ax = fig.facet_axis(i, j)
                location = facet_df["location"].drop_duplicates().values[0]
                location_cases = cases[cases["location"] == location].sort_values("date")

                ax2 = ax.twinx()
                ax2.plot(
                    location_cases["date"],
                    location_cases["cases"],
                    color="#CCCCCC",
                    zorder=-100,
                    linestyle="--",
                    linewidth=1.5,
                )

                # Consider smoothing case counts by upsampling to daily values, "forward filling" missing data,
                # and calculating the mean every 2 weeks.
                #mean_location_cases = location_cases.set_index("date").resample("1D").ffill().resample("14D").mean(numeric_only=True).reset_index()

                case_ticks = ax2.get_yticks()
                ax2.set_yticks(
                    [case_ticks.max()],
                    labels=[str(int(case_ticks.max()))],
                )

    # Set logit scale on the y-axis and define ticks
    # Set these at the end, so they apply to every facet
    # Choose 0.005 and 0.92 as y-limits to avoid infinite logit transformations
    fig.set(yscale="logit")
    fig.set(ylim=(0.018, 0.92))
    # Tick locations and labels:
    fig.set(yticks=[0.02, 0.1, 0.2, 0.5, 0.8, 0.9])
    fig.set(yticklabels=["2%", "10%", "20%", "50%", "80%", "90%"])

    # Disable minor ticks entirely
    for ax in fig.axes:
        ax.yaxis.set_minor_locator(mticker.NullLocator())

    fig.figure.subplots_adjust(wspace=0.25)
    sns.despine()

    fig.savefig(output_plot, bbox_inches="tight")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot Freq plots by location and variant.")
    parser.add_argument("-i", "--input_freq", type=str, required=True, help="Parsed MLR site freq TSV file (<model>_freq.tsv)")
    parser.add_argument("-r", "--input_raw", type=str, required=True, help="Path to weekly raw sequence TSV file")
    parser.add_argument("--input_cases", help="Path to case counts per location in a TSV file")
    parser.add_argument("-c", "--colors", type=str, required=True, help="Path to Nextstrain color scheme (configs/color_schemes.tsv)]")
    parser.add_argument("--auspice-config", help="Auspice config JSON with custom colorings for clades defined in a scale")
    parser.add_argument("--coloring-field", default="subclade", help="name of the coloring field in the given Auspice config JSON to use for the color scale")
    parser.add_argument("-ll", "--location_list", required=False, help="Location list TXT file to include in frequency plot")
    parser.add_argument("-vl", "--variant_list", required=False, help="Variant list TXT file to include in frequency plot")
    parser.add_argument("-o", "--output", type=str, required=True, help="Site frequency by location plot PDF")
    args = parser.parse_args()
    plot_freq(args.input_freq, args.input_raw, args.colors, args.output, args.input_cases, args.location_list, args.variant_list, args.auspice_config, args.coloring_field)
