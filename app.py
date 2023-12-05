import streamlit as st
import pandas as pd
# import plotly.express as px
import altair as alt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from nltk.tokenize import word_tokenize, sent_tokenize
import joblib


model = joblib.load('clf_nb.pkl')
vectorizer = joblib.load('tfidf.pkl')

# Class names
class_names = ['Negative', 'Positive']

# Function to get the sentiment analysis for a specific text
def SentimentAnalysis(text):
    # Vectorization using TF-IDF
    x_actual_matrix = vectorizer.transform([text])
    x_actual_tfidf_vector = x_actual_matrix.toarray()

    # Predict the class: Negative/Positive
    y_actual_pred = model.predict(x_actual_tfidf_vector)
    
    # Class probabilities
    class_prob = model.predict_proba(x_actual_tfidf_vector)
    
    sentiment = class_names[y_actual_pred[0]]
    
    # Return the sentiment and class probabilities
    return sentiment, class_prob

# Function to get the sentiment analysis for a specific aspect/keyword
def AspectBasedSentimentAnalysis(inText, aspect_list):
    
    # Sentence tokenization
    sent_list = sent_tokenize(str(inText))
    
    # Initialize dictionaries
    aspect_class = {}
    aspect_prob_diff = {}
    
    # Loop through all aspects/keywords submitted by user
    for aspect in aspect_list:
        # For every aspect, loop through all sentences
        for sentence in sent_list:
            
            # If aspect is in the sentence
            if aspect in sentence:
                
                # Remove the aspect from the sentence
                aspect_text =  sentence.replace(aspect, "")
                
                # Perform sentiment analysis on the sentence without the keyword
                aspect_sentiment = SentimentAnalysis(aspect_text)
                
                # Get the difference between negative and positive class probabilities
                # If the class probabilities are so close to each other (e.g., negative=0.49, positive=0.51), the difference is not too clear
                prob_diff = abs(aspect_sentiment[1][0][0] - aspect_sentiment[1][0][1])
                
                # print(aspect_text,aspect_sentiment[0],aspect_sentiment[1][0])
                
                # This will output only if the probability difference at least 10 PPS
                if (prob_diff >= 0.10) and (aspect_prob_diff.get(aspect) is not None and prob_diff > aspect_prob_diff.get(aspect) ) or ( (prob_diff >= 0.10) and (aspect_prob_diff.get(aspect) is None) ):
                    
                    # Update class dictionary
                    aspect_class[aspect] = aspect_sentiment[0]
                    
                    # Update class probability dictionary
                    aspect_prob_diff[aspect] = prob_diff
                                        
    # Return sentiment analysis for the aspect
    return aspect_class                    

def process_file(df):
    text_df = df["Review"]
    text_vectorized = vectorizer.transform(text_df)
    df["Sentiment"] = model.predict(text_vectorized)
    df["Sentiment"] = df["Sentiment"].apply(lambda x: "Negative" if x == 0 else "Positive")
    product_aspects = {}
    for i, row in df.iterrows():
        text = row["Review"]
        aspect_sentiments = AspectBasedSentimentAnalysis(text, row["aspect_list"].split(","))
        if row["Product"] not in product_aspects:
            product_aspects[row["Product"]] = [aspect_sentiments]
        elif aspect_sentiments:
            product_aspects[row["Product"]].append(aspect_sentiments)
            
    # st.dataframe(product_aspects)

    return df, product_aspects

def main():
    st.title("Sentiment Analysis Report")

    # File Upload
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "csv"])
    
    # Multi-select for Products
    selected_products = st.multiselect("Select Products", ["Timestamp", "Source", "Product", "Topic"])

    if uploaded_file is not None:
        # st.text("Selected: "+ str(selected_products))

        # Read file
        if uploaded_file.type == 'text/csv':
            # Text file
            df = pd.read_csv(uploaded_file, encoding="latin-1")

        if st.button("Process Text"):
            df, product_aspects  = process_file(df)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])

            # Streamlit App
            st.title("Product Sentiment Analysis Report")

            # Sentiment Distribution
            st.header("Sentiment Distribution")
            sentiment_counts = df['Sentiment'].value_counts()
            st.bar_chart(sentiment_counts)
            st.table(sentiment_counts)

            # Time Series Analysis
            st.header("Time Series Analysis")
            if 'Timestamp' in df.columns:
                time_df = df[['Timestamp', 'Sentiment', 'Source']]
                time_df = df.groupby(['Timestamp', 'Sentiment']).count().fillna(0)
                time_df = time_df.reset_index()
                time_df = pd.pivot_table(time_df, values='Source', index=['Timestamp'], columns='Sentiment', aggfunc="sum").fillna(0)
                time_df = time_df.reset_index()
                st.dataframe(time_df)
                chart_data = pd.DataFrame()
                chart_data['Timestamp'] = time_df['Timestamp']
                chart_data['Negative'] = time_df['Negative']
                # chart_data['Neutral'] = time_df['Neutral']
                chart_data['Positive'] = time_df['Positive']
                st.line_chart(chart_data.set_index('Timestamp'))


            st.header("Source Analysis")
            source_counts = df['Source'].value_counts()
            st.bar_chart(source_counts)
            st.table(source_counts)

            # # Topic Analysis
            # st.header("Topic Analysis")
            # topic_counts = df['Review'].str.lower().value_counts()
            # st.bar_chart(topic_counts)
            # st.table(topic_counts)

            # Comparison Across Products/Features
            st.header("Comparison Across Products/Features")
            if 'Product' in df.columns:
                # Filter data based on selected products
                product_sentiment_counts = df[['Product', 'Sentiment', 'Source']].groupby(['Product', 'Sentiment']).count().fillna(0)
                product_sentiment_counts = product_sentiment_counts.rename(columns={"Source": "Count"})
                product_sentiment_counts = product_sentiment_counts.reset_index()
                st.dataframe(product_sentiment_counts)
                bar_chart = alt.Chart(product_sentiment_counts).mark_bar().encode(
                        x="Product",
                        y="Count",
                        color="Sentiment",
                    )
                st.altair_chart(bar_chart, use_container_width=True)

                st.table(product_sentiment_counts)

            st.header("Aspects Across Products")
           
            for product, aspects in product_aspects.items():
                st.subheader(product+":")
                product_aspects_list = []
                for aspect in aspects:
                    aspect_name = list(aspect.keys())[0]
                    sentiment = list(aspect.values())[0]
                    product_aspects_list.append([aspect_name, sentiment])
                tmp_df = pd.DataFrame(product_aspects_list, columns=["Aspect", "Sentiment"])
                tmp_df = tmp_df.groupby(['Aspect', 'Sentiment']).size().reset_index(name='Count')
                # st.dataframe(tmp_df)

                bar_chart = alt.Chart(tmp_df).mark_bar().encode(
                        x="Aspect",
                        y="Count",
                        color="Sentiment",
                    )
                st.altair_chart(bar_chart, use_container_width=True)

                st.table(product_sentiment_counts)


if __name__ == "__main__":
    main()
