import os
import pandas as pd
from tqdm import tqdm
import h5py
import numpy as np
from sda.process.xcorr_noise_monitoring.main import merge_hdf5

import warnings
warnings.filterwarnings("ignore")



def load_h5_dvv(filename):
    
    with h5py.File(filename, "r") as f:
        results = h5_to_dict(f)
        
    obj = dvv_object(results, filename)

    return obj
  

 
def h5_to_dict(h5_group):
    result = {}
    for key, item in h5_group.items():
        if isinstance(item, h5py.Group):
            result[key] = h5_to_dict(item)
        elif isinstance(item, h5py.Dataset):
            data = item[()]
            if isinstance(data, bytes):
                data = data.decode()
            elif isinstance(data, np.ndarray) and data.dtype.kind == 'S':
                data = data.astype(str).tolist()
            elif isinstance(data, np.ndarray):
                data = data.tolist()
            result[key] = data
    return result


class dvv_object:
    
    def __init__(self, data, filename):
        print
        self.data = data
        self.filename = filename
        self.sta1 = data["metadata"]["sta1"]
        self.sta2 = data["metadata"]["sta2"]
        
        
        
    def get_metadata(self):
        return self.data["metadata"]
    
    
    
    def get_alldata(self):
        return self.data["data"]
    
    
    
    def get_data(self, method, frequency, stack, comp, lagtime=None, param=None):
        
        # Formatting inputs
        if isinstance(frequency, tuple) or isinstance(frequency, list):
            frequency = f"{frequency[0]:.3f}-{frequency[1]:.3f}Hz"
            
        if isinstance(stack, int):
            stack = f"{stack:03d}days"
            
        if isinstance(lagtime, tuple) or isinstance(lagtime, list):
            lagtime = "_".join([f"{l:.2f}" for l in lagtime]) + "s"
           
           
        # All lagtimes / All parameters
        if lagtime is None and param is None:
            data = self.data["data"][method][frequency][stack][comp]
            
            df = pd.concat([
                pd.DataFrame({k: v for k, v in values.items() if k != 'time'}, 
                            index=pd.to_datetime(values['time']))
                .set_axis(pd.MultiIndex.from_product([[lag], ['dvv', 'coherence', 'error']]), axis=1)
                for lag, values in data.items()
            ], axis=1)
                
            return df
        
        
        # All lagtimes / One parameter
        if lagtime is None and param is not None:
            data = self.data["data"][method][frequency][stack][comp]
            df = pd.concat([
                pd.DataFrame(values[param], index=pd.to_datetime(values['time']), columns=[lag]) for lag, values in data.items()
            ], axis=1)
            return df
        
        
        # One lagtime / All parameters
        if lagtime is not None and param is None:
            data = self.data["data"][method][frequency][stack][comp][lagtime]
            df = pd.DataFrame(data)
            df.set_index("time", inplace=True)
            df.set_index(pd.to_datetime(df.index), inplace=True)
            return df
        
        
        # One lagtime / One parameter
        if lagtime is not None and param is not None:
            data = self.data["data"][method][frequency][stack][comp][lagtime][param]
            time = data = self.data["data"][method][frequency][stack][comp][lagtime]["time"]
            df = pd.DataFrame(data, columns=[param], index=pd.to_datetime(time))
            return df
        
        

    def __repr__(self):
        pair_str = f"{self.sta1} - {self.sta2}"
        text =   "┏━━━   dv/v object   ━━━┓\n"
        text += f"┃  {pair_str:^20} ┃ \n"
        text += f"┣━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━  Possible actions  ━━━━━┓\n"
        text += f"┃ <obj>.get_metadata() # Get metadata                                ┃\n"
        text += f"┃ <obj>.get_alldata()  # Get all dataset (raw format)                ┃\n"
        text += f"┃ <obj>.get_data()     # Formatted dataset for given parameters      ┃\n"
        text += f"┃                        (see table below)                           ┃\n"
        text += f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        text += f"                          DATASETS AVAILABLE\n\n"
        text += f"┏━━━ method ━━━┳━━━ frequency ━━━┳━━ stack ━━┳━ comp ━┳━ lagtime ━━ •••\n"
        text += f"┃              ┃                 ┃           ┃        ┃\n"
        
        for method, res_method in self.data["data"].items():
            for freq, res_freq in res_method.items():
                for stack, res_stack in res_freq.items():
                    for comp, res_comp in res_stack.items():
                        lags = ""
                        for idx, lag in enumerate(res_comp.keys()):
                            lags += f"{lag}"
                            if idx < len(res_comp.keys()) - 1:
                                lags += " • "
                        
                        text += f"┃ {method:^12} ┃ {freq:^15} ┃ {stack:^9} ┃ {comp:^6} ┃ {lags}\n"
                            
        text += f"┗━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━┻━━━━━━━━┻━━━━━━━━━━━━ •••\n"
        
        return text
    
    
        
    def __str__(self):
        return self.__repr__()




