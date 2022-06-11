#!/usr/bin/env python
import subprocess


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
    process = subprocess.Popen(['kubeadm', 'join', k8s_master,
                                '--token', k8s_token,
                                '--discovery-token-ca-cert-hash', k8s_hash],
                               stdout=f)

  print('kubeadm join {} --token {} --discovery-token-ca-cert-hash {}'
        .format(k8s_master, k8s_token, k8s_hash))
