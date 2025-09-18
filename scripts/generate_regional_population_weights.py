#!/usr/bin/env python3
# script by Claude Code
"""
Generate regional population weights by aggregating country populations
according to the geo_regions mapping from nextstrain/seasonal-flu.
"""

import pandas as pd
import sys

def main():
    # Download and read the geo_regions mapping
    geo_regions_url = "https://raw.githubusercontent.com/nextstrain/seasonal-flu/master/config/geo_regions.tsv"
    geo_regions = pd.read_csv(geo_regions_url, sep='\t')

    # Download and read the population weights
    population_url = "https://raw.githubusercontent.com/nextstrain/ncov/master/defaults/population_weights.tsv"
    population_weights = pd.read_csv(population_url, sep='\t', comment='#')

    # Standardize column names for merging
    geo_regions.columns = ['country', 'region']
    population_weights.columns = ['country', 'weight']

    # Merge the dataframes
    merged = pd.merge(geo_regions, population_weights, on='country', how='left')

    # Check for countries without population data
    missing_pop = merged[merged['weight'].isna()]
    if not missing_pop.empty:
        print("Warning: Countries without population data:", file=sys.stderr)
        for _, row in missing_pop.iterrows():
            print(f"  {row['country']} ({row['region']})", file=sys.stderr)
        print(file=sys.stderr)

    # Remove rows with missing population data
    merged = merged.dropna(subset=['weight'])

    # Aggregate by region
    regional_weights = merged.groupby('region')['weight'].sum().reset_index()
    regional_weights.columns = ['region', 'weight']

    # Sort by region name
    regional_weights = regional_weights.sort_values('region')

    # Save to TSV
    output_path = "config/regional_population_weights.tsv"
    regional_weights.to_csv(output_path, sep='\t', index=False)
    print(f"Regional population weights saved to {output_path}")

    # Print summary statistics
    print("\nRegional Population Weights Summary:")
    print("-" * 50)
    total_pop = regional_weights['weight'].sum()
    for _, row in regional_weights.iterrows():
        percentage = (row['weight'] / total_pop) * 100
        # Convert weight to millions for readability
        pop_millions = row['weight'] / 1000
        print(f"{row['region']:<20} {pop_millions:>10.1f}M ({percentage:>5.1f}%)")
    print("-" * 50)
    print(f"{'Total':<20} {total_pop/1000:>10.1f}M (100.0%)")

    # Also check which regions from the results are present
    expected_regions = ['Africa', 'Europe', 'North America', 'Oceania',
                       'South America', 'Southeast Asia', 'West Asia']

    print("\nRegions in current workflow:")
    for region in expected_regions:
        # Map display names to actual region names in geo_regions.tsv
        region_map = {
            'North America': 'NorthAmerica',
            'South America': 'SouthAmerica',
            'Southeast Asia': 'SoutheastAsia',
            'West Asia': 'WestAsia'
        }
        actual_region = region_map.get(region, region)

        if actual_region in regional_weights['region'].values:
            weight = regional_weights[regional_weights['region'] == actual_region]['weight'].iloc[0]
            print(f"  ✓ {region:<20} (population: {weight/1000:.1f}M)")
        else:
            print(f"  ✗ {region:<20} (NOT FOUND in geo_regions)")

if __name__ == "__main__":
    main()
