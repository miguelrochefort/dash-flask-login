import pickle
import copy
import pathlib
import urllib.request
import dash
import math
import datetime as dt
import pytz
from datetime import datetime, timedelta
import pandas as pd
import dateparser
import ahocorasick
import yaml
import re
from urllib.parse import urlparse
from joblib import dump, load
import ast

PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

use_alias = False # TODO

wgu = yaml.load(open(DATA_PATH.joinpath("topics.yaml")), Loader=yaml.FullLoader)

map = {}

def populate_map(node, parent):
  if isinstance(node, str):
    map[node.lower()] = parent # TODO: Multiple parents support
    return None
  if isinstance(node, int):
    map[str(node)] = parent # TODO: Multiple parents support
    return None
  if isinstance(node, dict):
    if "id" in node:
      map[node["id"].lower()] = node
    for key in node.keys():
      if isinstance(node[key], list):
        for child in node[key]:
          populate_map(child, node)
      else:
        child = node[key]
        populate_map(child, node)
    node["parent"] = parent

populate_map(wgu, None)


def get_node(key):
    key = key.lower()
    if key in map:
        return map[key]
    return None

def get_parent(node):
    if node and "parent" in node:
        return node["parent"]
    return None

def get_id(node, use_alias=False):
    if node:
        if use_alias and "alias" in node:
            return get_id(node["alias"], use_alias)
        if "id" in node:
            return node["id"]
        if "parent" in node:
            return get_id(node["parent"], use_alias)
    return None

def get_name(node, use_alias=False):
    if node and "name" in node:
        return node["name"]
    return None

def is_ancestor(a, b):
    if a is None or b is None:
        return False

    node = get_node(b)
    parent = get_parent(node)
    parent_id = get_id(parent)
    if parent_id and parent_id == a:
        return True
    
    return is_ancestor(a, parent_id)



automaton = ahocorasick.Automaton()

for name in map.keys():
    automaton.add_word(name, get_id(get_node(name), use_alias))

automaton.make_automaton()

def search(text):
    try:
        text = text.lower()
        return list(set([key[1] for key in automaton.iter(text) if key[1] is not None]))
    except StopIteration:
        return []

def keyword_method(texts):
    return [search(text) for text in texts]




def get_main_topic(topics):
    # TODO: Improve logic, consider duration and multi-event threshold
    while len(topics) > 1 and is_ancestor(topics[0][0], topics[1][0]):
        topics = topics[1:]
    return topics[0][0]


def sessionize(df, gap, threshold):
  session = 0
  sessions = []

  if df is None or df.empty:
    return pd.DataFrame()

  df = df.sort_values("start")

  previous = None

  for x in df.itertuples():
    start = x[1]
    end = x[2]

    if previous:
      delta = start - previous[1]      
      if delta <= gap:
        previous = (min(previous[0], start), max(previous[1], end))
        sessions.append(session)
        continue
    
    session = session + 1
    sessions.append(session)
    previous = (start, end)
  
  return sessions


def aggregate_weighted_topics(weighted_topics):
  x = {}
  for weighted_topic in list(weighted_topics):
    for weighted_topic2 in weighted_topic:
      topic = weighted_topic2[0]
      weight = weighted_topic2[1]
      if topic not in x:
        x[topic] = timedelta(0)
      
      x[topic] = x[topic] + weight

  return list(sorted([(topic, x[topic]) for topic in x], key=lambda x: x[1], reverse=True))




def predict(df, method):
    df["text"] = (df["app"].astype(str) + " " + df["title"].astype(str) + " " + df["url"].astype(str)).str.lower()
    df["topics"] = method(df["text"].values)
    df = df[df["topics"].str.len() > 0]
    df["weighted_topics"] = df.apply(lambda x: [(topic, x.end - x.start) for topic in x.topics], axis=1)
    df["session"] = sessionize(df, timedelta(minutes=5), timedelta(minutes=5))
    df = df.groupby("session").agg(
        start = ("start", "min"),
        end = ("end", "max"),
        topics = ("weighted_topics", aggregate_weighted_topics),
    )

    df = df[(df["end"] - df["start"]) > timedelta(minutes=5)]
    
    return df






def preprocess_text(text):
  return " ".join(text.lower().split(" ")) # Simpler split, faster, still effective
  # return " ".join(re.split(r'[; +|,\-:/=()_]*', text.lower()))

def event_to_text(event):
  return str(event.app) + " " + str(event.title) + " " + str(event.url)

def get_domain(url):
  if not url:
    return None
  return urlparse(str(url)).netloc

