configfile: "config/defaults.yaml"

rule all:
    input:
        expand("plots/{build_name}/ga/ga_by_variant.png", build_name=list(config["builds"].keys())),
        expand("plots/{build_name}/ga/ga_by_location.png", build_name=list(config["builds"].keys())),
        expand("plots/{build_name}/freq/freq_by_location.png", build_name=list(config["builds"].keys())),

rule all_models:
    input:
        expand("results/{build_name}/mlr/MLR_results.json", build_name=list(config["builds"].keys())),

rule download_metadata:
    output:
        "data/{virus}/metadata.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.virus]["s3_metadata"]
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule download_nextclade:
    output:
        "data/{virus}/nextclade.tsv",
    params:
        s3_path=lambda wildcards: config["data"][wildcards.virus]["s3_nextclade"]
    shell:
        """
        aws s3 cp {params.s3_path} - | xz -c -d > {output}
        """

rule metadata_with_nextclade:
    input:
        metadata="data/{virus}/metadata.tsv",
        nextclade="data/{virus}/nextclade.tsv",
    output:
        metadata="data/{virus}/metadata_with_nextclade.tsv",
    shell:
        """
        augur merge \
            --metadata metadata={input.metadata} nextclade={input.nextclade} \
            --metadata-id-columns strain seqName \
            --output-metadata {output.metadata}
        """

rule filter_data:
    input:
        metadata=lambda wildcards: f"data/{config['builds'][wildcards.build_name]['virus']}/metadata_with_nextclade.tsv",
    output:
        metadata="results/{build_name}/metadata_with_nextclade.tsv",
    params:
        min_date=lambda wildcards: config["builds"][wildcards.build_name]["min_date"],
        max_date=lambda wildcards: config["builds"][wildcards.build_name]["max_date"],
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
        metadata="results/{build_name}/metadata_with_nextclade.tsv",
        mapping="config/{build_name}_mapping.tsv",
    output:
        metadata="results/{build_name}/metadata_with_nextclade_updated.tsv"
    shell:
        """
        python scripts/update-metadata.py \
            --input-metadata {input.metadata} \
            --input-mapping {input.mapping} \
            --output {output.metadata}
        """

rule clade_seq_counts:
    input:
        metadata="results/{build_name}/metadata_with_nextclade_updated.tsv",
    output:
        counts="results/{build_name}/variant_seq_counts.tsv",
    params:
        id_column="strain",
        date_column="date",
        variant_column=lambda wildcards: config["builds"][wildcards.build_name]["variant"],
        location_column=lambda wildcards: config["builds"][wildcards.build_name]["location"],
    shell:
        """
        ./scripts/summarize-clade-sequence-counts \
            --metadata {input.metadata} \
            --id-column {params.id_column:q} \
            --date-column {params.date_column:q} \
            --location-column {params.location_column:q} \
            --clade-column {params.variant_column:q} \
            --output /dev/stdout \
            | csvtk rename -t -f clade -n variant > {output.counts}
            """

rule get_location:
    input:
        counts="results/{build_name}/variant_seq_counts.tsv",
    output:
        locations="results/{build_name}/location.lst",
    params:
        threshold=lambda wildcards: config["builds"][wildcards.build_name]["threshold"],
    shell:
        """
        python3 scripts/get_location.py \
            --input_seqs {input.counts} \
            --threshold {params.threshold} \
            --output {output.locations}
        """

rule filter_location:
    input:
        counts="results/{build_name}/variant_seq_counts.tsv",
        location="results/{build_name}/location.lst",
    output:
        counts="results/{build_name}/variant_seq_counts_subloc.tsv",
    shell:
        """
        tsv-join -H -k location -f {input.location} {input.counts} > {output.counts}
        """

