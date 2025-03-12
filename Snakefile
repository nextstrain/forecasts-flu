configfile: "config/defaults.yaml"

wildcard_constraints:
    date = r"\d{4}-\d{2}-\d{2}"

def get_todays_date():
    from datetime import datetime
    date = datetime.today().strftime('%Y-%m-%d')
    return date

run_date = config.get("run_date", get_todays_date())

if config.get("s3_dst"):
    rule upload_all_models:
        input:
            expand("results/{lineage}/{geo_resolution}/mlr/{date}_results_s3_upload.done", lineage=config["lineages"], geo_resolution=config["geo_resolutions"], date=run_date),
            expand("results/{lineage}/{geo_resolution}/mlr/results_s3_upload.done", lineage=config["lineages"], geo_resolution=config["geo_resolutions"])
else:
    rule all:
        input:
            expand("plots/{lineage}/{geo_resolution}/ga/ga_by_variant.png", lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),
            expand("plots/{lineage}/{geo_resolution}/ga/ga_by_location.png", lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),
            expand("plots/{lineage}/{geo_resolution}/freq/freq_by_location.png", lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),

rule all_models:
    input:
        expand("results/{lineage}/{geo_resolution}/mlr/MLR_results.json", lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),

rule download_metadata:
    output:
        "data/{lineage}/metadata.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.lineage]["s3_metadata"]
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule download_nextclade:
    output:
        "data/{lineage}/nextclade.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.lineage]["s3_nextclade"]
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule metadata_with_nextclade:
    input:
        metadata="data/{lineage}/metadata.tsv",
        nextclade="data/{lineage}/nextclade.tsv",
    output:
        metadata="data/{lineage}/metadata_with_nextclade.tsv",
    shell:
        """
        augur merge \
            --metadata metadata={input.metadata} nextclade={input.nextclade} \
            --metadata-id-columns strain seqName \
            --output-metadata {output.metadata}
        """

rule filter_data:
    input:
        metadata="data/{lineage}/metadata_with_nextclade.tsv",
    output:
        metadata="results/{lineage}/{geo_resolution}/metadata_with_nextclade.tsv",
    params:
        min_date=lambda wildcards: config["prepare_data"][wildcards.geo_resolution]["min_date"],
        max_date=lambda wildcards: config["prepare_data"][wildcards.geo_resolution]["max_date"],
    shell:
        """
        augur filter \
            --metadata {input.metadata} \
            --query "(date != '?') & (country != '?') & (region != '?') & (subclade != '') & (\`qc.overallStatus\` == 'good')" \
            --min-date {params.min_date:q} \
            --max-date {params.max_date:q} \
            --output-metadata {output.metadata}
        """

rule update_metadata:
    input:
        metadata="results/{lineage}/{geo_resolution}/metadata_with_nextclade.tsv",
        mapping="config/{lineage}_mapping.tsv",
    output:
        metadata="results/{lineage}/{geo_resolution}/metadata_with_nextclade_updated.tsv"
    params:
        variant_column=config["variant"],
    shell:
        """
        python scripts/update-metadata.py \
            --input-metadata {input.metadata} \
            --input-mapping {input.mapping} \
            --variant-column {params.variant_column} \
            --output {output.metadata}
        """

rule clade_seq_counts:
    input:
        metadata="results/{lineage}/{geo_resolution}/metadata_with_nextclade_updated.tsv",
    output:
        sequence_counts="results/{lineage}/{geo_resolution}/seq_counts.tsv",
    params:
        id_column="strain",
        date_column="date",
        variant_column=config["variant"],
    shell:
        """
        ./scripts/summarize-clade-sequence-counts \
            --metadata {input.metadata} \
            --id-column {params.id_column:q} \
            --date-column {params.date_column:q} \
            --location-column {wildcards.geo_resolution:q} \
            --clade-column {params.variant_column:q} \
            --output {output.sequence_counts}
            """

