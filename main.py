import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from gtts import gTTS
import pygame
import speech_recognition as sr

# Nom du fichier audio temporaire
AUDIO_FILE = "temp_audio.mp3"

# Thread pour la reconnaissance vocale pour ne pas geler l'UI
class RecognitionThread(QThread):
    recognized = Signal(str)

    def run(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                # Ajustement au bruit ambiant
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
            except sr.WaitTimeoutError:
                self.recognized.emit("TIMEOUT_ERROR")
                return

        try:
            text = r.recognize_google(audio, language='fr-FR')
            self.recognized.emit(text)
        except sr.UnknownValueError:
            self.recognized.emit("UNKNOWN_VALUE_ERROR")
        except sr.RequestError as e:
            print(f"Erreur de service Google Speech Recognition; {e}")
            self.recognized.emit("REQUEST_ERROR")

class ReadingApp(QWidget):
    def __init__(self):
        super().__init__()

        # Initialisation de pygame pour le son
        pygame.mixer.init()

        # Thread de reconnaissance
        self.recognition_thread = RecognitionThread()
        self.recognition_thread.recognized.connect(self.on_recognition_complete)

        # Logique d'apprentissage
        self.sentences = [
            "Le chat boit du lait.",
            "Le chien joue avec la balle.",
            "Le soleil brille dans le ciel.",
            "Maman lit une histoire."
        ]
        self.current_sentence_index = 0
        self.current_word_index = 0
        self.words = []

        self.init_ui()
        self.load_sentence()

    def start_listening(self):
        self.feedback_label.setText("Écoute en cours...")
        self.speak_button.setEnabled(False)
        self.recognition_thread.start()

    def on_recognition_complete(self, text):
        self.speak_button.setEnabled(True)

        if "ERROR" in text:
            error_messages = {
                "TIMEOUT_ERROR": "Je n'ai rien entendu. Essaie encore !",
                "UNKNOWN_VALUE_ERROR": "Je n'ai pas bien compris. Peux-tu répéter ?",
                "REQUEST_ERROR": "Erreur de connexion. Vérifie internet."
            }
            self.feedback_label.setText(error_messages.get(text, "Une erreur est survenue."))
            self.speak_word(self.words[self.current_word_index]) # Répète le mot
            return

        # Nettoyage du texte reconnu et du mot attendu pour la comparaison
        recognized_text = text.lower().strip()
        expected_word = self.words[self.current_word_index].lower().strip(".,?!")

        if recognized_text == expected_word:
            self.feedback_label.setText("Bravo, c'est correct !")
            self.speak_button.setEnabled(False)  # Désactiver pendant le délai
            QTimer.singleShot(1500, self.next_word)  # Attendre 1.5s
        else:
            self.feedback_label.setText(f"Ce n'est pas tout à fait ça. J'ai entendu '{text}'. Essaie encore !")
            self.speak_word(self.words[self.current_word_index])


    def speak_word(self, word):
        try:
            tts = gTTS(text=word, lang='fr')
            tts.save(AUDIO_FILE)
            pygame.mixer.music.load(AUDIO_FILE)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Erreur lors de la synthèse vocale : {e}")
            self.feedback_label.setText("Erreur de son")

    def load_sentence(self):
        if self.current_sentence_index < len(self.sentences):
            sentence = self.sentences[self.current_sentence_index]
            self.words = sentence.split()
            self.current_word_index = 0
            self.update_word_display()
            self.speak_word(self.words[self.current_word_index])
            self.speak_button.setEnabled(True)
        else:
            self.sentence_label.setText("Bravo, tu as tout fini !")
            self.speak_button.setEnabled(False)
            self.speak_word("Bravo, tu as tout fini !")

    def next_word(self):
        self.current_word_index += 1
        if self.current_word_index < len(self.words):
            self.update_word_display()
            self.speak_word(self.words[self.current_word_index])
            self.speak_button.setEnabled(True)
        else:
            # Passer à la phrase suivante
            self.current_sentence_index += 1
            self.load_sentence()

    def update_word_display(self):
        html_sentence = ""
        for i, word in enumerate(self.words):
            if i == self.current_word_index:
                html_sentence += f"<font color='red'>{word}</font> "
            else:
                html_sentence += f"{word} "
        self.sentence_label.setText(html_sentence.strip())

    def init_ui(self):
        self.setWindowTitle("Apprends à lire !")
        self.setGeometry(100, 100, 600, 250)

        layout = QVBoxLayout()

        self.sentence_label = QLabel("Chargement...")
        self.sentence_label.setAlignment(Qt.AlignCenter)
        font = self.sentence_label.font()
        font.setPointSize(24)
        self.sentence_label.setFont(font)

        # Le bouton sert pour l'instant à passer au mot suivant
        self.speak_button = QPushButton("Appuie et parle")
        self.speak_button.clicked.connect(self.start_listening)
        font = self.speak_button.font()
        font.setPointSize(14)
        self.speak_button.setFont(font)

        # Label pour le feedback
        self.feedback_label = QLabel("Appuie sur le bouton pour commencer")
        self.feedback_label.setAlignment(Qt.AlignCenter)
        font = self.feedback_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.feedback_label.setFont(font)

        # Ajout des widgets au layout
        layout.addWidget(self.sentence_label)
        layout.addWidget(self.speak_button)
        layout.addWidget(self.feedback_label)

        self.setLayout(layout)

    def closeEvent(self, event):
        # Supprimer le fichier audio temporaire en quittant
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = ReadingApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
