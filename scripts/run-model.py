#!/usr/bin/env python
# coding: utf-8


import argparse
import numpy as np
import pandas as pd
import os
import yaml
import evofr as ef
from datetime import date
import hier_frequencies
import hier_mlr

from hier_frequencies import HierFrequencies
from hier_mlr import HierMLR

from latent_immunity_relative_fitness import RelativeFitnessDR
from latent_immunity_relative_fitness import LatentSplineRW

def parse_with_default(cf, var, dflt):
    if var in cf:
        return cf[var]
    else:
        print(f"Using default value for {var}")
        return dflt

def parse_generation_time(cf_m):
    tau = parse_with_default(cf_m, "generation_time", 4.8)
    return tau

def parse_pool_scale(cf_m):
    pool_scale = parse_with_default(cf_m, "pool_scale", 0.1)
    return pool_scale

class NUTS_from_MAP:
    def __init__(self, num_warmup, num_samples, iters, lr):
        self.num_warmup = num_warmup
        self.num_samples = num_samples
        self.iters = iters
        self.lr = lr

    def fit(self, model, data, name=None):
        init_strat, _ = ef.init_to_MAP(model, data, iters=self.iters, lr=self.lr)
        inference_method = ef.InferNUTS(
            num_warmup=self.num_warmup,
            num_samples=self.num_samples,
            init_strategy=init_strat,
            dense_mass=True,
        )
        return inference_method.fit(model, data, name=name)


def parse_inference_method(method_name, lr, iters, num_warmup, num_samples):
    if method_name == "FullRank":
        method = ef.InferFullRank(lr=lr, iters=iters, num_samples=num_samples)
    elif method_name == "MAP":
        method = ef.InferMAP(lr=lr, iters=iters)
    elif method_name == "NUTS":
        method = NUTS_from_MAP(
            num_warmup=num_warmup, num_samples=num_samples, iters=iters, lr=lr
        )
    else:  # Default is full rank
        method = ef.InferFullRank(lr=lr, iters=iters, num_samples=num_samples)
    return method


class ModelConfig:
    def __init__(self, path):
        self.path = path
        self.config = self.read_config(path)

    def read_config(self, path):
        with open(path, "r") as file:
            config = yaml.safe_load(file)
        return config

    def load_data(self, override_seq_path=None):
        data_cf = self.config["data"]

        # Load sequence count data
        seq_path = override_seq_path or data_cf["seq_path"]
        if seq_path.endswith(".tsv"):
            raw_seq = pd.read_csv(seq_path, sep="\t")
        else:
            raw_seq = pd.read_csv(seq_path)

        # Load locations
        if "locations" in data_cf:
            locations = data_cf["locations"]
        else:
            # Check if raw_seq has location column
            locations = pd.unique(raw_seq["location"])

        return raw_seq, locations

    def load_model(self, override_hier=None):
        model_cf = self.config["model"]

        # Processing generation time
        tau = parse_generation_time(model_cf)
        hier = parse_with_default(model_cf, "hierarchical", dflt=False)
        left_buffer = parse_with_default(model_cf, "left_buffer", dflt=0)
        right_buffer = parse_with_default(model_cf, "right_buffer", dflt=0)
        windowed = parse_with_default(model_cf, "windowed", dflt=False)
        simple_exclusion = parse_with_default(model_cf, "simple_exclusion", dflt=False)
        if override_hier is not None:
            hier = override_hier

        # Check which model to run
        models_avail = ["MLR", "Latent"]
        version = parse_with_default(model_cf, "version", dflt="MLR")
        if version not in models_avail:
            raise Exception(f"The model choice is not currently supported. Choose to run Model version 'MLR' or 'Latent'.")

        print("hierarchical:", hier)

        # Processing likelihoods
        if hier:
            if version == "MLR":
                print("Running hier MLR model")
                ps = parse_pool_scale(model_cf)
                print("Hierarchical pool scale:", ps)
                left_buffer = parse_with_default(model_cf, "left_buffer", dflt=0)
                right_buffer = parse_with_default(model_cf, "right_buffer", dflt=0)
                model = hier_mlr.HierMLR(
                    tau=tau,
                    pool_scale=ps,
                    left_buffer=left_buffer,
                    right_buffer=right_buffer,
                    windowed=windowed,
                    simple_exclusion=simple_exclusion,
                )
            elif version == "Latent":
                print("Running hier Latent model")
                order = parse_with_default(model_cf, "order", dflt=6)
                k = parse_with_default(model_cf, "k", dflt=4)
                phi_model = LatentSplineRW(ef.Spline(order=order, k=k))
                latent_dim = parse_with_default(model_cf, "latent_dim", dflt=4)
                model = RelativeFitnessDR(dim=latent_dim, phi_model=phi_model, tau=tau, hier=True)
        else:
            if version == "MLR":
                print("Running MLR model")
                left_buffer = parse_with_default(model_cf, "left_buffer", dflt=0)
                right_buffer = parse_with_default(model_cf, "right_buffer", dflt=0)
                model = ef.MultinomialLogisticRegression(tau=tau)
            elif version == "Latent":
                print("Running Latent model")
                phi_model = LatentSplineRW(ef.Spline(order=order, k=k))
                latent_dim = parse_with_default(model_cf, "latent_dim", dflt=4)
                model = RelativeFitnessDR(dim=latent_dim, hier=False)
        return model, hier

    def load_optim(self):
        infer_cf = self.config["inference"]
        lr = float(parse_with_default(infer_cf, "lr", dflt=1e-2))
        iters = int(parse_with_default(infer_cf, "iters", dflt=50000))
        num_warmup = int(parse_with_default(infer_cf, "num_warmup", dflt=500))
        num_samples = int(
            parse_with_default(infer_cf, "num_samples", dflt=1500)
        )

        method_name = parse_with_default(infer_cf, "method", dflt="FullRank")
        inference_method = parse_inference_method(
            method_name, lr, iters, num_warmup, num_samples
        )
        return inference_method

    def load_settings(self, override_export_path=None):
        settings_cf = self.config["settings"]
        fit = parse_with_default(settings_cf, "fit", dflt=False)
        save = parse_with_default(settings_cf, "save", dflt=False)
        load = parse_with_default(settings_cf, "load", dflt=False)
        export_json = parse_with_default(
            settings_cf, "export_json", dflt=False
        )
        export_path = override_export_path or parse_with_default(
            settings_cf, "export_path", dflt=None
        )
        return fit, save, load, export_json, export_path


