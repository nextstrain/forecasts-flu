This is the changelog for the Nextstrain forecasts-flu workflow.
All notable changes in a release will be documented in this file.

This changelog is intended for _humans_ and follows many of the principles from [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

Changes for this project _do not_ currently follow the [Semantic Versioning rules](https://semver.org/spec/v2.0.0.html).
Instead, changes appear below grouped by the date they were added to the workflow.

# 13 January 2025

 - Collapse low-count haplotype counts into their parental clades instead of the "other" group. See [#30](https://github.com/nextstrain/forecasts-flu/pull/30) for details.
 - Fix access to dated model results produced before we added support for amino acid haplotypes. See [#28](https://github.com/nextstrain/forecasts-flu/pull/28) for details.

# 23 December 2025

 - Add frequency and fitness estimates for amino acid haplotypes for each subtype and geographic resolution. See [#26](https://github.com/nextstrain/forecasts-flu/pull/26) for details.

# 4 August 2025

 - Enable forecasts for MLR models using a forecast horizon of 6 steps with a frequency estimation interval of 14-days to produce 84-day forecasts. See [#18](https://github.com/nextstrain/forecasts-flu/pull/18) for details.
 - Add `--max-date` option to `run-model.py` script, allowing us to specify the date to use to represent "now". All retrospective frequencies get estimated from this date backward in time at intervals defined by the model config's `aggregation_frequency` (currently 14 days). All forecasts get predicted from this date forward in time at the same intervals. The max date argument can be a specific date in the YYYY-MM-DD format or it can be an ISO-8601 duration before the current date. For example, "14D" specifies a maximum date 14 days before today (or "P14D", to follow the ISO specification precisely). See [#18](https://github.com/nextstrain/forecasts-flu/pull/18) for details.
