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


localtz = pytz.timezone("America/New_York") # TODO

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve() # TODO: Move out of Views

df_inputs = pd.read_csv(DATA_PATH.joinpath("all.csv"), parse_dates=["start", "end"])#, converters={'topics': clean})

# TODO: Remove long items probabyl daded by accident due to bug with AFK when screen turned off with AW
df_inputs = df_inputs[df_inputs.end - df_inputs.start < timedelta(hours=3)]

# TODO: Remove duplicate web browser events (Chrome)
df_inputs = df_inputs[~(df_inputs.title.astype(str).str.endswith("- Google Chrome"))]

df_inputs






def parse_topics():
  file = open(DATA_PATH.joinpath("activitywatch_wgu.txt"))

  indent = 0
  tree = (None, [])
  parents = [] # [None] * 4 * 10 # 10 level maximum
  for line in file.readlines():
    line = line.split("#")[0].rstrip() # Remove comments and right-side whitespace
    new_indent = len(line)-len(line.lstrip())
    line = line.strip()
    if line.isspace() or line == ' ' or line == '':
      continue
    
    node = (line.lower(), []) #{ "name": line, "children": [] } # TODO: Not lowercase

    parents = parents[0:new_indent]
    parent = [parent for parent in parents if parent is not None][-1] if parents else tree
    
    parent[1].append(node)

    parents = parents + [None] * (1 + new_indent - len(parents))
    parents[new_indent] = node

  return tree


topics = parse_topics()






def list_topics(topics, parent=None):
  result = []
  key = str(topics[0])
  value = key if topics[1] else parent
  result.append((key, value))
  for topic in topics[1]:
    result.extend(list_topics(topic, key))
  
  return result

topics = parse_topics()
names = dict(list(set(list_topics(topics))))

automaton = ahocorasick.Automaton()

for name in names:
    automaton.add_word(name, name)

automaton.make_automaton()

def findit_with_ahocorasick(element):
    try:
        return list(set([names[key[1]] for key in automaton.iter(element)]))
    except StopIteration:
        return []








def collapse(df, gap, threshold, equality, gate=False): # TODO: Sessionize?
  # TODO: Assume, or check: start, end as datetime
  # TODO: Sort chronologically, ascending or descending, because inputs they don't all follow the same order

  if df is None or df.empty:
    return pd.DataFrame()

  df = df.sort_values("start")

  sessions = []

  if gate:
    for x in df.itertuples():
      start = x[1]
      end = x[2]

      if sessions:
        session = sessions[-1]
        delta = start - session["end"]
        # print(delta)
        if delta <= gap: #and (not equality or equality(session["children"][0], row)):
          # print("SUCCESS!!!!! MERGE")
          session["start"] = min(session["start"], start)
          session["end"] = max(session["end"], end)
          #session["children"].append(row)
          continue

      sessions.append({
        "start": start,
        "end": end,
        #"children": [row]
      })
  else:
    for idx, row in df.iterrows():
      start = row["start"]
      end = row["end"]
      if sessions:
        session = sessions[-1]
        delta = start - session["end"]
        if delta <= gap and (not equality or equality(session["children"][0], row)):
          #print("SUCCESS!!!!! MERGE")
          session["start"] = min(session["start"], start)
          session["end"] = max(session["end"], end)
          session["children"].append(row)
          continue

      sessions.append({
        "start": start,
        "end": end,
        "children": [row]
      })

  df = pd.DataFrame(sessions)
  
  if df.empty:
    return df
  
  df["duration"] = df["end"] - df["start"]

  if threshold:
    df = df[df["duration"] >= threshold]

  return df


def describe_tags(x):
    total = 0

    tf = {}
    for child in x.children:
      tags = child["topics"]
    
      for tag in tags:
        if tag not in tf:
          tf[tag] = 0
        duration_seconds = (child.end - child.start).total_seconds()
        tf[tag] = tf[tag] + duration_seconds
        total = total + duration_seconds

    if total == 0:
      return "ERROR!"
    #print(total)
    tf = [(tag, tf[tag] / total) for tag in tf]
    tf = list(sorted(tf, key=lambda t: t[1], reverse=True))

    return tf

def predict(df):
    df["topics"] = (df["app"].astype(str) + " " + df["title"].astype(str) + " " + df["url"].astype(str)).str.lower().apply(findit_with_ahocorasick)
    df = df[df["topics"].str.len() > 0]
    df = collapse(df, timedelta(minutes=5), timedelta(minutes=5), None)
    df["topics"] = df.apply(describe_tags, axis=1)
    df = df[["start", "end", "topics"]] # Remove other columns (i.e., children), for privacy and performance
    return df


df_predictions = predict(df_inputs)
df_predictions

df = df_predictions



