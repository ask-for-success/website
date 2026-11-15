# Adhésions et invitations

Ce guide décrit le parcours d'invitation déjà implémenté. Swagger reste la source exacte des champs, des réponses et des codes HTTP : [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Limite fonctionnelle

L'invitation concerne une personne déjà acceptée après un recrutement réalisé hors des formulaires. Elle ne décide pas de son admission. Lors de sa création, le serveur prépare le compte inactif, l'adhésion, l'intégration et l'affectation initiale.

Un candidat qui possède déjà un compte actif utilise le parcours normal d'admission et se connecte avec ce compte. L'API d'invitation refuse volontairement un compte actif existant.

## Créer une invitation

`POST /api/v1/adhesions/invitations/`

Cette route exige un jeton d'accès appartenant à un gestionnaire de contenu qui possède aussi la permission individuelle de gestion des ressources humaines.

```json
{
  "adresse_electronique": "membre@example.com",
  "prenom": "Sara",
  "nom": "Amrani",
  "departement_id": "00000000-0000-0000-0000-000000000000",
  "poste_id": "00000000-0000-0000-0000-000000000000"
}
```

La réponse `201` contient l'identifiant de l'invitation, son expiration et le jeton de configuration. Le jeton brut est retourné une seule fois pour permettre les essais tant que le service de courriel n'est pas encore branché. Il ne doit pas être journalisé ni conservé par le frontend.

Une nouvelle création pour le même compte invité inactif annule le jeton précédent et conserve la même adhésion. Le département et le poste doivent rester identiques pendant cette nouvelle émission.

## Configurer le compte invité

`POST /api/v1/adhesions/invitations/accepter/`

Cette route est publique parce que le jeton constitue le secret temporaire. Elle ne nécessite pas de jeton de connexion.

```json
{
  "jeton": "jeton-recu-dans-le-message",
  "numero_telephone": "+212600000000",
  "mot_de_passe": "MotDePasseSolide!2026",
  "confirmation_mot_de_passe": "MotDePasseSolide!2026"
}
```

La réponse `204` confirme la configuration. Le compte devient actif, le téléphone unique est enregistré, le mot de passe est défini et l'invitation devient inutilisable. La personne peut ensuite se connecter normalement et poursuivre son intégration.

Le serveur refuse un jeton inconnu, annulé, déjà utilisé ou expiré, un téléphone déjà utilisé et un mot de passe qui ne respecte pas les règles de sécurité.

## Règles de sécurité

- Le jeton expire après quarante-huit heures.
- Une seule invitation peut être active pour un utilisateur.
- Seule l'empreinte cryptographique du jeton est stockée.
- Une invitation est utilisable une seule fois.
- Un compte actif ne peut pas rester sans numéro de téléphone.
- Le jeton d'invitation ne remplace jamais une décision d'admission.
