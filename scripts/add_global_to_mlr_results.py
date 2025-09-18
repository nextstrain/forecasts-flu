#!/usr/bin/env python3
# script by Claude Code
"""
Add Global region to MLR results by aggregating regional frequencies using population weights
and copying hierarchical GA values as Global GA values.
"""

import argparse
import json
import pandas as pd
import numpy as np
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-json', required=True,
                        help='Path to input MLR results JSON')
    parser.add_argument('--regional-weights', required=True,
                        help='Path to regional population weights TSV')
    parser.add_argument('--output-json', required=True,
                        help='Path to output MLR results JSON with Global added')
    args = parser.parse_args()

    # Read the MLR results JSON
    with open(args.input_json, 'r') as f:
        mlr_data = json.load(f)

    # Read regional population weights
    weights_df = pd.read_csv(args.regional_weights, sep='\t')

    # Map regional names to match MLR data
    region_name_map = {
        'Africa': 'Africa',
        'Europe': 'Europe',
        'NorthAmerica': 'North America',
        'SouthAmerica': 'South America',
        'SoutheastAsia': 'Southeast Asia',
        'WestAsia': 'West Asia',
        'Oceania': 'Oceania',
        'China': 'China',
        'JapanKorea': 'Japan Korea',
        'SouthAsia': 'South Asia'
    }

    # Apply mapping to weights
    weights_df['mapped_region'] = weights_df['region'].map(region_name_map)

    # Filter to only regions present in the MLR data
    available_regions = [loc for loc in mlr_data['metadata']['location']
                        if loc != 'hierarchical']
    weights_df = weights_df[weights_df['mapped_region'].isin(available_regions)]

    # Normalize weights
    total_weight = weights_df['weight'].sum()
    weights_df['normalized_weight'] = weights_df['weight'] / total_weight

    # Create weight lookup
    weight_lookup = dict(zip(weights_df['mapped_region'], weights_df['normalized_weight']))

    print(f"Using population weights for {len(weight_lookup)} regions:")
    for region, weight in weight_lookup.items():
        print(f"  {region:<20} weight: {weight:.4f}")

    # Add "Global" to metadata locations if not present
    if "Global" not in mlr_data['metadata']['location']:
        mlr_data['metadata']['location'].append("Global")

    # Collect data by site, date, variant, and ps for aggregation
    freq_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    raw_freq_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    freq_forecast_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    # Process existing data to collect regional values
    for record in mlr_data['data']:
        if record['location'] in weight_lookup:
            if record['site'] == 'freq':
                key = (record['date'], record['variant'], record['ps'])
                freq_data[key[0]][key[1]][key[2]][record['location']] = record['value']
            elif record['site'] == 'raw_freq':
                key = (record['date'], record['variant'])
                raw_freq_data[key[0]][key[1]][record['location']] = record['value']
            elif record['site'] == 'freq_forecast':
                key = (record['date'], record['variant'], record['ps'])
                freq_forecast_data[key[0]][key[1]][key[2]][record['location']] = record['value']

    # Create new Global records
    new_global_records = []

    # Aggregate freq data
    for date in freq_data:
        for variant in freq_data[date]:
            for ps in freq_data[date][variant]:
                regional_values = freq_data[date][variant][ps]
                if regional_values:
                    # Calculate weighted average, skipping None values
                    valid_regions = [region for region in regional_values
                                   if region in weight_lookup and regional_values[region] is not None]
                    if valid_regions:
                        weighted_sum = sum(regional_values[region] * weight_lookup[region]
                                         for region in valid_regions)
                        weight_sum = sum(weight_lookup[region] for region in valid_regions)
                        if weight_sum > 0:
                            global_value = weighted_sum / weight_sum
                            new_global_records.append({
                                'location': 'Global',
                                'date': date,
                                'variant': variant,
                                'site': 'freq',
                                'ps': ps,
                                'value': global_value
                            })

    # Aggregate raw_freq data
    for date in raw_freq_data:
        for variant in raw_freq_data[date]:
            regional_values = raw_freq_data[date][variant]
            if regional_values:
                # Calculate weighted average, skipping None values
                valid_regions = [region for region in regional_values
                               if region in weight_lookup and regional_values[region] is not None]
                if valid_regions:
                    weighted_sum = sum(regional_values[region] * weight_lookup[region]
                                     for region in valid_regions)
                    weight_sum = sum(weight_lookup[region] for region in valid_regions)
                    if weight_sum > 0:
                        global_value = weighted_sum / weight_sum
                        new_global_records.append({
                            'location': 'Global',
                            'date': date,
                            'variant': variant,
                            'site': 'raw_freq',
                            'value': global_value
                        })

    # Aggregate freq_forecast data
    for date in freq_forecast_data:
        for variant in freq_forecast_data[date]:
            for ps in freq_forecast_data[date][variant]:
                regional_values = freq_forecast_data[date][variant][ps]
                if regional_values:
                    # Calculate weighted average, skipping None values
                    valid_regions = [region for region in regional_values
                                   if region in weight_lookup and regional_values[region] is not None]
                    if valid_regions:
                        weighted_sum = sum(regional_values[region] * weight_lookup[region]
                                         for region in valid_regions)
                        weight_sum = sum(weight_lookup[region] for region in valid_regions)
                        if weight_sum > 0:
                            global_value = weighted_sum / weight_sum
                            new_global_records.append({
                                'location': 'Global',
                                'date': date,
                                'variant': variant,
                                'site': 'freq_forecast',
                                'ps': ps,
                                'value': global_value
                            })

    # Copy hierarchical GA values as Global GA
    hierarchical_ga_records = [r for r in mlr_data['data']
                               if r['location'] == 'hierarchical' and r['site'] == 'ga']
    for record in hierarchical_ga_records:
        new_record = record.copy()
        new_record['location'] = 'Global'
        new_global_records.append(new_record)

    # For smoothed_raw_freq and agg_counts, we'll create empty/zero records for Global
    # Get unique dates and variants
    dates = mlr_data['metadata']['dates']
    variants = mlr_data['metadata']['variants']

    # Add smoothed_raw_freq records (set to 0 or could aggregate if needed)
    for date in dates:
        for variant in variants:
            new_global_records.append({
                'location': 'Global',
                'date': date,
                'variant': variant,
                'site': 'smoothed_raw_freq',
                'value': 0.0  # Could aggregate these too if needed
            })

    # Add agg_counts records (set to 0 or could aggregate if needed)
    for date in dates:
        for variant in variants:
            new_global_records.append({
                'location': 'Global',
                'date': date,
                'variant': variant,
                'site': 'agg_counts',
                'value': 0  # Could aggregate these too if needed
            })

    # Add all new Global records to the data
    mlr_data['data'].extend(new_global_records)

    # Write output JSON
    with open(args.output_json, 'w') as f:
        json.dump(mlr_data, f, indent=2)

    print(f"\nAdded {len(new_global_records)} Global records to MLR results")
    print(f"Output saved to {args.output_json}")

    # Summary of what was added
    sites_added = defaultdict(int)
    for record in new_global_records:
        sites_added[record['site']] += 1

    print("\nRecords added by site:")
    for site, count in sorted(sites_added.items()):
        print(f"  {site:<20} {count:>6} records")

if __name__ == "__main__":
    main()
