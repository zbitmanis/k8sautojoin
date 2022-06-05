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
import threading

from k8sautocluster import show_cluster_join_command, join_cluster 

from k8sautogcp import (
    gc_init_firestore, 
    gc_get_cluster_node_join_credentials, 
    gc_clean_up_cluster_node_join_credentials, 
    gc_watch_cluster_node_join_credentials, 
    gc_set_cluster_node_join_credentials
    )


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

    db = gc_init_firestore(args.file, args.project)

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
      gc_clean_up_cluster_node_join_credentials(db)

    if args.set:
      gc_clean_up_cluster_node_join_credentials(db)
      gc_set_cluster_node_join_credentials(db, token=args.token, master=args.master, cluster=args.cluster, hash=args.hash)

    if args.get:
      k8s_creds = gc_get_cluster_node_join_credentials(db)
      show_cluster_join_command(k8s_creds)

    if args.watch:
      gc_watch_cluster_node_join_credentials(db, args.cluster)
