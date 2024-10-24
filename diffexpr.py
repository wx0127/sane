import sys
import os
import re
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches 
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import seaborn as sns
from scipy.stats import mannwhitneyu
from scipy.stats import ttest_ind
from operator import itemgetter
import datetime
import pickle
#from multiprocessing import Pool, Value, Lock
from multiprocess import Pool, Value, Lock
import time
import shutil

progress_counter = None
lock = None

def clear_output_directory(directory_path):
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)  # Remove the directory and its contents
    os.makedirs(directory_path, exist_ok=True)  # Recreate the empty directory

def load_dataset(dset):
    # Specify the directory where the pickle files are located
    pickle_dir = "pickle_files"  
    
    # Create the full file path
    file_path = os.path.join(pickle_dir, f'{dset}_data.pkl')
    
    # Open and load the pickle file
    with open(file_path, 'rb') as f:
        data = pickle.load(f)
    
    return data

def get_dataset_count(file_path):
    with open(file_path, 'r') as file:
        datasets = file.readlines()
    return len(datasets), datasets

# Function to handle parallel processing with chunks
def parallel_processing(datasets, gene_lists):
    global progress_counter, lock
    total_datasets = len(datasets)
    
    # Shared progress counter and lock for safe updates
    progress_counter = Value('i', 0)
    lock = Lock()

    with Pool(processes=16) as pool:
            results = pool.starmap(process_dataset, [(dset, gene_lists, total_datasets) for dset in datasets])
        
    # Collect results
    result_by_dset = {dset: aList for dset, aList in results}
    return result_by_dset

def process_dataset(dset, gene_lists, total_datasets):

    global progress_counter, lock

    start_time = time.time()
    print(f"Processing dataset {dset}...")
    sys.stdout.flush()

    # Load only the required dataset
    data = load_dataset(dset)
    Xcells = data['Xcells']
    mat = data['mat']
    cells = data['cells']
    genes = data['genes']
    Xcen = data['Xcen']

    map_cell = {c: ic for ic, c in enumerate(Xcells)}
    good_cell_ind = np.array([map_cell[c] for c in cells])
    Xcen = Xcen[good_cell_ind, :]
        
    map_gene = {g: ig for ig, g in enumerate(genes)}
        
    aG = gene_lists[0]
    gene_ids = [map_gene[gx] for gx in aG if gx in map_gene]
    gene_ids = np.array(gene_ids)
    avg = np.mean(mat[gene_ids, :], axis=0)
    v1x = np.percentile(avg, 90)
    m2 = np.where(avg > v1x)[0]
    v1x = np.percentile(avg, 10)
    m2x = np.where(avg <= v1x)[0]
    aList = []
        
    for ig, g in enumerate(genes):
        if sum(mat[ig, m2]) == 0 or sum(mat[ig, m2x]) == 0:
            continue
        t2 = ttest_ind(mat[ig, m2], mat[ig, m2x], equal_var=False)
        t2_ks = mannwhitneyu(mat[ig, m2], mat[ig, m2x])
        if t2[0] > 0 and t2[1] < 0.05 and t2_ks[1] < 0.05:
            aList.append((g, t2[1], t2_ks[1]))
    aList.sort(key=itemgetter(1), reverse=False)

    end_time = time.time()
    print(f"Processing {dset} took {end_time - start_time:.2f} seconds")
    sys.stdout.flush()

    with lock:
        progress_counter.value += 1
        progress = (progress_counter.value / total_datasets) * 100
        sys.stdout.write(f"Progress: {progress:.2f}%\n")
        sys.stdout.flush()

    return dset, aList

# Usage example:
# result_by_dset = parallel_processing(all_mat, all_Xcells, all_cells, all_genes, all_Xcen, gene_lists)

