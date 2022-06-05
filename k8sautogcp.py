import firebase_admin
import threading
from firebase_admin import credentials
from firebase_admin import firestore

from google.oauth2 import service_account
from k8sautocluster import join_cluster 

def gc_init_firestore(credfile, project):
  cred = credentials.Certificate(credfile)
  firebase_admin.initialize_app(cred, {
                                'projectId': project, }
                                )
  db = firestore.client()
  return db


def gc_set_cluster_node_join_credentials(db, token, master, hash, cluster,collection=u'k8s'):
  data = {
      u'cluster': cluster,
      u'token': token,
      u'hash': hash,
      u'master': master
  }
  db.collection(collection).document(cluster.upper()).set(data)


def gc_clean_up_cluster_node_join_credentials(db, collection=u'k8s'):
  clusters_ref = db.collection(collection)
  docs = clusters_ref.stream()
  for doc in docs:
    db.collection(collection).document(doc.id).delete()

def gc_get_cluster_node_join_credentials(db, collection=u'k8s'):
  clusters_ref = db.collection(collection)
  docs = clusters_ref.stream()
  k8s_creds = {}

  for doc in docs:
    k8s_creds = doc.to_dict()
    print(f'{doc.id} => {doc.to_dict()}')
  return  k8s_creds
    #show_cluster_join_command(k8s_creds)


def gc_watch_cluster_node_join_credentials(db, cluster, collection=u'k8s'):
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

