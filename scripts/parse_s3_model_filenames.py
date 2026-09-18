#!/usr/bin/env python

import argparse
import json
from collections import defaultdict

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

def _stringify_structure(structure):
    """Uses the hierarchy levels only"""
    return f"{structure['data_provenance']}|{structure['subtype']}|{structure['geography']}|" + \
        f"{structure['classification']}|{structure['date']}";

def deduplicate(elements):
    """
    Multiple s3 keys may produce the same hierarchy values, i.e. have a collision when
    passed through `_stringify_structure()`.
    Here we return the input list with any such collisions de-duplicated, by examining
    the "deprecated_key_syntax" boolean. If this can't decide for us we raise an error.
    Returned elements have this key stripped.
    """
    store = defaultdict(list)
    for idx,el in enumerate(elements):
        store[_stringify_structure(el)].append(idx)
    deduped = []
    for key,element_indexes in store.items():
        if len(element_indexes)>1:
            current_indexes = [idx for idx in element_indexes if elements[idx]['deprecated_key_syntax'] is False]
            if len(current_indexes) != 1:
                raise Exception(f"Unexpected duplicates for {key} which cannot be resoved by S3 key syntax")
            valid_idx = current_indexes[0]
        else:
            valid_idx = element_indexes[0]
        deduped.append({k:v for k,v in elements[valid_idx].items() if k!='deprecated_key_syntax'})
    return deduped
    

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
        deprecated_key_syntax = False
    elif parts[0] in ['h3n2', 'h1n1pdm', 'vic', 'yam']:
        # Older style URI paths, see <https://github.com/nextstrain/forecasts-flu/pull/45#issuecomment-5669332379>
        data_provenance = 'gisaid'
        classification = 'emerging_haplotype'
        deprecated_key_syntax = True
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
        'deprecated_key_syntax': deprecated_key_syntax,
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

    datasets = deduplicate(datasets)

    output = {
        'datasets': datasets,
        'display_names': DISPLAY_NAMES,
    }

    with open(args.output, 'w') as fh:
        json.dump(output, fh)