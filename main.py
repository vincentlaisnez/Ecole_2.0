import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QStackedWidget
from PySide6.QtCore import Qt, QThread, Signal, QTimer
import pyttsx3
import speech_recognition as sr

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

class MainMenuWidget(QWidget):
    # Signal pour demander un changement de jeu
    game_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        title = QLabel("Choisis ton jeu")
        title_font = title.font()
        title_font.setPointSize(28)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)

        reading_button = QPushButton("Jeu de Lecture")
        reading_button.clicked.connect(lambda: self.game_selected.emit("reading"))

        letters_button = QPushButton("Jeu des Lettres")
        letters_button.clicked.connect(lambda: self.game_selected.emit("letters"))

        layout.addWidget(title)
        layout.addWidget(reading_button)
        layout.addWidget(letters_button)
        self.setLayout(layout)

class ReadingGameWidget(QWidget):
    go_to_main_menu = Signal()

    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine

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
        # Créer une nouvelle instance de thread pour chaque écoute
        self.recognition_thread = RecognitionThread()
        self.recognition_thread.recognized.connect(self.on_recognition_complete)
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

        recognized_text = text.lower().strip()
        expected_word = self.words[self.current_word_index].lower().strip(".,?!")

        if recognized_text == expected_word:
            self.feedback_label.setText("Bravo, c'est correct !")
            self.speak_button.setEnabled(False)
            QTimer.singleShot(1500, self.next_word)
        else:
            self.feedback_label.setText(f"Ce n'est pas tout à fait ça. J'ai entendu '{text}'. Essaie encore !")
            self.speak_word(self.words[self.current_word_index])

    def speak_word(self, word):
        try:
            self.tts_engine.say(word)
            self.tts_engine.runAndWait()
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
        layout = QVBoxLayout()
        self.sentence_label = QLabel("Chargement...")
        self.sentence_label.setAlignment(Qt.AlignCenter)
        font = self.sentence_label.font()
        font.setPointSize(24)
        self.sentence_label.setFont(font)

        self.speak_button = QPushButton("Appuie et parle")
        self.speak_button.clicked.connect(self.start_listening)
        font = self.speak_button.font()
        font.setPointSize(14)
        self.speak_button.setFont(font)

        self.feedback_label = QLabel("Appuie sur le bouton pour commencer")
        self.feedback_label.setAlignment(Qt.AlignCenter)
        font = self.feedback_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.feedback_label.setFont(font)

        # Bouton pour revenir au menu principal
        menu_button = QPushButton("Menu Principal")
        menu_button.clicked.connect(self.go_to_main_menu.emit)

        layout.addWidget(self.sentence_label)
        layout.addWidget(self.speak_button)
        layout.addWidget(self.feedback_label)
        layout.addWidget(menu_button)
        self.setLayout(layout)

class LetterGameWidget(QWidget):
    go_to_main_menu = Signal()

    def __init__(self, tts_engine, parent=None):
        super().__init__(parent)
        self.tts_engine = tts_engine

        self.letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.current_letter_index = 0

        self.init_ui()
        self.load_letter()

    def load_letter(self):
        if self.current_letter_index < len(self.letters):
            letter = self.letters[self.current_letter_index]
            self.letter_label.setText(letter)
            self.speak_word(letter)
            self.speak_button.setEnabled(True)
        else:
            self.letter_label.setText("🎉")
            self.feedback_label.setText("Bravo, tu connais ton alphabet !")
            self.speak_button.setEnabled(False)

    def next_letter(self):
        self.current_letter_index += 1
        self.load_letter()

    def speak_word(self, word):
        try:
            self.tts_engine.say(word)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"Erreur lors de la synthèse vocale : {e}")
            self.feedback_label.setText("Erreur de son")

    def start_listening(self):
        self.feedback_label.setText("Écoute en cours...")
        self.speak_button.setEnabled(False)
        # Créer une nouvelle instance de thread pour chaque écoute
        self.recognition_thread = RecognitionThread()
        self.recognition_thread.recognized.connect(self.on_recognition_complete)
        self.recognition_thread.start()

    def on_recognition_complete(self, text):
        self.speak_button.setEnabled(True)

        if "ERROR" in text:
            # Gérer les erreurs de reconnaissance
            self.feedback_label.setText("Je n'ai pas bien compris. Essaie encore !")
            self.speak_word(self.letters[self.current_letter_index])
            return

        expected_letter = self.letters[self.current_letter_index]
        # Comparaison simple : on vérifie si la lettre attendue est au début du mot reconnu
        if text.strip().upper().startswith(expected_letter):
            self.feedback_label.setText("Super !")
            self.speak_button.setEnabled(False)
            QTimer.singleShot(1500, self.next_letter)
        else:
            self.feedback_label.setText(f"Ce n'est pas ça. J'ai entendu '{text}'. Essaie encore !")
            self.speak_word(expected_letter)

    def init_ui(self):
        layout = QVBoxLayout()

        self.letter_label = QLabel("")
        font = self.letter_label.font()
        font.setPointSize(150)
        font.setBold(True)
        self.letter_label.setFont(font)
        self.letter_label.setAlignment(Qt.AlignCenter)

        self.speak_button = QPushButton("Appuie et dis la lettre")
        self.speak_button.clicked.connect(self.start_listening)

        self.feedback_label = QLabel("Dis la lettre que tu vois")
        self.feedback_label.setAlignment(Qt.AlignCenter)

        menu_button = QPushButton("Retour au Menu")
        menu_button.clicked.connect(self.go_to_main_menu.emit)

        layout.addWidget(self.letter_label)
        layout.addWidget(self.speak_button)
        layout.addWidget(self.feedback_label)
        layout.addWidget(menu_button)
        self.setLayout(layout)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apprends à lire !")
        self.setGeometry(100, 100, 600, 300)

        # Création de l'instance partagée du moteur TTS
        tts_engine = pyttsx3.init()
        voices = tts_engine.getProperty('voices')
        french_voice = next((voice for voice in voices if "french" in voice.name.lower() or "fr_FR" in voice.id), None)
        if french_voice:
            tts_engine.setProperty('voice', french_voice.id)
        else:
            print("Avertissement : Aucune voix française n'a été trouvée. Utilisation de la voix par défaut.")

        self.stacked_widget = QStackedWidget()

        self.main_menu = MainMenuWidget()
        self.reading_game = ReadingGameWidget(tts_engine)
        self.letters_game = LetterGameWidget(tts_engine)

        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.reading_game)
        self.stacked_widget.addWidget(self.letters_game)

        self.main_menu.game_selected.connect(self.show_game)
        self.reading_game.go_to_main_menu.connect(self.show_main_menu)
        self.letters_game.go_to_main_menu.connect(self.show_main_menu)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

    def show_game(self, game_name):
        if game_name == "reading":
            self.stacked_widget.setCurrentWidget(self.reading_game)
        elif game_name == "letters":
            self.stacked_widget.setCurrentWidget(self.letters_game)

    def show_main_menu(self):
        self.stacked_widget.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
