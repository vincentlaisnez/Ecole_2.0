import sys
import random
import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QStackedWidget, QGridLayout, QProgressBar, QMessageBox,
                               QListWidget, QListWidgetItem, QScrollArea, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, Signal, QThread, QEasingCurve, \
    QSequentialAnimationGroup, QUrl
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioManager:
    """Gestionnaire centralisé des fichiers audio pré-générés"""

    def __init__(self, audio_dir="audio_cache"):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(exist_ok=True)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.is_playing = False

        # Vérifier si pico2wave est disponible
        self.pico_available = self._check_pico()

    def _check_pico(self):
        """Vérifie si pico2wave est installé"""
        try:
            subprocess.run(['pico2wave', '--help'],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           check=False)
            print("✓ Pico TTS détecté")
            return True
        except FileNotFoundError:
            print("✗ Pico TTS non détecté, utilisation d'espeak")
            return False

    def generate_all_audio(self, progress_callback=None):
        """Génère tous les fichiers audio nécessaires"""
        items_to_generate = []

        # Lettres A-Z
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            items_to_generate.append((letter, letter))

        # Chiffres 0-9
        for num in range(10):
            items_to_generate.append((str(num), str(num)))

        # Messages de félicitations
        messages = {
            'bravo': "Bravo",
            'super': "Super",
            'excellent': "Excellent",
            'genial': "Génial",
            'tres_bien': "Très bien"
        }
        for key, text in messages.items():
            items_to_generate.append((key, text))

        total = len(items_to_generate)

        for idx, (filename, text) in enumerate(items_to_generate):
            self._generate_audio_file(filename, text)
            if progress_callback:
                progress_callback(idx + 1, total, text)

        print(f"✓ {total} fichiers audio générés avec succès")

    def _generate_audio_file(self, filename, text):
        """Génère un fichier audio individuel"""
        audio_file = self.audio_dir / f"{filename}.wav"

        # Ne pas regénérer si le fichier existe déjà
        if audio_file.exists():
            return

        try:
            if self.pico_available:
                # Utiliser Pico TTS avec voix française de haute qualité
                subprocess.run([
                    'pico2wave',
                    '-l', 'fr-FR',
                    '-w', str(audio_file),
                    text
                ], check=True, capture_output=True, timeout=5)
            else:
                # Fallback sur espeak avec meilleurs paramètres
                subprocess.run([
                    'espeak',
                    '-v', 'fr',
                    '-s', '140',  # Vitesse modérée
                    '-p', '50',  # Pitch
                    '-a', '200',  # Amplitude
                    '-w', str(audio_file),
                    text
                ], check=True, capture_output=True, timeout=5)

        except subprocess.TimeoutExpired:
            print(f"⚠ Timeout lors de la génération de {filename}")
        except Exception as e:
            print(f"⚠ Erreur lors de la génération de {filename}: {e}")

    def play(self, text):
        """Joue un fichier audio pré-généré"""
        if self.is_playing:
            self.stop()

        # Déterminer le fichier à jouer
        audio_file = self.audio_dir / f"{text}.wav"

        if not audio_file.exists():
            print(f"⚠ Fichier audio manquant: {text}")
            # Essayer de le générer à la volée
            self._generate_audio_file(text, text)
            if not audio_file.exists():
                return

        try:
            self.is_playing = True
            self.player.setSource(QUrl.fromLocalFile(str(audio_file.absolute())))
            self.player.play()

            # Auto-reset du flag après la fin de lecture
            def on_playback_state_changed(state):
                if state == QMediaPlayer.PlaybackState.StoppedState:
                    self.is_playing = False

            self.player.playbackStateChanged.connect(on_playback_state_changed)

        except Exception as e:
            print(f"⚠ Erreur lors de la lecture de {text}: {e}")
            self.is_playing = False

    def stop(self):
        """Arrête la lecture en cours"""
        try:
            self.player.stop()
        except:
            pass
        self.is_playing = False

    def cleanup_cache(self):
        """Nettoie le cache audio (optionnel)"""
        for audio_file in self.audio_dir.glob("*.wav"):
            try:
                audio_file.unlink()
            except:
                pass


