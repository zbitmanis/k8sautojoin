#!/usr/bin/env python3
#  Unit for K8s join setings storage and cluser join
# Examples:
# Generate the token using kubedm on the master node
# _MASTER=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $3 }')
# _TOKEN=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $5 }')
# _HASH=$(echo $_KUBE_JOIN_COMMAND|awk '{ print $7 }')
#
# Google Cloud Platform
# ./k8sautojoin.py -C gcp --set -c clustera -t ${_TOKEN} -m $_MASTER -a $_HASH
# -f ~/.config/gcloud/service_accounts/k8scfs.json -p k8sp-1234
# 
# AWS
# ./k8sautojoin.py -C aws --set -c clustera -t ${_TOKEN} -m $_MASTER -a $_HASH
#
# Auto join nodes to the cluster nodes will watch
# until the token will be stored within firestore
#
# Google Cloud Platform
# ./k8sautojoin.py --join  -f ~/.config/gcloud/service_accounts/k8scfs.json -p k8sp-1234 --cluster clustera
#
#  AWS 
# ./k8sautojoin.py --join  --cluster clustera

from http import client
import json
import argparse

from cluster import show_cluster_join_command, join_cluster

def main():
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
    ap.add_argument("-f", "--file", required=False, help="set cluster join settings: auth file")
    ap.add_argument("-p", "--project", required=False, help="set cluster join settings: projectid")
    ap.add_argument("-C", "--cloud", required=True, help="cloud provider - currently supported aws,gcp")
    ap.add_argument("-j", "--join", required=False, action='store_true', help="auto join to the cluster")
    
    args = ap.parse_args()
    # Values to validate the logic of arguments
    mand_gcp_keys = set(['file', 'project'])
    mand_keys = set(['set', 'get', 'watch', 'delete', 'join'])
    mand_set_keys = set(['cluster', 'token', 'master', 'hash'])
    mand_watch_keys = set(['cluster'])
    missing_gcp_keys = set()
    missing_keys = set()
    missing_set_keys = set()
    missing_watch_keys = set()

    # Validate arguments
    for key, value in vars(args).items():
      if key in mand_gcp_keys and not value:
         missing_gcp_keys.add(key)
      if key in mand_keys and not value:
         missing_keys.add(key)
      if key in mand_set_keys and value is None:
         missing_set_keys.add(key)
      if key in mand_watch_keys and value is None:
         missing_watch_keys.add(key)

    if mand_keys == missing_keys:
      ap.error("At least one of --set, --get, --join, --delete  or --watch should be chosen")
   
    if args.cloud == 'gcp' and len(missing_gcp_keys) != 0:
      ap.error("For gcp operations --file and --project arguments are mandratory")
   
    if args.set and len(missing_set_keys) != 0:
      ap.error("For set operations --token, --master, --hash and --cluster  arguments are mandratory")
   
    if args.watch and len(missing_watch_keys) != 0:
      ap.error("for watch operations --cluster arguments are mandratory")


    if args.cloud == "gcp":

      from gcp import (
          gc_init_firestore,
          gc_get_cluster_node_join_credentials,
          gc_clean_up_cluster_node_join_credentials,
          gc_watch_cluster_node_join_credentials,
          gc_set_cluster_node_join_credentials)

      db = gc_init_firestore(args.file, args.project)
      
      if args.delete:
        gc_clean_up_cluster_node_join_credentials(db)
      
      if args.set:
        gc_set_cluster_node_join_credentials(db, token=args.token, master=args.master,
                                             cluster=args.cluster, hash=args.hash)
      
      if args.get:
        k8s_creds = gc_get_cluster_node_join_credentials(db, cluster=args.cluster)
        if k8s_creds is None:
          print('No creds for the cluster: {} found'.format(args.cluster))
        else:
          show_cluster_join_command(k8s_creds)
      
      if args.watch:
        gc_watch_cluster_node_join_credentials(db, args.cluster)

    elif args.cloud == "aws":

      from aws import (
          aws_clean_up_cluster_node_join_credentials,
          aws_set_cluster_node_join_credentials,
          aws_get_cluster_node_join_credentials,
          aws_init_dynamodb,
          aws_init_dynamodb_table,
          aws_watch_cluster_node_join_credentials)

      client = aws_init_dynamodb()
      aws_init_dynamodb_table(client)

      if args.delete:
        aws_clean_up_cluster_node_join_credentials(cluster=args.cluster)

      if args.set:
        aws_clean_up_cluster_node_join_credentials(cluster=args.cluster)
        aws_set_cluster_node_join_credentials(token=args.token, master=args.master, 
                                              cluster=args.cluster, hash=args.hash)
        print('set a new kubadmin join credentials for cluster: {} master: {}'
              .format(args.cluster,args.master))

      if args.get:
        k8s_creds = aws_get_cluster_node_join_credentials(cluster=args.cluster)
        if k8s_creds is None:
          print('no creds for the cluster: {} found'.format(args.cluster))
        else:
          show_cluster_join_command(k8s_creds)
      
      if args.watch:
        k8s_creds = aws_watch_cluster_node_join_credentials(cluster=args.cluster)
        show_cluster_join_command(k8s_creds)
      
      if args.join:
        k8s_creds = aws_watch_cluster_node_join_credentials(cluster=args.cluster)
        show_cluster_join_command(k8s_creds)
        join_cluster(k8s_creds)
    else:
      ap.error("autojoin support gcp and aws cloud providers")

if __name__ == "__main__":
  main()