def svc_method(docs):
    svc = load(DATA_PATH.joinpath('svc.joblib'))
    vectorizer = load(DATA_PATH.joinpath('vectorizer.joblib'))
    processed_docs = [preprocess_text(doc) for doc in docs]
    vector = vectorizer.transform(processed_docs)
    predictions = svc.predict(vector)
    topics = [["wgu"] if x == 1 else [] for x in predictions]
    return topics

def augment_data(df):
    df["main_topic"] = df["topics"].apply(lambda x: get_main_topic(x))
    df["parent"] = df["main_topic"].apply(get_node).apply(get_parent).apply(get_id)
    df["main_topic_short"] = df["main_topic"].apply(get_node).apply(get_id)
    df["main_topic_long"] = df["main_topic"].apply(get_node).apply(get_name)
    return df

def load_labels():
    print("LOADING LABELS")  
    df = pd.read_csv(
      DATA_PATH.joinpath("labeled_sessions.csv"), 
      parse_dates=["start", "end"], 
      converters={'topics': ast.literal_eval}
    )

    df = augment_data(df)
    return df

def load_generic(method):
    df = pd.read_csv(DATA_PATH.joinpath("events.csv"), parse_dates=["start", "end"])#, converters={'topics': clean})
    # TODO: Remove long items, probably recorded by accident due to a bug with ActvitiyWatch not considering AFK
    df = df[df.end - df.start < timedelta(hours=3)]
    # TODO: Remove duplicate web browser events (Chrome)
    df = df[~(df.title.astype(str).str.endswith("- Google Chrome"))]
    
    try:
      print("PREDICTING")
      df = df
      df = predict(df, method)
      df = augment_data(df)
      print("PREDICTED")
      return df
    except Exception as e:
      print("ERROR PREDICTING", e)
      return df

def load_keywords():
    print("LOAD KEYWORDS")
    return load_generic(keyword_method)
    
def load_svc():
    print("LOAD SVC")
    return load_generic(svc_method)
















def measure_accuracy():
    print("MEASURE ACCURACY")
    df_labels = load_labels()
    df_predictions = load_keywords()

    df_labels["type"] = "label"
    df_predictions["type"] = "prediction"

    df = pd.concat([df_labels, df_predictions]).sort_values("start")
    df

    intersections = []
    ongoings = []

    for idx, row in df.iterrows():
      for ongoing in reversed(ongoings):
        print(row["main_topic"], ongoing[2])
        if ongoing[1] <= row["start"]:
          ongoings.remove(ongoing)
        elif ongoing[0] != row["type"]: #and str(ongoing[2]).lower() == str(row["main_topic"]).lower():
          intersections.append((row["start"], min(row["end"], ongoing[1]), row["main_topic"]))
      ongoings.append((row["type"], row["end"], row["main_topic"]))

    df = pd.DataFrame(intersections)
    df["start"] = df[0]
    df["end"] = df[1]
    df["duration"] = df["end"] - df["start"]
    df["summary"] = "Intersection"
    df
    df_intersections = df

    labels_duration = (df_labels.end - df_labels.start).sum()
    total_duration = df["end"].max() - df["start"].min()
    positives_duration = labels_duration
    negatives_duration = total_duration - positives_duration

    predictions_duration = (df_predictions.end - df_predictions.start).sum()
    selected_elements_duration = predictions_duration
    relevant_elements_duration = labels_duration
    non_relevant_elements_duration = total_duration - relevant_elements_duration
    intersections_duration = df["duration"].sum()
    true_positives_duration = intersections_duration
    false_positives_duration = selected_elements_duration - true_positives_duration
    false_negatives_duration = positives_duration - true_positives_duration
    true_negatives_duration = negatives_duration - false_positives_duration

    prior_probability = relevant_elements_duration / total_duration

    print("Total Duration:", total_duration)
    print("Total Positives:", positives_duration)
    print("Total Negatives:", negatives_duration)
    print("Prior probability:", prior_probability)
    print("Labeled sessions:", labels_duration)
    print("Predicted sessions:", predictions_duration)
    print("Intersection:", intersections_duration)
    print("True Positives:", true_positives_duration, true_positives_duration / positives_duration)
    print("False Negative:", false_negatives_duration, false_negatives_duration / positives_duration)
    print("False Positives:", false_positives_duration, false_positives_duration / negatives_duration)
    print("True Negative", true_negatives_duration, true_negatives_duration / negatives_duration)
    print("Sensitivity:", true_positives_duration / relevant_elements_duration)
    print("Specificity:", true_negatives_duration / non_relevant_elements_duration)

# measure_accuracy()