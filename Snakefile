configfile: "config/defaults.yaml"

wildcard_constraints:
    data_provenance=r"(gisaid)",
    variant_classification=r"(emerging_haplotype|aa_haplotype)",
    lineage=r"(h1n1pdm|h3n2|vic)",
    date=r"\d{4}-\d{2}-\d{2}"

def get_todays_date():
    from datetime import datetime
    date = datetime.today().strftime('%Y-%m-%d')
    return date

run_date = config.get("run_date", get_todays_date())

if config.get("s3_dst"):
    rule upload_all_models:
        input:
            expand("results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/{date}_results_s3_upload.done", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"], date=run_date),
            expand("results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/results_s3_upload.done", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"])
else:
    rule all:
        input:
            expand("plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/ga/ga_by_variant.png", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),
            expand("plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/ga/ga_by_location.png", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),
            expand("plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/freq/freq_by_location.png", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),

rule all_models:
    input:
        expand("results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/MLR_results.json", data_provenance=config["data_provenances"], variant_classification=config["variant_classifications"], lineage=config["lineages"], geo_resolution=config["geo_resolutions"]),

rule download_metadata:
    output:
        "data/{data_provenance}/{lineage}/metadata.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.data_provenance][wildcards.lineage]["s3_metadata"],
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule download_nextclade:
    output:
        "data/{data_provenance}/{lineage}/nextclade.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.data_provenance][wildcards.lineage]["s3_nextclade"],
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule download_haplotype_definitions:
    output:
        haplotypes="data/nextstrain/{lineage}/haplotype_definitions.tsv",
    shell:
        """
        curl \
            -o {output.haplotypes} \
            -L \
            'https://raw.githubusercontent.com/nextstrain/seasonal-flu/refs/heads/master/config/{wildcards.lineage}/ha/emerging_haplotypes.tsv'
        """

rule metadata_with_nextclade:
    input:
        metadata="data/{data_provenance}/{lineage}/metadata.tsv",
        nextclade="data/{data_provenance}/{lineage}/nextclade.tsv",
    output:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade.tsv",
    shell:
        """
        augur merge \
            --metadata metadata={input.metadata} nextclade={input.nextclade} \
            --metadata-id-columns strain seqName \
            --output-metadata {output.metadata}
        """

rule filter_data:
    input:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade.tsv",
    output:
        metadata="data/{data_provenance}/{lineage}/filtered_metadata_with_nextclade.tsv",
    params:
        min_date=lambda wildcards: config["min_date"],
        max_date=lambda wildcards: config["max_date"],
    shell:
        """
        augur filter \
            --metadata {input.metadata} \
            --query "(date != '?') & (country != '?') & (region != '?') & (subclade != '') & (\`qc.overallStatus\` == 'good')" \
            --min-date {params.min_date:q} \
            --max-date {params.max_date:q} \
            --output-metadata {output.metadata}
        """

rule assign_emerging_haplotypes:
    input:
        metadata="data/{data_provenance}/{lineage}/filtered_metadata_with_nextclade.tsv",
        haplotypes="data/nextstrain/{lineage}/haplotype_definitions.tsv",
    output:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade_with_emerging_haplotypes.tsv",
    params:
        variant_column=config["haplotype_variant_column"],
        haplotype_column_name="emerging_haplotype",
        default_haplotype="other",
    shell:
        """
        python scripts/assign_haplotypes.py \
            --substitutions {input.metadata} \
            --haplotypes {input.haplotypes} \
            --clade-column {params.variant_column:q} \
            --haplotype-column-name {params.haplotype_column_name:q} \
            --default-haplotype {params.default_haplotype:q} \
            --output-table {output.metadata}
        """

rule assign_aa_haplotypes:
    input:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade_with_emerging_haplotypes.tsv",
    output:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade_with_aa_haplotypes.tsv",
    params:
        genes=["HA1"],
        clade_column=config["haplotype_variant_column"],
        mutations_column=config["mutations_column"],
        haplotype_column_name="aa_haplotype",
    shell:
        r"""
        python3 scripts/assign_aa_haplotypes.py \
            --nextclade {input.metadata:q} \
            --genes {params.genes:q} \
            --strip-genes \
            --clade-column {params.clade_column:q} \
            --mutations-column {params.mutations_column:q} \
            --attribute-name {params.haplotype_column_name:q} \
            --output {output.metadata:q}
        """

rule clade_seq_counts:
    input:
        metadata="data/{data_provenance}/{lineage}/metadata_with_nextclade_with_aa_haplotypes.tsv",
    output:
        sequence_counts="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/seq_counts.tsv",
    params:
        id_column="strain",
        date_column="date",
    shell:
        """
        ./scripts/summarize-clade-sequence-counts \
            --metadata {input.metadata} \
            --id-column {params.id_column:q} \
            --date-column {params.date_column:q} \
            --location-column {wildcards.geo_resolution:q} \
            --clade-column {wildcards.variant_classification:q} \
            --output {output.sequence_counts}
            """

rule collapse_haplotype_counts:
    input:
        sequence_counts = "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/seq_counts.tsv"
    output:
        sequence_counts = "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/collapsed_seq_counts.tsv"
    params:
        haplotype_min_seq=lambda wildcards: config["prepare_data"][wildcards.data_provenance][wildcards.variant_classification][wildcards.geo_resolution]["clade_min_seq"],
    shell:
        """
        python ./scripts/collapse_haplotype_counts.py \
            --seq-counts {input.sequence_counts} \
            --haplotype-min-seq {params.haplotype_min_seq} \
            --output-seq-counts {output.sequence_counts}
        """

rule prepare_clade_data:
    """Preparing clade counts for analysis"""
    input:
        sequence_counts = "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/collapsed_seq_counts.tsv"
    output:
        sequence_counts = "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/prepared_seq_counts.tsv"
    params:
        min_date=lambda wildcards: config["min_date"],
        location_min_seq=lambda wildcards: config["prepare_data"][wildcards.data_provenance][wildcards.variant_classification][wildcards.geo_resolution]["location_min_seq"],
        clade_min_seq=lambda wildcards: config["prepare_data"][wildcards.data_provenance][wildcards.variant_classification][wildcards.geo_resolution]["clade_min_seq"],
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
        counts="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/prepared_seq_counts.tsv",
        config="config/mlr/{lineage}.yaml",
    output:
        model="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/initial_MLR_results.json",
    params:
        data_name="initial_MLR",
        path=subpath(output.model, parent=True),
        max_date=config["max_date"],
    benchmark:
        "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/mlr-model_benchmark.tsv"
    resources:
        mem_mb=3000,
    shell:
        """
        python -u ./scripts/run-model.py \
            --seq-path {input.counts} \
            --config {input.config} \
            --data-name {params.data_name} \
            --export-path {params.path} \
            --max-date {params.max_date:q}
        """

rule add_colors_to_mlr_model:
    input:
        model="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/initial_MLR_results.json",
        auspice_config="data/nextstrain/{lineage}/auspice_config.json",
        color_schemes="config/color_schemes.tsv",
    output:
        model="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/MLR_results.json",
    shell:
        r"""
        python scripts/add_colors_to_model.py \
            --model {input.model:q} \
            --auspice-config {input.auspice_config:q} \
            --color-schemes {input.color_schemes:q} \
            --coloring-field {wildcards.variant_classification:q} \
            --output {output.model:q}
        """

rule parse_mlr_json:
    input:
        model="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/MLR_results.json",
    output:
        ga="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/ga.tsv",
        freq="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/freq.tsv",
        emp="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/raw_freq.tsv",
        freq_forecast="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/freq_forecast.tsv",
    params:
        version="MLR",
    shell:
        """
        python3 scripts/parse-json.py \
            --input {input.model} \
            --outga {output.ga} \
            --outfreq {output.freq} \
            --outraw {output.emp} \
            --outfreqforecast {output.freq_forecast} \
            --model {params.version}
        """

rule get_pivot:
    input:
        config="config/mlr/{lineage}.yaml"
    output:
        "results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/pivot.txt"
    shell:
        """
        python3 scripts/get_pivot.py \
            --input {input.config} \
            --output {output}
        """

rule download_auspice_config_json:
    output:
        config="data/nextstrain/{lineage}/auspice_config.json",
    shell:
        """
        curl \
            -o {output.config} \
            -L \
            'https://raw.githubusercontent.com/nextstrain/seasonal-flu/refs/heads/master/profiles/nextflu-private/{wildcards.lineage}/ha/auspice_config.json'
        """

rule plot_freq:
    input:
        freq_data="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/freq.tsv",
        raw_data="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/raw_freq.tsv",
        color_scheme="config/color_schemes.tsv",
        auspice_config="data/nextstrain/{lineage}/auspice_config.json",
    output:
        variant="plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/freq/freq_by_location.png",
    params:
        auspice_config_arg=lambda wildcards, input: f"--auspice-config {input.auspice_config}" if wildcards.variant_classification == "emerging_haplotype" else "",
    shell:
        """
        python3 ./scripts/plot-freq.py \
            --input_freq {input.freq_data} \
            --input_raw {input.raw_data} \
            --colors {input.color_scheme} \
            {params.auspice_config_arg} \
            --coloring-field {wildcards.variant_classification} \
            --output {output.variant}
        """

rule plot_ga:
    input:
        ga="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/mlr/ga.tsv",
        color_scheme="config/color_schemes.tsv",
        pivot="results/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/pivot.txt",
        auspice_config="data/nextstrain/{lineage}/auspice_config.json"
    output:
        variant="plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/ga/ga_by_variant.png",
        location="plots/{data_provenance}/{variant_classification}/{lineage}/{geo_resolution}/ga/ga_by_location.png",
    params:
        auspice_config_arg=lambda wildcards, input: f"--auspice-config {input.auspice_config}" if wildcards.variant_classification == "emerging_haplotype" else "",
    shell:
        """
        python3 ./scripts/plot-ga.py \
            --input_ga {input.ga} \
            --virus {wildcards.lineage} \
            --colors {input.color_scheme} \
            --out_variant {output.variant} \
            --out_location {output.location} \
            --pivot {input.pivot} \
            {params.auspice_config_arg} \
            --coloring-field {wildcards.variant_classification}
        """

if config.get("s3_dst"):
    include: "workflow/upload.smk"
