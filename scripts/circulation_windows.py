import numpy as np


def find_extant_window(data, left_buffer=0, right_buffer=0):
    # Reduce the data along the rest of dimensions to see if any entry is non-zero
    reduced_data = np.any(data != 0, axis=tuple(range(2, data.ndim)))

    # Find the first non-zero index for each variable across all groups
    first_non_zero = np.argmax(reduced_data, axis=0)
    # Find the last non-zero index for each variable across all groups
    last_non_zero = (
        reduced_data.shape[0] - np.argmax(reduced_data[::-1], axis=0) - 1
    )

    # Check if any variable is non-zero at every time point
    is_non_zero_everywhere = np.all(reduced_data, axis=0)
    first_non_zero[is_non_zero_everywhere] = 0
    last_non_zero[is_non_zero_everywhere] = data.shape[0] - 1

    # Apply buffers, ensuring indices remain within valid range
    first_index = np.maximum(first_non_zero - left_buffer, 0)
    last_index = np.minimum(last_non_zero + right_buffer, data.shape[0] - 1)

    # Combine and return the indices
    return np.vstack((first_index, last_index)).T


def find_circulating_at_time(data, left_buffer=0, right_buffer=0):
    # Initialize a list to hold lists of variable indices for each time point
    T = data.shape[0]

    # Find windows
    windows = find_extant_window(
        data, left_buffer=left_buffer, right_buffer=right_buffer
    )

    # Initialize a mask array
    mask = np.zeros((T, data.shape[1]), dtype=bool)

    # True where the time point falls within window
    for v, (start, end) in enumerate(windows):
        mask[start : end + 1, v] = True

    # Convert mask to list of indices for each time point
    circulating_at_time = [np.where(mask[t])[0].tolist() for t in range(T)]

    return circulating_at_time, mask


def generate_minimal_windows(circulating_at_time):
    # Initialize variables
    minimal_windows = []
    current_start = 0
    current_vars = set(circulating_at_time[0])

    # Iterate over each time point after the first
    for t in range(1, len(circulating_at_time)):
        new_vars = set(circulating_at_time[t])

        # Check if the current set of variables is different from the new set
        if new_vars != current_vars:
            # If different, end the current window and start a new one
            window_idx = np.arange(current_start, t)
            minimal_windows.append((window_idx, np.array(list(current_vars))))
            current_start = t
            current_vars = new_vars

    # Add the last window
    window_idx = np.arange(current_start, len(circulating_at_time))
    minimal_windows.append((window_idx, np.array(list(current_vars))))

    return minimal_windows
