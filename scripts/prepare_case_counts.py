#!/usr/bin/env python3
import argparse
import pandas as pd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--cases", required=True, help="CSV file of case counts from FluNet")
    parser.add_argument("--country-mapping", required=True, help="TSV file mapping FluNet country names (column 1) to Nextstrain country names (column 2)")
    parser.add_argument("--lineage", choices=["h1n1pdm", "h3n2", "vic"], required=True, help="lineage for which cases should be prepared")
    parser.add_argument("--output", required=True, help="TSV of case counts for requested lineage")
    args = parser.parse_args()

    flunet_country_to_nextstrain_country = dict(
        pd.read_csv(
            args.country_mapping,
            sep="\t",
        ).loc[
            :,
            ["flunet_country", "nextstrain_country"]
        ].values
    )

    lineage_by_case_column = {
        "AH1N12009": "h1n1pdm",
        "AH3": "h3n2",
        "INF_B": "vic",
    }
    case_column_by_lineage = {
        lineage: case_column
        for case_column, lineage in lineage_by_case_column.items()
    }

    case_columns = [case_column_by_lineage[args.lineage]]
    columns = [
        "COUNTRY_AREA_TERRITORY",
        "ISO_WEEKSTARTDATE",
    ] + case_columns

    df = pd.read_csv(
        args.cases,
        usecols=columns,
        parse_dates=["ISO_WEEKSTARTDATE"],
    ).rename(columns={
        "COUNTRY_AREA_TERRITORY": "country",
        "ISO_WEEKSTARTDATE": "date",
    })

    for column in case_columns:
        df[column] = df[column].fillna(0).astype(int)

    df = df.rename(columns=lineage_by_case_column)

    lineage_df = df.melt(
        id_vars=["country", "date"],
        value_vars=[args.lineage],
        var_name="lineage",
        value_name="cases",
    ).groupby([
        "lineage",
        "country",
        "date",
    ])["cases"].sum().reset_index()

    case_countries = set(lineage_df["country"].drop_duplicates().values)
    nextstrain_countries = set(flunet_country_to_nextstrain_country.keys())
    missing_countries = case_countries - nextstrain_countries
    if len(missing_countries) > 0:
        print("Missing the following countries:")
        print(missing_countries)

        with open("missing_countries.tsv", "w", encoding="utf-8") as oh:
            for country in missing_countries:
                print(f"{country}\t{country}", file=oh)

    lineage_df = lineage_df[lineage_df["country"].isin(flunet_country_to_nextstrain_country.keys())].copy()
    lineage_df["country"] = lineage_df["country"].map(flunet_country_to_nextstrain_country)

    lineage_df = lineage_df.groupby([
        "country",
        "date",
    ])["cases"].sum().reset_index().rename(columns={"country": "location"})

    lineage_df.to_csv(
        args.output,
        index=False,
        sep="\t",
    )