rule prepare_clade_data:
    """Preparing clade counts for analysis"""
    input:
        sequence_counts = "results/{lineage}/{geo_resolution}/seq_counts.tsv"
    output:
        sequence_counts = "results/{lineage}/{geo_resolution}/prepared_seq_counts.tsv"
    params:
        min_date=lambda wildcards: config["prepare_data"][wildcards.geo_resolution]["min_date"],
        location_min_seq=lambda wildcards: config["prepare_data"][wildcards.geo_resolution]["location_min_seq"],
        clade_min_seq=lambda wildcards: config["prepare_data"][wildcards.geo_resolution]["clade_min_seq"],
    shell:
        """
        python ./scripts/prepare-data.py \
            --seq-counts {input.sequence_counts} \
            --min-date {params.min_date} \
            --location-min-seq {params.location_min_seq} \
            --clade-min-seq {params.clade_min_seq} \
            --output-seq-counts {output.sequence_counts}
        """

rule mlr_model:
    input:
        counts="results/{lineage}/{geo_resolution}/prepared_seq_counts.tsv",
        config="config/mlr/{lineage}.yaml",
    output:
        model="results/{lineage}/{geo_resolution}/mlr/MLR_results.json",
    params:
        run="MLR",
        path="results/{lineage}/{geo_resolution}/mlr/",
    benchmark:
        "results/{lineage}/{geo_resolution}/mlr/mlr-model_benchmark.tsv"
    resources:
        mem_mb=3000,
    shell:
        """
        python -u ./scripts/run-model.py \
            --seq-path {input.counts} \
            --config {input.config} \
            --data-name {params.run} \
            --export-path {params.path}
        """

rule parse_mlr_json:
    input:
        model="results/{lineage}/{geo_resolution}/mlr/MLR_results.json",
    output:
        ga="results/{lineage}/{geo_resolution}/mlr/ga.tsv",
        freq="results/{lineage}/{geo_resolution}/mlr/freq.tsv",
        emp="results/{lineage}/{geo_resolution}/mlr/raw_freq.tsv",
    params:
        version="MLR",
    shell:
        """
        python3 scripts/parse-json.py \
            --input {input.model} \
            --outga {output.ga} \
            --outfreq {output.freq} \
            --outraw {output.emp} \
            --model {params.version}
        """

rule get_pivot:
    input:
        config="config/mlr/{lineage}.yaml"
    output:
        "results/{lineage}/{geo_resolution}/pivot.txt"
    shell:
        """
        python3 scripts/get_pivot.py \
            --input {input.config} \
            --output {output}
        """

rule download_auspice_config_json:
    output:
        config="results/{lineage}/auspice_config.json",
    shell:
        """
        curl \
            -o {output.config} \
            -L \
            'https://raw.githubusercontent.com/nextstrain/seasonal-flu/master/profiles/nextflu-private/{wildcards.lineage}/ha/auspice_config.json'
        """

rule plot_freq:
    input:
        freq_data="results/{lineage}/{geo_resolution}/mlr/freq.tsv",
        raw_data="results/{lineage}/{geo_resolution}/mlr/raw_freq.tsv",
        color_scheme="config/color_schemes.tsv",
        auspice_config="results/{lineage}/auspice_config.json"
    output:
        variant="plots/{lineage}/{geo_resolution}/freq/freq_by_location.png"
    params:
        coloring_field=config["coloring_field"],
    shell:
        """
        python3 ./scripts/plot-freq.py \
            --input_freq {input.freq_data} \
            --input_raw {input.raw_data} \
            --colors {input.color_scheme} \
            --auspice-config {input.auspice_config} \
            --coloring-field {params.coloring_field} \
            --output {output.variant}
        """

rule plot_ga:
    input:
        ga="results/{lineage}/{geo_resolution}/mlr/ga.tsv",
        color_scheme="config/color_schemes.tsv",
        pivot="results/{lineage}/{geo_resolution}/pivot.txt",
        auspice_config="results/{lineage}/auspice_config.json"
    output:
        variant="plots/{lineage}/{geo_resolution}/ga/ga_by_variant.png",
        location="plots/{lineage}/{geo_resolution}/ga/ga_by_location.png",
    params:
        coloring_field=config["coloring_field"],
    shell:
        """
        python3 ./scripts/plot-ga.py \
            --input_ga {input.ga} \
            --virus {wildcards.lineage} \
            --colors {input.color_scheme} \
            --out_variant {output.variant} \
            --out_location {output.location} \
            --pivot {input.pivot} \
            --auspice-config {input.auspice_config} \
            --coloring-field {params.coloring_field}
        """

if config.get("s3_dst"):
    include: "workflow/upload.smk"
