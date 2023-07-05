import re
import math
import difflib
class SentenceSimilarityComparator:
    def __init__(self):
        self.universalSetOfUniqueWords = []

    def calculateSimilarityTFIDF(self, sentence1, sentence2):
        matchPercentage = 0

        # Preprocess sentence1
        lowercaseSentence1 = sentence1.lower()
        wordList1 = re.sub("[^\w]", " ", lowercaseSentence1).split()
        for word in wordList1:
            if word not in self.universalSetOfUniqueWords:
                self.universalSetOfUniqueWords.append(word)

        # Preprocess sentence2
        lowercaseSentence2 = sentence2.lower()
        wordList2 = re.sub("[^\w]", " ", lowercaseSentence2).split()
        for word in wordList2:
            if word not in self.universalSetOfUniqueWords:
                self.universalSetOfUniqueWords.append(word)

        # Calculate term frequency (TF)
        sentence1TF = []
        sentence2TF = []
        for word in self.universalSetOfUniqueWords:
            sentence1TFCounter = wordList1.count(word)
            sentence1TF.append(sentence1TFCounter)

            sentence2TFCounter = wordList2.count(word)
            sentence2TF.append(sentence2TFCounter)

        # Calculate dot product
        dotProduct = sum([a * b for a, b in zip(sentence1TF, sentence2TF)])

        # Calculate vector magnitudes
        sentence1VectorMagnitude = math.sqrt(sum([tf ** 2 for tf in sentence1TF]))
        sentence2VectorMagnitude = math.sqrt(sum([tf ** 2 for tf in sentence2TF]))

        # Calculate match percentage
        matchPercentage = (float)(dotProduct / (sentence1VectorMagnitude * sentence2VectorMagnitude)) * 100

        return matchPercentage

    def calculateSimilarityDiffLIB(self, sentence1, sentence2):
        matchPercentage = difflib.SequenceMatcher(None, sentence1, sentence2).ratio() * 100
        return matchPercentage

    def compareSentencesWithSources(self, answer_string, sources_list):
        sentences = re.split('[.!?]', answer_string)  # Split answer_string into sentences
        sentences = [sentence.strip() for sentence in sentences if sentence.strip() != '']

        matches = []
        for sentence in sentences:
            max_similarity = -1
            best_match_index = -1

            for i, source in enumerate(sources_list):
                source_sentences = re.split('[.!?]', source)
                source_sentences = [s.strip() for s in source_sentences if s.strip() != '']

                highest_similarity = -1
                for source_sentence in source_sentences:
                    similarity = self.calculateSimilarityDiffLIB(sentence, source_sentence)
                    if similarity > highest_similarity:
                        highest_similarity = similarity

                if highest_similarity > max_similarity:
                    max_similarity = highest_similarity
                    best_match_index = i

            matches.append((sentence, best_match_index, max_similarity))

        return matches
