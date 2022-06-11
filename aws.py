#!/usr/bin/env python3
import sys
import time
import threading
import boto3

from pprint import pprint
from botocore.exceptions import ClientError


def aws_init_dynamodb(table_name=u'k8sclusters'):
  client = boto3.client('dynamodb')
  return client


def aws_init_dynamodb_table(client=None, table_name=u'k8sclusters'):
  if client is not None:
   client = boto3.client('dynamodb')

  dd_tables = client.list_tables()['TableNames']

  if table_name not in dd_tables:
    try:
      response = client.create_table(
          TableName=table_name,
          AttributeDefinitions=[{
              'AttributeName': 'cluster',
              'AttributeType': 'S',
          }, ],
          KeySchema=[{
              'AttributeName': 'cluster',
              'KeyType': 'HASH',
          }, ],
          ProvisionedThroughput={
              'ReadCapacityUnits': 5,
              'WriteCapacityUnits': 5,
          },
          StreamSpecification={
              'StreamEnabled': True,
              'StreamViewType': 'NEW_IMAGE'
          },
      )
      time.sleep(10)

    except ClientError as e:
      print('Error on init table: {}'.format(e.response['Error']['Message']))


def aws_set_cluster_node_join_credentials(token, master, hash, cluster, table_name=u'k8sclusters', resource=None):
  if resource is None:
      resource = boto3.resource('dynamodb')
  data = {
      u'cluster': cluster,
      u'token': token,
      u'hash': hash,
      u'master': master
  }
  table = resource.Table(table_name)
  response = table.put_item(Item=data)
  return response


def aws_clean_up_cluster_node_join_credentials(cluster, table_name=u'k8sclusters', resource=None):
  if resource is None:
      resource = boto3.resource('dynamodb')
  try:

    table = resource.Table(table_name)
    response = table.delete_item(
        Key={
            "cluster": cluster
        }
    )
  except ClientError as e:
    print('Error on cleaning data: {}'.format(e.response['Error']['Message']))
  else:
      return response


def aws_get_cluster_node_join_credentials(cluster, table_name=u'k8sclusters', resource=None):
  if resource is None:
      resource = boto3.resource('dynamodb')

  k8s_creds = None
  table = resource.Table(table_name)

  try:
    response = table.get_item(Key={'cluster': cluster})
  except ClientError as e:
    print('Error on geting data: {}'.format(e.response['Error']['Message']))
  else:
    if "Item" in response:
      k8s_creds = response['Item']

  return k8s_creds


def aws_watch_cluster_node_join_credentials(cluster, table_name=u'k8sclusters', resource=None):
  if resource is None:
      resource = boto3.resource('dynamodb')

  _delay = 10
  k8s_creds = aws_get_cluster_node_join_credentials(cluster=cluster,
                                                    table_name=table_name,
                                                    resource=resource)

  while k8s_creds is None:
    k8s_creds = aws_get_cluster_node_join_credentials(cluster=cluster,
                                                      table_name=table_name,
                                                      resource=resource)
    time.sleep(_delay)

  return k8s_creds


def aws_watch_cluster_node_join_dynamodbstream(cluster, table_name=u'k8sclusters', client=None):
  if client is None:
    client = boto3.client('dynamodbstreams')

  _delay = 10
  _limit = 10

  response = client.list_streams(TableName=table_name, Limit=_limit)

  if not response['Streams']:
    print('No streams definded for the DynamoDB table: {}'.format(table_name))
    sys.exit(101)

  stream_arn = response['Streams'][0]['StreamArn']
  response = client.describe_stream(StreamArn=stream_arn, Limit=_limit)

  if not response['StreamDescription']['Shards']:
    print('No shards definded for the DynamoDB stream table: {}'.format(stream_arn))
    sys.exit(102)

  shard = response['StreamDescription']['Shards'][0]['ShardId']

  response = client.get_shard_iterator(StreamArn=stream_arn,
                                       ShardId=shard,
                                       ShardIteratorType='TRIM_HORIZON')

  shard_iterator = response['ShardIterator']
  response = client.get_records(ShardIterator=shard_iterator, Limit=_limit)

  records = response['Records']
  while len(records) == 0:

    shard_iterator = response['NextShardIterator']
    response = client.get_records(
        ShardIterator=shard_iterator,
        Limit=_limit
    )
    records = response['Records']
    pprint(response)
    time.sleep(10)
