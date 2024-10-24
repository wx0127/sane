import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import os
import pickle
import sys
from scipy.stats import zscore
import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list



def read_coord(n):
    Xcen = []
    cells = []
    with open(n) as f:
        for l in f:
            l = l.rstrip("\n")
            ll = l.split(",")
            cells.append(ll[0])
            Xcen.append((float(ll[-2]), float(ll[-1])))

    Xcen2 = np.empty((len(Xcen), 2), dtype="float32")
    for ind, (i, j) in enumerate(Xcen):
        Xcen2[ind, :] = [j, -1.0 * i]
    Xcen = Xcen2
    return Xcen, cells

def read_expression(n):
    with open(n) as f:
        h = f.readline().rstrip("\n").split()
        h = [xh.replace(".", "-") for xh in h]
        num_gene = sum(1 for _ in f)
    
    mat = np.empty((num_gene, len(h)), dtype="float32")
    genes = []
    
    with open(n) as f:
        f.readline()  # skip header
        for ig, l in enumerate(f):
            l = l.rstrip("\n")
            ll = l.split()
            gene = ll[0]
            values = [float(v) for v in ll[1:]]
            mat[ig, :] = values
            genes.append(gene)
    
    return mat, h, genes

def save_dataset(dset):
    print(f"Loading and saving data for dataset: {dset}")

    mat_file = f"dir_{dset}/Giotto_norm_expr.txt"
    coord_file = f"dir_{dset}/spatial/tissue_positions_list.csv"

    # Ensure the files exist before processing
    if not os.path.exists(mat_file) or not os.path.exists(coord_file):
        print(f"Files for dataset {dset} do not exist. Skipping.")
        return

    mat, cells, genes = read_expression(mat_file)
    Xcen, Xcells = read_coord(coord_file)

    dataset = {
        'mat': mat,
        'cells': cells,
        'genes': genes,
        'Xcen': Xcen,
        'Xcells': Xcells
    }

    with open(f'{dset}_data.pkl', 'wb') as f:
        pickle.dump(dataset, f)

def read_genes(n):
    f = open(n)
    #NUAK1 12.705882 66.176471 0 9
    genes = []
    for l in f:
        l = l.rstrip("\n")
        ll = l.split()
        genes.append(ll[1])
    f.close()
    return genes

def read_query(n):
    f = open(n)
    query = f.readline().rstrip("\n").split()
    f.close()
    return query

#save_dataset(sys.argv[1])
if __name__=="__main__":

    input_dataset = sys.argv[1] #e.g. gsm.list\
    input_query = sys.argv[2] #e.g. sample.query.list
    
    output_gene_list = sys.argv[3]
    
    with open(input_dataset) as f:
        datasets = [line.strip() for line in f]
    
    by_dset = {}
    for i in datasets:
        #print(i)
        #datasets.append("%s_data.pkl"%i)
        with open(f"pickle_files/%s_data.pkl"%i, "rb") as f:
            by_dset[i] = pickle.load(f)
    print(datasets)
    
    genes = read_genes(output_gene_list)
    
    query = read_query(input_query)


    aG = query

    print(genes[1:100])    
    mat_by_dset = {}
    for i in datasets:
        t_dset = i
        mat = by_dset[i]["mat"]
        #mat_z = mat
        mat_z = zscore(mat, axis=1)
        t_gene = by_dset[i]["genes"]
        map_gene = {}
        for ig,g in enumerate(t_gene):
            map_gene[g] = ig
        #mat_by_dset[i] = 

        gene_ids = []
        for gx in aG:
            if not gx in map_gene:
                continue
            gene_ids.append(map_gene[gx])
        gene_ids = np.array(gene_ids)
        avg = np.mean(mat[gene_ids, :], axis=0)
        v1x = np.percentile(avg, 50)
        m2 = np.where(avg>v1x)[0] #condition_high
        v1x = np.percentile(avg, 10)
        m2x = np.where(avg<=v1x)[0] #condition_low

        m2_new = []
        for ix in m2:
            m2_new.append(ix)
        #for ix in m2x:
        #    m2_new.append(ix)
        m2_new = np.array(m2_new)

        mat_new = mat_z[:,m2_new]
        show_gene_ids = []
        show_genes = []

        matx = np.empty((len(genes[1:100]), mat_new.shape[1]), dtype="float32")
        for ig,g in enumerate(genes[1:100]):
            if g in map_gene:
                show_gene_ids.append(map_gene[g])
                show_genes.append(g)
                matx[ig,:] = mat_new[map_gene[g], :]
            else:
                show_genes.append(g)
                matx[ig,:] = 0

        #show_gene_ids = np.array(show_gene_ids)
        #mat_new = mat_new[show_gene_ids, :]

        mat_by_dset[i] = pd.DataFrame(matx, index=show_genes, columns=[f'Condition_{i+1}' for i in range(len(m2_new))])


    '''
    df1 = pd.DataFrame(data1, index=gene_labels, columns=[f'Condition_{i+1}' for i in range(n_conditions)])
df2 = pd.DataFrame(data2, index=gene_labels, columns=[f'Condition_{i+1}' for i in range(n_conditions)])
df3 = pd.DataFrame(data3, index=gene_labels, columns=[f'Condition_{i+1}' for i in range(n_conditions)])
df4 = pd.DataFrame(data4, index=gene_labels, columns=[f'Condition_{i+1}' for i in range(n_conditions)])
    '''
    # Create a 1x4 grid of subplots (all in one row) without gene and condition labels
    #fig, axs = plt.subplots(1, 10, figsize=(50, 50), gridspec_kw={"wspace": 0.1})

    for ind,i in enumerate(datasets):
        print(i)
        col_linkage = linkage(mat_by_dset[i].T, method="ward")
        col_order = leaves_list(col_linkage)

        fig,axs = plt.subplots(1,1, figsize=(5,50), gridspec_kw={"wspace":0.1})
        plt.subplots_adjust(top=0.999, right = 0.99 , left = 0 )
        
        v1 = np.percentile(mat_by_dset[i], 5)
        v2 = np.percentile(mat_by_dset[i], 95)
        # Plot each heatmap on its corresponding subplot without labels
        sns.heatmap(mat_by_dset[i].iloc[:, col_order], cmap='viridis', ax=axs, cbar=False, xticklabels=False, yticklabels=False, vmin=v1, vmax=v2)
        #sns.clustermap(mat_by_dset[i], cmap='viridis', ax=axs[i-start], col_cluster=True, cbar=False, xticklabels=False, yticklabels=False)
        #axs[i-start].set_title("Heatmap %d" % (i-start))
        fig.savefig("output_heatmaps/%s.png" % i, dpi=300, bbox_inches='tight')

    

    '''
sns.heatmap(df2, cmap='viridis', ax=axs[1], cbar=False, xticklabels=False, yticklabels=False)
axs[1].set_title("Heatmap 2")

sns.heatmap(df3, cmap='viridis', ax=axs[2], cbar=False, xticklabels=False, yticklabels=False)
axs[2].set_title("Heatmap 3")

sns.heatmap(df4, cmap='viridis', ax=axs[3], cbar=False, xticklabels=False, yticklabels=False)
axs[3].set_title("Heatmap 4")
    '''
    '''
# Create a common colorbar below all subplots
cbar_ax = fig.add_axes([0.3, 0.05, 0.4, 0.03])  # Adjust the position and size of the color bar
sns.heatmap(df4, cmap='viridis', cbar_ax=cbar_ax, cbar_kws={"orientation": "horizontal"}, xticklabels=False, yticklabels=False)
    '''
    # Show plot
    #plt.show()    

