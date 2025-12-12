import os
import pandas as pd
from tqdm import tqdm
import h5py
import numpy as np

import warnings
warnings.filterwarnings("ignore")



def load_h5_dvv(filename):
    
    with h5py.File(filename, "r") as f:
        results = h5_to_dict(f)

    return results
  

 
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



def average_dvv(output_path, comps=["ZZ","RR","TT","RT","RZ","TR","TZ","ZT","ZR"], methods=None, frequencies=None, stacks=None):

    monitoring_folder = os.path.join(output_path, "xcorr_noise_monitoring")
    if methods is None:
        list_methods = os.listdir(monitoring_folder)
    else:
        list_methods = methods.copy()

    for method in list_methods:

        method_folder = os.path.join(monitoring_folder, method)
        if frequencies is None:
            list_freqs = os.listdir(method_folder)
        else:
            list_freqs = [f"{fmin:.2f}-{fmax:.2f}Hz" for fmin, fmax in frequencies]

        for freq in list_freqs:

            freq_folder = os.path.join(method_folder, freq)
            if stacks is None:
                list_stacks = os.listdir(freq_folder)
            else:
                list_stacks = [f"{int(s):03d}days" for s in stacks]

            for stack in list_stacks:

                data_folder = os.path.join(freq_folder, stack)
                files = os.listdir(os.path.join(data_folder, "ZZ"))

                for file in tqdm(files, desc=f"Averaging dv/v [{method}, {freq}, {stack}]", bar_format="{l_bar}{bar:30}{r_bar}"):
                    
                    sta1, sta2 = file.split(".")[0].split("-")
                    components = []
                    
                    for comp in comps:
                    # comps : ["ZZ","NN","EE","ZN","ZE","EZ","NZ","EN","NE"]:
                        filename = os.path.join(data_folder, comp, f"{sta1}-{sta2}.csv")
                        if not os.path.exists(filename): continue 
                        datafile = pd.read_csv(filename, index_col=[0], header=[0,1])
                        datafile = datafile.set_index(pd.to_datetime(datafile.index, format="%Y-%m-%d"))
                        components.append(datafile)
                        
                    if len(components) == 0:
                        continue
                    
                    elif len(components) == 1:
                        result = components[0]
                        
                    else:
                        stack_components = pd.concat(components, axis=0, keys=range(len(components)))
                        result = pd.DataFrame(index=components[0].index, columns=components[0].columns)
                        
                        for col in components[0].columns:
                            level_name = col[-1]
                            
                            if level_name == "dv":
                                prefix = col[:-1]
                                cc_col = prefix + ("cc",)
                                
                                dv_vals = stack_components[col].unstack(0)
                                cc_vals = stack_components[cc_col].unstack(0)
                                
                                weighted = (dv_vals * cc_vals).sum(axis=1) / cc_vals.sum(axis=1)
                                result[col] = weighted
                                
                            else:
                                vals = stack_components[col].unstack(0)
                                result[col] = vals.mean(axis=1)
                            
                    save_folder = os.path.join(freq_folder, stack, "avg")
                    os.makedirs(save_folder, exist_ok=True)
                    save_filename = os.path.join(save_folder, f"{sta1}-{sta2}.csv")
                    result.to_csv(save_filename)
