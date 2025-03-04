# forecasts-flu

Seasonal influenza variant growth rates and frequency forecast

## Environment setup

1. Create a GitHub token using [this link](https://github.com/settings/tokens/new?description=flu+geo+fitness&scopes=read:packages).
    1. Expiration: 90 days (or however long you expect to be using)
    2. Scroll down and click Generate token
2. Copy the token for the next step.
3. Pull the custom Docker image (replace `<GitHub username>` and `<GitHub token>`)

    ```
    docker login ghcr.io -u <GitHub username> -p <access token>
    docker pull --quiet ghcr.io/blab/flu-geo-fitness:latest
    ```

## Configure the workflow

Edit `config/defaults.yaml` to set the minimum number of total sequences per location to use for modeling, the geographic resolution, date range for analysis, and variant column to use from Nextclade annotations.
Edit the MLR model config per lineage `config/mlr-model/<lineage>.yaml` to define the pivot to use for relative growth advantage calculations.

## Run the workflow

By default, the workflow will run MLR models for all builds defined in `config/defaults.yaml` and plot the inferred frequencies and growth advantages.

```
nextstrain build --docker --image=ghcr.io/blab/flu-geo-fitness:latest .
```

Alternately, you can run the workflow through the creation of MLR model JSONs and upload these JSONs to S3 by specifying an additional configuration file.
Since we only need the custom Docker image for plotting model outputs, we can use the Nextstrain base image in the following command.

```
nextstrain build --docker . \
    --configfile config/defaults.yaml config/optional.yaml
```