def plot_results(dset_list, gene_lists, output_dir, cmap="Reds", plot_width=3, dot_size=6):
    # Define the size factor and plot size
    size_factor = 3.15  # Size factor for height
    ncol = len(dset_list)  # Number of columns = number of datasets
    nrow = 1  # Single row
    fig_width = plot_width * ncol  # Total figure width
    fig_height = size_factor * nrow  # Set height based on size factor

    # Create the output directory if it doesn't exist
    plot_dir = os.path.join(output_dir, 'output_plots')
    os.makedirs(plot_dir, exist_ok=True)
    
    clear_output_directory(plot_dir)

    # Create a figure with a dynamic width based on the number of plots
    for ct in range(len(dset_list)):
        f, ax = plt.subplots(figsize=(plot_width, fig_height))

        t_dset = dset_list[ct]
        data = load_dataset(t_dset)
        Xcen = data['Xcen']
        Xcells = data['Xcells']
        genes = data['genes']
        cells = data['cells']
        mat = data['mat']

        map_gene = {g: ig for ig, g in enumerate(genes)}
        map_cell = {c: ic for ic, c in enumerate(Xcells)}

        aG = gene_lists[0]
        gene_ids = [map_gene[gx] for gx in aG if gx in map_gene]
        gene_ids = np.array(gene_ids)
        avg = np.mean(mat[gene_ids, :], axis=0)

        good_cell_ind = np.array([map_cell[c] for c in cells])
        Xcen = Xcen[good_cell_ind, :]
        v1 = 0
        v2 = 1.5
        
        

        # Scatter plot for each dataset with dynamic cmap and dot size
        ax.scatter(Xcen[:, 0], Xcen[:, 1], s=dot_size, c=avg, cmap=cmap, vmin=v1, vmax=v2)

        plt.subplots_adjust(top=0.999, right = 0.99 , left = 0 )
        
        # Create a colorbar with the selected colormap
        #cbar = f.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(v1, v2), cmap=cmap), 
        #ax=ax, orientation='vertical', fraction=0.046, pad=0.04)
        #cbar.ax.tick_params(labelsize=8) 
        cbar = f.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(v1, v2), cmap=cmap), 
        ax=ax, orientation='horizontal', fraction=0.046, pad=0.1)  # 'horizontal' for below the plot
        cbar.ax.tick_params(labelsize=8) 
        
        ax.set_facecolor("white")
        ax.axis("off")

        # Add a black outline (rectangle) around each plot
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none', transform=ax.transAxes)
        ax.add_patch(rect)

        # Save the individual plot
        plot_path = os.path.join(plot_dir, f'{t_dset}.png')
        plt.savefig(plot_path, dpi=200)
        plt.close(f)  # Close the figure to avoid memory issues
        



def plot_results_2(dset_list, gene_lists, output_dir, dotSize2 = 6, outlineThickness = 1):
    size_factor = 3.15  # Size factor for height
    ncol = len(dset_list)  # Number of columns = number of datasets
    nrow = 1  # Single row
    plot_width = 3  # Width of each plot
    fig_width = plot_width * ncol  # Total figure width
    fig_height = size_factor * nrow  # Set height based on size factor

    # Create the output directory if it doesn't exist
    plot_dir = os.path.join(output_dir, 'output_plots_2')
    os.makedirs(plot_dir, exist_ok=True)
    
    clear_output_directory(plot_dir)

    for ct in range(len(dset_list)):
        f, ax = plt.subplots(figsize=(plot_width, fig_height))

        t_dset = dset_list[ct]
        data = load_dataset(t_dset)
        Xcen = data['Xcen']
        Xcells = data['Xcells']
        genes = data['genes']
        cells = data['cells']
        mat = data['mat']

        map_gene = {g: ig for ig, g in enumerate(genes)}
        map_cell = {c: ic for ic, c in enumerate(Xcells)}

        aG = gene_lists[0]
        gene_ids = [map_gene[gx] for gx in aG if gx in map_gene]
        gene_ids = np.array(gene_ids)
        avg = np.mean(mat[gene_ids, :], axis=0)

        good_cell_ind = np.array([map_cell[c] for c in cells])
        Xcen = Xcen[good_cell_ind, :]
        v1 = 0
        v2 = 1.5
        
        plt.subplots_adjust(top=0.999, right = 0.99 , left = 0 )

        ax.set_facecolor("white")
        
        v1x = np.percentile(avg, 90)
        m2 = np.where(avg>v1x)[0]
        m2x = np.where(avg<=v1x)[0]
        sc = ax.scatter(Xcen[m2x,0], Xcen[m2x,1], s=dotSize2, facecolors="none", edgecolors="white", linewidths=outlineThickness)
        sc = ax.scatter(Xcen[m2,0], Xcen[m2,1], s=dotSize2, facecolors="none", edgecolors="black", linewidths= outlineThickness)
        
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=2, edgecolor='black', facecolor='none', transform=ax.transAxes)
        ax.add_patch(rect)

        # Save the individual plot
        plot_path = os.path.join(plot_dir, f'{t_dset}.png')
        plt.savefig(plot_path, dpi=200)
        plt.close(f)  # Close the figure to avoid memory issues





def read_query(n):
    f = open(n)
    query = f.readline().rstrip("\n").split()
    f.close()
    return query

def get_AA_list():
    alist = ["GSM6433627", "GSM6433614", "GSM6433613", "GSM6433590", "GSM6433589", "GSM6433588", 
    "GSM6433587", "GSM6433586", "GSM6433585", "GSM6433597", "GSM6433598", "GSM6433599", "GSM6433600", 
    "GSM6433601", "GSM6433602", "GSM6433603", "GSM6433604"]
    return alist

def get_EA_list():
    alist = ["GSM6433596", "GSM6433595", "GSM6433592", "GSM6433591", "GSM6433612", "GSM6433611",
    "GSM6433610", "GSM6433609", "GSM6433608", "GSM6433607", "GSM6433606", "GSM6433605"]
    return alist

