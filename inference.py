import random
import json
import pickle
import numpy as np
import nltk
from datetime import datetime
from zoneinfo import ZoneInfo
from keras.models import load_model
from nltk.stem import WordNetLemmatizer

lemmatizer = WordNetLemmatizer()

# load files
intents = json.loads(open("intents.json").read())
words = pickle.load(open('model/words.pkl', 'rb'))
classes = pickle.load(open('model/classes.pkl', 'rb'))
model = load_model('model/chatbotmodel.h5', compile=False)

def clean_up_sentences(sentence):
	sentence_words = nltk.word_tokenize(sentence)
	sentence_words = [lemmatizer.lemmatize(word.lower())
					for word in sentence_words]
	return sentence_words 

def bagw(sentence): 	
	# separate out words from the input sentence 
	sentence_words = clean_up_sentences(sentence) 
	bag = [0]*len(words) 
	for w in sentence_words: 
		for i, word in enumerate(words): 
			# check whether the word is present in the input as well 
			if word == w: 
				bag[i] = 1
	return np.array(bag) 

def predict_class(sentence): 
	bow = bagw(sentence) 
	res = model.predict(np.array([bow]), verbose=0)[0]
	ERROR_THRESHOLD = 0.25
	results = [[i, r] for i, r in enumerate(res) 
			if r > ERROR_THRESHOLD] 
	results.sort(key=lambda x: x[1], reverse=True) 
	return_list = []
	for r in results:
		return_list.append({'intent': classes[r[0]],
							'probability': str(r[1])})
	return return_list

def get_response(intents_list, intents_json):
	tag = intents_list[0]['intent'] if intents_list else "unknown"
	if tag == "time":
		now = datetime.now(ZoneInfo("America/New_York"))
		return f"BMO says it's {now.strftime('%I:%M %p')}!"
	list_of_intents = intents_json['intents']
	result = ""
	for i in list_of_intents:
		if i['tag'] == tag:
			# prints a random response
			result = random.choice(i['responses'])
			break
	return result

def chat(user_input):
    ints = predict_class(user_input)
    res = get_response(ints, intents)
    return res