def fit_models(rs, locations, model, inference_method, hier, path, save, pivot=None, aggregation_frequency=None):
    multi_posterior = ef.MultiPosterior()

    if hier:
        # Subset data to locations of interest
        raw_seq = rs[rs.location.isin(locations)]
        data = hier_frequencies.HierFrequencies(raw_seq=raw_seq, pivot=pivot, group="location", aggregation_frequency=aggregation_frequency)

        # Fit model
        posterior = inference_method.fit(model, data, name="hierarchical")

        multi_posterior.add_posterior(posterior=posterior)

        if save:
            posterior.save_posterior(f"{path}/models/hierarchical.json")
    else:
        for location in locations:
            # Subset to data of interest
            raw_seq = rs[rs.location == location].copy()

            # Check to see if location available
            if len(raw_seq) == 0:
                print(f"Location {location} not in data")
                continue

            data = ef.VariantFrequencies(raw_seq=raw_seq, pivot=pivot)

            # Fit model
            posterior = inference_method.fit(model, data, name=location)

            # Add posterior to group
            multi_posterior.add_posterior(posterior=posterior)

            # if save, save
            if save:
                posterior.save_posterior(f"{path}/models/{location}.json")

    return multi_posterior


def load_models(rs, locations, model, path=None):
    multi_posterior = ef.MultiPosterior()

    for location in locations:
        # Subset to data of interest
        raw_seq = rs[rs.location == location].copy()
        data = ef.VariantFrequencies(raw_seq=raw_seq)

        # Load samples
        posterior = ef.PosteriorHandler(data=data, name=location)
        posterior.load_posterior(f"{path}/models/{location}.json")

        # Add posterior to group
        multi_posterior.add_posterior(posterior=posterior)

    return multi_posterior


def make_path_if_absent(path):
    dirname = os.getcwd()
    file_path = os.path.join(dirname, path)
    if not os.path.exists(file_path):
        os.makedirs(file_path)
        print(f"{path} created.")
    return None


def make_model_directories(path):
    make_path_if_absent(path)
    make_path_if_absent(path + "/models")