if __name__=="__main__":
    
    if "plot_results" == sys.argv[1] :
        try:
        
        
        # Example argument parsing for the `plot_results` function

            input_dataset = sys.argv[2]#e.g. gsm.list
            input_query = sys.argv[3] #e.g. sample.query.list
            customization_params = json.loads(sys.argv[4])  # Customization parameters
            with open(input_dataset) as f:
                dset_list = [line.strip() for line in f]
                
            query = read_query(input_query)
            gene_lists = [query]
            print(f"Customization parameters received: {customization_params}")
            plot_results(dset_list, gene_lists, '', cmap=customization_params['cmap'], 
                        plot_width=customization_params['plotWidth'], dot_size=customization_params['dotSize'])
            plot_results_2(dset_list, gene_lists, '' , dotSize2=customization_params['dotSize2'] , 
                    outlineThickness= customization_params['outlineThickness'])
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:

    
    
        input_dataset = sys.argv[1] #e.g. gsm.list
        input_query = sys.argv[2] #e.g. sample.query.list

        output_png = sys.argv[3] #e.g. output.png
        output_result = sys.argv[4] #e.g. output.gene.list.txt
        output_png2 = sys.argv[5]

        
        

        with open(input_dataset) as f:
            dset_list = [line.strip() for line in f]

    #all_mat, all_cells, all_genes, all_Xcen, all_Xcells = read_all_datasets(input_dataset)
        print("Done reading")


        query = read_query(input_query)
        gene_lists = [query]
    #gene_lists.append(query)
    
        

        customization_params = {
        "cmap": "Reds",  # Default values in case customization data is missing
        "plotWidth": 3,
        "dotSize": 1,
        "dotSize2": 1,
        "outlineThickness": .1
        }

        plot_results(dset_list, gene_lists, '', cmap=customization_params['cmap'], 
        plot_width=customization_params['plotWidth'], dot_size=customization_params['dotSize'])
        
        plot_results_2(dset_list, gene_lists, '' , dotSize2=customization_params['dotSize2'] , 
                    outlineThickness= customization_params['outlineThickness'])



    #result_by_dset = parallel_processing(all_mat, all_Xcells, all_cells, all_genes, all_Xcen, gene_lists)
        result_by_dset = parallel_processing(dset_list, gene_lists)

        EA_list = {}
        AA_list = {}
        EA = list(set(get_EA_list()) & set(result_by_dset.keys()))
        AA = list(set(get_AA_list()) & set(result_by_dset.keys()))
        for dset in EA:
            EA_list[dset] = result_by_dset[dset]
        for dset in AA:
            AA_list[dset] = result_by_dset[dset]
    
        print("Query:", gene_lists[0])

        by_gene = {}
        for dset in result_by_dset:
            for g,i,j in result_by_dset[dset]:
                by_gene.setdefault(g, [])
                by_gene[g].append(np.log(i))
        
        chi_by_gene = {}
        gs = []
        for g in by_gene:
            chi_by_gene[g] = -2.0*np.sum(np.array(by_gene[g]))
            gs.append((g, chi_by_gene[g], chi_by_gene[g], 10, 10))
        '''
        by_gene_EA = {}
        for dset in EA:
            for g, i, j in EA_list[dset]:
                by_gene_EA.setdefault(g, 0)
                by_gene_EA[g]+=1
        by_gene_AA = {}
        for dset in AA:
            for g, i, j in AA_list[dset]:
                by_gene_AA.setdefault(g, 0)
                by_gene_AA[g]+=1

        genes = set(list(by_gene_EA.keys()) + list(by_gene_AA.keys()))
        gs = []
        for g in genes:
            #print(q, g, by_gene_EA.get(g, 0), by_gene_AA.get(g, 0))
            count_EA = by_gene_EA.get(g, 0)
            count_AA = by_gene_AA.get(g, 0)
            size_ratio = len(AA) / len(EA)
            if count_EA==0:
                ratio = count_AA / len(AA) / (1/(len(EA)*2))
                score = ratio * (1.0 * size_ratio +count_AA) / 2
            else:
                ratio = count_AA/ len(AA)  / (count_EA / len(EA))
                score = ratio * (count_EA * size_ratio +count_AA) / 2
            if ratio>1.2 and count_AA/len(AA) >= 0.5:
        #if ratio<1.2 and ratio>1 and count_AA/len(AA) >= 0.5:
                gs.append((g, ratio, score, count_EA, count_AA))
        '''
        gs.sort(key=itemgetter(2), reverse=True)
        fw = open(output_result, "w")
        for rank, (g, c1, c2, c3, c4) in enumerate(gs, start=1):  # Add rank (starting from 1)
            fw.write("%d %s %f %f %d %d\n" % (rank, g, c1, c2, c3, c4))  # Write rank as c5
        fw.close()
