# K8sAutoJoin 

Application to outo join for kubeadm build  K8s cluster

## Prerequisites 

K8s cluster must to be built with kubeadm 
K8sAutojoin currently supports gcloud and uses firestore as key storage 

Autojoin gcloud service account can be created with the folowing script 
``` 
#!/bin.bash
gcloud iam service-accounts create k8scfs \
    --description="Firestore k8s" \
    --display-name="k8scfs"
gcloud projects add-iam-policy-binding $(_PROJECT) \
    --member="serviceAccount:k8scfs@${_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/datastore.user"
gcloud iam service-accounts keys create k8scfs.json \
    --iam-account=k8scfs@${_PROJECT}.iam.gserviceaccount.com 
```