rule mlr_model:
    input:
        counts="results/{build_name}/variant_seq_counts_subloc.tsv",
        config="config/mlr/{build_name}.yaml",
    output:
        model="results/{build_name}/mlr/MLR_results.json",
    params:
        run="MLR",
        path="results/{build_name}/mlr/",
    benchmark:
        "results/{build_name}/mlr/mlr-model_benchmark.tsv"
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
        model="results/{build_name}/mlr/MLR_results.json",
    output:
        ga="results/{build_name}/mlr/ga.tsv",
        freq="results/{build_name}/mlr/freq.tsv",
        emp="results/{build_name}/raw_freq.tsv",
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
        config="config/mlr/{build_name}.yaml"
    output:
        "results/{build_name}/pivot.txt"
    shell:
        """
        python3 scripts/get_pivot.py \
            --input {input.config} \
            --output {output}
        """

rule download_auspice_config_json:
    output:
        config="results/{build_name}/auspice_config.json",
    params:
        lineage=lambda wildcards: config["builds"][wildcards.build_name]["virus"],
    shell:
        """
        curl \
            -o {output.config} \
            -L \
            'https://raw.githubusercontent.com/nextstrain/seasonal-flu/master/profiles/nextflu-private/{params.lineage}/ha/auspice_config.json'
        """

rule download_cases:
    output:
        cases="results/cases.csv",
    shell:
        """
        curl -o {output.cases} -L 'https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv'
        """

rule prepare_cases:
    input:
        cases="results/cases.csv",
        country_mapping="config/flunet_to_nextstrain_country.tsv",
    output:
        cases="results/{build_name}/cases.tsv",
    params:
        lineage=lambda wildcards: config["builds"][wildcards.build_name]["virus"],
    shell:
        """
        python3 scripts/prepare_case_counts.py \
            --cases {input.cases} \
            --country-mapping {input.country_mapping} \
            --lineage {params.lineage:q} \
            --output {output.cases}
        """

rule get_location_to_plot:
    input:
        locations="results/{build_name}/location.lst",
    output:
        locations="results/{build_name}/locations_to_plot.lst",
    params:
        total_locations=8,
    shell:
        """
        echo "location" > {output.locations};
        sed 1d {input.locations} | head -n {params.total_locations} >> {output.locations}
        """

rule plot_freq:
    input:
        freq_data="results/{build_name}/mlr/freq.tsv",
        raw_data="results/{build_name}/raw_freq.tsv",
        color_scheme="config/color_schemes.tsv",
        auspice_config="results/{build_name}/auspice_config.json",
        loc_lst="results/{build_name}/locations_to_plot.lst",
    output:
        variant="plots/{build_name}/freq/freq_by_location.png"
    params:
        coloring_field=lambda wildcards: config["builds"][wildcards.build_name]["coloring_field"],
    shell:
        """
        python3 ./scripts/plot-freq.py \
            --input_freq {input.freq_data} \
            --input_raw {input.raw_data} \
            --colors {input.color_scheme} \
            --location_list {input.loc_lst} \
            --auspice-config {input.auspice_config} \
            --coloring-field {params.coloring_field} \
            --output {output.variant}
        """

rule plot_ga:
    input:
        ga="results/{build_name}/mlr/ga.tsv",
        color_scheme="config/color_schemes.tsv",
        pivot="results/{build_name}/pivot.txt",
        auspice_config="results/{build_name}/auspice_config.json",
        loc_lst="results/{build_name}/locations_to_plot.lst",
        var_lst=lambda wildcards: config["builds"][wildcards.build_name]["var_lst"],
    output:
        variant="plots/{build_name}/ga/ga_by_variant.png",
        location="plots/{build_name}/ga/ga_by_location.png",
    params:
        virus=lambda wildcards: config["builds"][wildcards.build_name]["virus"],
        coloring_field=lambda wildcards: config["builds"][wildcards.build_name]["coloring_field"],
    shell:
        """
        python3 ./scripts/plot-ga.py \
            --input_ga {input.ga} \
            --virus {params.virus} \
            --colors {input.color_scheme} \
            --out_variant {output.variant} \
            --out_location {output.location} \
            --location_list {input.loc_lst} \
            --variant_list {input.var_lst} \
            --pivot {input.pivot} \
            --auspice-config {input.auspice_config} \
            --coloring-field {params.coloring_field}
        """
