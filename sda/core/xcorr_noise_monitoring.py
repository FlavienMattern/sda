import os
import warnings

import h5py
import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore")


def load_h5_dvv(filename):
    return dvv_object(filename)


def stack_to_dict(stack_group):
    time = pd.Timestamp("1970-01-01") + pd.to_timedelta(np.asarray(stack_group["time"][:]), unit="D")
    time = time.strftime("%Y-%m-%d").tolist()
    lag_bounds = np.asarray(stack_group["lag_bounds"][:], dtype=np.float32)
    lag_labels = [f"{lag_min:.2f}_{lag_max:.2f}s" for lag_min, lag_max in lag_bounds]
    components = [value.decode() if isinstance(value, bytes) else value for value in stack_group["components"][:]]

    result = {}
    for comp_idx, comp in enumerate(components):
        result[comp] = {}

        for lag_idx, lag_label in enumerate(lag_labels):
            dvv = stack_group["dvv"][:, lag_idx, comp_idx].astype(np.float32)
            coherence = stack_group["coherence"][:, lag_idx, comp_idx].astype(np.float32)
            error = stack_group["error"][:, lag_idx, comp_idx].astype(np.float32)

            if np.all(np.isnan(dvv)) and np.all(np.isnan(coherence)) and np.all(np.isnan(error)):
                continue

            result[comp][lag_label] = {
                "time": time,
                "dvv": dvv.tolist(),
                "coherence": coherence.tolist(),
                "error": error.tolist(),
            }

    return result


