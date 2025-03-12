def _get_s3_url(w, input_file):
    s3_dst = config["s3_dst"].rstrip("/")
    s3_path = Path(input_file).relative_to("results")

    # The last part of the path should always be the model name
    while s3_path.stem != "mlr":
        s3_path = s3_path.parent

    return f"{s3_dst}/{s3_path}/"

rule copy_latest_model_results_to_dated:
    input:
        latest_model_results = "results/{lineage}/{geo_resolution}/mlr/MLR_results.json",
    output:
        dated_model_results = "results/{lineage}/{geo_resolution}/mlr/{date}_MLR_results.json",
    shell:
        """
        cp {input.latest_model_results} {output.dated_model_results}
        """

rule upload_dated_model_results_to_s3:
    input:
        model_results = "results/{lineage}/{geo_resolution}/mlr/{date}_MLR_results.json"
    output:
        touch("results/{lineage}/{geo_resolution}/mlr/{date}_results_s3_upload.done")
    params:
        s3_url=lambda w, input: _get_s3_url(w, input.model_results),
    shell:
        """
        ./bin/nextstrain-remote-upload-with-slack-notification \
            --quiet \
            {params.s3_url} \
            {input.model_results}
        """

rule upload_latest_model_results_to_s3:
    input:
        model_results = "results/{lineage}/{geo_resolution}/mlr/MLR_results.json"
    output:
        touch("results/{lineage}/{geo_resolution}/mlr/results_s3_upload.done")
    params:
        s3_url=lambda w, input: _get_s3_url(w, input.model_results),
    shell:
        """
        ./bin/nextstrain-remote-upload-with-slack-notification \
            --quiet \
            {params.s3_url} \
            {input.model_results}
        """