# # TODO: Remove this part
# def clean(x):
#   return [topic.replace("'", "").strip() for topic in x[1:-1].split(",")]

# def get_topic_ratio(topics):
#   num_topics = len(topics)
#   return [(topic, 1/num_topics) for topic in topics]

# df = pd.read_csv(DATA_PATH.joinpath("labels.csv"), parse_dates=["start", "end"], converters={'topics': clean})
# df["topics"] = df["topics"].apply(get_topic_ratio)



filtered_df = df





















topic_names = {
    "BSCS": "Bachelor of Computer Science ",
    "TOEFL": "English proficiency",
    "Study.com": "Study.com",
    "Sophia.org": "Sophia.org",
    "WGU": "Western Governors University",
    "ORA1": "Orientation",
    "C482": "Software I",
    "C683": "Natural Science Lab",
    "C950": "Data Structures and Algorithms II",
    "C867": "Scripting and Programming - Applications",
    "C195": "Software II - Advanced Java Concepts",
    "C455": "English Composition I",
    "C188": "Software Engineering",
    "C173": "Scripting and Programming - Foundations",
    "C955": "Applied Probability and Statistics",
    "C175": "Data Management - Foundations",
    "C993": "Structured Query Language",
    "C170": "Data Management - Applications",
    "C949": "Data Structures and Algorithms I",
    "C846": "Business of IT - Applications",
    "C779": "Web Development Foundations",
    "C165": "Integrated Physical Sciences",
    "C172": "Network and Security - Foundations",
    "C963": "American Politics and the US Constitution",
    "C958": "Calculus I",
    "C176": "Business of IT - Project Management",
    "C191": "Operating Systems for Programmers",
    "C952": "Computer Architecture",
    "C836": "Fundamentals of Information Security",
    "C959": "Discrete Mathematics I",
    "C960": "Discrete Mathematics II",
    "C182": "Introduction to IT",
    "C961": "Ethics in Technology",
    "C464": "Introduction to Communication",
    "C100": "Introduction to Humanities",
    "C255": "Introduction to Geography",
    "C857": "Software Quality Assurance",
    "C951": "Introduction to Artificial Intelligence",
    "C768": "Technical Communication",
    "C964": "Computer Science Capstone",
}
long_topic_names = dict(map(lambda x: (x.lower(), topic_names[x]), topic_names))
short_topic_names = dict(map(lambda x: (x.lower(), x), topic_names))

def beautify_topic_short(topic):
  try:
    return short_topic_names[topic]
  except:
    return topic

def beautify_topic_long(topic):
  try:
    return long_topic_names[topic]
  except:
    return topic

beautify_topic_long("wgu")

























wgu_courses = [
      "C455",
      "C952",
      "C195",
      "C960",
      "C191",
      "C867",
      "C683",
      "C950",
      "C482",
      "C959",
      "C949",
      "C172",
      "C961",
      "C779",
      "C836",
      "C173",
      "C182",
      "C857",
      "C464",
      "C100",
      "C255",
      "C188",
      "C846",
      "C951",
      "C768",
      "C964",
      "ORA1",
  ]

sophia_courses = [
               "C955",
               "C176",
               "C165",   
] 

study_courses = [
         "C958",
         "C963",
         "C993",
         "C175",
         "C170",   
]

schools = [
         "WGU",
         "Study.com",
         "Sophia.org",  
         "TOEFL",
]

def get_parent(tag):
  if tag in [x.lower() for x in wgu_courses]:
    return "wgu"
  if tag in [x.lower() for x in sophia_courses]:
    return "sophia.org"
  if tag in [x.lower() for x in study_courses]:
    return "study.com"
    
#   if tag in [x.lower() for x in schools]:
#     return "bscs"
#   if tag == "wgu":
#     return "bscs"
  return ""

def topic_alias(topic):
  if topic in ["wgu", "sophia.org", "study.com", "bscs", "toefl"]:
    return "unknown"
  return topic


# TODO: Remove this
def get_main_topic(topics):
  if len(topics) == 1:
    return (topics[0][0], 1.0)
  if topics[0][0].startswith("c") or topics[0][0] == "toefl":
    return (topics[0][0], 1.0)
  if topics[0][0] == "bscs":
    topics = topics[1:]
  if topics[0][0] == "database courses":
    return ("c993", 1.0) # TODO: 33% each
  if len(topics) > 4:
    return ("wgu", 1.0)

  to_ignore = ["bscs", "wgu", "study.com", "sophia.org"]
  for x in to_ignore:
    if any([t for t in topics if t[0].startswith("c") or t[0].startswith("toefl")]) and topics[0][0] in to_ignore:
      topics = topics[1:]

  return (topics[0][0], 1.0)
































































