def save_dvv_results(h5_file, results):
    time_origin = np.datetime64("1970-01-01")
    parameters = ["dvv", "coherence", "error"]

    h5_file.attrs["layout"] = "data/<method>/<frequency>/<stack>/{time,lag_bounds,components,dvv,coherence,error}"

    metadata_group = h5_file.require_group("metadata")
    for key in list(metadata_group.keys()):
        del metadata_group[key]
    metadata_group.attrs["sta1"] = results["metadata"]["sta1"]
    metadata_group.attrs["sta2"] = results["metadata"]["sta2"]
    metadata_group.attrs["time_origin"] = str(time_origin)
    metadata_group.attrs["time_units"] = "days"
    metadata_group.attrs["lag_units"] = "seconds"
    metadata_group.attrs["matrix_order"] = "time,lag,component"
    metadata_group.attrs["storage"] = "float32"

    data_group = h5_file.require_group("data")

    for method, method_dict in results["data"].items():
        method_group = data_group.require_group(method)

        for frequency, frequency_dict in method_dict.items():
            frequency_group = method_group.require_group(frequency)

            for stack, new_stack_dict in frequency_dict.items():
                stack_dict = {}
                if stack in frequency_group:
                    stack_dict = stack_to_dict(frequency_group[stack])

                if np.any([comp != "avg" for comp in new_stack_dict.keys()]):
                    stack_dict.pop("avg", None)

                for comp, comp_dict in new_stack_dict.items():
                    stack_dict.setdefault(comp, {})

                    for lag_label, lag_values in comp_dict.items():
                        merged = {}

                        if lag_label in stack_dict[comp]:
                            old_values = stack_dict[comp][lag_label]
                            for time_value, dvv, coherence, error in zip(
                                old_values["time"],
                                old_values["dvv"],
                                old_values["coherence"],
                                old_values["error"],
                            ):
                                merged[time_value] = {
                                    "dvv": dvv,
                                    "coherence": coherence,
                                    "error": error,
                                }

                        for time_value, dvv, coherence, error in zip(
                            lag_values["time"],
                            lag_values["dvv"],
                            lag_values["coherence"],
                            lag_values["error"],
                        ):
                            merged[time_value] = {
                                "dvv": dvv,
                                "coherence": coherence,
                                "error": error,
                            }

                        time = sorted(merged.keys())
                        stack_dict[comp][lag_label] = {
                            "time": time,
                            "dvv": [merged[time_value]["dvv"] for time_value in time],
                            "coherence": [merged[time_value]["coherence"] for time_value in time],
                            "error": [merged[time_value]["error"] for time_value in time],
                        }

                if len(stack_dict) == 0:
                    continue

                components = sorted([comp for comp in stack_dict.keys() if comp != "avg"])
                if "avg" in stack_dict:
                    components.append("avg")

                lag_labels = sorted(
                    {
                        lag_label
                        for comp in components
                        for lag_label in stack_dict[comp].keys()
                    },
                    key=lambda lag_label: tuple(float(value) for value in lag_label[:-1].split("_")),
                )

                time = sorted(
                    {
                        time_value
                        for comp in components
                        for lag_values in stack_dict[comp].values()
                        for time_value in lag_values["time"]
                    }
                )

                time_index = {time_value: idx for idx, time_value in enumerate(time)}
                lag_index = {lag_label: idx for idx, lag_label in enumerate(lag_labels)}
                component_index = {comp: idx for idx, comp in enumerate(components)}

                values = {
                    param: np.full((len(time), len(lag_labels), len(components)), np.nan, dtype=np.float32)
                    for param in parameters
                }

                for comp, comp_dict in stack_dict.items():
                    comp_idx = component_index[comp]

                    for lag_label, lag_values in comp_dict.items():
                        lag_idx = lag_index[lag_label]

                        for time_value, dvv, coherence, error in zip(
                            lag_values["time"],
                            lag_values["dvv"],
                            lag_values["coherence"],
                            lag_values["error"],
                        ):
                            time_idx = time_index[time_value]
                            values["dvv"][time_idx, lag_idx, comp_idx] = dvv
                            values["coherence"][time_idx, lag_idx, comp_idx] = coherence
                            values["error"][time_idx, lag_idx, comp_idx] = error

                if stack in frequency_group:
                    del frequency_group[stack]
                stack_group = frequency_group.create_group(stack)

                time_days = (np.array(time, dtype="datetime64[D]") - time_origin).astype(np.int32)
                lag_bounds = np.array(
                    [[float(value) for value in lag_label[:-1].split("_")] for lag_label in lag_labels],
                    dtype=np.float32,
                )

                stack_group.attrs["matrix_order"] = "time,lag,component"

                time_dataset = stack_group.create_dataset(
                    "time",
                    data=time_days,
                    compression="gzip",
                    compression_opts=9,
                    shuffle=True,
                )
                time_dataset.attrs["units"] = f"days since {time_origin}"

                lag_dataset = stack_group.create_dataset(
                    "lag_bounds",
                    data=lag_bounds,
                    compression="gzip",
                    compression_opts=9,
                    shuffle=True,
                )
                lag_dataset.attrs["units"] = "seconds"
                lag_dataset.attrs["columns"] = "lag_min,lag_max"

                stack_group.create_dataset("components", data=np.array(components, dtype=h5py.string_dtype()))

                for param in parameters:
                    stack_group.create_dataset(
                        param,
                        data=values[param],
                        compression="gzip",
                        compression_opts=9,
                        shuffle=True,
                    )


