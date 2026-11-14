# Décisions approuvées

Ce registre contient les décisions stables du projet. Les autres documents doivent y faire référence au lieu de recopier les mêmes règles.

## D-001 — Cadre du serveur

Le serveur utilise Django et Django REST Framework.

## D-002 — Base de données

PostgreSQL est la base de données de l'application. Les migrations Django définissent le schéma réel.

## D-003 — Environnement local

Docker Compose fournit Django et PostgreSQL. Une infrastructure supplémentaire est ajoutée seulement lorsqu'une fonctionnalité approuvée l'exige.

## D-004 — Identité utilisateur

Chaque utilisateur possède un identifiant universel unique et immuable. L'adresse électronique sert à la connexion, mais ne constitue pas l'identifiant de la base de données.

## D-005 — Modèle de compte unique

Les candidats, membres, gestionnaires et administrateurs partagent le même modèle de compte. Les responsabilités métier restent séparées de l'authentification.

## D-006 — Absence de vérification initiale de l'adresse électronique

Un compte actif peut se connecter immédiatement après son inscription. Aucun modèle de vérification initiale de l'adresse électronique n'est prévu.

## D-007 — Authentification par jetons

Le jeton d'accès dure quinze minutes et le jeton de renouvellement dure sept jours. Le renouvellement remplace la paire, la déconnexion révoque le jeton transmis et le changement de mot de passe invalide les sessions.

## D-008 — Langue du projet

Tous les livrables du projet sont rédigés en français, sauf demande explicite de l'utilisateur pour un livrable précis.

## D-009 — Traduction de l'interface

Le frontend traduit les libellés fixes. Le contenu dynamique du gestionnaire de contenu utilise actuellement une seule langue source. Un stockage multilingue nécessite une nouvelle conception approuvée.

## D-010 — Identité nationale après admission

Le numéro d'identité nationale est demandé pendant l'intégration d'un membre accepté, jamais pendant l'inscription. Aucun scan, image ou fichier de pièce d'identité n'est accepté.

## D-011 — Contrat OpenAPI généré

La bibliothèque de génération produit OpenAPI, Swagger et ReDoc à partir des sérialiseurs et des vues. Chaque nouvelle route doit déclarer sa requête, ses réponses, son authentification, son résumé et sa description.

## D-012 — Modèle global d'autorisation

Les rôles globaux utilisent les groupes Django et les capacités utilisent les permissions Django. Les rôles globaux approuvés sont l'administration des comptes et la gestion du contenu. L'accès aux opérations de ressources humaines est une permission individuelle réservée à certains gestionnaires de contenu ; ce n'est ni un rôle ni un type de compte. Le statut de candidat dépend du contexte, l'adhésion appartient au futur domaine des membres et le contrôle d'accès aux événements reste propre à chaque événement. La table des utilisateurs ne contient aucun champ de rôle.

## D-013 — Une seule affectation active

Un membre possède exactement un département actif et un poste actif à un instant donné. Les candidatures multiples sont autorisées, mais aucune décision ne peut créer plusieurs affectations actives. L'historique des affectations est conservé.

## D-014 — Chemins d'admission

Une candidature approuvée crée une adhésion pour le compte existant du candidat. Pour une personne recrutée et interrogée en dehors des formulaires, un gestionnaire de contenu autorisé aux opérations de ressources humaines lance l'invitation. Le système crée ou réutilise le compte et envoie un message sécurisé d'acceptation et d'intégration. Un compte existant est toujours réutilisé afin d'éviter les doublons.

## D-015 — Nouvelle candidature après un départ

Lorsqu'un membre quitte l'association, son affectation active prend fin sans supprimer son compte ni son historique. La personne utilise le même compte pour présenter une nouvelle candidature et peut ensuite recevoir une nouvelle affectation unique.

## D-016 — Accès au numéro d'identité nationale

Le numéro complet est visible uniquement par un gestionnaire de contenu autorisé aux opérations de ressources humaines et par l'administrateur système autorisé. Chaque accès est sensible et doit être audité. Les autres utilisateurs ne reçoivent jamais la valeur complète.

## D-017 — Changement de département

Un membre déjà actif peut présenter une candidature à une nouvelle occasion dans un autre département. Une acceptation ultérieure ne crée ni une seconde adhésion, ni une seconde affectation active, ni une nouvelle intégration. Un gestionnaire de contenu autorisé aux opérations de ressources humaines effectue le changement de département.

Le changement ferme l'affectation courante et crée la nouvelle affectation dans une seule transaction. Il enregistre obligatoirement l'ancien département, le nouveau département, l'ancien poste, le nouveau poste, le responsable de l'action, la date et le motif. Le membre reçoit une notification de changement. Son état d'intégration reste inchangé.

## D-018 — Absence de sélection entre plusieurs départements

Le produit ne propose aucun écran permettant de choisir entre plusieurs départements acceptés. La première admission crée l'affectation initiale. Toute acceptation concernant un membre déjà affecté doit passer par l'opération explicite de changement de département. Une approbation de candidature ne peut jamais contourner cette règle.

## D-019 — Intégration unique

L'intégration appartient au membre et non au département. Le système distingue l'état d'envoi des messages de l'état réel de l'intégration. Une intégration terminée n'est jamais répétée après un changement de département. Aucun compteur de messages ne décide de l'état d'intégration.
