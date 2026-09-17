#!/usr/bin/env python

import argparse
import json

LEVELS = ['data_provenance', 'subtype', 'geography', 'classification', 'dates'];
LATEST = "LATEST"
DISPLAY_NAMES = { # map of names (substrings) in filenames to display names
    "data_provenance": {
        "gisaid": "GISAID",
        "open": "Open data (GenBank)",
    },
    "geography": {
        "country": "Country",
        "region": "Region"
    },
    "subtype": {
        "h1n1pdm": "H1N1pdm",
        "h3n2": "H3N2",
        "vic": "Vic",
    },
    "classification": {
        "emerging_haplotype": "Emerging Haplotypes",
        "aa_haplotype": "Amino Acid Haplotypes",
    },
}


def key_structure(key):
    """
    Parse the S3 key structure, returning a dictionary with values for each
    of the levels as well as the original key (s3 object pathname).
    Returns False if the key doesn't appear to be a valid structure.
    """
    if not key.startswith('files/workflows/forecasts-flu/') \
            or not key.endswith('.json') \
            or key.endswith('/available-datasets.json'):
        return False
    
    parts = key.removeprefix('files/workflows/forecasts-flu/').split('/')

    if parts[0] == 'trial':
        return False
    if parts[0] == 'gisaid':
        # GISAID key structure includes classification next
        data_provenance = parts[0]
        classification = parts[1]
        parts = parts[2:]
    elif parts[0] in ['h3n2', 'h1n1pdm', 'vic', 'yam']:
        # Older style URI paths, see <https://github.com/nextstrain/forecasts-flu/pull/45#issuecomment-5669332379>
        data_provenance = 'gisaid'
        classification = 'emerging_haplotype'
    else:
        print("Unexpected key structure", key)
        return False

    if len(parts)!=4:
        print("Unexpected key structure", key)
        return False

    subtype = parts[0]
    geography = parts[1]

    if parts[3] == 'MLR_results.json':
        date = LATEST
    else:
        date = parts[3].split('_')[0]

    return {
        'data_provenance': data_provenance,
        'subtype': subtype,
        'geography': geography,
        'classification': classification,
        'date': date,
        'key': key,
    }

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and parse MLR-model JSON data")
    parser.add_argument("--s3", required=True, metavar="TXT", 
        help="Object keys (filepaths) from 's3 ls --recursive' ")
    parser.add_argument("--output", required=True, metavar="JSON")
    args = parser.parse_args()    

    datasets = []

    with open(args.s3) as fh:
        for line in fh:
            if structure:=key_structure(line.strip().split()[3]):
                datasets.append(structure)

    output = {
        'datasets': datasets,
        'display_names': DISPLAY_NAMES,
    }

    with open(args.output, 'w') as fh:
        json.dump(output, fh)