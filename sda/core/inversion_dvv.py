import numpy as np
from tqdm import tqdm
from disba import GroupSensitivity
from numpy.linalg import inv
import pickle as pkl
import torch
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from contextlib import nullcontext
import matplotlib.cm as cm
import matplotlib.patches as patches
from scipy.optimize import curve_fit



def read(filename):
    with open(filename, 'rb') as f:
        obj = pkl.load(f)
    return obj



class Inversion:

    #######################################################
    ###                   INIT METHOD                   ###
    #######################################################

    def __init__(self, xmin, xmax, ymin, ymax, zmin=0, zmax=0, dr=1, dz=1):
        
        # Initiating variables
        self.xmin = xmin / 1e3
        self.xmax = xmax / 1e3
        self.ymin = ymin / 1e3
        self.ymax = ymax / 1e3
        self.zmin = zmin
        self.zmax = zmax
        self.dr = dr
        self.dz = dz
        self.dataset = {}
        self.model = {}
        self.Cd = {}
        self._KERNELS = {}
        self.print_all = True
        self.device = torch.device(device="cuda" if torch.cuda.is_available() else 'cpu')

        # Initiating the grid
        self.x = np.arange(self.xmin, self.xmax, self.dr)
        self.y = np.arange(self.ymin, self.ymax, self.dr)
        if self.zmin != self.zmax:
            self.z = np.arange(self.zmin, self.zmax, self.dz) 
        else:
            self.z = np.array([0])
            self.dz = 1

        self.DV = self.dr*self.dr*self.dz
        self.M = len(self.x)*len(self.y)*len(self.z)
        self.grid = [(xi, yi, zi) for zi in self.z for yi in self.y for xi in self.x]



    #######################################################
    ###                 PUBLIC METHODS                  ###
    #######################################################

    def add_dataset(self, name, data, coherence, coordinates, stations, freq, c, l, lagtime, data_type="velocity"):
        
        # Remove nan values if data or coherence contains NaN
        mask_nona = ~np.isnan(data) & ~np.isnan(coherence)
        if sum(mask_nona) < len(data):
            data = data[mask_nona]
            coherence = coherence[mask_nona]
            coordinates = coordinates[mask_nona,:,:]
            stations = stations[mask_nona]
            freq = freq[mask_nona]
            c = c[mask_nona]
            l = l[mask_nona]
            lagtime = lagtime[mask_nona,:]

        if len(data) == 0: return
        
        t = np.array([(min(lag)+max(lag))/2 for lag in lagtime])
        tnorm = c*t/l * 1.3 # Position dans le temps normalisé tnorm=t/t* avec t*=l*/c    ==>     t = tnorm x t* = tnorm x l*/c
        alpha = np.exp(-0.08*tnorm) # Universal law (from Obermann et al., 2016)
        
        self.dataset[name] = {
            "data":        np.array(data),
            "coherence":   np.array(coherence),
            "coordinates": np.array(coordinates),
            "stations":    np.array(stations),
            "freq":        np.array(freq),
            "c":           np.array(c),
            "l":           np.array(l),
            "lagtime":     np.array(lagtime),
            "alpha":       alpha,
            "t":           t,
            "data_type":   data_type
        }

        self._build_Cd(name, data_type, show_progress=False)      



    def build_velocity_model(self, velocity_model):
        self.velocity_model = velocity_model
            

    
    def build_Cm(self, stdm, Lambda, Lambda0=None, show_progress=True):
        
        if show_progress:
            print(f"Building Cm ({self.M} x {self.M} = {self.M*self.M} elts) : ", end="")
        
            size = 8*self.M**2 # 64 bits : 1 élément = 8 octets (1 octet = 8bits: 8bits*8octets = 64bits)
            # size = 4*self.M**2 # 32 bits : 1 élément = 4 octets (1 octet = 8bits: 8bits*4octets = 32bits)
            if size < 1024:      print(f"{(8*self.M**2):.2f} octets")
            elif size < 1024**2: print(f"{(8*self.M**2)/1024:.2f} ko")
            elif size < 1024**3: print(f"{(8*self.M**2)/1024**2:.2f} Mo")
            elif size < 1024**4: print(f"{(8*self.M**2)/1024**3:.2f} Go")
            else:                print(f"{(8*self.M**2)/1024**4:.2f} To")
        
        self.stdm = stdm
        self.Lambda = Lambda
        if Lambda0 is None:
            self.Lambda0 = self.dr
        else:
            self.Lambda0 = Lambda0

        
        positions = np.array(self.grid)
        positions = torch.tensor(positions, dtype=torch.float32)

        block_size = min(2000, self.M)
        self.Cm = np.zeros((self.M, self.M), dtype=np.float32) 

        # Compute Cm by blocks to optimize memory usage
        for i in range(0, self.M, block_size):
            for j in range(i, self.M, block_size):
                i_end = min(i + block_size, self.M)
                j_end = min(j + block_size, self.M)
                pos_i = positions[i:i_end]
                pos_j = positions[j:j_end]
                pos_i_gpu = pos_i.to(self.device)
                pos_j_gpu = pos_j.to(self.device)

                distances_block = torch.cdist(pos_i_gpu, pos_j_gpu, p=2)
                Cm_block_gpu = (self.stdm * self.Lambda0 / self.Lambda)**2 * torch.exp(-distances_block / self.Lambda)

                Cm_block = Cm_block_gpu.cpu()
                self.Cm[i:i_end, j:j_end] = Cm_block
                if i != j:
                    self.Cm[j:j_end, i:i_end] = Cm_block.T # by symmetry



    def compute_kernels(self, show_progress=True):

        # --- 1) Collecte des kernels déjà présents (pair_name, params)
        existing = set()
        for pair_name, sub in self._KERNELS.items():
            # sub: dict[params_tuple] -> kernel
            for params in sub:
                existing.add((pair_name, params))

        # --- 2) Préparation des kernels à calculer (dédup via set)
        to_compute = set()

        items = self.dataset.items()
        it = tqdm(items, total=len(self.dataset), desc="Preparing Kernels") if show_progress else items

        for _, value in it:
            coords = value["coordinates"]
            stations = value["stations"]
            t_arr = value["t"]
            c_arr = value["c"]
            l_arr = value["l"]
            a_arr = value["alpha"]
            f_arr = value["freq"]

            for idx, pair_name in enumerate(stations):
                coord1, coord2 = coords[idx]
                sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
                sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3

                params = (sta1x, sta1y, sta2x, sta2y,
                        t_arr[idx], c_arr[idx], l_arr[idx], a_arr[idx], f_arr[idx])

                key = (pair_name, params)

                if key not in existing:
                    to_compute.add(key)

        if (len(to_compute) == 0) & (show_progress==True):
            print("Computing Kernels: All kernels have already been computed. Skipping...")
            return
        
        seq = list(to_compute)
        pbar = tqdm(seq, total=len(seq), desc="Computing Kernels") if show_progress else seq
        
        for pair_name, params in pbar:

            (sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq) = params

            if pair_name not in self._KERNELS.keys():
                self._KERNELS[pair_name] = {}

            if params in self._KERNELS[pair_name]:
                continue

            self._KERNELS[pair_name][params] = self._Kpair(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)



    def build_G(self, name):

            dataset = self.dataset[name]
            data_type = dataset["data_type"]
            d = dataset["data"]
            N = len(d)
            M = self.M
            
            # Define G
            G = np.zeros((N,M))
            for idx, pair_name in enumerate(dataset["stations"]):
                coord1, coord2 = dataset["coordinates"][idx]
                sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
                sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3
                t = dataset["t"][idx]
                c = dataset["c"][idx]
                l = dataset["l"][idx]
                alpha = dataset["alpha"][idx]
                freq = dataset["freq"][idx]
                K = self._KERNELS[pair_name][(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)].flatten()
                
                if data_type == "velocity":
                    G[idx,:] = self.DV / t * K
                elif data_type == "coherence":
                    G[idx,:] = c * self.DV / 2 * K
            
            #####################      
            # A ENLEVER A TERME
            # ça vient du fait que parfois les noyaux K sont remplis de NaN
            # comprendre d'où ça vient ??
            # Note : vu à BF (1/4 - 1/2 s pour la première bande de lagtime dans la coda)
            # Mauvaise vitesse, donc ça fait un soucis pour le calcul du noyau ??
            G = np.nan_to_num(G, nan=0.0)
            #####################

            return G


    def invert(self, name=None, compute_restitution_index=True, show_progress=True):

        if name is None:
            names = list(self.dataset.keys())
        elif type(name) == list:
            names = name
        else:
            names = [name]

        if show_progress:
            pbar = tqdm(names)
            pbar.set_description(f"Inversion")
        else:
            pbar = names

        for name in pbar:

            # Initialize variables
            dataset = self.dataset[name]
            d = dataset["data"]
            N = len(d)
            if N == 0: continue
            m0 = np.zeros(self.M)
            Cd = self.get_Cd(name)
            Cm = self.Cm
            
            G = self.build_G(name)

            # Inversion
            G  = torch.tensor(G,  dtype=torch.float32, device=self.device)
            m0 = torch.tensor(m0, dtype=torch.float32, device=self.device)
            Cm = torch.tensor(Cm, dtype=torch.float32, device=self.device)
            Cd = torch.tensor(Cd, dtype=torch.float32, device=self.device)
            d  = torch.tensor(d,  dtype=torch.float32, device=self.device)
            
            A = G @ Cm @ G.T
            A.diagonal().add_(Cd)
            rhs = d - G @ m0
            m = m0 + Cm @ G.T @ torch.linalg.solve(A, rhs)
            # m = m0 + Cm @ G.T @ torch.linalg.solve(G @ Cm @ G.T + Cd, d - G @ m0)
            rms = self._RMS(d, G, m, Cd)

            m = m.cpu().numpy()
            rms = rms.cpu().numpy()
            d = d.cpu().numpy()
            Cm = Cm.cpu().numpy()
            Cd = Cd.cpu().numpy()
            G = G.cpu().numpy()
            #################################################################################

            # Saving results
            self.model[name] = {
                    "model": m,
                    "RMS": rms
                }
            
            # Saving Restitution Index
            if compute_restitution_index:
                self.model[name]["restitution_index"] = self._Restitution(G, Cm, Cd)



    def get_model(self, name): 
        z = self.z if self.zmin != self.zmax else None
        return self.x*1e3, self.y*1e3, z, self.model[name]["model"].reshape(len(self.z), len(self.y), len(self.x)).squeeze(),



    def get_Cd(self, name):
        # return np.diag(self.Cd[name])
        return self.Cd[name]
    


    def get_restitution_index(self, name):
        if "restitution_index" in self.model[name].keys():
            rest = self.model[name]["restitution_index"]
        else:
            Cd = self.get_Cd(name)
            Cm = self.Cm
            G = self.build_G(name)
            rest = self._Restitution(G, Cm, Cd)

        return rest
    
    
    def get_resolution(self, name):
        Cd = self.get_Cd(name)
        Cm = self.Cm
        G = self.build_G(name)
        R = self._Resolution(G, Cm, Cd)

        return R



    def get_RMS(self, name):
        return self.model[name]["RMS"]
              


    def clear_model(self, name=None):
        if name==None or name==[]:
            self.model = {}
        elif isinstance(name, list):
            [self.model.pop(n, None) for n in name]
        else:
            self.model.pop(name, None)
    
    

    def set_print_all(self, bool):
        self.print_all = bool



    def write(self, filename):
        with open(filename, 'wb') as f:
            pkl.dump(self, f, protocol=pkl.HIGHEST_PROTOCOL)



    #######################################################
    ###                PRIVATE METHODS                  ###
    #######################################################

    def __repr__(self):
        text =   "┏━ Axis ━┳━━ Min [km] ━━┳━━ Max [km] ━━┳━ Step [km] ━┳━ Size ━┓\n"
        text += f"┃   X    ┃ {self.xmin:>12.2f} ┃ {self.xmax:>12.2f} ┃ {self.dr:>11.2f} ┃ {len(self.x):>6} ┃\n"
        text += f"┃   Y    ┃ {self.ymin:>12.2f} ┃ {self.ymax:>12.2f} ┃ {self.dr:>11.2f} ┃ {len(self.y):>6} ┃\n"
        if len(self.z) > 1:
            text += f"┃   Z    ┃{self.zmin:<12} ┃ {self.zmax:<12} ┃ {self.dz:<4.1f} ┃ {len(self.z):<3}\n"
        text += f"┣━━━━━━━━┻━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━┻━━━━━━━━━━━━━┻━━━━━━━━┫\n"
        text += f"┃ Datasets : {len(self.dataset.keys()):>10} ┃  ■/□ Inverted/Not     □/○ dvv/coh   ┃\n"
        text += f"┣━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"
        
        data_list = list(self.dataset.keys())
        
        if self.print_all:
            max_dataset = len(data_list)
        else:
            max_dataset = 40
        
        if len(data_list) > max_dataset:
            data_list = data_list[:int(max_dataset/2)] + data_list[-int(max_dataset/2):]
        Ncol = 5
        Nlines = -(-len(data_list) // Ncol)
        if len(data_list) == 0:
            max_larg = 21
        else:
            max_larg = max(len(chaine) for chaine in data_list) + 10
        data_list += [""] * (Ncol * Nlines - len(data_list))

        dataset_list = []
        for elt in data_list:
            if elt in self.dataset.keys():
                data_type = self.dataset[elt]["data_type"]
                if data_type == "velocity":
                    symbol = "□" if elt not in self.model.keys() else "■"
                else:
                    symbol = "○" if elt not in self.model.keys() else "●"
                dataset_list.append(f"┃ {symbol} {elt}")
            elif elt == "...":
                dataset_list.append("┃  ...")
            else:
                dataset_list.append("")
            
        for i in range(Nlines):
            ligne = dataset_list[i * Ncol:(i + 1) * Ncol]
            if (i==int(Nlines/2)) & (self.print_all==False) & (len(dataset_list)>max_dataset):
                text += "".join(f"{'┃  ...':<{max_larg}}" for elem in ligne) + "\n"
            text += "".join(f"{elem:<{max_larg}}" for elem in ligne) + "\n"
        
        return text
     
     

    def __str__(self):
        return self.__repr__()
    


    def _build_Cd(self, name=None, data_type="velocity", show_progress=True):

        if name is None:
            names = list(self.dataset.keys())
        else:
            names = [name]

        if show_progress:
            pbar = tqdm(names)
            pbar.set_description(f"Building Cd")
        else:
            pbar = names

        for name in pbar:
            wc = 2*np.pi*self.dataset[name]["freq"]
            T = 1/self.dataset[name]["freq"]
            ti = np.array([min(lag) for lag in self.dataset[name]["lagtime"]])
            tf = np.array([max(lag) for lag in self.dataset[name]["lagtime"]])
            coh = self.dataset[name]["coherence"]

            if data_type == "coherence":
                std = 1-coh
            elif data_type == "velocity":
                std = np.sqrt(1-coh**2) / (2*coh) * np.sqrt( (6*np.sqrt(np.pi/2)*T) / (wc**2 * (tf**3 - ti**3)) )
            
            self.Cd[name] = std.astype(np.float32)
                    


    def _Ksurf_fond(self, velocity_model, z, freq):
        ps = GroupSensitivity(*velocity_model.T)
        depthList = [0]
        for i in range(len(velocity_model)):
            if i != len(velocity_model)-1:
                depthList.append(velocity_model[i][0]+depthList[i])
        skr = ps(1/freq, mode=0, wave="rayleigh", parameter="velocity_s")

        K = np.interp(x=z, xp=np.array(depthList), fp=skr.kernel)
        
        return K



    def _Kpair(self, sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq):
        
        sta1x = torch.tensor(sta1x, device=self.device)
        sta1y = torch.tensor(sta1y, device=self.device)
        sta2x = torch.tensor(sta2x, device=self.device)
        sta2y = torch.tensor(sta2y, device=self.device)
        t = torch.tensor(t, device=self.device)
        c = torch.tensor(c, device=self.device)
        l = torch.tensor(l, device=self.device)
        dr = torch.tensor(self.dr, device=self.device)
        
        # Convertir les positions des stations
        Spos = torch.tensor([sta1x, sta1y, 0], device=self.device)
        Rpos = torch.tensor([sta2x, sta2y, 0], device=self.device)

        # Calcul de la distance entre stations
        rSR = torch.sqrt(torch.tensor([(sta1x - sta2x)**2 + (sta1y - sta2y)**2], device=self.device))
        
        # Convertir les grilles en tenseurs PyTorch
        x = torch.tensor(self.x, device=self.device, dtype=torch.float32)
        y = torch.tensor(self.y, device=self.device, dtype=torch.float32)
        z = torch.tensor(self.z, device=self.device, dtype=torch.float32)       
        
        
        ### KSurf (2D) #########################
        X, Y = torch.meshgrid(x, y, indexing='ij')
        A = torch.sqrt((Spos[0] - X)**2 + (Spos[1] - Y)**2) + self.dr/4
        B = torch.sqrt((Rpos[0] - X)**2 + (Rpos[1] - Y)**2) + self.dr/4
        # Note : We add a slight distance shift of dr/4 to avoid singularities in the computation of itensitities
        A = A.unsqueeze(-1)
        B = B.unsqueeze(-1)
        
        N2D_ci = torch.exp(-A/l) / (2*torch.pi*A*c) * self._p2D_i(t-A/c, B, c, l, dr)
        N2D_ic = torch.exp(-B/l) / (2*torch.pi*B*c) * self._p2D_i(t-B/c, A, c, l, dr)
        N2D_ii = self._integrate(self._N2D_ii, 0, t, 273, t, A, B, c, l, dr)
        p2D_SR = self._p2D_c(t, rSR, c, l, dr) + self._p2D_i(t, rSR, c, l, dr)
        KSurf = (N2D_ci + N2D_ic + N2D_ii) / p2D_SR 
        # KSurf *= t/torch.sum(KSurf) # Normalise K so that the integrale gives the lapse time t
        if self.zmin != self.zmax : KSurf = KSurf.repeat(1, 1, len(z))
        KSurf = KSurf.cpu().numpy()
        
        
        ### KBody (3D) #########################
        X, Y, Z = torch.meshgrid(x, y, z, indexing='ij')
        A = torch.sqrt((Spos[0] - X)**2 + (Spos[1] - Y)**2 + (Spos[2] - Z)**2) + self.dr/4
        B = torch.sqrt((Rpos[0] - X)**2 + (Rpos[1] - Y)**2 + (Rpos[2] - Z)**2) + self.dr/4
        # Note : We add a slight distance shift of dr/4 to avoid singularities in the computation of itensitities
        
        N3D_ci = torch.exp(-A/l) / (4*torch.pi*A**2*c) * self._p3D_i(t-A/c, B, c, l, dr)
        N3D_ic = torch.exp(-B/l) / (4*torch.pi*B**2*c) * self._p3D_i(t-B/c, A, c, l, dr)
        N3D_ii = self._integrate(self._N3D_ii, 0, t, 500, t, A, B, c, l, dr)
        p3D_SR = self._p3D_c(t, rSR, c, l, dr) + self._p3D_i(t, rSR, c, l, dr)
        KBody = (N3D_ci + N3D_ic + N3D_ii) / p3D_SR
        # KBody *= t/torch.sum(KBody) # Normalise K so that the integrale gives the lapse time t
        KBody = KBody.cpu().numpy()
        
    
        ###########################################################
        # N2D_ci = N2D_ci.cpu().numpy().squeeze()
        # N2D_ic = N2D_ic.cpu().numpy().squeeze()
        # N2D_ii = N2D_ii.cpu().numpy().squeeze()
        # p2D_SR = p2D_SR.cpu().numpy().squeeze()
        # KSurf2 = KSurf.squeeze()
        
        # N3D_ci = N3D_ci.cpu().numpy().squeeze()
        # N3D_ic = N3D_ic.cpu().numpy().squeeze()
        # N3D_ii = N3D_ii.cpu().numpy().squeeze()
        # p3D_SR = p3D_SR.cpu().numpy().squeeze()
        # KBody2 = KBody.squeeze()
        
        # fig, axs = plt.subplots(1,4,figsize=(23,5))
        # ax=axs[0]
        # vmin = 0
        # vmax = np.nanquantile(N2D_ci, 0.995)
        # ax.set_title("N2D_ci")
        # p = ax.pcolormesh(N2D_ci.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[1]
        # vmin = 0
        # vmax = np.nanquantile(N2D_ic, 0.995)
        # ax.set_title("N2D_ic")
        # p = ax.pcolormesh(N2D_ic.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[2]
        # vmin = 0
        # vmax = np.nanquantile(N2D_ii, 0.995)
        # ax.set_title("N2D_ii")
        # p = ax.pcolormesh(N2D_ii.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[3]
        # vmin = 0
        # vmax = np.nanquantile(KSurf2, 0.995)
        # ax.set_title("KSurf")
        # p = ax.pcolormesh(KSurf2.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # plt.savefig("/data1/fmattern/WORK/these/inversion/class_inversion/RESULTS/testK1.png",dpi=300)
        # plt.show()
        
        # fig, axs = plt.subplots(1,4,figsize=(23,5))
        # ax=axs[0]
        # vmin = 0
        # vmax = np.nanquantile(N3D_ci, 0.995)
        # ax.set_title("N3D_ci")
        # p = ax.pcolormesh(N3D_ci.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[1]
        # vmin = 0
        # vmax = np.nanquantile(N3D_ic, 0.995)
        # ax.set_title("N3D_ic")
        # p = ax.pcolormesh(N3D_ic.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[2]
        # vmin = 0
        # vmax = np.nanquantile(N3D_ii, 0.995)
        # ax.set_title("N3D_ii")
        # p = ax.pcolormesh(N3D_ii.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # ax=axs[3]
        # vmin = 0
        # vmax = np.nanquantile(KBody2, 0.995)
        # ax.set_title("KBody")
        # p = ax.pcolormesh(KBody2.T, vmin=vmin, vmax=vmax, cmap="Reds")
        # fig.colorbar(p, orientation="vertical")
        # plt.savefig("/data1/fmattern/WORK/these/inversion/class_inversion/RESULTS/testK2.png",dpi=300)
        # plt.show()
        ###########################################################
        

        # Compute sensitivity kernels of rayleigh waves fundamental mode
        Ksurf_ballistic_1D = self._Ksurf_fond(self.velocity_model, self.z, freq)
        Ksurf_ballistic_3D = np.zeros_like(KSurf) * np.nan
        for i in range(len(self.x)):
            for j in range(len(self.y)):
                Ksurf_ballistic_3D[i,j,:] = Ksurf_ballistic_1D  
        
        t = t.cpu().numpy()
        K = alpha*KSurf*Ksurf_ballistic_3D + (1-alpha)*KBody
        K = K.squeeze()
        K = K.T # On oriente correctement la matrice pour l'affichage
        # K *= t/np.sum(K) # Normalise K so that the integrale gives the lapse time t

        return K
    

            
    def _p2D_c(self, t, r, c, l, dr):
    
        try:
            t_len = t.shape[0]
            t = t.unsqueeze(0).unsqueeze(0).unsqueeze(0).repeat(r.shape[0], r.shape[1], r.shape[2], 1)
            r = r.unsqueeze(-1).repeat(1, 1, 1, t_len)
        except:
            pass
        
        eps = dr/2
        
        p = torch.where(
                torch.abs(t-r/c) <= eps, # Dirac condition
                torch.exp(-c*t/l) / (2*torch.pi*r*c),
                torch.tensor(0.0, device=self.device)
            )

        return p



    def _p2D_i(self, t, r, c, l, dr):

        try:
            t_len = t.shape[0]
            t = t.unsqueeze(0).unsqueeze(0).unsqueeze(0).repeat(r.shape[0], r.shape[1], r.shape[2], 1)
            r = r.unsqueeze(-1).repeat(1, 1, 1, t_len)
        except:
            pass
        
        eps = dr/2
        
        p = torch.where(
                c*t-r > eps,  # Heaviside condition
                1 / (2 * torch.pi * l * c * t)
                * (1 - r**2 / (c**2 * t**2))**(-1/2)
                * torch.exp((1/l) * (torch.sqrt(c**2 * t**2 - r**2) - c*t)),
                torch.tensor(0.0, device=self.device)
            )
        
        return p
    
    
    
    def _N2D_ii(self, u, t, A, B, c, l, dr):
        return self._p2D_i(u, A, c, l, dr) * self._p2D_i(t-u, B, c, l, dr)
    
    
    
    def _p3D_c(self, t, r, c, l, dr):
    
        try:
            t_len = t.shape[0]
            t = t.unsqueeze(0).unsqueeze(0).unsqueeze(0).repeat(r.shape[0], r.shape[1], r.shape[2], 1)
            r = r.unsqueeze(-1).repeat(1, 1, 1, t_len)
        except:
            pass

        eps = dr/2

        p = torch.where(
                torch.abs(t-r/c) < eps, # Dirac condition
                torch.exp(-c * t / l) / (4 * torch.pi * r**2 * c),
                torch.tensor(0.0, device=self.device)
            )

        return p



    def _p3D_i(self, t, r, c, l, dr):

        try:
            t_len = t.shape[0]
            t = t.unsqueeze(0).unsqueeze(0).unsqueeze(0).repeat(r.shape[0], r.shape[1], r.shape[2], 1)
            r = r.unsqueeze(-1).repeat(1, 1, 1, t_len)
        except:
            pass

        eps = dr/2

        p = torch.where(
                c*t-r > eps, # Heaviside condition
                (1 - r**2/(c**2*t**2))**(1/8) / (4*torch.pi*l*c*t/3)**(3/2) * torch.exp(-c*t/l) * self._G(c*t/l * (1 - r**2/(c**2*t**2))**(3/4)),
                torch.tensor(0.0, device=self.device)
            )

        return p
    
    
    
    def _N3D_ii(self, u, t, A, B, c, l, dr):
        return self._p3D_i(u, A, c, l, dr) * self._p3D_i(t-u, B, c, l, dr)
            


    def _G(self, x):
        return torch.exp(x) * torch.sqrt(1+2.026/x)
    


    def _integrate(self, func, a, b, n, *args):
        # Discrétisation de l'intervalle
        tau = torch.linspace(a, b, steps=n, device=self.device)
        dtau = (b - a) / (n - 1)
        
        # Évaluation de la fonction
        y = func(tau, *args)
        
        # Méthode des trapèzes
        integral = torch.nansum(y, dim=3) * dtau
        return integral 
    

            
    def _Resolution(self, G, Cm, Cd):
        G = torch.tensor(G, dtype=torch.float32, device=self.device)
        Cm = torch.tensor(Cm, dtype=torch.float32, device=self.device)
        Cd = torch.tensor(Cd, dtype=torch.float32, device=self.device)
        
        # R = Cm @ G.T @ torch.inverse(G @ Cm @ G.T + Cd) @ G
        A = G @ Cm @ G.T
        A.diagonal().add_(Cd)
        X = torch.linalg.solve(A, G)
        R = Cm @ G.T @ X
        
        return R.cpu().numpy()
    

    def _Restitution(self, G, Cm, Cd):
        R = self._Resolution(G, Cm, Cd)

        if len(self.z) == 1:
            rest = np.sum(R, axis=1).reshape(len(self.y), len(self.x))
        else:
            rest = np.sum(R, axis=1).reshape(len(self.z), len(self.y), len(self.x))

        return rest
        

    def _RMS(self, d, G, m, Cd):
        N = d.numel()
        residual = d - G@m
        # x = torch.linalg.solve(Cd, residual)
        x = residual / Cd
        rms = torch.sqrt( (1/N) * (residual.T @ x) )
        return rms


    def lcurve(self, name, stdm_list=[1e-2,5e-2,1e-1,5e-1], lambda_list=[2,3,5,10], show_progress=True, show_2D=True, return_values=False):
        lcurve_model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        lcurve_model.build_velocity_model(self.velocity_model)

        try:
            Lambda0 = self.Lambda0
        except:
            Lambda0 = self.dr

        lcurve_model.add_dataset(name,
                    self.dataset[name]["data"],
                    self.dataset[name]["coherence"],
                    self.dataset[name]["coordinates"],
                    self.dataset[name]["stations"],
                    self.dataset[name]["freq"],
                    self.dataset[name]["c"],
                    self.dataset[name]["l"],
                    self.dataset[name]["lagtime"],
                    data_type=self.dataset[name]["data_type"])

        lcurve_model._KERNELS = self._KERNELS
        Lcurve = pd.DataFrame(index=stdm_list, columns=lambda_list)

        with tqdm(total=len(stdm_list)*len(lambda_list), desc="L-curve analysis") if show_progress else nullcontext() as pbar:
            for sigma in stdm_list:
                for lambda_ in lambda_list:
                    lcurve_model.build_Cm(stdm=sigma, Lambda=lambda_, Lambda0=Lambda0, show_progress=False)
                    try:
                        lcurve_model.invert(name, show_progress=False)
                        _, _, _, m = lcurve_model.get_model(name)
                        rms = lcurve_model.get_RMS(name)
                        Lcurve.at[sigma, lambda_] = (rms, np.max(np.abs(m)))
                    except:
                        Lcurve.at[sigma, lambda_] = (np.nan, np.nan)
                    if show_progress: pbar.update(1)

        symbols = [".", "v", "*", "o", "+", "s", "X", "D", "^", "<", ">", "1", "2", "3", "4", "8", "p", "P", "h", "H", "x", "d", "|", "_"]

        cmap_name = "inferno"
        cmap = matplotlib.colors.ListedColormap(matplotlib.colormaps[cmap_name](np.linspace(0, 0.8, len(lambda_list))))

        def as_si(x):
            s = f"{x:.1e}"
            m, e = s.split('e')
            return rf"{m}\times 10^{{{int(e)}}}"

        values_list = []
        
        
        rms_list = []
        
        if return_values:
            rms = np.array([[v for v, _ in row] for row in Lcurve.values], dtype=np.float32)
            max_m = np.array([[e for _, e in row] for row in Lcurve.values], dtype=np.float32)
            return rms, max_m, stdm_list, lambda_list
        
        else:

            if show_2D:
                
                x = list(Lcurve.columns)
                y = list(Lcurve.index)
                L = np.array([[v for v, e in row] for row in Lcurve.values], dtype=np.float32)
                
                x_edges = np.linspace(np.min(x), np.max(x), len(x)+1)
                y_edges = np.logspace(np.log10(np.min(y)), np.log10(np.max(y)), len(y)+1)

                vmin, vmax = np.nanquantile(L,0.02), np.nanquantile(L,0.98)

                fig, ax = plt.subplots(1,1, figsize=(5,4))
                ax.tick_params(direction="in", which="both", top=True, right=True)
                p = ax.pcolormesh(x_edges, y_edges, L, vmin=vmin, vmax=vmax, cmap="inferno")
                ax.set_yscale("log")
                ax.set_xlabel(r"$\lambda$ [km]")
                ax.set_ylabel(r"$\sigma_m$")
                cbar = fig.colorbar(p, ax=ax)
                cbar.set_label("RMS", fontweight="bold")
                
                plt.show()
                
            else:
                ratios = dict(width_ratios=[1,0.2])
                fig, axs = plt.subplots(1,2, gridspec_kw=ratios, figsize=(12,4))
                plt.subplots_adjust(wspace=0.5)

                ax = axs[0]
                ax.tick_params(direction="in", top=True, right=True)
                for idx, (sigma, row) in enumerate(Lcurve.iterrows()):
                    for ii in range(len(row)):
                        rms_plot, value = row.iloc[ii]
                        frac    = ii/(len(row) - 1)
                        c  = cmap(frac)
                        
                        values_list.append(value)
                        rms_list.append(rms_plot)

                        ax.scatter(value, rms_plot, marker=symbols[idx], color=c, zorder=10)
                        
                        if idx == 0:
                            axs[1].scatter(-1e3, 0, marker=symbols[idx], color=c, label=f"$\lambda = {lambda_list[ii]:.0f}$ km", zorder=10)
                                    
                    ax.scatter(-1e3, 0, marker=symbols[idx], c="black", label=f"$\sigma _m = {as_si(sigma)}$", zorder=10)


                dx = max(values_list) - min(values_list)
                dy = max(rms_list) - min(rms_list)
                xmin, xmax = min(values_list), max(values_list)
                ymin, ymax = min(rms_list), max(rms_list)
                ax.set_xlim(xmin-0.02*dx, xmax+0.02*dx)
                ax.set_ylim(ymin-0.05*dy, ymax+0.05*dy)
                ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1))
                ax.grid(color="lightgray", ls=":", lw=1, zorder=0)
                ax.set_xlabel(f"max(m)", fontweight="bold")
                ax.set_ylabel("RMS", fontweight="bold")
                ax.set_xlim()

                axs[1].legend()
                axs[1].axis("off")
                axs[1].set_xlim(-1,1)
                axs[1].set_ylim(-1,1)

                plt.show()
            



    def spatial_resolution(self, name, stdm=None, Lambda=None, return_values=False):
        if stdm == None: stdm = self.stdm
        if Lambda == None: Lambda = self.Lambda

        data_type = self.dataset[name]["data_type"]

        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.add_dataset(name,
                    self.dataset[name]["data"],
                    self.dataset[name]["coherence"],
                    self.dataset[name]["coordinates"],
                    self.dataset[name]["stations"],
                    self.dataset[name]["freq"],
                    self.dataset[name]["c"],
                    self.dataset[name]["l"],
                    self.dataset[name]["lagtime"],
                    data_type=data_type)
        model._KERNELS = self._KERNELS
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=self.Lambda0, show_progress=False)

        st_pairs = self.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))
        
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=model.Lambda0, show_progress=False)
        model.invert(name, show_progress=False)
        x, y, _, _ = model.get_model(name)
        R = model.get_resolution(name)
        
        Rhalf = np.zeros((len(y),len(x))) * np.nan
        k_list = [19, 352, 450, 453]
        
        for k in tqdm(range(R.shape[0]), total=R.shape[0], desc="Computing Spatial Resolution"):

            ##########################################################
            ## Gaussian Fit 2D
            i = k // len(x)
            j = k % len(x)
            resol = R[k,:].reshape((len(y),len(x)))
            x0, y0 = x[j], y[i]
            
            def gauss2d(coords, A, sigma):
                x, y = coords
                return A * np.exp(-((x-x0)**2 + (y-y0)**2)/(2*sigma**2)).ravel()

            X, Y = np.meshgrid(x, y)
            X_flat = X.ravel()
            Y_flat = Y.ravel()
            Z_flat = resol.ravel()
            popt, pcov = curve_fit(gauss2d, (X_flat, Y_flat), Z_flat,
                                   p0 = (resol.max(), model.dr*1e3), # Initial guess
                                   bounds = ([0, 0], [np.inf, np.inf])) # Bounds

            A_fit, sigma_fit = popt
            r_half = sigma_fit * np.sqrt(2 * np.log(2)) / 1e3
            Rhalf[i,j] = r_half
            
            ##########################################################
            ### Méthode des moments
            # i = k // len(x)
            # j = k % len(x)
            # resol = R[k,:].reshape((len(y),len(x)))
            # x0, y0 = x[j], y[i]

            # X, Y = np.meshgrid(x, y)
            # Z = resol.copy()
            # Xf = X.ravel(); Yf = Y.ravel(); Zf = Z.ravel()

            # r = np.sqrt((Xf - x0)**2 + (Yf - y0)**2)

            # w = np.clip(Zf, 0, None) # weights
            # if w.sum() == 0:
            #     sigma_moment = np.nan
            # else:
            #     thr = 1e-6 * w.max()
            #     mask = w > thr
            #     if mask.sum() == 0:
            #         mask = w > 0
            #     r2_mean = (w[mask] * r[mask]**2).sum() / w[mask].sum()
            #     sigma_moment = np.sqrt(r2_mean / 2.0)

            # r_half = sigma_moment * np.sqrt(2 * np.log(2)) / 1e3
            # Rhalf[i, j] = r_half

            ##########################################################
            ### Méthode des écarts types
            # i = k // len(x)
            # j = k % len(x)
            # resol = R[k,:].reshape((len(y),len(x)))
            # x0, y0 = x[j], y[i]

            # X, Y = np.meshgrid(x, y)
            # Z = resol.copy()
            # XX = X.ravel(); YY = Y.ravel()

            # r = np.sqrt((XX - x0)**2 + (YY - y0)**2)
            # w = Z.ravel()
            # w = np.clip(w, 0, None)
            
            # r_mean = np.average(r, weights=w)
            # sigma = np.sqrt(np.average((r - r_mean)**2, weights=w))
            # r_half = sigma * np.sqrt(2 * np.log(2)) / 1e3
            # Rhalf[i, j] = r_half

            ##########################################################
            
            if not return_values:
                if k in k_list:
                    fig, ax = plt.subplots(1,1,figsize=(6,6))
                    ax.tick_params(direction="in", color="white", top=True, right=True)
                    vmin = 0
                    vmax = np.nanmax(resol)
                    p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, resol, cmap="cividis", vmin=vmin, vmax=vmax, zorder=0)
                    ax.scatter(stations[:,0], stations[:,1], zorder=20, color="white", s=5, marker=".")

                    [ax.axvline(xi, color="gray", ls="-", lw=0.8, alpha=0.5) for xi in x]
                    [ax.axhline(yi, color="gray", ls="-", lw=0.8, alpha=0.5) for yi in y]

                    ax.plot([x0,x0+model.dr*1e3], [y0,y0], lw=1, color="white")
                    ax.plot([x0,x0+model.dr*1e3], [y0+model.dr*1e3,y0+model.dr*1e3], lw=1, color="white")
                    ax.plot([x0,x0], [y0,y0+model.dr*1e3], lw=1, color="white")
                    ax.plot([x0+model.dr*1e3,x0+model.dr*1e3], [y0+model.dr*1e3,y0], lw=1, color="white")
                    
                    
                    fig.colorbar(p, label="Resolution", shrink=0.7)
                    ax.set_aspect("equal")
                    ax.set_xlabel("X [m]")
                    ax.set_ylabel("Y [m]")
                    ax.set_xlim(np.min(x), np.max(x))
                    
                    title = (
                        f"Spatial resolution = {r_half:.1f} km\n"
                        f"Restitution Index  = {np.nansum(resol):.2f}"
                    )
                    
                    ax.set_title(title, loc="left", fontsize=9)
                    
                    # ax.set_title(r"Texte normal, $\mathit{italique}$, équation $x^2+y^2=z^2$, $\mathbf{GRAS}$", loc="left", fontsize=8)
                    
                    # Z_fit = A_fit * np.exp(-((X-x0)**2 + (Y-y0)**2)/(2*sigma_fit**2))
                    # ax.contour(
                    #     X + model.dr/2*1e3,
                    #     Y + model.dr/2*1e3,
                    #     Z_fit,
                    #     levels=[A_fit/2],
                    #     colors='red',
                    #     linewidths=1.5,
                    # )
                    
                    from matplotlib.patches import Circle
                    circle = Circle((x0 + model.dr/2*1e3, y0 + model.dr/2*1e3), r_half*1e3, fill=False, color='red')
                    ax.add_patch(circle)
                
                
            ##########################################################
            
        if return_values:
            return x, y, Rhalf
            
        else:  
            cmap = cm.get_cmap('turbo_r', 20)
                
            fig, ax = plt.subplots(1,1,figsize=(6,6))
            ax.tick_params(direction="in", color="white", top=True, right=True)
            vmin = model.dr # np.nanquantile(Rhalf, 0.05)
            vmax = 30 # np.nanquantile(Rhalf, 0.95)
            p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, Rhalf, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
            ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
            fig.colorbar(p, label="Spatial Resolution [km]", shrink=0.7)
            ax.set_aspect("equal")
            ax.set_xlabel("X [m]")
            ax.set_ylabel("Y [m]")
            plt.show()  
        
        ##########################################################
            

    def restitution_index(self, name, stdm=None, Lambda=None):
        if stdm == None: stdm = self.stdm
        if Lambda == None: Lambda = self.Lambda

        data_type = self.dataset[name]["data_type"]

        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.add_dataset(name,
                    self.dataset[name]["data"],
                    self.dataset[name]["coherence"],
                    self.dataset[name]["coordinates"],
                    self.dataset[name]["stations"],
                    self.dataset[name]["freq"],
                    self.dataset[name]["c"],
                    self.dataset[name]["l"],
                    self.dataset[name]["lagtime"],
                    data_type=data_type)
        model._KERNELS = self._KERNELS
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=self.Lambda0, show_progress=False)

        st_pairs = self.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))

        cmap = cm.get_cmap('turbo', 20)

        fig, ax = plt.subplots(1,1,figsize=(6,6))
        ax.tick_params(direction="in", color="white", top=True, right=True)
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=model.Lambda0, show_progress=False)
        model.invert(name, show_progress=False)
        x, y, _, _ = model.get_model(name)
        Rsum = model.get_restitution_index(name)
        
        vmin = 0
        vmax = np.nanmax(Rsum)
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, Rsum, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        fig.colorbar(p, label="Restitution index", shrink=0.7)
        ax.set_aspect("equal")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")

        plt.show()
        
        
        
    def plot_model(self, name, mask_restitution=0.8, stdm=None, Lambda=None):
        if stdm == None: stdm = self.stdm
        if Lambda == None: Lambda = self.Lambda

        data_type = self.dataset[name]["data_type"]
        if data_type == "velocity":
            data = self.dataset[name]["data"]
            coherence = self.dataset[name]["coherence"]
        else:
            data = self.dataset[name]["data"]
            coherence = self.dataset[name]["coherence"]

        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.add_dataset(name,
                    data,
                    coherence,
                    self.dataset[name]["coordinates"],
                    self.dataset[name]["stations"],
                    self.dataset[name]["freq"],
                    self.dataset[name]["c"],
                    self.dataset[name]["l"],
                    self.dataset[name]["lagtime"],
                    data_type=data_type)
        model._KERNELS = self._KERNELS
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=self.Lambda0, show_progress=False)

        st_pairs = self.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))

        if data_type == "velocity":
            cmap = cm.get_cmap('coolwarm', 20)
        else:
            cmap = cm.get_cmap('Spectral', 20)

        fig, ax = plt.subplots(1,1,figsize=(6,6))
        ax.tick_params(direction="in", color="white", top=True, right=True)
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=model.Lambda0, show_progress=False)
        model.invert(name, show_progress=False)
        x, y, _, m = model.get_model(name)
        if mask_restitution > 0:
            R = model.get_restitution_index(name)
            m[R < mask_restitution] = np.nan
        
        if data_type == "velocity":
            vmax = np.nanquantile(np.abs(m), 0.95)
            vmin = -vmax
            label = "dv/v [%]"
        else:
            vmax = np.nanquantile(np.abs(m), 0.95)
            vmin = np.nanquantile(np.abs(m), 0.05)
            label = r"$\sigma$ [km/km²]"
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, m, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        fig.colorbar(p, label=label, shrink=0.7)
        ax.set_aspect("equal")
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")

        plt.show()



    def checker_board(self, name, size=1.5, min_amplitude=-1, max_amplitude=1, mask_restitution=0, return_values=False):
        
        data_type = self.dataset[name]["data_type"]

        cboard = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        cboard.build_velocity_model(self.velocity_model)
        cboard.build_Cm(stdm=self.stdm, Lambda=self.Lambda, Lambda0=self.Lambda0, show_progress=False)
        
        synt_x = np.arange(cboard.xmin, cboard.xmax+size, size)
        synt_y = np.arange(cboard.ymin, cboard.ymax+size, size)
        synt_model = np.zeros( (len(cboard.y),len(cboard.x)) )
        
        # Synthetic checkerboard model
        di = int(size / cboard.dr)
        check_size = di*cboard.dr
        nx = len(cboard.x)
        ny = len(cboard.y)
        synt_model = np.ones((nx, ny))
        X, Y = np.meshgrid(np.arange(ny), np.arange(nx))
        synt_model[((X // di) + (Y // di)) % 2 == 0] = -1
        synt_model = synt_model.T

        if data_type == "velocity":
            data = self.dataset[name]["data"]
            coherence = self.dataset[name]["coherence"]
        else:
            data = self.dataset[name]["data"]
            coherence = self.dataset[name]["coherence"]
        
        cboard.add_dataset("checker_board",
                        data,
                        coherence,
                        self.dataset[name]["coordinates"],
                        self.dataset[name]["stations"],
                        self.dataset[name]["freq"],
                        self.dataset[name]["c"],
                        self.dataset[name]["l"],
                        self.dataset[name]["lagtime"],
                        data_type=data_type)
        cboard._KERNELS = self._KERNELS
        coordinates = self.dataset[name]["coordinates"]
        stations = self.dataset[name]["stations"]
            
        N = len(data)
        M = cboard.M
        K = np.zeros((N,M))


        # Simulate data based on model and sensitivity kernels
        G = np.zeros((N,M))
        dataset = cboard.dataset["checker_board"]
        for idx, pair_name in enumerate(dataset["stations"]):
            coord1, coord2 = dataset["coordinates"][idx]
            sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
            sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3
            t = dataset["t"][idx]
            c = dataset["c"][idx]
            l = dataset["l"][idx]
            alpha = dataset["alpha"][idx]
            freq = dataset["freq"][idx]
            K = cboard._KERNELS[pair_name][(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)].flatten()
            
            if data_type=="velocity":
                G[idx,:] = self.DV / t * K
            elif data_type=="coherence":
                G[idx,:] = c * self.DV / 2 * K

        data = G @ synt_model.flatten()

        cboard.add_dataset("checker_board", data, coherence, coordinates, stations,
                            dataset["freq"], dataset["c"], dataset["l"], dataset["lagtime"], data_type)

        # Invert data
        cboard.invert("checker_board", show_progress=False)
        
        if mask_restitution > 0:
            R = cboard.get_restitution_index("checker_board")
            mask = R < mask_restitution



        st_pairs = cboard.dataset["checker_board"]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))
        
        if mask_restitution > 0: synt_model[mask] = np.nan

        x, y, _, m = cboard.get_model("checker_board")

        if not return_values:
            if data_type == "velocity":
                cmap = "coolwarm"
            else:
                cmap = "Spectral"

            # Plot checkerboard test
            plt.figure(figsize=(15,7))
            plt.subplot(121)
            plt.scatter(stations[:,0]/1e3, stations[:,1]/1e3, zorder=20, color="black", s=5, marker=".")
            p = plt.pcolormesh(cboard.x+cboard.dr/2, cboard.y+cboard.dr/2, synt_model, vmin=min_amplitude, vmax=max_amplitude, cmap=cmap)
            [plt.axvline(min(cboard.x) +i*di*cboard.dr, color="black", ls="--", lw=0.5) for i in range(len(synt_x))]
            [plt.axhline(min(cboard.y) +i*di*cboard.dr, color="black", ls="--", lw=0.5) for i in range(len(synt_y))]
            plt.xlim(min(cboard.x), max(cboard.x)+cboard.dr)
            plt.ylim(min(cboard.y), max(cboard.y)+cboard.dr)
            plt.xlabel("x [km]")
            plt.ylabel("y [km]")
            plt.colorbar(p, orientation="horizontal", location="top", label=f"Checkerboard Input (Block size = {check_size}km)", shrink=0.7)
            plt.gca().set_aspect("equal", adjustable='box')

            if mask_restitution > 0: m[mask] = np.nan
            # vmax = np.nanmax(np.abs(m))
            # vmin = -vmax
            vmin, vmax = min_amplitude, max_amplitude
            plt.subplot(122)
            plt.scatter(stations[:,0]/1e3, stations[:,1]/1e3, zorder=20, color="black", s=5, marker=".")
            p = plt.pcolormesh(x/1e3+cboard.dr/2, y/1e3+cboard.dr/2, m, cmap=cmap, vmin=vmin, vmax=vmax)
            [plt.axvline(min(cboard.x) +i*di*cboard.dr, color="black", ls="--", lw=0.5) for i in range(len(synt_x))]
            [plt.axhline(min(cboard.y) +i*di*cboard.dr, color="black", ls="--", lw=0.5) for i in range(len(synt_y))]
            plt.xlim(min(cboard.x), max(cboard.x)+cboard.dr)
            plt.ylim(min(cboard.y), max(cboard.y)+cboard.dr)
            plt.xlabel("x [km]")
            plt.ylabel("y [km]")
            plt.colorbar(p, orientation="horizontal", location="top", label="Checkerboard Inverted", shrink=0.7)
            plt.gca().set_aspect("equal", adjustable='box')

            plt.show()
        else:
            return x, y, synt_model, m, size



    def simulate(self, name, points=[], size=[], anomalies_ampl=[], background_ampl=0, mask_restitution=0, return_values=False):
        
        data_type = self.dataset[name]["data_type"]

        # Collect current model/data information
        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.build_Cm(stdm=self.stdm, Lambda=self.Lambda, Lambda0=self.Lambda0, show_progress=False)

        # Create synthetic model
        synt_model = np.zeros( (len(model.y),len(model.x)) ) + background_ampl

        if not (len(points) == len(size) == len(anomalies_ampl)):
            print("[ERROR] 'points', 'size', and 'anomalies_ampl' should have the exact same length !")
            return
        else:
            for idx in range(len(points)):
                x0, y0 = points[idx][0]/1e3, points[idx][1]/1e3
                dx, dy = size[idx][0], size[idx][1]
                xi = np.argmin(np.abs(model.x - x0))
                xf = np.argmin(np.abs(model.x - (x0 + dx)))
                yi = np.argmin(np.abs(model.y - y0))
                yf = np.argmin(np.abs(model.y - (y0 + dy)))
                synt_model[yi:yf+1,xi:xf+1] = anomalies_ampl[idx]

        model.add_dataset(name,
                        self.dataset[name]["data"],
                        self.dataset[name]["coherence"],
                        self.dataset[name]["coordinates"],
                        self.dataset[name]["stations"],
                        self.dataset[name]["freq"],
                        self.dataset[name]["c"],
                        self.dataset[name]["l"],
                        self.dataset[name]["lagtime"],
                        data_type=data_type)
        model._KERNELS = self._KERNELS
        data = self.dataset[name]["data"]
        coherence = self.dataset[name]["coherence"]
        coordinates = self.dataset[name]["coordinates"]
        stations = self.dataset[name]["stations"]

        N = len(data)
        M = model.M
        K = np.zeros((N,M))


        # Simulate data based on model and sensitivity kernels
        G = np.zeros((N,M))
        dataset = model.dataset[name]
        for idx, pair_name in enumerate(dataset["stations"]):
            coord1, coord2 = dataset["coordinates"][idx]
            sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
            sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3
            t = dataset["t"][idx]
            c = dataset["c"][idx]
            l = dataset["l"][idx]
            alpha = dataset["alpha"][idx]
            freq = dataset["freq"][idx]
            K = model._KERNELS[pair_name][(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)].flatten()
            
            if data_type=="velocity":
                G[idx,:] = self.DV / t * K
            elif data_type=="coherence":
                G[idx,:] = c * self.DV / 2 * K

        data = G @ synt_model.flatten()
        model.add_dataset(name, data, coherence, coordinates, stations,
                            dataset["freq"], dataset["c"], dataset["l"], dataset["lagtime"], data_type)

        # Invert data
        model.invert(name, show_progress=False)
        
        if mask_restitution > 0:
            R = model.get_restitution_index(name)
            mask = R < mask_restitution

        st_pairs = model.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))

        x, y, _, m = model.get_model(name)

        # Plot checkerboard test
        if not return_values:
            if mask_restitution > 0: synt_model[mask] = np.nan
            vmin = np.nanmin([np.nanmin(anomalies_ampl), background_ampl])
            vmax = np.nanmax([np.nanmax(anomalies_ampl), background_ampl])
            plt.figure(figsize=(15,7))
            plt.subplot(121)
            plt.scatter(stations[:,0]/1e3, stations[:,1]/1e3, zorder=20, color="black", s=5, marker=".")
            p = plt.pcolormesh(model.x+model.dr/2, model.y+model.dr/2, synt_model, vmin=vmin, vmax=vmax, cmap="coolwarm")
            # [plt.plot([min(model.x),max(model.x)+model.dr], [yi,yi], color="black", ls=":", lw=1) for yi in model.y]
            # [plt.plot([xi,xi], [min(model.y),max(model.y)+model.dr], color="black", ls=":", lw=1) for xi in model.x]
            # plt.plot([min(model.x),max(model.x)+model.dr], [max(model.y)+model.dr,max(model.y)+model.dr], color="black", ls=":", lw=1)
            # plt.plot([max(model.x)+model.dr,max(model.x)+model.dr], [min(model.y),max(model.y)+model.dr], color="black", ls=":", lw=1)
            if mask_restitution > 0:
                for idx in range(len(points)):
                    x0, y0 = points[idx][0]/1e3, points[idx][1]/1e3
                    dx, dy = size[idx][0], size[idx][1]
                    xi = np.argmin(np.abs(model.x - x0))
                    xf = np.argmin(np.abs(model.x - (x0 + dx)))
                    yi = np.argmin(np.abs(model.y - y0))
                    yf = np.argmin(np.abs(model.y - (y0 + dy)))
                    dx = (model.x[xf]-model.x[xi])+model.dr
                    dy = (model.y[yf]-model.y[yi])+model.dr
                    rectangle = patches.Rectangle((model.x[xi], model.y[yi]), dx, dy, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
                    plt.gca().add_patch(rectangle)
            plt.xlim(min(model.x), max(model.x)+model.dr)
            plt.ylim(min(model.y), max(model.y)+model.dr)
            plt.xlabel("x [km]")
            plt.ylabel("y [km]")
            plt.colorbar(p, orientation="horizontal", location="top", label="Initial model", shrink=0.7)
            plt.gca().set_aspect("equal", adjustable='box')
            
            if mask_restitution > 0: m[mask] = np.nan
            vmax = np.nanmax(np.abs(m))
            vmin = -vmax
            plt.subplot(122)
            plt.scatter(stations[:,0]/1e3, stations[:,1]/1e3, zorder=20, color="black", s=5, marker=".")
            p = plt.pcolormesh(x/1e3+model.dr/2, y/1e3+model.dr/2, m, cmap="coolwarm", vmin=vmin, vmax=vmax)
            # [plt.plot([min(model.x)/1e3,max(model.x)/1e3+model.dr], [yi/1e3,yi/1e3], color="black", ls="-", lw=1) for yi in model.x]
            # [plt.plot([xi/1e3,xi/1e3], [min(model.y)/1e3,max(model.y)/1e3+model.dr], color="black", ls="-", lw=1) for xi in model.y]
            # plt.plot([min(model.x),max(model.x)+model.dr], [max(model.y)+model.dr,max(model.y)+model.dr], color="black", ls="-", lw=1)
            # plt.plot([max(model.x)+model.dr,max(model.x)+model.dr], [min(model.y),max(model.y)+model.dr], color="black", ls="-", lw=1)
            for idx in range(len(points)):
                x0, y0 = points[idx][0]/1e3, points[idx][1]/1e3
                dx, dy = size[idx][0], size[idx][1]
                xi = np.argmin(np.abs(model.x - x0))
                xf = np.argmin(np.abs(model.x - (x0 + dx)))
                yi = np.argmin(np.abs(model.y - y0))
                yf = np.argmin(np.abs(model.y - (y0 + dy)))
                dx = (model.x[xf]-model.x[xi])+model.dr
                dy = (model.y[yf]-model.y[yi])+model.dr
                rectangle = patches.Rectangle((model.x[xi], model.y[yi]), dx, dy, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
                plt.gca().add_patch(rectangle)
            plt.xlim(min(model.x), max(model.x)+model.dr)
            plt.ylim(min(model.y), max(model.y)+model.dr)
            plt.xlabel("x [km]")
            plt.ylabel("y [km]")
            plt.colorbar(p, orientation="horizontal", location="top", label="Inverted results", shrink=0.7)
            plt.gca().set_aspect("equal", adjustable='box')

            plt.show()
        else:
            return x, y, synt_model, m



    def restitution_index3D(self, name, stdm=None, Lambda=None, Xpos=None, Ypos=None, Zpos=None,):
        
        data_type = self.dataset[name]["data_type"]

        if stdm == None: stdm = self.stdm
        if Lambda == None: Lambda = self.Lambda

        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.add_dataset(name,
                        self.dataset[name]["data"],
                        self.dataset[name]["coherence"],
                        self.dataset[name]["coordinates"],
                        self.dataset[name]["stations"],
                        self.dataset[name]["freq"],
                        self.dataset[name]["c"],
                        self.dataset[name]["l"],
                        self.dataset[name]["lagtime"],
                        data_type=data_type)
        model._KERNELS = self._KERNELS
        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=self.Lambda0, show_progress=False)

        st_pairs = self.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))


        model.build_Cm(stdm=stdm, Lambda=Lambda, Lambda0=model.Lambda0, show_progress=False)
        model.invert(name, show_progress=False)
        x, y, z, _ = model.get_model(name)
        Rsum = model.get_restitution_index(name)

        Xpos = (max(x)+min(x))/2 if Xpos==None else Xpos
        Ypos = (max(y)+min(y))/2 if Ypos==None else Ypos
        Zpos = (max(z)+min(z))/2 if Zpos==None else Zpos

        idxX = np.argmin(np.abs(x-Xpos))
        idxY = np.argmin(np.abs(y-Ypos))
        idxZ = np.argmin(np.abs(z-Zpos))

        Ridx_hor = Rsum[idxZ,:,:]
        Ridx_lat = Rsum[:,:,idxX].T
        Ridx_lon = Rsum[:,idxY,:]

        vmin = 0
        vmax = np.nanmax(Rsum)
        cmap = cm.get_cmap('turbo', 20)

        fig, axs = plt.subplots(2, 2, figsize=(10,10))
        plt.subplots_adjust(hspace=0, wspace=0)

        ax = axs[0,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelbottom=False, labeltop=True)
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Distance [km]")
        ax.xaxis.set_label_position('top')
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, Ridx_hor, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        ax.set_aspect("equal", adjustable='box')
        ax.axvline(x[idxX]+model.dr/2*1e3, color="black", lw=0.7, ls="--")
        ax.axhline(y[idxY]+model.dr/2*1e3, color="black", lw=0.7, ls="--")

        ax = axs[0,1]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelleft=False, labelright=True)
        ax.set_xlabel("Depth [km]")
        ax.set_ylabel("Distance [km]")
        ax.yaxis.set_label_position('right')
        ax.pcolormesh(z+model.dz/2, y+model.dr/2*1e3, Ridx_lat, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
        ax.axvline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")

        ax = axs[1,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True)   
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Depth [km]")
        ax.pcolormesh(x+model.dr/2*1e3, z+model.dz/2, Ridx_lon, cmap=cmap, vmin=vmin, vmax=vmax, zorder=0)
        ax.invert_yaxis()
        ax.axhline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")


        # Place bottom left subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[1,0].set_position([new_x0_bot, pos_top.y0-depth_width, pos_top.width, depth_width])

        # Place top right subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[0,1].set_position([right_top, pos_top.y0, depth_width, pos_top.height])

        # Place colorbar subplot
        pos_bl = axs[1,0].get_position()
        pos_tr = axs[0,1].get_position()
        axs[1,1].set_position([pos_tr.x0, pos_bl.y0, pos_tr.width, pos_bl.height])
        axs[1,1].axis("off")
        cax = axs[1,1].inset_axes([0,0,1,0.5]) ; cax.axis("off")
        fig.colorbar(p, ax=cax, orientation="horizontal", label="Restitution index", shrink=0.8, fraction=1)

        plt.show()



    def checker_board3D(self, name, size_horizontal, size_vertical, Xpos=None, Ypos=None, Zpos=None, min_amplitude=-1, max_amplitude=1, mask_restitution=0):
        
        data_type = self.dataset[name]["data_type"]

        # Collect current model/data information
        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.build_Cm(stdm=self.stdm, Lambda=self.Lambda, Lambda0=self.Lambda0, show_progress=False)

        # Synthetic checkerboard model
        di = int(size_horizontal / model.dr)
        dz = int(size_vertical / model.dz)
        check_size = di*model.dr
        nx = len(model.x)
        ny = len(model.y)
        nz = len(model.z)
        synt_model = np.ones((nx, ny, nz))
        X, Y, Z = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
        synt_model[((X // di) + (Y // di) + ((Z // dz))) % 2 == 0] = -1
        synt_model = synt_model.T

        model.add_dataset(name,
                        self.dataset[name]["data"],
                        self.dataset[name]["coherence"],
                        self.dataset[name]["coordinates"],
                        self.dataset[name]["stations"],
                        self.dataset[name]["freq"],
                        self.dataset[name]["c"],
                        self.dataset[name]["l"],
                        self.dataset[name]["lagtime"],
                        data_type=data_type)
        model._KERNELS = self._KERNELS
        data = self.dataset[name]["data"]
        coherence = self.dataset[name]["coherence"]
        coordinates = self.dataset[name]["coordinates"]
        stations = self.dataset[name]["stations"]
            
        N = len(data)
        M = model.M
        K = np.zeros((N,M))

        # Simulate data based on model and sensitivity kernels
        G = np.zeros((N,M))
        dataset = model.dataset[name]
        for idx, pair_name in enumerate(dataset["stations"]):
            coord1, coord2 = dataset["coordinates"][idx]
            sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
            sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3
            t = dataset["t"][idx]
            c = dataset["c"][idx]
            l = dataset["l"][idx]
            alpha = dataset["alpha"][idx]
            freq = dataset["freq"][idx]
            K = model._KERNELS[pair_name][(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)].flatten()
            
            if data_type=="velocity":
                G[idx,:] = self.DV / t * K
            elif data_type=="coherence":
                G[idx,:] = c * self.DV / 2 * K
                
        #####################      
        # !!!!!! A ENLEVER A TERME
        # ça vient du fait que parfois les noyaux K sont remplis de NaN
        # comprendre d'où ça vient ??
        # Note : vu à BF (1/4 - 1/2 s pour la première bande de lagtime dans la coda)
        # Mauvaise vitesse, donc ça fait un soucis pour le calcul du noyau ???
        G = np.nan_to_num(G, nan=0.0)
        #####################

        data = G @ synt_model.flatten()
        model.add_dataset(name, data, coherence, coordinates, stations,
                            dataset["freq"], dataset["c"], dataset["l"], dataset["lagtime"], data_type)


        # Invert data
        model.invert(name, show_progress=True)
        
        if mask_restitution > 0:
            R = model.get_restitution_index(name)
            mask = R < mask_restitution

        st_pairs = model.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))
        
        x, y, z, m = model.get_model(name)
        if mask_restitution > 0:
            synt_model[mask] = np.nan
            m[mask] = np.nan

        Xpos = (max(x)+min(x))/2 if Xpos==None else Xpos
        Ypos = (max(y)+min(y))/2 if Ypos==None else Ypos
        Zpos = (max(z)+min(z))/2 if Zpos==None else Zpos

        idxX = np.argmin(np.abs(x-Xpos))
        idxY = np.argmin(np.abs(y-Ypos))
        idxZ = np.argmin(np.abs(z-Zpos))
        
        
        # Figures
        fig, axs = plt.subplots(2, 5, figsize=(15,10))
        plt.subplots_adjust(hspace=0, wspace=0)

        ### Initial model
        vmin = min_amplitude
        vmax = max_amplitude
        
        ax = axs[0,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelbottom=False, labeltop=True)
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Distance [km]")
        ax.xaxis.set_label_position('top')
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, synt_model[idxZ,:,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        ax.set_aspect("equal", adjustable='box')
        ax.axvline(x[idxX]+model.dr/2*1e3, color="black", lw=0.7, ls="--")
        ax.axhline(y[idxY]+model.dr/2*1e3, color="black", lw=0.7, ls="--")

        ax = axs[0,1]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelleft=False, labelright=True)
        ax.set_xlabel("Depth [km]")
        ax.set_ylabel("Distance [km]")
        ax.yaxis.set_label_position('right')
        ax.pcolormesh(z+model.dz/2, y+model.dr/2*1e3, synt_model[:,:,idxX].T, cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.axvline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")

        ax = axs[1,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True)   
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Depth [km]")
        ax.pcolormesh(x+model.dr/2*1e3, z+model.dz/2, synt_model[:,idxY,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.invert_yaxis()
        ax.axhline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")


        # Place bottom left subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[1,0].set_position([new_x0_bot, pos_top.y0-depth_width, pos_top.width, depth_width])

        # Place top right subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[0,1].set_position([right_top, pos_top.y0, depth_width, pos_top.height])

        # Place colorbar subplot
        pos_bl = axs[1,0].get_position()
        pos_tr = axs[0,1].get_position()
        axs[1,1].set_position([pos_tr.x0, pos_bl.y0, pos_tr.width, pos_bl.height])
        axs[1,1].axis("off")
        cax = axs[1,1].inset_axes([0,0,1,0.5]) ; cax.axis("off")
        fig.colorbar(p, ax=cax, orientation="horizontal", label="Initial model", shrink=0.8, fraction=1)
        
        
        # Inverted model
        vmax = np.nanmax(abs(m))
        vmin = -vmax
        
        
        ax = axs[0,3]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelbottom=False, labeltop=True)
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Distance [km]")
        ax.xaxis.set_label_position('top')
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, m[idxZ,:,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        ax.set_aspect("equal", adjustable='box')
        ax.axvline(x[idxX]+model.dr/2*1e3, color="black", lw=0.7, ls="--")
        ax.axhline(y[idxY]+model.dr/2*1e3, color="black", lw=0.7, ls="--")

        ax = axs[0,4]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelleft=False, labelright=True)
        ax.set_xlabel("Depth [km]")
        ax.set_ylabel("Distance [km]")
        ax.yaxis.set_label_position('right')
        ax.pcolormesh(z+model.dz/2, y+model.dr/2*1e3, m[:,:,idxX].T, cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.axvline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")

        ax = axs[1,3]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True)   
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Depth [km]")
        ax.pcolormesh(x+model.dr/2*1e3, z+model.dz/2, m[:,idxY,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.invert_yaxis()
        ax.axhline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")


        # Place bottom left subplot
        pos_top = axs[0,3].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[1,3].set_position([new_x0_bot, pos_top.y0-depth_width, pos_top.width, depth_width])

        # Place top right subplot
        pos_top = axs[0,3].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[0,4].set_position([right_top, pos_top.y0, depth_width, pos_top.height])

        # Place colorbar subplot
        pos_bl = axs[1,3].get_position()
        pos_tr = axs[0,4].get_position()
        axs[1,4].set_position([pos_tr.x0, pos_bl.y0, pos_tr.width, pos_bl.height])
        axs[1,4].axis("off")
        cax = axs[1,4].inset_axes([0,0,1,0.5]) ; cax.axis("off")
        fig.colorbar(p, ax=cax, orientation="horizontal", label="Inverted results", shrink=0.8, fraction=1)
        
        axs[0,2].axis("off"); axs[1,2].axis("off")

        plt.show()


        
    def simulate3D(self, name, points=[], size=[], anomalies_ampl=[], background_ampl=0, Xpos=None, Ypos=None, Zpos=None, Nstations=None, mask_restitution=0):
        
        data_type = self.dataset[name]["data_type"]

        # Collect current model/data information
        model = Inversion(xmin=self.xmin*1e3, xmax=self.xmax*1e3, ymin=self.ymin*1e3, ymax=self.ymax*1e3, zmin=self.zmin, zmax=self.zmax, dr=self.dr, dz=self.dz)
        model.build_velocity_model(self.velocity_model)
        model.build_Cm(stdm=self.stdm, Lambda=self.Lambda, Lambda0=self.Lambda0, show_progress=False)

        # Create synthetic model
        synt_model = np.zeros( (len(model.z), len(model.y),len(model.x)) ) + background_ampl

        if not (len(points) == len(size) == len(anomalies_ampl)):
            print("[ERROR] 'points', 'size', and 'anomalies_ampl' should have the exact same length !")
            return
        else:
            for idx in range(len(points)):
                x0, y0, z0 = points[idx][0]/1e3, points[idx][1]/1e3, points[idx][2]
                dx, dy, dz = size[idx][0], size[idx][1], size[idx][2]
                xi = np.argmin(np.abs(model.x - x0))
                xf = np.argmin(np.abs(model.x - (x0 + dx)))
                yi = np.argmin(np.abs(model.y - y0))
                yf = np.argmin(np.abs(model.y - (y0 + dy)))
                zi = np.argmin(np.abs(model.z - z0))
                zf = np.argmin(np.abs(model.z - (z0 + dz)))
                synt_model[zi:zf+1, yi:yf+1, xi:xf+1] = anomalies_ampl[idx]

        model.add_dataset(name,
                        self.dataset[name]["data"],
                        self.dataset[name]["coherence"],
                        self.dataset[name]["coordinates"],
                        self.dataset[name]["stations"],
                        self.dataset[name]["freq"],
                        self.dataset[name]["c"],
                        self.dataset[name]["l"],
                        self.dataset[name]["lagtime"],
                        data_type=data_type)
        model._KERNELS = self._KERNELS
        data = self.dataset[name]["data"]
        coherence = self.dataset[name]["coherence"]
        coordinates = self.dataset[name]["coordinates"]
        stations = self.dataset[name]["stations"]
            
        N = len(data)
        M = model.M
        K = np.zeros((N,M))

        # Simulate data based on model and sensitivity kernels
        G = np.zeros((N,M))
        dataset = model.dataset[name]
        for idx, pair_name in enumerate(dataset["stations"]):
            coord1, coord2 = dataset["coordinates"][idx]
            sta1x, sta1y = coord1[0]/1e3, coord1[1]/1e3
            sta2x, sta2y = coord2[0]/1e3, coord2[1]/1e3
            t = dataset["t"][idx]
            c = dataset["c"][idx]
            l = dataset["l"][idx]
            alpha = dataset["alpha"][idx]
            freq = dataset["freq"][idx]
            K = model._KERNELS[pair_name][(sta1x, sta1y, sta2x, sta2y, t, c, l, alpha, freq)].flatten()
            
            if data_type=="velocity":
                G[idx,:] = self.DV / t * K
            elif data_type=="coherence":
                G[idx,:] = c * self.DV / 2 * K
                
        #####################      
        # !!!!!! A ENLEVER A TERME
        # ça vient du fait que parfois les noyaux K sont remplis de NaN
        # comprendre d'où ça vient ??
        # Note : vu à BF (1/4 - 1/2 s pour la première bande de lagtime dans la coda)
        # Mauvaise vitesse, donc ça fait un soucis pour le calcul du noyau ???
        G = np.nan_to_num(G, nan=0.0)
        #####################

        data = G @ synt_model.flatten()
        model.add_dataset(name, data, coherence, coordinates, stations,
                            dataset["freq"], dataset["c"], dataset["l"], dataset["lagtime"], data_type)

        # Invert data
        model.invert(name, show_progress=False)
        if mask_restitution > 0:
            R = model.get_restitution_index(name)
            mask = R < mask_restitution

        st_pairs = model.dataset[name]["coordinates"]
        stations = []
        for idx in range(len(st_pairs)):
            stations.append((st_pairs[idx][0][0],st_pairs[idx][0][1]))
            stations.append((st_pairs[idx][1][0],st_pairs[idx][1][1]))
        stations = np.array(list(set(list(stations))))
        
        x, y, z, m = model.get_model(name)
        if mask_restitution > 0:
            synt_model[mask] = np.nan
            m[mask] = np.nan

        Xpos = (max(x)+min(x))/2 if Xpos==None else Xpos
        Ypos = (max(y)+min(y))/2 if Ypos==None else Ypos
        Zpos = (max(z)+min(z))/2 if Zpos==None else Zpos

        idxX = np.argmin(np.abs(x-Xpos))
        idxY = np.argmin(np.abs(y-Ypos))
        idxZ = np.argmin(np.abs(z-Zpos))
        
        
        # Figures
        fig, axs = plt.subplots(2, 5, figsize=(15,10))
        plt.subplots_adjust(hspace=0, wspace=0)

        ### Initial model
        vmin = np.min([np.min(anomalies_ampl), background_ampl])
        vmax = np.max([np.max(anomalies_ampl), background_ampl])
        
        ax = axs[0,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelbottom=False, labeltop=True)
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Distance [km]")
        ax.xaxis.set_label_position('top')
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, synt_model[idxZ,:,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        ax.set_aspect("equal", adjustable='box')
        ax.axvline(x[idxX]+model.dr/2*1e3, color="black", lw=0.7, ls="--")
        ax.axhline(y[idxY]+model.dr/2*1e3, color="black", lw=0.7, ls="--")

        ax = axs[0,1]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelleft=False, labelright=True)
        ax.set_xlabel("Depth [km]")
        ax.set_ylabel("Distance [km]")
        ax.yaxis.set_label_position('right')
        ax.pcolormesh(z+model.dz/2, y+model.dr/2*1e3, synt_model[:,:,idxX].T, cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.axvline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")

        ax = axs[1,0]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True)   
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Depth [km]")
        ax.pcolormesh(x+model.dr/2*1e3, z+model.dz/2, synt_model[:,idxY,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.invert_yaxis()
        ax.axhline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")
        
        for idx in range(len(points)):
            x0, y0, z0 = points[idx][0]/1e3, points[idx][1]/1e3, points[idx][2]
            dx, dy, dz = size[idx][0], size[idx][1], size[idx][2]
            xi = np.argmin(np.abs(model.x - x0))
            xf = np.argmin(np.abs(model.x - (x0 + dx)))
            yi = np.argmin(np.abs(model.y - y0))
            yf = np.argmin(np.abs(model.y - (y0 + dy)))
            zi = np.argmin(np.abs(model.z - z0))
            zf = np.argmin(np.abs(model.z - (z0 + dz)))
            dx = (model.x[xf]-model.x[xi])+model.dr
            dy = (model.y[yf]-model.y[yi])+model.dr
            dz = (model.z[zf]-model.z[zi])+model.dz
            
            rectangle = patches.Rectangle((model.x[xi]*1e3, model.y[yi]*1e3), dx*1e3, dy*1e3, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[0,0].add_patch(rectangle)
            
            rectangle = patches.Rectangle((model.z[zi], model.y[yi]*1e3), dz, dy*1e3, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[0,1].add_patch(rectangle)
            
            rectangle = patches.Rectangle((model.x[xi]*1e3, model.z[zi]), dx*1e3, dz, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[1,0].add_patch(rectangle)


        # Place bottom left subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[1,0].set_position([new_x0_bot, pos_top.y0-depth_width, pos_top.width, depth_width])

        # Place top right subplot
        pos_top = axs[0,0].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[0,1].set_position([right_top, pos_top.y0, depth_width, pos_top.height])

        # Place colorbar subplot
        pos_bl = axs[1,0].get_position()
        pos_tr = axs[0,1].get_position()
        axs[1,1].set_position([pos_tr.x0, pos_bl.y0, pos_tr.width, pos_bl.height])
        axs[1,1].axis("off")
        cax = axs[1,1].inset_axes([0,0,1,0.5]) ; cax.axis("off")
        fig.colorbar(p, ax=cax, orientation="horizontal", label="Initial model", shrink=0.8, fraction=1)
        
        
        # Inverted model
        vmax = np.max(abs(m))
        vmin = -vmax
        
        
        
        ax = axs[0,3]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelbottom=False, labeltop=True)
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Distance [km]")
        ax.xaxis.set_label_position('top')
        p = ax.pcolormesh(x+model.dr/2*1e3, y+model.dr/2*1e3, m[idxZ,:,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.scatter(stations[:,0], stations[:,1], zorder=20, color="black", s=5, marker=".")
        ax.set_aspect("equal", adjustable='box')
        ax.axvline(x[idxX]+model.dr/2*1e3, color="black", lw=0.7, ls="--")
        ax.axhline(y[idxY]+model.dr/2*1e3, color="black", lw=0.7, ls="--")

        ax = axs[0,4]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True, labelleft=False, labelright=True)
        ax.set_xlabel("Depth [km]")
        ax.set_ylabel("Distance [km]")
        ax.yaxis.set_label_position('right')
        ax.pcolormesh(z+model.dz/2, y+model.dr/2*1e3, m[:,:,idxX].T, cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.axvline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")

        ax = axs[1,3]
        ax.tick_params(direction="in", top=True, bottom=True, left=True, right=True)   
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Depth [km]")
        ax.pcolormesh(x+model.dr/2*1e3, z+model.dz/2, m[:,idxY,:], cmap="coolwarm", vmin=vmin, vmax=vmax, zorder=0)
        ax.invert_yaxis()
        ax.axhline(z[idxZ]+model.dz/2, color="black", lw=0.7, ls="--")
        
        for idx in range(len(points)):
            x0, y0, z0 = points[idx][0]/1e3, points[idx][1]/1e3, points[idx][2]
            dx, dy, dz = size[idx][0], size[idx][1], size[idx][2]
            xi = np.argmin(np.abs(model.x - x0))
            xf = np.argmin(np.abs(model.x - (x0 + dx)))
            yi = np.argmin(np.abs(model.y - y0))
            yf = np.argmin(np.abs(model.y - (y0 + dy)))
            zi = np.argmin(np.abs(model.z - z0))
            zf = np.argmin(np.abs(model.z - (z0 + dz)))
            dx = (model.x[xf]-model.x[xi])+model.dr
            dy = (model.y[yf]-model.y[yi])+model.dr
            dz = (model.z[zf]-model.z[zi])+model.dz
            
            rectangle = patches.Rectangle((model.x[xi]*1e3, model.y[yi]*1e3), dx*1e3, dy*1e3, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[0,3].add_patch(rectangle)
            
            rectangle = patches.Rectangle((model.z[zi], model.y[yi]*1e3), dz, dy*1e3, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[0,4].add_patch(rectangle)
            
            rectangle = patches.Rectangle((model.x[xi]*1e3, model.z[zi]), dx*1e3, dz, edgecolor="black", facecolor="None", linewidth=0.5, ls="--")
            axs[1,3].add_patch(rectangle)


        # Place bottom left subplot
        pos_top = axs[0,3].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[1,3].set_position([new_x0_bot, pos_top.y0-depth_width, pos_top.width, depth_width])

        # Place top right subplot
        pos_top = axs[0,3].get_position()
        depth_width = min([pos_top.width,pos_top.height])/1.5
        right_top = pos_top.x0 + pos_top.width
        new_x0_bot = right_top - pos_top.width
        axs[0,4].set_position([right_top, pos_top.y0, depth_width, pos_top.height])

        # Place colorbar subplot
        pos_bl = axs[1,3].get_position()
        pos_tr = axs[0,4].get_position()
        axs[1,4].set_position([pos_tr.x0, pos_bl.y0, pos_tr.width, pos_bl.height])
        axs[1,4].axis("off")
        cax = axs[1,4].inset_axes([0,0,1,0.5]) ; cax.axis("off")
        fig.colorbar(p, ax=cax, orientation="horizontal", label="Inverted results", shrink=0.8, fraction=1)
        
        axs[0,2].axis("off"); axs[1,2].axis("off")

        plt.show()