#!/usr/bin/env python
import json
import argparse
#import ConfigParser
import firebase_admin

from firebase_admin import credentials
from firebase_admin import firestore

from google.oauth2 import service_account

def initFirestore():
  cred = credentials.Certificate('/Users/andris/src/python/k8sfsc/k8scfs.json') 
  firebase_admin.initialize_app(cred, {
    'projectId': 'lfsk-294616', 
  })
  db = firestore.client()
  return db;


def setClusterNodeJoinCredentials (db,token, master, cluster):
   # db=initFirestore()
  data = {
      u'cluster': cluster,
      u'token':  token,
      u'master': master
  }
  db.collection(u'k8s').document(cluster.upper()).set(data)

def cleanUpClusterNodeJoinCredentials(db, collection=u'k8s'):
  clusters_ref = db.collection(collection)
  docs = clusters_ref.stream()
  for doc in docs:
    db.collection(collection).document(doc.id).delete()

def getClusterNodeJoinCredentials(db):
  clusters_ref = db.collection(u'k8s')
  docs = clusters_ref.stream()

  for doc in docs:
      print(f'{doc.id} => {doc.to_dict()}')
      k8sSett=doc.to_dict()
      k8s_token=k8sSett['token']
      k8s_cluster=k8sSett['cluster']
      k8s_master=k8sSett['master']
      print("token: {} master: {} cluster {}".format(k8s_token,k8s_cluster, k8s_master)) 
      
if __name__ == "__main__": 
    ap = argparse.ArgumentParser()
    # Add the arguments to the parser
    ap.add_argument("-s","--set",required=False,action='store_true', help="set cluster join settings")
    ap.add_argument("-g","--get",required=False,action='store_true',help="get cluster join settings")
    ap.add_argument("-t","--token",required=False, help="set cluster join settings: token")
    ap.add_argument("-m","--master",required=False, help="set cluster join settings: master")
    ap.add_argument("-c","--cluster",required=False, help="set cluster join settings: cluster")
    
    args = ap.parse_args()
    
    #Values to validate the logic of arguments
    mand_keys = set(['set','get'])
    mand_set_keys = set(['cluster','token','master'])
    missing_keys=set()
    missing_set_keys=set()
    
    db=initFirestore()

    #Validate arguments
    for key, value in vars(args).items():
      if key in mand_keys and not value:
         missing_keys.add(key)
      if key in mand_set_keys and value is None:
         missing_set_keys.add(key)
      
    if mand_keys == missing_keys:
      ap.error("at least one of --set and --get required")
    
    if args.set and len(missing_set_keys) !=0 :
      ap.error("for set operations --token, --master and --cluster arguments are mandratory")
     
    if args.set:
      cleanUpClusterNodeJoinCredentials(db)
      setClusterNodeJoinCredentials (db,args.token, args.master, args.cluster)

    if  args.get:
      getClusterNodeJoinCredentials(db)
