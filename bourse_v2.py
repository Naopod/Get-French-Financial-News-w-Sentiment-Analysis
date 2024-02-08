import requests
from bs4 import BeautifulSoup
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import spacy
import fr_core_news_sm
from spacy.lang.fr.stop_words import STOP_WORDS
from string import punctuation
from heapq import nlargest

import tkinter as tk
from tkinter import ttk

def scrape_article(url):
    response = requests.get(url)
    if response.status_code == 200:
        article_soup = BeautifulSoup(response.text, 'html.parser')
        date_element = article_soup.find('span', class_='sc-17ifq26-0 cpeasH')
        date = date_element.get_text().replace('Publié le ', '') if date_element else 'No Date'

        article_content = article_soup.find_all('p')
        text_content = ' '.join([p.get_text() for p in article_content])
        text_content = text_content.replace('Contenu réservé aux abonnés', '')
        unwanted_start = 'Un accès immédiat à l\'intégralité des contenus'
        text_content = text_content.split(unwanted_start, 1)[0]

        return date, text_content
    else:
        return "No Date", "Failed to retrieve the article"

def scrape_articles(url):
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('div', class_='sc-1vhx99f-0 idRUQR')
    data = []

    for article in articles:
        full_html = article.find_all('a')
        for html in full_html:
            title = html.get('aria-label')
            if title:
                link_url = 'https://investir.lesechos.fr' + html['href']
                date, article_content = scrape_article(link_url)
                data.append({'Date': date, 'Title': title, 'Link': link_url, 'Article': article_content})

    return data

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'\[[0-9]*\]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def summarize_text(text, per):
    nlp = spacy.load('fr_core_news_sm')
    doc= nlp(text)
    tokens=[token.text for token in doc]
    word_frequencies={}
    for word in doc:
        if word.text.lower() not in list(STOP_WORDS):
            if word.text.lower() not in punctuation:
                if word.text not in word_frequencies.keys():
                    word_frequencies[word.text] = 1
                else:
                    word_frequencies[word.text] += 1
    max_frequency=max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word]=word_frequencies[word]/max_frequency
    sentence_tokens= [sent for sent in doc.sents]
    sentence_scores = {}
    for sent in sentence_tokens:
        for word in sent:
            if word.text.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():                            
                    sentence_scores[sent]=word_frequencies[word.text.lower()]
                else:
                    sentence_scores[sent]+=word_frequencies[word.text.lower()]
    select_length=int(len(sentence_tokens)*per)
    summary=nlargest(select_length, sentence_scores,key=sentence_scores.get)
    final_summary=[word.text for word in summary]
    summary=''.join(final_summary)
    return summary

def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_result = analyzer.polarity_scores(text)
    compound_score = sentiment_result['compound']

    if compound_score >= 0.05:
        return ('positive', f'It is positive with a compound sentiment score of {compound_score}.')
    elif compound_score <= -0.05:
        return ('negative', f'It is negative with a compound sentiment score of {compound_score}.')
    else:
        return ('neutral', 'The sentiment is neutral.')
    
def remove_duplicates(dicts, key):
    unique_dicts = []
    seen_values = set()

    for d in dicts:
        value = d.get(key)
        if value not in seen_values:
            seen_values.add(value)
            unique_dicts.append(d)

    return unique_dicts

url_actu_valeurs = "https://investir.lesechos.fr/actu-des-valeurs"
articles_data_actu_valeurs = scrape_articles(url_actu_valeurs)

for article in articles_data_actu_valeurs:
    preprocessed_text = preprocess_text(article['Article'])
    article['Summary'] = summarize_text(preprocessed_text, 0.2)
    sentiment_label, sentiment_explanation = analyze_sentiment(preprocessed_text)
    article['Sentiment'] = sentiment_label
    article['Sentiment Explanation'] = sentiment_explanation

url = "https://investir.lesechos.fr/conseils-boursiers/conseils-actions/"
articles_data = scrape_articles(url)

for article in articles_data:
    preprocessed_text = preprocess_text(article['Article'])
    article['Summary'] = summarize_text(preprocessed_text, 0.2)
    sentiment_label, sentiment_explanation = analyze_sentiment(preprocessed_text)
    article['Sentiment'] = sentiment_label
    article['Sentiment Explanation'] = sentiment_explanation

articles = articles_data + articles_data_actu_valeurs[::2]

articles = remove_duplicates(articles, 'Title')

##Application

def on_article_selected(event):
    widget = event.widget
    selected_index = widget.curselection()[0]
    selected_article = articles[selected_index]

    detail_window = tk.Toplevel(root)
    detail_window.title(selected_article['Title'])
    detail_window.state('zoomed')  

    tk.Label(detail_window, text=f"Title: {selected_article['Title']}", font=("Arial", 14)).pack(pady=5)
    tk.Label(detail_window, text=f"Date: {selected_article['Date']}", font=("Arial", 12)).pack(pady=5)
    tk.Label(detail_window, text=f"Link: {selected_article['Link']}", font=("Arial", 12)).pack(pady=5)
    tk.Label(detail_window, text=f"Summary: {selected_article['Summary']}", font=("Arial", 12), wraplength=500).pack(pady=5)

    sentiment_color = {'positive': 'green', 'neutral': 'gray', 'negative': 'red'}
    tk.Label(detail_window, text=f"Sentiment: {selected_article['Sentiment Explanation']}", font=("Arial", 12), fg=sentiment_color[selected_article['Sentiment']]).pack(pady=5)

    text_area = tk.Text(detail_window, wrap='word', font=("Arial", 10), height=15)
    text_area.insert('end', selected_article['Article'])
    text_area.pack(pady=5)
    text_area.config(state='disabled')  

root = tk.Tk()
root.title("Article Scraper")
root.state('zoomed')  

frame = ttk.Frame(root)
frame.pack(pady=20, fill='both', expand=True)

scrollbar = ttk.Scrollbar(frame, orient='vertical')
scrollbar.pack(side='right', fill='y')

listbox = tk.Listbox(frame, width=100, height=30, yscrollcommand=scrollbar.set, font=('Arial', 12))
listbox.pack(side='left', fill='both', expand=True)
scrollbar.config(command=listbox.yview)

sentiment_color = {'positive': 'green', 'neutral': 'gray', 'negative': 'red'}
for article in articles:
    listbox.insert(tk.END, f"{article['Date']} - {article['Title']}")
    listbox.itemconfig(tk.END, {'fg': sentiment_color[article['Sentiment']]})

listbox.bind('<<ListboxSelect>>', on_article_selected)

root.mainloop()