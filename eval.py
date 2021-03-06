import torch
import torch.utils.data
from dataloader import RNA_Dataset
from dataloader import ATAC_Dataset
from model import FC_VAE,FC_Classifier,FC_Autoencoder,Simple_Classifier
from scipy.spatial import cKDTree
import numpy as np

netRNA = FC_Autoencoder(n_input=2613, nz=50,n_hidden=2613)
netATAC = FC_Autoencoder(n_input=815, nz=50,n_hidden=815)

#netRNA = FC_VAE(n_input=2613, nz=50,n_hidden=2613)

#netATAC = FC_VAE(n_input=815, nz=50,n_hidden=815)

def mink(arraylist,k):
    minlist=[]
    minlist_id=list(range(0,k))
    m=[minlist,minlist_id]
    for i in minlist_id:
        minlist.append(arraylist[i])
    for i in range(k,len(arraylist)):
        if arraylist[i]<max(minlist):
            mm=minlist.index(max(minlist))
            del m[0][mm]
            del m[1][mm]
            m[0].append(arraylist[i])
            m[1].append(i)
    return minlist_id
#netClf=FC_Classifier(nz=50,n_out=3)
netConClf=Simple_Classifier(nz=50)

netRNA.eval()
netATAC.eval()
netConClf.eval()

#netRNA.cuda()
#netATAC.cuda()
#netClf.cuda()


def find_mutual_nn(data1, data2, k1, k2, n_jobs):
     k_index_1 = cKDTree(data1).query(x=data2, k=k1, workers=n_jobs)[1]
     k_index_2 = cKDTree(data2).query(x=data1, k=k2, workers=n_jobs)[1]
     #print(k_index_1)
     #print(k_index_2)
     mutual_1 = []
     mutual_2 = []
     sum=0
     for index_2 in range(data2.shape[0]):
         for index_1 in k_index_1[index_2]:
             if index_2 in k_index_2[index_1]:
                 mutual_1.append(index_1)
                 mutual_2.append(index_2)
                 if index_1==index_2:
                   sum+=1
     return sum


def eva():

  #netConClf.load_state_dict(torch.load("AE_condi_adv/netCondClf_1000.pth"))
  RNA_dataset=RNA_Dataset(datadir="mydata/",mode="test")
  ATAC_dataset=ATAC_Dataset(datadir="mydata/",mode="test")
  
  RNA_loader=torch.utils.data.DataLoader(RNA_dataset,batch_size=32,drop_last=False,shuffle=False)
  ATAC_loader=torch.utils.data.DataLoader(ATAC_dataset,batch_size=32,drop_last=False,shuffle=False)
  
  predicted_label=np.zeros(shape=(0,),dtype=int)
  ATAC_class_label=np.zeros(shape=(0,),dtype=int)
  RNA_latent=np.zeros(shape=(0,50))
  ATAC_latent=np.zeros(shape=(0,50))
  RNA_recon=np.zeros(shape=(0,2613))
  ATAC_recon=np.zeros(shape=(0,815))
  
  for idx, (rna_samples,atac_samples) in enumerate(zip(RNA_loader,ATAC_loader)):
    rna_inputs=rna_samples['tensor']
    rna_labels=rna_samples['binary_label']
    atac_inputs=atac_samples['tensor']
    atac_labels=atac_samples['binary_label'] 
    
    #print(ATAC_label.shape)
    #print(atac_labels.shape)
    #print(atac_labels.numpy().shape)
    ATAC_class_label=np.concatenate((ATAC_class_label,atac_labels.numpy()),axis=0)
    
    #rna_inputs=rna_inputs.cuda()
    #atac_inputs=atac_inputs.cuda()
    
    rna_latents,_=netRNA(rna_inputs)
    atac_latents,_=netATAC(atac_inputs)
    
    #_,rna_latents,_,_=netRNA(rna_inputs)
    #_,atac_latents,_,_=netATAC(atac_inputs)
    
    atac_recon=netATAC.decoder(atac_latents)
    rna_recon=netRNA.decoder(rna_latents)
    
    #print(netConClf(atac_latents))
    
    predicted_label=np.concatenate((predicted_label,np.argmax(netConClf(atac_latents).detach().numpy(),axis=1)))
    #print(RNA_predicted_label)
    #break
    
    RNA_latent=np.concatenate((RNA_latent,rna_latents.detach().numpy()),axis=0)
    ATAC_latent=np.concatenate((ATAC_latent,atac_latents.detach().numpy()),axis=0)
    
    RNA_recon=np.concatenate((RNA_recon,rna_recon.detach().numpy()),axis=0)
    ATAC_recon=np.concatenate((ATAC_recon,atac_recon.detach().numpy()),axis=0)
  
  
  #print(ATAC_label.shape)
  
  for k in range(1,6):
    k=k*10
    print("When k = %d"%k)
    pairlist=[]
    classlist=[]
    distlist=[]
    flag=np.zeros(358)
    kright=0
    
    
    for index,i in enumerate(ATAC_latent):
      mini=999999
      minindex=0
      distlist.clear()
      for idx,j in enumerate(RNA_latent):
        dist=np.linalg.norm(i-j)
        distlist.append(dist)
        #print(dist)
        if(dist<mini and flag[idx]==0):
          mini=dist
          minindex=idx
      kindex=mink(distlist,k)
      if(index in kindex):
        kright+=1
      flag[minindex]=1
      pairlist.append(minindex)
      classlist.append(ATAC_class_label[minindex])
    
    ATAC_seq=np.arange(0,358,1)
    
    #print(len(pairlist))
    pairlist=np.array(pairlist)
    
    #print(flag)
    
    classlist=np.array(classlist)
    #print(pairlist)
    #print(classlist)
    print(float(kright)/358.0)
    print(float(np.sum(pairlist==ATAC_seq)))
    print(float(np.sum(ATAC_class_label==classlist)/358.0))
  #print(type(ATAC_label))
  #print(pairlist.shape)
  #print(RNA_latent.shape)
  #print(ATAC_latent.shape)
  #print(RNA_recon.shape)
  #print(ATAC_recon.shape)
  
  sum=find_mutual_nn(RNA_latent,ATAC_latent,10,10,1)
  print(sum)
  
  
for i in range(1,5):
  print("when epoch = %d"%(i*1000))
  netRNA.load_state_dict(torch.load("AE_tri_anchor/netRNA_DE_"+str(1000*i)+".pth"))
  netATAC.load_state_dict(torch.load("AE_tri_anchor/netATAC_DE_"+str(1000*i)+".pth"))
  eva()