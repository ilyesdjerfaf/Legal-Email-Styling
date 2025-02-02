#%%
# Imports
import pandas as pd
import pickle
from typing import List, Tuple
import matplotlib.pyplot as plt
import re

# Ignore warnings
import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter('ignore')

#%%
def plot_na(data:pd.DataFrame) -> None:
    """
    Plot the missing values in the dataset

    Params:
        data (pd.DataFrame): Input dataset

    Returns:
        None
    """
    missing_percentage = data.isnull().mean() * 100  
    missing_count = data.isnull().sum()

    stats_sorted = missing_percentage.sort_values(ascending=False)
    counts_sorted = missing_count[stats_sorted.index]

    plt.figure(figsize=(12, 6))
    bars = plt.bar(stats_sorted.index, stats_sorted.values, color='skyblue')

    for bar, count in zip(bars, counts_sorted.values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(stats_sorted.values) * 0.01),
            f"{count:,}", 
            ha='center', va='bottom', fontsize=10
        )

    plt.title("Pourcentage de valeurs manquantes par colonne avec count", fontsize=16)
    plt.xlabel("Colonnes", fontsize=12)
    plt.ylabel("Pourcentage de valeurs manquantes (%)", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()


#%%
def keep_valid_senders(X) -> Tuple[List[str], List[str]]:
    """Keep only valid senders

    Params:
        X : list of senders
    
    Returns:
        List[str]: list of valid senders
    """
    enron_senders = [sender for sender in X if 'enron' in sender.lower()]
    news_senders = [sender for sender in X if 'news' in sender.lower()]
    no_reply_senders = [sender for sender in X if 'no-reply' in sender.lower()]

    with open('not_enron_correct_mails.pkl', 'rb') as f:
        not_enron_correct_mails = pickle.load(f)
    
    concat_good_senders = enron_senders + not_enron_correct_mails
    concat_good_senders = [sender for sender in concat_good_senders if sender not in news_senders]
    concat_good_senders = [sender for sender in concat_good_senders if sender not in no_reply_senders]
    concat_good_senders = [sender for sender in concat_good_senders if "announcement" not in sender.lower()]
    
    # keep only enron senders that are like nom.prenom@enron.com only with a regex
    matching_re = re.compile(r'^[a-zA-Z]+(?:\.[a-zA-Z]+)?@enron\.com$')
    enron_valid = [sender for sender in concat_good_senders if matching_re.match(sender) is not None]
    return concat_good_senders, enron_valid

#%%
def get_n_mails_to_keep(X:pd.DataFrame, n_words:int) -> pd.DataFrame:
    """Get the number of mails to keep per user that satisfies the condition of n words

    Params:
        X (pd.DataFrame): Input dataset
        n_words (int): Number of words to keep per user
    
    Returns:
        pd.DataFrame: Return the dataframe with the exact n mails to keep per user
    """
    X['body_length'] = X['body'].apply(lambda x: len(x.split()))
    X['cumsum'] = X.groupby('from')['body_length'].cumsum()
    X = X[X['cumsum'] <= n_words]
    return X


#%%
# emails : pd.DataFrame, represents the initial emails dataset after few preprocessing steps by TEAM 1
df = pd.read_csv('emails.csv', low_memory=False)
plot_na(df)

#%%
df.sort_values(by=['from', 'date'], inplace=True)
df.drop(columns=['id', 'date', 'xto', 'xcc', 'to'], inplace=True)
plot_na(df)

#%%
df.dropna(inplace=True)
unique_senders = df['from'].unique()
concat_good_senders, enron_valid = keep_valid_senders(unique_senders)
X = df[df['from'].isin(enron_valid)]
graph_users = [
    'sally.beck@enron.com',
    'sarah.davis@enron.com',
    'daryll.fuentes@enron.com',
    'lee.fascetti@enron.com',
    'richard.tomaski@enron.com',
    'vicki.sharp@enron.com',
    'steven.kean@enron.com',
    'robin.rodrigue@enron.com',
    'tana.jones@enron.com',
    'frank.davis@enron.com',
    'stephanie.sever@enron.com',
    'kimberly.watson@enron.com'
]
X_graph = X[X['from'].isin(graph_users)]
# number of mails per user
print(X_graph['from'].value_counts())

#%%
X_graph['body_length'] = X_graph['body'].apply(lambda x: len(x.split()))
print(X_graph.groupby('from')['body_length'].mean())
# sum of number of words per user
print(X_graph.groupby('from')['body_length'].sum())

#%%
# we have a limit of 6k body length per user
n_words = 6000
n_mails_to_keep = get_n_mails_to_keep(X_graph, n_words)
# sum of number of words per user
n_mails_to_keep.groupby('from')['body_length'].sum()
# drop the users with less than 1k words
n_mails_to_keep = n_mails_to_keep.groupby('from').filter(lambda x: x['body_length'].sum() >= 1000)
# save the dataframe
n_mails_to_keep.to_csv('sample_graph.csv', index=False)
# save the list of users
with open('sample_users_graph.pkl', 'wb') as f:
    pickle.dump(list(n_mails_to_keep["from"].unique()), f)

#%%
sender_counts = X['from'].value_counts()
# save enron senders
with open('valid_enron_senders.pkl', 'wb') as f:
    pickle.dump(enron_valid, f)

#%%
max_mails = X['from'].value_counts().max()
# identify the corresponding user	
user_with_max_mails = X['from'].value_counts()[X['from'].value_counts() == max_mails]

#%%
# plot the top 10 mails per senders
plt.figure(figsize=(15, 10))
X['from'].value_counts().head(11).plot(kind='bar')
plt.show()

#%%
# count the number of mails per sender
sender_counts = X['from'].value_counts()
# Créer un boxplot
plt.figure(figsize=(10, 5))
plt.boxplot(sender_counts, vert=False, patch_artist=True, showmeans=True)
plt.title("Boxplot du nombre de mails par expéditeur")
plt.xlabel("Nombre de mails")
plt.show()

#%%
# keep only users with more than 10 mails
X = X[X['from'].isin(sender_counts[sender_counts >= 19].index)]
sender_counts = X['from'].value_counts()
# Create a boxplot boxplot
plt.figure(figsize=(10, 5))
plt.boxplot(sender_counts, vert=False, patch_artist=True, showmeans=True)
plt.title("Boxplot du nombre de mails par expéditeur")
plt.xlabel("Nombre de mails")
plt.show()

#%%
X.to_csv('enron.csv', index=False)
X['word_count'] = X['body'].apply(lambda x: len(x.split()))
max_tokens = X['word_count'].max()
user_with_max_tokens = X[X['word_count'] == max_tokens]['from']

#%%
plt.figure(figsize=(15, 10))
X.groupby('from')['word_count'].sum().sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Top 10 Senders by Word Count')
plt.xlabel('Sender')
plt.ylabel('Total Word Count')
plt.show()

#%%
avg_word_count = X.groupby('from')['word_count'].mean()
plt.figure(figsize=(15, 10))
avg_word_count.sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Top 10 Senders by Average Word Count')
plt.xlabel('Sender')
plt.ylabel('Average Word Count')
plt.show()

#%%
sender_counts = X['from'].value_counts()
# keep only users with less than 6k words (future work : contexte size of llama3 70B)
X = X[X['from'].isin(avg_word_count[avg_word_count < 6000].index)]
# keep the top 10 senders with the highest average word count less than 6k
X = X[X['from'].isin(avg_word_count.sort_values(ascending=False).head(16).index)]

#%%
# mails per user
plt.figure(figsize=(15, 10))
X['from'].value_counts().plot(kind='bar')
plt.title('Number of mails per user')
plt.xlabel('Sender')
plt.ylabel('Number of mails')
plt.show()
