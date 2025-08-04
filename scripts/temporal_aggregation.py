from collections import deque
import isodate
import pandas as pd


def aggregate_temporally(seq_counts, dates, max_date, frequency):
    """
    Aggregates time-series data based on a specified frequency (e.g., weekly, monthly).

    Parameters:
        - 'seq_counts' (numpy.ndarray): A 2D array where each row corresponds to a time point and columns
        - 'dates' (list of pandas.Timestamp): A list of timestamps corresponding to each row in 'seq_counts'.
        - max_date (pandas.Timestamp): The latest date to use for observed frequency estimation. Aggregated dates get constructed
          backward in time from this date using the given frequency value.
        - frequency (str): A string representing the frequency of aggregation, according to pandas offset aliases.
          Examples include 'W-SUN' for weekly aggregation ending on Sunday, 'M' for monthly.

    Returns:
        - 'seq_counts_agg' (numpy.ndarray): A 2D array where each row corresponds to aggreagted counts
        - 'dates_agg' (list of pandas.Timestamp): A list of timestamps corresponding to each row in 'seq_counts'.
        - 'date_to_index' (dict): A dictionary mapping timestamps to row in 'seq_counts_agg'

    """
    columns_seq_counts = [f"seq_{i}" for i in range(seq_counts.shape[1])]
    df = pd.DataFrame(seq_counts, index=dates, columns=columns_seq_counts)

    # Default frequency is 1 day.
    # Ensure the given frequency is a standard ISO duration with a leading "P".
    if frequency is None:
        frequency = "P1D"
    elif not frequency.startswith("P"):
        frequency = f"P{frequency}"

    # Start calculating dates to estimate frequencies starting from the max date
    # (inclusive), working backwards in time by a time delta that matches the
    # user-requested aggregation frequency. Include the start date in the final
    # dates when the interval spacing allows that date to be included. This
    # approach allows us to specify a fixed latest date regardless of the
    # available data. The pandas's "backward resample" approach accomplishes
    # nearly the same outcome except that approach will use the latest observed
    # date in the given data frame as the latest date bin.
    delta = isodate.parse_duration(frequency)
    min_date = min(dates)
    dates_to_estimate = deque([])
    date_to_estimate = max_date
    while date_to_estimate > min_date:
        dates_to_estimate.appendleft(date_to_estimate)
        date_to_estimate = max_date - delta * len(dates_to_estimate)

    # Always include the earliest observed date at the left of the list of dates
    # to estimate, so the binning with pandas cut can include that earliest
    # record in the next date bin.
    dates_to_estimate.appendleft(min_date)

    # Aggregate each record in the data frame into one of the precalculated date
    # bins with the latest date representing the latest record through to the
    # next earliest date bin. This approach ensures that any given date bin
    # represents the records collected up to that date and not after that date.
    bins = pd.to_datetime(dates_to_estimate)
    date_bin_labels = pd.cut(df.index, bins=bins, labels=bins[1:], include_lowest=True)

    # Grouping the data according to the specified date bin labels.
    grouped = df.groupby(date_bin_labels).sum()

    seq_counts_agg = grouped[columns_seq_counts].values
    dates_agg = list(grouped.index)
    date_to_index = {d: i for (i, d) in enumerate(dates_agg)}
    return seq_counts_agg, dates_agg, date_to_index


def aggregate_temporally_hierarchical(groups, dates, max_date, frequency):
    """
    Applies `aggregate_temporally` to each group within a hierarchical model.
    """

    for group in groups:
        seq_counts, dates_agg, date_to_index = aggregate_temporally(
            group.seq_counts, dates, max_date, frequency
        )
        group.seq_counts = seq_counts
        group.dates = dates_agg
        group.date_to_index = date_to_index

    return groups, dates_agg, date_to_index