class dvv_object:
    def __init__(self, filename):
        self.filename = filename

        with h5py.File(filename, "r") as f:
            self.metadata = {
                key: value.decode() if isinstance(value, bytes) else value
                for key, value in f["metadata"].attrs.items()
            }

        self.sta1 = self.metadata["sta1"]
        self.sta2 = self.metadata["sta2"]

    def get_metadata(self):
        return self.metadata

    def get_alldata(self):
        result = {}

        with h5py.File(self.filename, "r") as f:
            for method, method_group in f["data"].items():
                result[method] = {}

                for frequency, frequency_group in method_group.items():
                    result[method][frequency] = {}

                    for stack, stack_group in frequency_group.items():
                        result[method][frequency][stack] = stack_to_dict(stack_group)

        return result

    def get_data(self, method, frequency, stack, comp, lagtime=None, param=None, avg_sides=True):
        if isinstance(frequency, tuple) or isinstance(frequency, list):
            frequency = f"{frequency[0]:.3f}-{frequency[1]:.3f}Hz"

        if isinstance(stack, int):
            stack = f"{stack:03d}days"

        if isinstance(lagtime, tuple) or isinstance(lagtime, list):
            lagtime = "_".join([f"{lag:.2f}" for lag in lagtime]) + "s"

        with h5py.File(self.filename, "r") as f:
            data = stack_to_dict(f["data"][method][frequency][stack])[comp]

        if lagtime is None and param is None:
            cols = ["dvv", "coherence", "error"]
            df = pd.concat(
                [
                    pd.DataFrame(
                        {key: value for key, value in values.items() if key != "time"},
                        index=pd.to_datetime(values["time"]),
                    )
                    .reindex(columns=cols)
                    .set_axis(pd.MultiIndex.from_product([[lag], cols]), axis=1)
                    for lag, values in data.items()
                ],
                axis=1,
            )
            if len(df.columns) != 0 and not isinstance(df.columns, pd.MultiIndex):
                df.columns = pd.MultiIndex.from_tuples(df.columns)

            if avg_sides:
                lags = [
                    (float(elt.split("_")[0]), float(elt.split("_")[1][:-1]))
                    for elt in list(dict.fromkeys(df.columns.get_level_values(0)))
                    if elt[0] != "-"
                ]
                lags.sort()
                new_df = pd.DataFrame(index=df.index)

                for lagmin, lagmax in lags:
                    lag_causal = f"{lagmin:.2f}_{lagmax:.2f}s"
                    lag_acausal = f"{-lagmax:.2f}_{-lagmin:.2f}s"

                    if lag_acausal not in df.columns.get_level_values(0):
                        sub_df = df[lag_causal].copy()
                        sub_df.columns = pd.MultiIndex.from_product([[lag_causal], sub_df.columns])
                        new_df = pd.concat([new_df, sub_df], axis=1)
                        continue

                    coh_causal = df[(lag_causal, "coherence")].to_numpy(dtype=float)
                    coh_acausal = df[(lag_acausal, "coherence")].to_numpy(dtype=float)
                    err_causal = df[(lag_causal, "error")].to_numpy(dtype=float)
                    err_acausal = df[(lag_acausal, "error")].to_numpy(dtype=float)
                    dvv_causal = df[(lag_causal, "dvv")].to_numpy(dtype=float)
                    dvv_acausal = df[(lag_acausal, "dvv")].to_numpy(dtype=float)

                    weight_sum = np.nansum(np.vstack([coh_causal, coh_acausal]), axis=0)
                    dvv_sum = np.nansum(np.vstack([dvv_causal * coh_causal, dvv_acausal * coh_acausal]), axis=0)
                    dvv_avg = np.full_like(weight_sum, np.nan, dtype=float)
                    valid = weight_sum != 0
                    dvv_avg[valid] = dvv_sum[valid] / weight_sum[valid]

                    sub_df = pd.DataFrame(
                        {
                            (lag_causal, "dvv"): dvv_avg,
                            (lag_causal, "coherence"): np.nanmean(np.vstack([coh_causal, coh_acausal]), axis=0),
                            (lag_causal, "error"): np.nanmean(np.vstack([err_causal, err_acausal]), axis=0),
                        },
                        index=df.index,
                    )

                    new_df = pd.concat([new_df, sub_df], axis=1)

                if len(new_df.columns) != 0 and not isinstance(new_df.columns, pd.MultiIndex):
                    new_df.columns = pd.MultiIndex.from_tuples(new_df.columns)
                return new_df

            return df

        if lagtime is None and param is not None:
            return pd.concat(
                [
                    pd.DataFrame(values[param], index=pd.to_datetime(values["time"]), columns=[lag])
                    for lag, values in data.items()
                ],
                axis=1,
            )

        if lagtime is not None and param is None:
            df = pd.DataFrame(data[lagtime])
            df.set_index("time", inplace=True)
            df.set_index(pd.to_datetime(df.index), inplace=True)
            return df

        time = data[lagtime]["time"]
        return pd.DataFrame(data[lagtime][param], columns=[param], index=pd.to_datetime(time))

    def __repr__(self):
        text = "┏━━━   dv/v object   ━━━┓\n"
        text += f"┃  {f'{self.sta1} - {self.sta2}':^20} ┃ \n"
        text += "┣━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━  Possible actions  ━━━━━┓\n"
        text += "┃ <obj>.get_metadata() # Get metadata                                ┃\n"
        text += "┃ <obj>.get_alldata()  # Get all dataset (raw format)                ┃\n"
        text += "┃ <obj>.get_data()     # Formatted dataset for given parameters      ┃\n"
        text += "┃                        (see table below)                           ┃\n"
        text += "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        text += "                          DATASETS AVAILABLE\n\n"
        text += "┏━━━ method ━━━┳━━━ frequency ━━━┳━━ stack ━━┳━ comp ━┳━ lagtime ━━ •••\n"
        text += "┃              ┃                 ┃           ┃        ┃\n"

        with h5py.File(self.filename, "r") as f:
            for method, method_group in f["data"].items():
                for frequency, frequency_group in method_group.items():
                    for stack, stack_group in frequency_group.items():
                        for comp, comp_dict in stack_to_dict(stack_group).items():
                            lags = " • ".join(comp_dict.keys())
                            text += f"┃ {method:^12} ┃ {frequency:^15} ┃ {stack:^9} ┃ {comp:^6} ┃ {lags}\n"

        text += "┗━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━┻━━━━━━━━┻━━━━━━━━━━━━ •••\n"
        return text

    def __str__(self):
        return self.__repr__()