class InitializationScreen(QWidget):
    """Écran d'initialisation avec génération des fichiers audio"""
    initialization_complete = Signal()

    def __init__(self, audio_manager):
        super().__init__()
        self.audio_manager = audio_manager
        self.setup_ui()

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(230, 245, 255))
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("🎓 Apprends l'Alphabet !")
        title.setFont(QFont('Arial', 48, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FF6B6B; margin: 30px;")

        self.status_label = QLabel("Préparation des sons...")
        self.status_label.setFont(QFont('Arial', 18))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4ECDC4; margin: 20px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumWidth(400)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 3px solid #4ECDC4;
                border-radius: 15px;
                text-align: center;
                height: 40px;
                background-color: white;
                color: #2C3E50;
                font-weight: bold;
                font-size: 16px;
            }
            QProgressBar::chunk {
                background-color: #4ECDC4;
                border-radius: 12px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def start_initialization(self):
        """Lance l'initialisation des fichiers audio"""
        QTimer.singleShot(500, self._generate_audio)

    def _generate_audio(self):
        """Génère les fichiers audio avec mise à jour de la progression"""

        def progress_callback(current, total, text):
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.status_label.setText(f"Génération: {text} ({current}/{total})")
            QApplication.processEvents()  # Force la mise à jour de l'interface

        try:
            self.audio_manager.generate_all_audio(progress_callback)
            self.status_label.setText("✓ Prêt à jouer !")
            QTimer.singleShot(500, self.initialization_complete.emit)
        except Exception as e:
            self.status_label.setText(f"⚠ Erreur: {e}")
            print(f"Erreur d'initialisation: {e}")


class VoiceEngine:
    """Gestionnaire de synthèse vocale utilisant AudioManager"""

    def __init__(self, audio_manager):
        self.audio_manager = audio_manager

    def speak_async(self, text):
        """Prononce le texte de manière asynchrone"""
        # Normaliser le texte
        text_normalized = text.lower().strip()

        # Mapper les messages aux fichiers audio
        message_map = {
            'bravo !': 'bravo',
            'bravo!': 'bravo',
            'super !': 'super',
            'super!': 'super',
            'excellent !': 'excellent',
            'excellent!': 'excellent',
            'génial !': 'genial',
            'génial!': 'genial',
            'très bien !': 'tres_bien',
            'très bien!': 'tres_bien'
        }

        audio_key = message_map.get(text_normalized, text.upper())
        self.audio_manager.play(audio_key)

    def speak(self, text):
        """Alias pour compatibilité"""
        self.speak_async(text)

    def stop(self):
        """Arrête la synthèse vocale en cours"""
        self.audio_manager.stop()

    def shutdown(self):
        """Ferme proprement le moteur"""
        self.audio_manager.stop()


class DataManager:
    """Gestionnaire de données pour les profils et statistiques"""

    def __init__(self):
        self.data_file = Path('alphabet_data.json')
        self.data = self.load_data()
        self.observers = []
        self.executor = ThreadPoolExecutor(max_workers=2)

    def add_observer(self, callback):
        """Ajoute un observateur pour les mises à jour"""
        self.observers.append(callback)

    def notify_observers(self):
        """Notifie tous les observateurs d'une mise à jour"""
        for callback in self.observers:
            try:
                QTimer.singleShot(0, callback)
            except:
                pass

    def load_data(self):
        """Charge les données depuis le fichier"""
        if self.data_file.exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'users': {}}

    def save_data(self):
        """Sauvegarde les données dans le fichier (asynchrone)"""

        def save_task():
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.notify_observers()

        self.executor.submit(save_task)

    def save_data_sync(self):
        """Sauvegarde synchrone des données"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_all_users(self):
        """Retourne la liste de tous les utilisateurs"""
        return list(self.data['users'].keys())

    def create_user(self, name):
        """Crée un nouveau profil utilisateur"""
        if name not in self.data['users']:
            self.data['users'][name] = {
                'created': datetime.now().isoformat(),
                'stats': {letter: {'correct': 0, 'attempts': 0} for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'},
                'stats_numbers': {str(num): {'correct': 0, 'attempts': 0} for num in range(10)},
                'total_correct': 0,
                'total_attempts': 0,
                'total_correct_numbers': 0,
                'total_attempts_numbers': 0
            }
            self.save_data()
            return True
        return False

    def get_user(self, name):
        """Récupère les données d'un utilisateur"""
        return self.data['users'].get(name)

    def update_stats(self, name, letter, correct):
        """Met à jour les statistiques pour une lettre"""
        user = self.data['users'][name]
        user['stats'][letter]['attempts'] += 1
        user['total_attempts'] += 1
        if correct:
            user['stats'][letter]['correct'] += 1
            user['total_correct'] += 1
        self.save_data()

    def update_stats_numbers(self, name, number, correct):
        """Met à jour les statistiques pour un chiffre"""
        user = self.data['users'][name]
        user['stats_numbers'][number]['attempts'] += 1
        user['total_attempts_numbers'] += 1
        if correct:
            user['stats_numbers'][number]['correct'] += 1
            user['total_correct_numbers'] += 1
        self.save_data()

    def get_difficult_letters(self, name, count=5):
        """Retourne les lettres les plus difficiles pour l'utilisateur"""
        user = self.data['users'][name]
        letter_scores = []

        for letter, stats in user['stats'].items():
            if stats['attempts'] > 0:
                success_rate = stats['correct'] / stats['attempts']
                letter_scores.append((letter, success_rate, stats['attempts']))

        letter_scores.sort(key=lambda x: (x[1], -x[2]))

        difficult = [l[0] for l in letter_scores[:count]]
        if len(difficult) < count:
            all_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            remaining = [l for l in all_letters if l not in difficult]
            difficult.extend(random.sample(remaining, min(count - len(difficult), len(remaining))))

        return difficult

    def get_difficult_numbers(self, name, count=4):
        """Retourne les chiffres les plus difficiles pour l'utilisateur"""
        user = self.data['users'][name]

        if 'stats_numbers' not in user:
            user['stats_numbers'] = {str(num): {'correct': 0, 'attempts': 0} for num in range(10)}
            user['total_correct_numbers'] = 0
            user['total_attempts_numbers'] = 0

        number_scores = []

        for number, stats in user['stats_numbers'].items():
            if stats['attempts'] > 0:
                success_rate = stats['correct'] / stats['attempts']
                number_scores.append((number, success_rate, stats['attempts']))

        number_scores.sort(key=lambda x: (x[1], -x[2]))

        difficult = [n[0] for n in number_scores[:count]]
        if len(difficult) < count:
            all_numbers = [str(i) for i in range(10)]
            remaining = [n for n in all_numbers if n not in difficult]
            difficult.extend(random.sample(remaining, min(count - len(difficult), len(remaining))))

        return difficult


class ColorfulButton(QPushButton):
    """Bouton personnalisé avec couleur et taille adaptative"""

    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self.setMinimumSize(200, 120)
        self.setMaximumSize(400, 150)
        self.setFont(QFont('Arial', 36, QFont.Bold))
        self.base_color = color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 5px solid #555;
                border-radius: 20px;
                padding: 20px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
                border: 5px solid #000;
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """)

    def lighten_color(self, color):
        """Éclaircit une couleur"""
        colors = {
            '#FF6B6B': '#FF8E8E',
            '#4ECDC4': '#6EDDD4',
            '#45B7D1': '#65C7E1',
            '#FFA07A': '#FFB89A',
            '#98D8C8': '#B8E8D8',
            '#F7DC6F': '#F7E68F',
            '#E67E22': '#F39C12',
            '#2ECC71': '#52D98C',
            '#E74C3C': '#F16A5E',
            '#95A5A6': '#AAB7B8'
        }
        return colors.get(color, color)

    def darken_color(self, color):
        """Assombrit une couleur"""
        colors = {
            '#FF6B6B': '#FF4B4B',
            '#4ECDC4': '#3EBDB4',
            '#45B7D1': '#3597B1',
            '#FFA07A': '#FF805A',
            '#98D8C8': '#78B8A8',
            '#F7DC6F': '#D7BC4F',
            '#E67E22': '#D35400',
            '#2ECC71': '#27AE60',
            '#E74C3C': '#C0392B',
            '#95A5A6': '#7F8C8D'
        }
        return colors.get(color, color)


class UserSelectionScreen(QWidget):
    """Écran de sélection d'utilisateur"""
    user_selected = Signal(str)

    def __init__(self, data_manager, voice_engine):
        super().__init__()
        self.data_manager = data_manager
        self.voice_engine = voice_engine
        self.setup_ui()

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(255, 250, 205))
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("🎈 Qui va jouer aujourd'hui ? 🎈")
        title.setFont(QFont('Arial', 42, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FF6B6B; margin: 20px; background-color: transparent;")

        self.user_list = QListWidget()
        self.user_list.setFont(QFont('Arial', 20))
        self.user_list.setMaximumWidth(500)
        self.user_list.setMinimumHeight(300)
        self.user_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 3px solid #4ECDC4;
                border-radius: 15px;
                padding: 10px;
                color: #2C3E50;
            }
            QListWidget::item {
                padding: 15px;
                border-radius: 10px;
                margin: 5px;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
            QListWidget::item:selected {
                background-color: #4ECDC4;
                color: white;
            }
        """)
        self.user_list.itemDoubleClicked.connect(self.select_user)

        btn_layout = QHBoxLayout()

        self.select_btn = ColorfulButton("✓ Sélectionner", "#4ECDC4")
        self.select_btn.setMaximumWidth(390)
        self.select_btn.clicked.connect(self.select_user)

        self.new_user_btn = ColorfulButton("+ Nouvel enfant", "#45B7D1")
        self.new_user_btn.setMaximumWidth(430)
        self.new_user_btn.clicked.connect(self.show_new_user_form)

        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.new_user_btn)

        self.new_user_widget = QWidget()
        new_user_layout = QVBoxLayout()

        new_user_label = QLabel("Prénom du nouvel enfant :")
        new_user_label.setFont(QFont('Arial', 18))
        new_user_label.setStyleSheet("color: #2C3E50; background-color: transparent;")

        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("Prénom...")
        self.new_name_input.setFont(QFont('Arial', 20))
        self.new_name_input.setMaximumWidth(400)
        self.new_name_input.setStyleSheet("""
            QLineEdit {
                padding: 15px;
                border: 3px solid #4ECDC4;
                border-radius: 15px;
                background-color: white;
                color: #2C3E50;
            }
        """)
        self.new_name_input.returnPressed.connect(self.create_new_user)

        new_user_btn_layout = QHBoxLayout()

        create_btn = ColorfulButton("✓ Créer", "#2ECC71")
        create_btn.setMaximumWidth(180)
        create_btn.clicked.connect(self.create_new_user)

        cancel_btn = ColorfulButton("✕ Annuler", "#E74C3C")
        cancel_btn.setMaximumWidth(180)
        cancel_btn.clicked.connect(self.hide_new_user_form)

        new_user_btn_layout.addWidget(create_btn)
        new_user_btn_layout.addWidget(cancel_btn)

        new_user_layout.addWidget(new_user_label, alignment=Qt.AlignCenter)
        new_user_layout.addWidget(self.new_name_input, alignment=Qt.AlignCenter)
        new_user_layout.addLayout(new_user_btn_layout)

        self.new_user_widget.setLayout(new_user_layout)
        self.new_user_widget.setVisible(False)
        self.new_user_widget.setStyleSheet("background-color: transparent;")

        layout.addWidget(title)
        layout.addWidget(self.user_list, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addLayout(btn_layout)
        layout.addSpacing(10)
        layout.addWidget(self.new_user_widget)

        self.setLayout(layout)
        self.refresh_user_list()

    def refresh_user_list(self):
        """Rafraîchit la liste des utilisateurs"""
        self.user_list.clear()
        users = self.data_manager.get_all_users()

        if not users:
            item = QListWidgetItem("Aucun enfant enregistré")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.user_list.addItem(item)
        else:
            for user in sorted(users):
                self.user_list.addItem(user)

    def show_new_user_form(self):
        """Affiche le formulaire de création"""
        self.new_user_widget.setVisible(True)
        self.new_name_input.setFocus()

    def hide_new_user_form(self):
        """Cache le formulaire de création"""
        self.new_user_widget.setVisible(False)
        self.new_name_input.clear()

    def create_new_user(self):
        """Crée un nouvel utilisateur"""
        name = self.new_name_input.text().strip()
        if name:
            if self.data_manager.create_user(name):
                self.refresh_user_list()
                self.hide_new_user_form()
                QMessageBox.information(self, "Succès", f"Bienvenue {name} ! 🎉")
                items = self.user_list.findItems(name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.user_list.setCurrentItem(items[0])
                    QTimer.singleShot(500, self.select_user)
            else:
                QMessageBox.warning(self, "Attention", f"{name} existe déjà !")
        else:
            QMessageBox.warning(self, "Attention", "Entre un prénom !")

    def select_user(self):
        """Sélectionne un utilisateur"""
        current_item = self.user_list.currentItem()
        if current_item and current_item.flags() != Qt.ItemFlag.NoItemFlags:
            username = current_item.text()
            self.user_selected.emit(username)


class GameScreen(QWidget):
    """Écran principal du jeu des lettres"""
    back_to_menu = Signal()

    def __init__(self, data_manager, voice_engine, username):
        super().__init__()
        self.data_manager = data_manager
        self.voice_engine = voice_engine
        self.username = username
        self.current_letter = None
        self.choices = []
        self.correct_answer = None
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        self.is_active = False
        self.message_label = None
        self.transition_label = None
        self.setup_ui()

    def showEvent(self, event):
        """Appelé quand l'écran devient visible"""
        super().showEvent(event)
        if not self.is_active:
            self.is_active = True
            self.update_score_display()
            QTimer.singleShot(100, self.new_question)

    def hideEvent(self, event):
        """Appelé quand l'écran est caché"""
        super().hideEvent(event)
        self.is_active = False
        self.voice_engine.stop()
        self.data_manager.save_data()

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(227, 242, 253))
        self.setPalette(palette)

        layout = QVBoxLayout()

        header = QHBoxLayout()

        self.name_label = QLabel(f"👤 {self.username}")
        self.name_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.name_label.setStyleSheet("color: #4ECDC4; background-color: transparent;")

        self.score_label = QLabel()
        self.score_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.score_label.setStyleSheet("color: #45B7D1; background-color: transparent;")

        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.score_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(26)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4ECDC4;
                border-radius: 10px;
                text-align: center;
                height: 30px;
                background-color: white;
                color: #2C3E50;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4ECDC4;
            }
        """)

        self.update_score_display()

        self.question_label = QLabel("🔊 Écoute bien et choisis la bonne lettre !")
        self.question_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setStyleSheet("color: #FF6B6B; margin: 20px; background-color: transparent;")

        self.listen_btn = ColorfulButton("🔊 Écouter", "#F7DC6F")
        self.listen_btn.clicked.connect(self.play_letter)
        self.listen_btn.setMaximumWidth(300)

        self.buttons_widget = QWidget()
        self.buttons_widget.setStyleSheet("background-color: transparent;")
        self.buttons_layout = QGridLayout()
        self.choice_buttons = []

        for i in range(4):
            btn = ColorfulButton("", self.colors[i])
            btn.clicked.connect(lambda checked, idx=i: self.check_answer(idx))
            self.choice_buttons.append(btn)
            self.buttons_layout.addWidget(btn, i // 2, i % 2)

        self.buttons_widget.setLayout(self.buttons_layout)

        menu_btn = QPushButton("🏠 Menu")
        menu_btn.setFont(QFont('Arial', 14))
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)
        menu_btn.clicked.connect(self.back_to_menu.emit)

        layout.addLayout(header)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.question_label)
        layout.addWidget(self.listen_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.buttons_widget)
        layout.addWidget(menu_btn)

        self.setLayout(layout)

    def update_score_display(self):
        """Met à jour l'affichage du score"""
        user = self.data_manager.get_user(self.username)
        correct = user['total_correct']
        total = user['total_attempts']
        self.score_label.setText(f"⭐ Score: {correct}/{total}")

        letters_learned = sum(1 for stats in user['stats'].values()
                              if stats['attempts'] > 0 and stats['correct'] / stats['attempts'] >= 0.7)
        self.progress_bar.setValue(letters_learned)
        self.progress_bar.setFormat(f"{letters_learned}/26 lettres maîtrisées")

    def new_question(self):
        """Génère une nouvelle question"""
        if not self.is_active:
            return

        self.clear_messages()
        self.show_transition()

        if random.random() < 0.6:
            difficult = self.data_manager.get_difficult_letters(self.username, 10)
            self.current_letter = random.choice(difficult)
        else:
            self.current_letter = random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))

        all_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        all_letters.remove(self.current_letter)
        wrong_choices = random.sample(all_letters, 3)
        self.choices = [self.current_letter] + wrong_choices
        random.shuffle(self.choices)
        self.correct_answer = self.choices.index(self.current_letter)

        for i, btn in enumerate(self.choice_buttons):
            btn.setText(self.choices[i])
            btn.setEnabled(True)

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors[i]};
                    color: white;
                    border: 5px solid #555;
                    border-radius: 20px;
                    padding: 20px;
                    font-size: 36px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {btn.lighten_color(self.colors[i])};
                    border: 5px solid #000;
                }}
                QPushButton:pressed {{
                    background-color: {btn.darken_color(self.colors[i])};
                }}
            """)

        if self.is_active:
            QTimer.singleShot(300, self.play_letter)

    def play_letter(self):
        """Prononce la lettre actuelle"""
        if self.current_letter and self.is_active:
            self.voice_engine.speak_async(self.current_letter)

    def check_answer(self, choice_idx):
        """Vérifie la réponse de l'enfant avec effets visuels"""
        if not self.is_active:
            return

        correct = (choice_idx == self.correct_answer)

        self.data_manager.update_stats(self.username, self.current_letter, correct)

        for btn in self.choice_buttons:
            btn.setEnabled(False)

        if correct:
            self.animate_success(choice_idx)
            messages = ["Bravo !", "Super !", "Excellent !", "Génial !"]
            self.voice_engine.speak_async(random.choice(messages))
        else:
            self.animate_failure(choice_idx)

        self.update_score_display()

        if self.is_active:
            QTimer.singleShot(2500, self.new_question)

    def clear_messages(self):
        """Nettoie tous les messages affichés"""
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass
        finally:
            self.message_label = None

    def show_transition(self):
        """Affiche un indicateur de transition rapide"""
        try:
            if self.transition_label is not None:
                self.transition_label.deleteLater()
        except RuntimeError:
            pass

        self.transition_label = QLabel("⏳ Nouvelle lettre...", self)
        self.transition_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.transition_label.setStyleSheet("""
            color: #7F8C8D;
            background-color: #ECF0F1;
            border: 2px solid #BDC3C7;
            border-radius: 10px;
            padding: 10px;
        """)
        self.transition_label.setAlignment(Qt.AlignCenter)
        self.transition_label.setGeometry(
            self.width() // 2 - 100,
            20,
            200,
            50
        )
        self.transition_label.show()

        def cleanup_transition():
            try:
                if self.transition_label is not None:
                    self.transition_label.deleteLater()
                    self.transition_label = None
            except RuntimeError:
                pass

        QTimer.singleShot(500, cleanup_transition)

    def animate_success(self, choice_idx):
        """Animation de succès avec encadré vert épais"""
        btn = self.choice_buttons[choice_idx]

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[choice_idx]};
                color: white;
                border: 12px solid #2ECC71;
                border-radius: 20px;
            }}
        """)

        animation = QPropertyAnimation(btn, b"geometry")
        animation.setDuration(600)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)

        original_geo = btn.geometry()
        larger_geo = QRect(
            original_geo.x() - 15,
            original_geo.y() - 15,
            original_geo.width() + 30,
            original_geo.height() + 30
        )

        animation.setStartValue(original_geo)
        animation.setKeyValueAt(0.5, larger_geo)
        animation.setEndValue(original_geo)
        animation.start()

        self.show_success_message()
        self.flash_background("#A9DFBF")

    def animate_failure(self, choice_idx):
        """Animation d'échec avec encadrés rouge et vert bien visibles"""
        wrong_btn = self.choice_buttons[choice_idx]
        correct_btn = self.choice_buttons[self.correct_answer]

        wrong_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[choice_idx]};
                color: white;
                border: 12px solid #E74C3C;
                border-radius: 20px;
            }}
        """)

        correct_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[self.correct_answer]};
                color: white;
                border: 12px solid #2ECC71;
                border-radius: 20px;
            }}
        """)

        shake_animation = QPropertyAnimation(wrong_btn, b"geometry")
        shake_animation.setDuration(500)

        original_geo = wrong_btn.geometry()

        shake_animation.setStartValue(original_geo)
        shake_animation.setKeyValueAt(0.2,
                                      QRect(original_geo.x() - 10, original_geo.y(), original_geo.width(),
                                            original_geo.height()))
        shake_animation.setKeyValueAt(0.4,
                                      QRect(original_geo.x() + 10, original_geo.y(), original_geo.width(),
                                            original_geo.height()))
        shake_animation.setKeyValueAt(0.6,
                                      QRect(original_geo.x() - 10, original_geo.y(), original_geo.width(),
                                            original_geo.height()))
        shake_animation.setKeyValueAt(0.8,
                                      QRect(original_geo.x() + 10, original_geo.y(), original_geo.width(),
                                            original_geo.height()))
        shake_animation.setEndValue(original_geo)
        shake_animation.start()

        pulse_animation = QPropertyAnimation(correct_btn, b"geometry")
        pulse_animation.setDuration(1000)
        pulse_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        correct_geo = correct_btn.geometry()
        larger_geo = QRect(
            correct_geo.x() - 10,
            correct_geo.y() - 10,
            correct_geo.width() + 20,
            correct_geo.height() + 20
        )

        pulse_animation.setStartValue(correct_geo)
        pulse_animation.setKeyValueAt(0.5, larger_geo)
        pulse_animation.setEndValue(correct_geo)
        pulse_animation.start()

        self.show_correct_letter()
        self.flash_background("#F5B7B1")

    def show_success_message(self):
        """Affiche un message de félicitations animé"""
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass

        success_messages = ["🎉 BRAVO ! 🎉", "⭐ SUPER ! ⭐", "🏆 GÉNIAL ! 🏆", "✨ EXCELLENT ! ✨"]

        self.message_label = QLabel(random.choice(success_messages), self)
        self.message_label.setFont(QFont('Arial', 40, QFont.Bold))
        self.message_label.setStyleSheet("""
            color: #2ECC71;
            background-color: #FFFFFF;
            border: 6px solid #2ECC71;
            border-radius: 20px;
            padding: 15px;
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setGeometry(self.width() // 2 - 250, 30, 500, 80)
        self.message_label.show()

        opacity_effect = QGraphicsOpacityEffect()
        self.message_label.setGraphicsEffect(opacity_effect)

        fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        fade_out = QPropertyAnimation(opacity_effect, b"opacity")
        fade_out.setDuration(400)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        animation_group = QSequentialAnimationGroup(self)

        def cleanup_message():
            try:
                if self.message_label is not None:
                    self.message_label.deleteLater()
            except RuntimeError:
                pass

        animation_group.addAnimation(fade_in)
        animation_group.addPause(1000)
        animation_group.addAnimation(fade_out)
        animation_group.finished.connect(cleanup_message)
        animation_group.start()

    def show_correct_letter(self):
        """Affiche la bonne lettre en grand"""
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass

        self.message_label = QLabel(f"C'était la lettre\n{self.current_letter}", self)
        self.message_label.setFont(QFont('Arial', 48, QFont.Bold))
        self.message_label.setStyleSheet("""
            color: #2ECC71;
            background-color: #FFFFFF;
            border: 8px solid #2ECC71;
            border-radius: 25px;
            padding: 25px;
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setGeometry(self.width() // 2 - 250, 30, 500, 180)
        self.message_label.show()

        opacity_effect = QGraphicsOpacityEffect()
        self.message_label.setGraphicsEffect(opacity_effect)

        fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        fade_out = QPropertyAnimation(opacity_effect, b"opacity")
        fade_out.setDuration(500)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        animation_group = QSequentialAnimationGroup(self)

        def cleanup_message():
            try:
                if self.message_label is not None:
                    self.message_label.deleteLater()
            except RuntimeError:
                pass

        animation_group.addAnimation(fade_in)
        animation_group.addPause(1200)
        animation_group.addAnimation(fade_out)
        animation_group.finished.connect(cleanup_message)
        animation_group.start()

    def flash_background(self, color):
        """Flash de couleur du fond"""
        original_palette = self.palette()
        flash_palette = self.palette()
        flash_palette.setColor(QPalette.Window, QColor(color))

        self.setPalette(flash_palette)
        QTimer.singleShot(300, lambda: self.setPalette(original_palette))


class NumbersGameScreen(QWidget):
    """Écran de jeu pour les chiffres"""
    back_to_menu = Signal()

    def __init__(self, data_manager, voice_engine, username):
        super().__init__()
        self.data_manager = data_manager
        self.voice_engine = voice_engine
        self.username = username
        self.current_number = None
        self.choices = []
        self.correct_answer = None
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        self.is_active = False
        self.message_label = None
        self.transition_label = None
        self.setup_ui()

    def showEvent(self, event):
        """Appelé quand l'écran devient visible"""
        super().showEvent(event)
        if not self.is_active:
            self.is_active = True
            self.update_score_display()
            QTimer.singleShot(100, self.new_question)

    def hideEvent(self, event):
        """Appelé quand l'écran est caché"""
        super().hideEvent(event)
        self.is_active = False
        self.voice_engine.stop()
        self.data_manager.save_data()

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(255, 243, 224))
        self.setPalette(palette)

        layout = QVBoxLayout()

        header = QHBoxLayout()

        self.name_label = QLabel(f"👤 {self.username}")
        self.name_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.name_label.setStyleSheet("color: #FF6B6B; background-color: transparent;")

        self.score_label = QLabel()
        self.score_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.score_label.setStyleSheet("color: #E67E22; background-color: transparent;")

        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.score_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E67E22;
                border-radius: 10px;
                text-align: center;
                height: 30px;
                background-color: white;
                color: #2C3E50;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #E67E22;
            }
        """)

        self.update_score_display()

        self.question_label = QLabel("🔢 Écoute bien et choisis le bon chiffre !")
        self.question_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setStyleSheet(
            "color: #E67E22; margin: 20px; background-color: transparent;")

        self.listen_btn = ColorfulButton("🔊 Écouter", "#F7DC6F")
        self.listen_btn.clicked.connect(self.play_number)
        self.listen_btn.setMaximumWidth(250)

        self.buttons_widget = QWidget()
        self.buttons_widget.setStyleSheet("background-color: transparent;")
        self.buttons_layout = QGridLayout()
        self.choice_buttons = []

        for i in range(4):
            btn = ColorfulButton("", self.colors[i])
            btn.clicked.connect(lambda checked, idx=i: self.check_answer(idx))
            self.choice_buttons.append(btn)
            self.buttons_layout.addWidget(btn, i // 2, i % 2)

        self.buttons_widget.setLayout(self.buttons_layout)

        menu_btn = QPushButton("🏠 Menu")
        menu_btn.setFont(QFont('Arial', 14))
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)
        menu_btn.clicked.connect(self.back_to_menu.emit)

        layout.addLayout(header)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.question_label)
        layout.addWidget(self.listen_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.buttons_widget)
        layout.addWidget(menu_btn)

        self.setLayout(layout)

    def update_score_display(self):
        user = self.data_manager.get_user(self.username)

        if 'total_correct_numbers' not in user:
            user['total_correct_numbers'] = 0
            user['total_attempts_numbers'] = 0

        correct = user['total_correct_numbers']
        total = user['total_attempts_numbers']
        self.score_label.setText(f"⭐ Score: {correct}/{total}")

        if 'stats_numbers' not in user:
            user['stats_numbers'] = {str(num): {'correct': 0, 'attempts': 0} for num in range(10)}

        numbers_learned = sum(1 for stats in user['stats_numbers'].values()
                              if stats['attempts'] > 0 and stats['correct'] / stats['attempts'] >= 0.7)
        self.progress_bar.setValue(numbers_learned)
        self.progress_bar.setFormat(f"{numbers_learned}/10 chiffres maîtrisés")

    def new_question(self):
        if not self.is_active:
            return

        self.clear_messages()
        self.show_transition()

        if random.random() < 0.6:
            difficult = self.data_manager.get_difficult_numbers(self.username, 5)
            self.current_number = random.choice(difficult)
        else:
            self.current_number = str(random.randint(0, 9))

        all_numbers = [str(i) for i in range(10)]
        all_numbers.remove(self.current_number)
        wrong_choices = random.sample(all_numbers, 3)
        self.choices = [self.current_number] + wrong_choices
        random.shuffle(self.choices)
        self.correct_answer = self.choices.index(self.current_number)

        for i, btn in enumerate(self.choice_buttons):
            btn.setText(self.choices[i])
            btn.setEnabled(True)

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors[i]};
                    color: white;
                    border: 5px solid #555;
                    border-radius: 20px;
                    padding: 20px;
                    font-size: 36px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {btn.lighten_color(self.colors[i])};
                    border: 5px solid #000;
                }}
                QPushButton:pressed {{
                    background-color: {btn.darken_color(self.colors[i])};
                }}
            """)

        if self.is_active:
            QTimer.singleShot(300, self.play_number)

    def play_number(self):
        if self.current_number and self.is_active:
            self.voice_engine.speak_async(self.current_number)

    def check_answer(self, choice_idx):
        if not self.is_active:
            return

        correct = (choice_idx == self.correct_answer)

        self.data_manager.update_stats_numbers(self.username, self.current_number, correct)

        for btn in self.choice_buttons:
            btn.setEnabled(False)

        if correct:
            self.animate_success(choice_idx)
            messages = ["Bravo !", "Super !", "Excellent !", "Génial !"]
            self.voice_engine.speak_async(random.choice(messages))
        else:
            self.animate_failure(choice_idx)

        self.update_score_display()

        if self.is_active:
            QTimer.singleShot(2500, self.new_question)

    def clear_messages(self):
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass
        finally:
            self.message_label = None

    def show_transition(self):
        try:
            if self.transition_label is not None:
                self.transition_label.deleteLater()
        except RuntimeError:
            pass

        self.transition_label = QLabel("⏳ Nouveau chiffre...", self)
        self.transition_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.transition_label.setStyleSheet("""
            color: #7F8C8D;
            background-color: #ECF0F1;
            border: 2px solid #BDC3C7;
            border-radius: 10px;
            padding: 10px;
        """)
        self.transition_label.setAlignment(Qt.AlignCenter)
        self.transition_label.setGeometry(self.width() // 2 - 100, 20, 200, 50)
        self.transition_label.show()

        def cleanup_transition():
            try:
                if self.transition_label is not None:
                    self.transition_label.deleteLater()
                    self.transition_label = None
            except RuntimeError:
                pass

        QTimer.singleShot(500, cleanup_transition)

    def animate_success(self, choice_idx):
        btn = self.choice_buttons[choice_idx]

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[choice_idx]};
                color: white;
                border: 12px solid #2ECC71;
                border-radius: 20px;
            }}
        """)

        animation = QPropertyAnimation(btn, b"geometry")
        animation.setDuration(600)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)

        original_geo = btn.geometry()
        larger_geo = QRect(original_geo.x() - 15, original_geo.y() - 15, original_geo.width() + 30,
                           original_geo.height() + 30)

        animation.setStartValue(original_geo)
        animation.setKeyValueAt(0.5, larger_geo)
        animation.setEndValue(original_geo)
        animation.start()

        self.show_success_message()
        self.flash_background("#A9DFBF")

    def animate_failure(self, choice_idx):
        wrong_btn = self.choice_buttons[choice_idx]
        correct_btn = self.choice_buttons[self.correct_answer]

        wrong_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[choice_idx]};
                color: white;
                border: 12px solid #E74C3C;
                border-radius: 20px;
            }}
        """)

        correct_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors[self.correct_answer]};
                color: white;
                border: 12px solid #2ECC71;
                border-radius: 20px;
            }}
        """)

        shake_animation = QPropertyAnimation(wrong_btn, b"geometry")
        shake_animation.setDuration(500)
        original_geo = wrong_btn.geometry()

        shake_animation.setStartValue(original_geo)
        shake_animation.setKeyValueAt(0.2, QRect(original_geo.x() - 10, original_geo.y(),
                                                 original_geo.width(),
                                                 original_geo.height()))
        shake_animation.setKeyValueAt(0.4, QRect(original_geo.x() + 10, original_geo.y(),
                                                 original_geo.width(),
                                                 original_geo.height()))
        shake_animation.setKeyValueAt(0.6, QRect(original_geo.x() - 10, original_geo.y(),
                                                 original_geo.width(),
                                                 original_geo.height()))
        shake_animation.setKeyValueAt(0.8, QRect(original_geo.x() + 10, original_geo.y(),
                                                 original_geo.width(),
                                                 original_geo.height()))
        shake_animation.setEndValue(original_geo)
        shake_animation.start()

        pulse_animation = QPropertyAnimation(correct_btn, b"geometry")
        pulse_animation.setDuration(1000)
        pulse_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        correct_geo = correct_btn.geometry()
        larger_geo = QRect(correct_geo.x() - 10, correct_geo.y() - 10, correct_geo.width() + 20,
                           correct_geo.height() + 20)

        pulse_animation.setStartValue(correct_geo)
        pulse_animation.setKeyValueAt(0.5, larger_geo)
        pulse_animation.setEndValue(correct_geo)
        pulse_animation.start()

        self.show_correct_number()
        self.flash_background("#F5B7B1")

    def show_success_message(self):
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass

        success_messages = ["🎉 BRAVO ! 🎉", "⭐ SUPER ! ⭐", "🏆 GÉNIAL ! 🏆", "✨ EXCELLENT ! ✨"]

        self.message_label = QLabel(random.choice(success_messages), self)
        self.message_label.setFont(QFont('Arial', 40, QFont.Bold))
        self.message_label.setStyleSheet("""
            color: #2ECC71;
            background-color: #FFFFFF;
            border: 6px solid #2ECC71;
            border-radius: 20px;
            padding: 15px;
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setGeometry(self.width() // 2 - 250, 30, 500, 80)
        self.message_label.show()

        opacity_effect = QGraphicsOpacityEffect()
        self.message_label.setGraphicsEffect(opacity_effect)

        fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        fade_out = QPropertyAnimation(opacity_effect, b"opacity")
        fade_out.setDuration(400)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        animation_group = QSequentialAnimationGroup(self)

        def cleanup_message():
            try:
                if self.message_label is not None:
                    self.message_label.deleteLater()
            except RuntimeError:
                pass

        animation_group.addAnimation(fade_in)
        animation_group.addPause(1000)
        animation_group.addAnimation(fade_out)
        animation_group.finished.connect(cleanup_message)
        animation_group.start()

    def show_correct_number(self):
        try:
            if self.message_label is not None:
                self.message_label.deleteLater()
        except RuntimeError:
            pass

        self.message_label = QLabel(f"C'était le chiffre\n{self.current_number}", self)
        self.message_label.setFont(QFont('Arial', 48, QFont.Bold))
        self.message_label.setStyleSheet("""
            color: #2ECC71;
            background-color: #FFFFFF;
            border: 8px solid #2ECC71;
            border-radius: 25px;
            padding: 25px;
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setGeometry(self.width() // 2 - 250, 30, 500, 180)
        self.message_label.show()

        opacity_effect = QGraphicsOpacityEffect()
        self.message_label.setGraphicsEffect(opacity_effect)

        fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)

        fade_out = QPropertyAnimation(opacity_effect, b"opacity")
        fade_out.setDuration(500)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)

        animation_group = QSequentialAnimationGroup(self)

        def cleanup_message():
            try:
                if self.message_label is not None:
                    self.message_label.deleteLater()
            except RuntimeError:
                pass

        animation_group.addAnimation(fade_in)
        animation_group.addPause(1200)
        animation_group.addAnimation(fade_out)
        animation_group.finished.connect(cleanup_message)
        animation_group.start()

    def flash_background(self, color):
        original_palette = self.palette()
        flash_palette = self.palette()
        flash_palette.setColor(QPalette.Window, QColor(color))

        self.setPalette(flash_palette)
        QTimer.singleShot(300, lambda: self.setPalette(original_palette))


class StatsScreen(QWidget):
    """Écran des statistiques"""
    back_to_menu = Signal()

    def __init__(self, data_manager, username):
        super().__init__()
        self.data_manager = data_manager
        self.username = username
        self.setup_ui()
        self.data_manager.add_observer(self.refresh_stats)

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(255, 245, 230))
        self.setPalette(palette)

        layout = QVBoxLayout()

        self.title = QLabel(f"📊 Statistiques de {self.username}")
        self.title.setFont(QFont('Arial', 32, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color: #4ECDC4; margin: 20px; background-color: transparent;")

        self.stats_text = QLabel()
        self.stats_text.setFont(QFont('Arial', 18))
        self.stats_text.setWordWrap(True)
        self.stats_text.setAlignment(Qt.AlignCenter)
        self.stats_text.setStyleSheet("color: #2C3E50; background-color: transparent;")

        self.difficult_label = QLabel()
        self.difficult_label.setFont(QFont('Arial', 16))
        self.difficult_label.setAlignment(Qt.AlignCenter)
        self.difficult_label.setStyleSheet(
            "color: #E74C3C; margin: 20px; background-color: transparent;")

        details_title = QLabel("🔍 Détails par lettre :")
        details_title.setFont(QFont('Arial', 18, QFont.Bold))
        details_title.setAlignment(Qt.AlignCenter)
        details_title.setStyleSheet("color: #2C3E50; margin: 10px; background-color: transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 2px solid #4ECDC4;
                border-radius: 10px;
                background-color: white;
            }
        """)

        self.details_widget = QWidget()
        self.details_layout = QGridLayout()
        self.details_widget.setLayout(self.details_layout)
        self.details_widget.setStyleSheet("background-color: white;")
        scroll.setWidget(self.details_widget)

        back_btn = ColorfulButton("🏠 Retour au menu", "#45B7D1")
        back_btn.setMaximumWidth(650)
        back_btn.clicked.connect(self.back_to_menu.emit)

        layout.addWidget(self.title)
        layout.addWidget(self.stats_text)
        layout.addWidget(self.difficult_label)
        layout.addWidget(details_title)
        layout.addWidget(scroll)
        layout.addStretch()
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        self.refresh_stats()

    def refresh_stats(self):
        user = self.data_manager.get_user(self.username)
        if not user:
            return

        total = user['total_attempts']
        correct = user['total_correct']
        percentage = (correct / total * 100) if total > 0 else 0

        letters_learned = sum(1 for stats in user['stats'].values()
                              if stats['attempts'] > 0 and stats['correct'] / stats['attempts'] >= 0.7)

        total_num = user.get('total_attempts_numbers', 0)
        correct_num = user.get('total_correct_numbers', 0)
        percentage_num = (correct_num / total_num * 100) if total_num > 0 else 0

        if 'stats_numbers' in user:
            numbers_learned = sum(1 for stats in user['stats_numbers'].values()
                                  if stats['attempts'] > 0 and stats['correct'] / stats['attempts'] >= 0.7)
        else:
            numbers_learned = 0

        self.stats_text.setText(f"""
        🔤 LETTRES:
        ✅ Réponses correctes: {correct}/{total} ({percentage:.1f}%)
        📚 Lettres maîtrisées: {letters_learned}/26

        🔢 CHIFFRES:
        ✅ Réponses correctes: {correct_num}/{total_num} ({percentage_num:.1f}%)
        📚 Chiffres maîtrisés: {numbers_learned}/10

        🎯 Continue comme ça, tu progresses bien !
        """)

        difficult = self.data_manager.get_difficult_letters(self.username, 5)
        self.difficult_label.setText("🔍 Lettres à réviser: " + ", ".join(difficult))

        while self.details_layout.count():
            child = self.details_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        row, col = 0, 0
        for letter in sorted(user['stats'].keys()):
            stats = user['stats'][letter]
            attempts = stats['attempts']
            correct = stats['correct']

            if attempts > 0:
                success_rate = (correct / attempts) * 100
                if success_rate >= 70:
                    color = "#2ECC71"
                    icon = "✓"
                elif success_rate >= 40:
                    color = "#F39C12"
                    icon = "~"
                else:
                    color = "#E74C3C"
                    icon = "✗"
            else:
                color = "#95A5A6"
                icon = "○"
                success_rate = 0

            letter_label = QLabel(f"{icon} {letter}: {correct}/{attempts} ({success_rate:.0f}%)")
            letter_label.setFont(QFont('Arial', 12))
            letter_label.setStyleSheet(f"color: {color}; padding: 5px; background-color: transparent;")

            self.details_layout.addWidget(letter_label, row, col)

            col += 1
            if col > 3:
                col = 0
                row += 1


class MenuScreen(QWidget):
    """Écran du menu principal"""
    play_letters_clicked = Signal()
    play_numbers_clicked = Signal()
    stats_clicked = Signal()
    change_user_clicked = Signal()
    quit_clicked = Signal()

    def __init__(self, username, voice_engine):
        super().__init__()
        self.username = username
        self.voice_engine = voice_engine
        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.voice_engine.stop()

    def setup_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(230, 245, 255))
        self.setPalette(palette)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel(f"👋 Bienvenue {self.username} !")
        title.setFont(QFont('Arial', 36, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FF6B6B; margin: 20px; background-color: transparent;")

        subtitle = QLabel("🎮 Choisis ton jeu !")
        subtitle.setFont(QFont('Arial', 24))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #4ECDC4; margin: 10px; background-color: transparent;")

        play_letters_btn = ColorfulButton("🔤 Les Lettres (A-Z)", "#4ECDC4")
        play_letters_btn.setMaximumWidth(600)
        play_letters_btn.setMinimumHeight(90)
        play_letters_btn.clicked.connect(self.play_letters_clicked.emit)

        play_numbers_btn = ColorfulButton("🔢 Les Chiffres (0-9)", "#E67E22")
        play_numbers_btn.setMaximumWidth(600)
        play_numbers_btn.setMinimumHeight(90)
        play_numbers_btn.clicked.connect(self.play_numbers_clicked.emit)

        stats_btn = ColorfulButton("📊 Mes statistiques", "#45B7D1")
        stats_btn.setMaximumWidth(600)
        stats_btn.setMinimumHeight(90)
        stats_btn.clicked.connect(self.stats_clicked.emit)

        change_user_btn = QPushButton("👥 Changer d'enfant")
        change_user_btn.setFont(QFont('Arial', 16))
        change_user_btn.setMaximumWidth(400)
        change_user_btn.setMinimumHeight(60)
        change_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #9B59B6;
                color: white;
                padding: 10px;
                border-radius: 10px;
                border: 3px solid #8E44AD;
            }
            QPushButton:hover {
                background-color: #8E44AD;
            }
        """)
        change_user_btn.clicked.connect(self.change_user_clicked.emit)

        quit_btn = ColorfulButton("👋 Quitter", "#95A5A6")
        quit_btn.setMaximumWidth(400)
        quit_btn.setMinimumHeight(90)
        quit_btn.clicked.connect(self.quit_clicked.emit)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(play_letters_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(play_numbers_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(stats_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(change_user_btn, alignment=Qt.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(quit_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apprends l'Alphabet !")
        self.setMinimumSize(900, 700)

        # Initialiser l'AudioManager et VoiceEngine
        self.audio_manager = AudioManager()
        self.voice_engine = VoiceEngine(self.audio_manager)
        self.data_manager = DataManager()
        self.username = None

        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFF9C4;
            }
        """)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Écran d'initialisation
        self.init_screen = InitializationScreen(self.audio_manager)
        self.init_screen.initialization_complete.connect(self.show_user_selection)
        self.stack.addWidget(self.init_screen)

        # Lancer l'initialisation après l'affichage
        QTimer.singleShot(100, self.init_screen.start_initialization)

    def show_user_selection(self):
        """Affiche l'écran de sélection d'utilisateur"""
        self.user_selection_screen = UserSelectionScreen(self.data_manager, self.voice_engine)
        self.user_selection_screen.user_selected.connect(self.start_game)
        self.stack.addWidget(self.user_selection_screen)
        self.stack.setCurrentWidget(self.user_selection_screen)

    def start_game(self, username):
        """Démarre le jeu pour l'utilisateur sélectionné"""
        self.username = username

        # Nettoyer les anciens widgets si nécessaire
        while self.stack.count() > 2:
            widget = self.stack.widget(2)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        # Créer les écrans de jeu
        self.menu_screen = MenuScreen(username, self.voice_engine)
        self.menu_screen.play_letters_clicked.connect(self.show_letters_game)
        self.menu_screen.play_numbers_clicked.connect(self.show_numbers_game)
        self.menu_screen.stats_clicked.connect(self.show_stats)
        self.menu_screen.change_user_clicked.connect(self.change_user)
        self.menu_screen.quit_clicked.connect(self.close)

        self.letters_game_screen = GameScreen(self.data_manager, self.voice_engine, username)
        self.letters_game_screen.back_to_menu.connect(self.show_menu)

        self.numbers_game_screen = NumbersGameScreen(self.data_manager, self.voice_engine, username)
        self.numbers_game_screen.back_to_menu.connect(self.show_menu)

        self.stats_screen = StatsScreen(self.data_manager, username)
        self.stats_screen.back_to_menu.connect(self.show_menu)

        self.stack.addWidget(self.menu_screen)
        self.stack.addWidget(self.letters_game_screen)
        self.stack.addWidget(self.numbers_game_screen)
        self.stack.addWidget(self.stats_screen)

        self.show_menu()

    def show_menu(self):
        """Affiche le menu principal"""
        self.data_manager.save_data()
        self.stack.setCurrentWidget(self.menu_screen)

    def show_letters_game(self):
        """Affiche le jeu des lettres"""
        self.stack.setCurrentWidget(self.letters_game_screen)

    def show_numbers_game(self):
        """Affiche le jeu des chiffres"""
        self.stack.setCurrentWidget(self.numbers_game_screen)

    def show_stats(self):
        """Affiche les statistiques"""
        self.stats_screen.refresh_stats()
        self.stack.setCurrentWidget(self.stats_screen)

    def change_user(self):
        """Retourne à la sélection d'utilisateur"""
        self.data_manager.save_data_sync()
        self.voice_engine.stop()
        self.user_selection_screen.refresh_user_list()
        self.stack.setCurrentWidget(self.user_selection_screen)

    def closeEvent(self, event):
        """Nettoyage lors de la fermeture"""
        self.data_manager.save_data_sync()
        self.voice_engine.shutdown()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())