def make_raw_freq_tidy(data, location):
    # Unpack HierFrequencies
    variants = data.var_names
    date_map = data.date_to_index

    # Calculate raw frequencies
    raw_freq = data.seq_counts / data.seq_counts.sum(axis=1)[:, None]

    # agg_counts
    agg_counts = data.seq_counts

    # Calculate the 7-day moving sum for each of the clades
    kernel = np.ones(7)  # 7-day window
    numerator = np.apply_along_axis(lambda x: np.convolve(x, kernel, mode='same'), axis=0, arr=data.seq_counts)

    # Calculate the 7-day moving sum for the total count across all clades (Denominator)
    total_counts = data.seq_counts.sum(axis=1)
    denominator = np.convolve(total_counts, kernel, mode='same')

    # Calculate the 7-day smoothed daily frequency
    smoothed_raw_freq = numerator / denominator[:, None]

    # Create metadata
    metadata = {
        "dates": data.dates,
        "variants": data.var_names,
        "sites": ["raw_freq", "smoothed_raw_freq", "agg_counts"],
        "location": [location]
    }

    # Tidy entries
    entries = []
    for v, variant in enumerate(variants):
        for day, d in date_map.items():
            entries.append({
                "location": location,
                "site": "raw_freq",
                "variant": variant,
                "date": day.strftime("%Y-%m-%d"),
                "value": (
                    None
                    if np.isnan(raw_freq[d, v])
                    else np.around(raw_freq[d, v], decimals=3))
            })
            entries.append({
                "location": location,
                "site": "smoothed_raw_freq",
                "variant": variant,
                "date": day.strftime("%Y-%m-%d"),
                "value": (
                    None
                    if np.isnan(smoothed_raw_freq[d, v])
                    else np.around(smoothed_raw_freq[d, v], decimals=3))
            })

            entries.append({
                "location": location,
                "site": "agg_counts",
                "variant": variant,
                "date": day.strftime("%Y-%m-%d"),
                "value": None if np.isnan(agg_counts[d, v])
                    else int(agg_counts[d, v])})

    return {"metadata": metadata, "data": entries}

# export results MLR model (with GA)
def export_results_mlr(multi_posterior, ps, path, data_name, hier):
    EXPORT_SITES = ["freq", "ga"]
    EXPORT_DATED = [True, False]
    EXPORT_FORECASTS = [False, False]
    EXPORT_ATTRS = ["pivot"]

    # Make directories
    make_model_directories(path)

    # Split hierarchical results into group posteriors
    if hier:
        def get_group_samples(samples, sites, group):
            samples_group = dict()
            for site in sites:
                samples_group[site] = samples[site][..., group]
            return samples_group

        mp = multi_posterior
        hier_posterior = mp.locator["hierarchical"]
        hier_samples = hier_posterior.samples
        hier_data = hier_posterior.data
        multi_posterior = ef.MultiPosterior()
        for n, name in enumerate(hier_data.names):
            hier_data.groups[n].dates = hier_data.dates
            multi_posterior.add_posterior(
                 ef.PosteriorHandler(
                    samples=get_group_samples(hier_samples, EXPORT_SITES, n),
                    data=hier_data.groups[n],
                    name=name)
            )
        # Add final posterior for hierarchical growth advantages
        multi_posterior.add_posterior(
            ef.PosteriorHandler(
                samples={"ga": hier_samples["ga_loc"]},
                data=hier_data,
                name="hierarchical")
        )

    # Combine jsons from multiple model runs
    results = []
    for location, posterior in multi_posterior.locator.items():
        if location == "hierarchical":
            results.append(
                ef.posterior.get_sites_variants_tidy(
                    posterior.samples,
                    posterior.data,
                    ["ga"],
                    [False],
                    [False],
                    ps,
                    location
                )
            )
        else:
            results.append(
                ef.posterior.get_sites_variants_tidy(
                    posterior.samples,
                    posterior.data,
                    EXPORT_SITES,
                    EXPORT_DATED,
                    EXPORT_FORECASTS,
                    ps,
                    location,
                )
            )

    # Add raw frequencies
    for location, posterior in multi_posterior.locator.items():
        if location != "hierarchical":
            results.append(
                make_raw_freq_tidy(posterior.data, location)
            )

    results = ef.posterior.combine_sites_tidy(results)
    results["metadata"]["updated"] = pd.to_datetime(date.today())
    ef.save_json(results, path=f"{path}/{data_name}_results.json")