def average_dvv(output_path, comps=["ZZ", "NN", "EE", "ZN", "ZE", "EZ", "NZ", "EN", "NE"]):
    monitoring_folder = os.path.join(output_path, "xcorr_noise_monitoring")
    files = os.listdir(monitoring_folder)

    for f in tqdm(files, desc="Averaging dv/v", bar_format="{l_bar}{bar:30}{r_bar}"):
        sta1, sta2 = f.split(".")[0].split("-")
        filename = os.path.join(output_path, "xcorr_noise_monitoring", f"{sta1}-{sta2}.h5")
        if not os.path.exists(filename):
            continue

        dvvobj = load_h5_dvv(filename)
        dvv_params = dvvobj.get_alldata()
        results = {"metadata": {"sta1": sta1, "sta2": sta2}, "data": {}}

        for method in dvv_params.keys():
            results["data"][method] = {}

            for freq in dvv_params[method].keys():
                results["data"][method][freq] = {}

                for stack in dvv_params[method][freq].keys():
                    results["data"][method][freq][stack] = {}
                    components = []

                    for comp in comps:
                        try:
                            df = dvvobj.get_data(method, freq, stack, comp, avg_sides=False)
                        except Exception:
                            continue
                        components.append(df)

                    if len(components) == 0:
                        continue

                    if len(components) == 1:
                        result = components[0]
                    else:
                        stack_components = pd.concat(components, axis=0, keys=range(len(components)))
                        result = pd.DataFrame(index=components[0].index, columns=components[0].columns)

                        for col in components[0].columns:
                            if col[-1] == "dvv":
                                cc_col = col[:-1] + ("coherence",)
                                dv_vals = stack_components[col].unstack(0)
                                cc_vals = stack_components[cc_col].unstack(0)
                                result[col] = (dv_vals * cc_vals).sum(axis=1) / cc_vals.sum(axis=1)
                            else:
                                vals = stack_components[col].unstack(0)
                                result[col] = vals.mean(axis=1)

                    results["data"][method][freq][stack]["avg"] = {}
                    for lag_str in result.columns.get_level_values(0).unique().tolist():
                        results["data"][method][freq][stack]["avg"][lag_str] = {
                            "time": result.index.strftime("%Y-%m-%d").tolist(),
                            "dvv": result[lag_str]["dvv"].tolist(),
                            "coherence": result[lag_str]["coherence"].tolist(),
                            "error": result[lag_str]["error"].tolist(),
                        }

        with h5py.File(filename, "a") as f:
            save_dvv_results(f, results)
