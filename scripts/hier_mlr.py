from functools import partial
from typing import Optional
import numpy as np
from jax import vmap
import jax.numpy as jnp
from jax.nn import softmax

import numpyro
import numpyro.distributions as dist
from numpyro.infer.reparam import TransformReparam

from evofr import ModelSpec
from evofr import MultinomialLogisticRegression
import circulation_windows

def hier_MLR_numpyro(
    seq_counts,
    N,
    X,
    circulating_at_time,
    circulating_periods,
    circulation_mask,
    tau=None,
    pool_scale=None,
    pred=False,
    var_names=None,
    windowed=False,
    simple_exclusion=False,
):
    _, N_variants, N_groups = seq_counts.shape
    _, N_features, _ = X.shape

    pool_scale = 0.1 if pool_scale is None else pool_scale

    # Sampling intercept and fitness parameters
    reparam_config = {
        "beta_loc": TransformReparam(),
        "beta_scale": TransformReparam(),
        "alpha": TransformReparam(),
        "raw_beta": TransformReparam(),
    }
    with numpyro.handlers.reparam(config=reparam_config):
        beta_scale = numpyro.sample(
            "beta_scale",
            dist.TransformedDistribution(
                dist.HalfNormal(1.0),
                dist.transforms.AffineTransform(0.0, pool_scale),
            ),
        )
        with numpyro.plate("variants", N_variants - 1, dim=-2):
            # Define loc and scale for fitness beta
            beta_loc = numpyro.sample(
                "beta_loc",
                dist.TransformedDistribution(
                    dist.Normal(0.0, 1.0),
                    dist.transforms.AffineTransform(0.0, 0.2),
                ),
            )

            # Use location and scale parameter to draw within group
            with numpyro.plate("group", N_groups, dim=-1):
                # Leave intercept alpha unpooled
                raw_alpha = numpyro.sample(
                    "alpha",
                    dist.TransformedDistribution(
                        dist.Normal(0.0, 1.0),
                        dist.transforms.AffineTransform(0.0, 6.0),
                    ),
                )
                raw_beta = numpyro.sample(
                    "raw_beta",
                    dist.TransformedDistribution(
                        dist.Normal(0.0, 1.0),
                        dist.transforms.AffineTransform(beta_loc, beta_scale),
                    ),
                )

    # All parameters are relative to last column / variant
    beta = numpyro.deterministic(
        "beta",
        jnp.concatenate(
            (
                jnp.stack((raw_alpha, raw_beta)),
                jnp.zeros((N_features, 1, N_groups)),
            ),
            axis=1,
        ),
    )

    # (T, F, G) times (F, V, G) -> (T, V, G)
    dot_by_group = vmap(jnp.dot, in_axes=(-1, -1), out_axes=-1)
    logits = dot_by_group(X, beta)  # Logit frequencies by variant

    if windowed:
        freq = jnp.zeros_like(logits)
        seq_counts_gen = jnp.zeros_like(logits)

        # Evaluate likelihood
        obs = None if pred else np.nan_to_num(seq_counts)
        for p, (t, circulating) in enumerate(circulating_periods):
            _logits = logits[t[:, None], circulating, :]
            _seq_counts = numpyro.sample(
                f"_seq_counts_{p}",
                dist.MultinomialLogits(
                    logits=_logits.swapaxes(1, 2),
                    total_count=np.nan_to_num(N[t, :]),
                ),
                obs=None
                if pred
                else obs[t[:, None], circulating, :].swapaxes(1, 2),
            )

            freq = freq.at[t[:, None], circulating, :].set(
                softmax(_logits, axis=1)
            )
            seq_counts_gen = seq_counts_gen.at[t[:, None], circulating, :].set(
                jnp.swapaxes(_seq_counts, 1, 2)
            )
    elif simple_exclusion:
        logits = logits.at[~circulation_mask, :].set(-10)
        freq = jnp.full_like(logits, jnp.nan)
        seq_counts_gen = jnp.zeros_like(logits)

        # Evaluate likelihood
        obs = None if pred else np.nan_to_num(seq_counts)
        _seq_counts = numpyro.sample(
            "_seq_counts",
            dist.MultinomialLogits(
                logits=logits.swapaxes(1, 2), total_count=np.nan_to_num(N)
            ),
            obs=None if pred else obs.swapaxes(1, 2),
        )

        freq = softmax(logits, axis=1)
        seq_counts_gen = jnp.swapaxes(_seq_counts, 1, 2)
    else:
        # Evaluate likelihood
        obs = None if pred else np.swapaxes(np.nan_to_num(seq_counts), 1, 2)

        _seq_counts = numpyro.sample(
            "_seq_counts",
            dist.MultinomialLogits(
                logits=jnp.swapaxes(logits, 1, 2), total_count=np.nan_to_num(N)
            ),
            obs=obs,
        )

        # Re-ordering so groups are last
        seq_counts_gen = jnp.swapaxes(_seq_counts, 1, 2)
        freq = softmax(logits, axis=1)

    # Compute frequency
    numpyro.deterministic("freq", freq)
    numpyro.deterministic("seq_counts", seq_counts_gen)

    # Compute growth advantage from model
    if tau is not None:
        numpyro.deterministic(
            "ga", jnp.exp(beta[-1, :-1, :] * tau)
        )  # Last row corresponds to linear predictor / growth advantage
        numpyro.deterministic("ga_loc", jnp.exp(beta_loc[:, 0] * tau))


