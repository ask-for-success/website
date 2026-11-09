# Conception de la base de données AFS

**Projet :** site public et plateforme des membres Ask For Success

**Moteur retenu :** PostgreSQL

**État :** modèle V1 corrigé et prêt pour validation d’équipe

## Décision

PostgreSQL est retenu comme moteur de base de données. Le modèle utilise des identifiants UUID, des dates avec fuseau horaire, des contraintes relationnelles explicites et des types PostgreSQL adaptés aux données structurées.

Le fichier [`AFS_Database.dbml`](./AFS_Database.dbml) représente les tables métier AFS. Il ne reproduit pas les tables techniques créées automatiquement par Django.

## Tables gérées automatiquement par Django

Django crée et maintient notamment :

- `django_migrations` ;
- `django_content_type` ;
- `django_session` ;
- `auth_group` ;
- `auth_permission` ;
- les tables de liaison entre utilisateurs, groupes et permissions.

Ces tables servent aux migrations, sessions, groupes et permissions globales. Elles seront créées par les migrations Django et ne doivent pas être recréées manuellement dans le DBML métier.

Le modèle AFS conserve une table utilisateur personnalisée, car le compte possède des champs métier propres au projet. Les groupes et permissions globales restent gérés par Django. Les autorisations de contrôle d’entrée liées à un événement précis sont conservées dans une table métier dédiée.

## Changements principaux

### Identité et membres

- séparation entre le statut du compte et le statut de l’adhésion ;
- ajout des départements et fonctions internes ;
- ajout de l’affectation principale du membre ;
- ajout du parcours d’intégration obligatoire ;
- protection du document d’identité par une référence vers un fichier sensible ;
- ajout d’une médiathèque de fichiers réutilisables.

### Recrutement

- remplacement des formulaires par poste par un formulaire réutilisable par département ;
- verrouillage du formulaire après la première candidature ;
- ajout des choix de questions dans une table structurée ;
- ajout du type de question date ;
- ajout des six statuts de candidature confirmés ;
- ajout des notes RH privées ;
- ajout des demandes d’adhésion directe ;
- conservation séparée du résultat d’envoi du courriel de décision.

### Événements

- ajout des périodes d’ouverture et de fermeture des inscriptions ;
- ajout du mode de validation automatique ou manuelle ;
- ajout de la configuration QR ;
- distinction entre validation de l’inscription et présence réelle ;
- création d’un contrôle d’entrée unique et auditable ;
- ajout des autorisations de contrôle limitées à un événement ;
- stockage du jeton QR sous forme d’empreinte ;
- simplification du formulaire public aux champs confirmés pour la V1.

### Contenus et CMS

- remplacement des tables photo et vidéo par une médiathèque commune ;
- suppression des albums et catégories de galerie non requis en V1 ;
- unification des actualités, histoires et annonces publiques ;
- ajout des sélections de contenu mises en avant ;
- conservation des sections fixes des pages publiques ;
- suppression de la traduction multilingue de la V1 ;
- suppression de l’état lu ou non lu des notifications membres.

### Audit et sécurité

- journal d’audit en ajout seulement ;
- ajout de l’acteur, de la cible, du résultat, de la requête et des métadonnées techniques ;
- politiques de suppression explicites sur toutes les relations ;
- interdiction de stocker les secrets dans les paramètres du site ;
- conservation des fichiers réels hors de PostgreSQL.

## Modules métier

| Module | Responsabilité |
|---|---|
| Identité et organisation | comptes, membres, départements, fonctions et fichiers |
| Recrutement | formulaires, opportunités, candidatures, réponses, notes RH et adhésion directe |
| Événements | événements, inscriptions, QR, contrôle d’entrée et rappels |
| Contenus et CMS | contenus publics, galerie, sections, mises en avant et notifications |
| Engagement | dons, partenaires et demandes de partenariat |
| Audit | historique sécurisé des actions importantes |

## Règles obligatoires à appliquer dans les migrations

Certaines contraintes PostgreSQL dépassent la syntaxe portable du DBML. Les migrations doivent ajouter explicitement :

- l’extension `citext` ;
- un seul droit actif de contrôle par utilisateur et événement ;
- la cohérence des dates de début, fin, ouverture et fermeture d’un événement ;
- des valeurs positives pour capacité, prix, montant et taille de fichier ;
- exactement une cible pour chaque mise en avant ;
- exactement une valeur de réponse correspondant au type de question ;
- les champs obligatoires selon le type de don ;
- la cohérence entre activation QR et inscription active.

## Politique de suppression

- les comptes utilisateurs sont désactivés et non supprimés physiquement ;
- les candidatures, inscriptions, décisions, contrôles et audits sont conservés ;
- les contenus publics sont archivés ;
- les fichiers sensibles sont supprimés du stockage selon la politique de conservation, puis leur métadonnée est archivée ;
- les relations historiques utilisent `RESTRICT` afin d’éviter une suppression accidentelle ;
- seules les véritables données dépendantes utilisent `CASCADE`.

## Résultat attendu

Ce modèle devient la source de vérité pour les migrations de la base de données. Les modèles de l’ORM devront respecter les noms, contraintes, relations et responsabilités définis dans le DBML approuvé.
