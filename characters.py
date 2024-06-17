# apprendre les lettres pour une enfant en maternel
import random
import string

# TODO: faire correspondre les lettres afficher aléatoirement avec ce qu'il marque
# Ajouter une API de reconnaissance vocale pour correspondre ce qui est afficher
# avec ce que dit l'utilisateur.
points = 0
lettres = string.ascii_letters
choise = "1"
while choise != "2":
    print("--"*30)
    Lettre_aleatoire = (random.choice(lettres))
    print(Lettre_aleatoire)
    lettre = input("Quelle lettre est affichée ? : ")
    if lettre == Lettre_aleatoire:
        points += 1
        print("Bravo ! Tu as ", points, "points")
    else:
        print("Dommage ! C'est la lettre :", Lettre_aleatoire)
    print("--"*30)
    print("Voulez-vous continuer ?")
    print("1. Oui")
    print("2. Non")
    choise = input("Taper 1 ou 2 : ")

print("Merci d'avoir joué !")
print("Tu as obtenu", points, "points")

if __name__ == '__main__':
    pass