class HierMLR(ModelSpec):
    def __init__(
        self,
        tau: float,
        pool_scale: Optional[float] = None,
        left_buffer: Optional[int] = None,
        right_buffer: Optional[int] = None,
        windowed: bool = False,
        simple_exclusion: bool = False,
    ) -> None:
        """Construct ModelSpec for Hierarchial multinomial logistic regression.

        Parameters
        ----------
        tau:
            Assumed generation time for conversion to relative R.

        pool_scale:
            Prior standard deviation for pooling of growth advantages.

        left_buffer:
            Time points preceeding first observation to include variant in.

        right_buffer:
            Time points proceeding last observation to include variant in.

        Returns
        -------
        HierMLR
        """
        self.tau = tau  # Fixed generation time
        self.pool_scale = pool_scale  # Prior std for coefficients
        self.model_fn = partial(hier_MLR_numpyro, pool_scale=self.pool_scale)
        self.left_buffer = left_buffer if left_buffer is not None else 0
        self.right_buffer = right_buffer if right_buffer is not None else 0
        self.windowed = windowed
        self.simple_exclusion = simple_exclusion

    @staticmethod
    def make_ols_feature(start, stop, n_groups):
        """
        Construct simple OLS features (1, x) for HierMLR as nd.array.

        Parameters
        ----------
        start:
            Start value for OLS feature.
        stop:
            Stop value for OLS feature.

        n_groups:
            number of groups in the hierarchical model.
        """
        X_flat = MultinomialLogisticRegression.make_ols_feature(start, stop)
        return np.stack([X_flat] * n_groups, axis=-1)

    def augment_data(self, data: dict) -> None:
        T, G = data["N"].shape
        data["tau"] = self.tau
        data["X"] = self.make_ols_feature(0, T, G)
        (
            data["circulating_at_time"],
            data["circulation_mask"],
        ) = circulation_windows.find_circulating_at_time(
            data["seq_counts"], self.left_buffer, self.right_buffer
        )
        data["circulating_periods"] = circulation_windows.generate_minimal_windows(
            data["circulating_at_time"]
        )
        data["windowed"] = self.windowed
        data["simple_exclusion"] = self.simple_exclusion

    @staticmethod
    def forecast_frequencies(samples, forecast_L):
        """
        Use posterior beta to forecast posterior frequencies.
        """

        # Making feature matrix for forecasting
        last_T = samples["freq"].shape[1]
        n_groups = samples["freq"].shape[-1]

        X = HierMLR.make_ols_feature(
            start=last_T, stop=last_T + forecast_L, n_groups=n_groups
        )

        # (T, F, G) times (F, V, G) -> (T, V, G)
        dot_by_group = vmap(jnp.dot, in_axes=(-1, -1), out_axes=-1)
        dbg_by_sample = vmap(dot_by_group, in_axes=(None, 0), out_axes=0)

        # Creating frequencies from posterior beta
        beta = jnp.array(samples["beta"])
        logits = dbg_by_sample(X, beta)
        samples["freq_forecast"] = softmax(logits, axis=-2)  # (S, T, V, G)
        return samples
