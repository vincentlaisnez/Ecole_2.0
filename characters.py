# apprendre les lettres pour une enfant en maternel
import json
import random
import pyttsx3
import os


class Pyttsx3Voice:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        for voice in self.voices:
            if "french" in voice.languages:
                self.engine.setProperty('voice', voice.id)
                break

    def say(self, text):
        self.engine.say(text)
        self.engine.runAndWait()


def check_file_exist():
    if os.path.exists("profil.json"):
        with open("profil.json", 'r') as f:
            datas = json.load(f)
    else:
        datas = {'nom': '', 'score': 0, 'alphabet': []}
    return datas


def update_file(data_updated):
    with open("profil.json", 'w') as f:
        json.dump(data_updated, f, indent=4)


engine = Pyttsx3Voice()

datas = check_file_exist()

points = 0
lettres = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
           'w', 'x', 'y', 'z']
choise = "1"

if datas['nom'] != '':
    nom = datas['nom']
else:
    nom = input('Quel est votre nom ? ')

points = datas['score']
chars = datas['alphabet']
print("Bienvenue", nom, "!")
while choise != "2":
    print("--" * 30)
    Lettre_aleatoire = (random.choice(lettres))
    print(Lettre_aleatoire)
    engine.say(Lettre_aleatoire)
    lettre = input("Quelle lettre est affichée ? : ")
    if lettre == Lettre_aleatoire:
        points += 1
        print("Bravo ! Tu as réussi !")
        if not lettre in chars:
            chars.append(lettre)
    else:
        print("Dommage ! C'est la lettre :", Lettre_aleatoire)

    print("--" * 30)
    print("Voulez-vous continuer ?")
    print("1. Oui")
    print("2. Non")
    choise = input("Taper 1 ou 2 : ")

print("Merci d'avoir joué !")
print("Tu as au total", points, "points")

if len(chars) == 26:
    print("Tu as réussi à reconnaître les 26 lettres de l'alphabet !")
    print("Tu peux passer au niveau suivant !")

datas['nom'] = nom
datas['score'] = points
datas['alphabet'] = chars
update_file(datas)

if __name__ == '__main__':
    pass