def average_dvv(output_path, comps=["ZZ","NN","EE","ZN","ZE","EZ","NZ","EN","NE"]):

    monitoring_folder = os.path.join(output_path, "xcorr_noise_monitoring")
    files = os.listdir(monitoring_folder)
    
    for f in tqdm(files, desc=f"Averaging dv/v", bar_format="{l_bar}{bar:30}{r_bar}"):
        
        sta1, sta2 = f.split(".")[0].split("-")
        filename = os.path.join(output_path, "xcorr_noise_monitoring", f"{sta1}-{sta2}.h5")
        if not os.path.exists(filename): continue
        dvvobj = load_h5_dvv(filename)
        dvv_params = dvvobj.get_alldata()
        results = {"metadata":{"sta1":sta1,"sta2":sta2}, "data":{}}
        

        for method in dvv_params.keys():
            results["data"][method] = {}

            for freq in dvv_params[method].keys():
                results["data"][method][freq] = {}

                for stack in dvv_params[method][freq].keys():
                    results["data"][method][freq][stack] = {}
                        
                    components = []
                    
                    for comp in comps:
                           
                        try:
                            df = dvvobj.get_data(method, freq, stack, comp)
                        except:
                            continue
                        components.append(df)
                        
                    if len(components) == 0:
                        continue
                    
                    elif len(components) == 1:
                        result = components[0]
                        
                    else:
                        stack_components = pd.concat(components, axis=0, keys=range(len(components)))
                        result = pd.DataFrame(index=components[0].index, columns=components[0].columns)
                        
                        for col in components[0].columns:
                            level_name = col[-1]
                            
                            if level_name == "dvv":
                                prefix = col[:-1]
                                cc_col = prefix + ("coherence",)
                                
                                dv_vals = stack_components[col].unstack(0)
                                cc_vals = stack_components[cc_col].unstack(0)
                                
                                weighted = (dv_vals * cc_vals).sum(axis=1) / cc_vals.sum(axis=1)
                                result[col] = weighted
                                
                            else:
                                vals = stack_components[col].unstack(0)
                                result[col] = vals.mean(axis=1)
                            
                    # save_folder = os.path.join(freq_folder, stack, "avg")
                    # os.makedirs(save_folder, exist_ok=True)
                    # save_filename = os.path.join(save_folder, f"{sta1}-{sta2}.csv")
                    # result.to_csv(save_filename)
                    results["data"][method][freq][stack]["avg"] = {}
                    lags = result.columns.get_level_values(0).unique().tolist()
                    
                    for lag_str in lags:
                        results["data"][method][freq][stack]["avg"][lag_str] = {
                            "time": result.index.strftime("%Y-%m-%d").tolist(),
                            "dvv": result[lag_str]["dvv"].tolist(),
                            "coherence": result[lag_str]["coherence"].tolist(),
                            "error": result[lag_str]["error"].tolist(),
                        }                  

        with h5py.File(filename, "a") as f:
            merge_hdf5(f, results)