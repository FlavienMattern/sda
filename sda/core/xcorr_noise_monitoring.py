import os
import pandas as pd
from tqdm import tqdm

import warnings
warnings.filterwarnings("ignore")


def average_dvv(output_path, comps=["ZZ","RR","TT","RT","RZ","TR","TZ","ZT","ZR"]):

    monitoring_folder = os.path.join(output_path, "xcorr_noise_monitoring")
    methods = os.listdir(monitoring_folder)

    for method in methods:

        method_folder = os.path.join(monitoring_folder, method)
        freqs = os.listdir(method_folder)
        for freq in freqs:

            freq_folder = os.path.join(method_folder, freq)
            stacks = os.listdir(freq_folder)

            for stack in stacks:

                save_folder = os.path.join(stack, "avg")
                files = os.listdir(os.path.join(save_folder, "ZZ"))

                for file in tqdm(files, desc=f"Averaging dv/v [{method}, {freq}, {stack}]"):
                    
                    sta1, sta2 = file.split(".")[0].split("-")
                    components = []
                    
                    for comp in comps:
                    # comps : ["ZZ","NN","EE","ZN","ZE","EZ","NZ","EN","NE"]:
                        filename = os.path.join(save_folder, comp, f"{sta1}-{sta2}.csv")
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
                            
                    os.makedirs(save_folder, exist_ok=True)
                    save_filename = os.path.join(save_folder, f"{sta1}-{sta2}.csv")
                    result.to_csv(save_filename)