# Export results Latent model (without GA)
# Eventually add relative fitness (RF) where we have GA for MLR
def export_results_latent(multi_posterior, ps, path, data_name, hier):
    EXPORT_SITES = ["freq", "delta", "ga"]
    EXPORT_DATED = [True, True, True]
    EXPORT_FORECASTS = [False, False, False]
    EXPORT_ATTRS = ["pivot"]

    # Make directories
    make_model_directories(path)

    # Split hierarchical results into group posteriors
    if hier:
        def get_group_samples(samples, sites, group):
            samples_group = dict()
            for site in sites:
                samples_group[site] = samples[site][..., group]
            return samples_group

        mp = multi_posterior
        hier_posterior = mp.locator["hierarchical"]
        hier_samples = hier_posterior.samples
        hier_data = hier_posterior.data
        multi_posterior = ef.MultiPosterior()
        for n, name in enumerate(hier_data.names):
            hier_data.groups[n].dates = hier_data.dates
            multi_posterior.add_posterior(
                 ef.PosteriorHandler(
                    samples=get_group_samples(hier_samples, EXPORT_SITES, n),
                    data=hier_data.groups[n],
                    name=name)
            )

    # Combine jsons from multiple model runs
    results = []
    for location, posterior in multi_posterior.locator.items():
        if location == "hierarchical":
            results.append(
                ef.posterior.get_sites_variants_tidy(
                    posterior.samples,
                    posterior.data
                    [False],
                    [False],
                    ps,
                    location
                )
            )
        else:
            results.append(
                ef.posterior.get_sites_variants_tidy(
                    posterior.samples,
                    posterior.data,
                    EXPORT_SITES,
                    EXPORT_DATED,
                    EXPORT_FORECASTS,
                    ps,
                    location,
                )
            )

    # Add raw frequencies
    for location, posterior in multi_posterior.locator.items():
        if location != "hierarchical":
            results.append(
                make_raw_freq_tidy(posterior.data, location)
            )

    results = ef.posterior.combine_sites_tidy(results)
    results["metadata"]["updated"] = pd.to_datetime(date.today())
    ef.save_json(results, path=f"{path}/{data_name}_results.json")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Estimating variant growth rates."
    )
    parser.add_argument("--config", help="path to config file")
    parser.add_argument(
        "--seq-path",
        help="File path to sequence data. Overrides data.seq_path in config.",
    )
    parser.add_argument(
        "--export-path",
        help="Path to export directory. Overrides settings.export_path in config.",
    )
    parser.add_argument(
        "--data-name",
        help="Name of the data set to include in the results filename as <data_name>_results.json. "
        + "Overrides data.name in config.",
    )
    parser.add_argument(
        "--pivot",
        help="Variant to use as pivot. Overrides model.pivot in config.",
    )

    parser.add_argument(
        "--hier",  action='store_true', default=False,
        help="Whether to run the model as hierarchical. Overrides model.hierarchical in config. "
        + "Default is false if unspecified."
    )
    args = parser.parse_args()

    # Load configuration, data, and create model
    config = ModelConfig(args.config)
    print(f"Config loaded: {config.path}")

    raw_seq, locations = config.load_data(args.seq_path)
    print("Data loaded sucessfuly")

    override_hier = None
    if args.hier:
        override_hier = args.hier

    mlr_model, hier = config.load_model(override_hier=override_hier)
    print("Model created.")

    inference_method = config.load_optim()
    print("Inference method defined.")

    fit, save, load, export_json, export_path = config.load_settings(
        args.export_path
    )
    print("Settings loaded")

    # Find export path
    if export_path:
        make_model_directories(export_path)

    # Find pivot
    # Use mlr config pivot unless a dataset-specific pivot is specified
    pivot = None
    if config.config["model"]["pivot"]:
        pivot = config.config["model"]["pivot"]
    if args.pivot and args.pivot != "None":
        pivot = args.pivot
    print("pivot", pivot)

    # Find aggregation_frequency
    aggregation_frequency = None
    if config.config["data"]["aggregation_frequency"]:
        aggregation_frequency = config.config["data"]["aggregation_frequency"]

    # Fit or load model results
    if fit:
        print("Fitting model")
        multi_posterior = fit_models(
            raw_seq,
            locations,
            mlr_model,
            inference_method,
            hier,
            export_path,
            save,
            pivot=pivot,
            aggregation_frequency=aggregation_frequency
        )
    elif load:
        print("Loading results")
        multi_posterior = load_models(
            raw_seq,
            locations,
            mlr_model,
            export_path,
        )
    else:
        print("No models fit or results loaded.")
        multi_posterior = ef.MultiPosterior()

    # Export results
    if export_json and (fit or load):
        print(f"Exporting results as .json at {export_path}")
        ps = parse_with_default(
            config.config["settings"], "ps", dflt=[0.5, 0.8, 0.95]
        )
        data_name = args.data_name or config.config["data"]["name"]
        if config.config["model"]["version"] == "MLR":
            export_results_mlr(multi_posterior, ps, export_path, data_name, hier)
        elif config.config["model"]["version"] == "Latent":
            export_results_latent(multi_posterior, ps, export_path, data_name, hier)
