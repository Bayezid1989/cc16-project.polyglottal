import nltk
import numpy as np
from nltk.stem.porter import PorterStemmer
stemmer = PorterStemmer()


def tokenize(sentence):
    return nltk.word_tokenize(sentence)


def stem(word):
    return stemmer.stem(word.lower())


def bag_of_words(tokenized_sentence, all_words):
    """
    sentence = ["hello","how","are","you"]
    words = ["hi","hello","I","you","bye","thank","cool"]
    bag =   [0,      1,    0,   1,    0,     0,     0]
    """

    sentence_words = [stem(word) for word in tokenized_sentence]
    bag = np.zeros(len(all_words), dtype=np.float32)
    for index, word in enumerate(all_words):
        if word in sentence_words:
            bag[index] = 1.0
    return bag
