#!/usr/bin/env python

#  Unit for K8s join setings storage and cluser join
# Examples:
# Generate the token using kubedm on the master node
#_MASTER=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $3 }')
#_TOKEN=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $5 }')
#_HASH=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $7 }')
#./k8sautojoin.py --set -c clustera -t ${_TOKEN} -m $_MASTER -a $_HASH  
# -f ~/.config/gcloud/service_accounts/k8scfs.json -p k8sp-1234
#
#  Auto join nodes to the cluster nodes will watch 
# until the token will be stored within firestore 
#
# ./k8sautojoin.py --watch  -f ~/.config/gcloud/service_accounts/k8scfs.json -p k8sp-1234 --cluster clustera   

import json
import argparse
import firebase_admin
import threading
import subprocess

from firebase_admin import credentials
from firebase_admin import firestore

from google.oauth2 import service_account


def init_firestore(credfile, project):
  cred = credentials.Certificate(credfile)
  firebase_admin.initialize_app(cred, {
                                'projectId': project, }
                                )
  db = firestore.client()
  return db


def set_cluster_node_join_credentials(db, token, master, hash, cluster,collection=u'k8s'):
  data = {
      u'cluster': cluster,
      u'token': token,
      u'hash': hash,
      u'master': master
  }
  db.collection(collection).document(cluster.upper()).set(data)


def clean_up_cluster_node_join_credentials(db, collection=u'k8s'):
  clusters_ref = db.collection(collection)
  docs = clusters_ref.stream()
  for doc in docs:
    db.collection(collection).document(doc.id).delete()


def get_cluster_node_join_credentials(db, collection=u'k8s'):
  clusters_ref = db.collection(collection)
  docs = clusters_ref.stream()

  for doc in docs:
    k8s_creds = doc.to_dict()
    print(f'{doc.id} => {doc.to_dict()}')
    show_cluster_join_command(k8s_creds)


def show_cluster_join_command(k8s_creds):
  k8s_token = k8s_creds['token']
  k8s_hash = k8s_creds['hash']
  k8s_master = k8s_creds['master']
  print("kubeadm join {} --token {} --discovery-token-ca-cert-hash {}".format(k8s_master, k8s_token, k8s_hash))


def join_cluster(k8s_creds):
  k8s_token = k8s_creds['token']
  k8s_hash = k8s_creds['hash']
  k8s_master = k8s_creds['master']
  with open('join-log.out', 'w') as f:
    process = subprocess.Popen(['kubeadm', 'join', k8s_master, \
                                '--token', k8s_token, \
                                '--discovery-token-ca-cert-hash', \
                                 k8s_hash ], stdout=f)
  print("kubeadm join {} --token {} --discovery-token-ca-cert-hash {}".format(k8s_master, k8s_token, k8s_hash))


def watch_cluster_node_join_credentials(db, cluster, collection=u'k8s'):
    callback_done = threading.Event()

    # Create a callback on_snapshot function to capture changes
    def on_snapshot(doc_snapshot, changes, read_time):

        for change in changes:
            k8s_creds = change.document.to_dict()
            if change.type.name == 'ADDED':
                print(f'Joining using new cluster settings: {change.document.id}')
                join_cluster(k8s_creds)
                callback_done.set()
            elif change.type.name == 'MODIFIED':
                print(f'Joining using modified cluster settings:: {change.document.id}')
                join_cluster(k8s_creds)
                callback_done.set()
            elif change.type.name == 'REMOVED':
                print(f'Cluster join settings removed - going home: {change.document.id}')
                callback_done.set()

    col_query = db.collection(collection).where(u'cluster', u'==', cluster)
    query_watch = col_query.on_snapshot(on_snapshot)

    callback_done.wait(timeout=600)
    query_watch.unsubscribe()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    # Add the arguments to the parser
    ap.add_argument("-s", "--set", required=False, action='store_true', help="set cluster join settings")
    ap.add_argument("-w", "--watch", required=False, action='store_true', help="set cluster join settings")
    ap.add_argument("-g", "--get", required=False, action='store_true', help="get cluster join settings")
    ap.add_argument("-d", "--delete", required=False, action='store_true', help="cleanup cluster join settings")
    ap.add_argument("-t", "--token", required=False, help="set cluster join settings: token")
    ap.add_argument("-m", "--master", required=False, help="set cluster join settings: master")
    ap.add_argument("-a", "--hash", required=False, help="set cluster join settings: master")
    ap.add_argument("-c", "--cluster", required=False, help="set cluster join settings: cluster")
    ap.add_argument("-f", "--file", required=True, help="set cluster join settings: auth file")
    ap.add_argument("-p", "--project", required=True, help="set cluster join settings: projectid")

    args = ap.parse_args()

    # Values to validate the logic of arguments
    mand_keys = set(['set', 'get', 'watch', 'delete'])
    mand_set_keys = set(['cluster', 'token', 'master', 'hash'])
    mand_watch_keys = set(['cluster'])
    missing_keys = set()
    missing_set_keys = set()
    missing_watch_keys = set()

    db = init_firestore(args.file, args.project)

    # Validate arguments
    for key, value in vars(args).items():
      if key in mand_keys and not value:
         missing_keys.add(key)
      if key in mand_set_keys and value is None:
         missing_set_keys.add(key)
      if key in mand_watch_keys and value is None:
         missing_watch_keys.add(key)

    if mand_keys == missing_keys:
      ap.error("at least one of --set, --get or --watch required")

    if args.set and len(missing_set_keys) != 0:
      ap.error("for set operations --token, --master and --cluster arguments are mandratory")

    if args.watch and len(missing_watch_keys) != 0:
      ap.error("for watch operations --cluster arguments are mandratory")

    if args.delete:
      clean_up_cluster_node_join_credentials(db)

    if args.set:
      clean_up_cluster_node_join_credentials(db)
      set_cluster_node_join_credentials(db, token=args.token, master=args.master, cluster=args.cluster, hash=args.hash)

    if args.get:
      get_cluster_node_join_credentials(db)

    if args.watch:
      watch_cluster_node_join_credentials(db, args.cluster)
