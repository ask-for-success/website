# AFS Database Architecture & Design Decisions

**Project:** Ask For Success – Website and Member Platform

**Modeling Language:** DBML  
**Diagramming Tool:** dbdiagram.io  
**Status:** Database Design Completed · Implementation Pending

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Database Architecture Overview](#2-database-architecture-overview)
3. [Module 01 - Identity & Access Management](#3-module-01---identity--access-management)
4. [Module 02 - Recruitment & Applications](#4-module-02---recruitment--applications)
5. [Module 03 - Events & Registrations](#5-module-03---events--registrations)
6. [Module 04 - Content & Media Management](#6-module-04---content--media-management)
7. [Module 05 - Community & Engagement](#7-module-05---community--engagement)
8. [Module 06 - Website CMS & Configuration](#8-module-06---website-cms--configuration)
9. [Important Implementation Considerations](#9-important-implementation-considerations)
10. [Conclusion](#conclusion)

---

## 1. Introduction

The AFS database is designed to support the Ask For Success website and its internal member platform.

It provides a centralized structure for managing user accounts, member permissions, recruitment applications, events, content, community engagement, and website configuration.

The database is organized into six functional modules. This modular organization makes the structure easier to understand, maintain, and extend as the platform develops.

The database diagram represents the logical structure of the system, including its tables, attributes, constraints, and relationships.

---

## 2. Database Architecture Overview

The database is divided into six modules:

| Module | Responsibility |
|---|---|
| **01. Identity & Access Management** | User accounts, member profiles, roles, permissions, notifications, and activity logs. |
| **02. Recruitment & Applications** | Departments or positions, application questions, applications, and submitted answers. |
| **03. Events & Registrations** | Event information, participant registrations, tickets, check-in, and reminders. |
| **04. Content & Media Management** | Articles, article categories, gallery photos, videos, and gallery categories. |
| **05. Community & Engagement** | Donations, partners, and partnership requests. |
| **06. Website CMS & Configuration** | Website statistics, editable page sections, settings, and translations. |

Each module groups tables according to their responsibilities rather than placing all application data into a single collection of tables.

---

## 3. Module 01 - Identity & Access Management

This module manages the identity of users and controls access to the platform.

### Main Tables

- **`USERS`**: Stores account information, including names, email addresses, password hashes, account status, and creation dates.
- **`MEMBER_PROFILES`**: Stores additional profile information separately from the main account after being an approved member.
- **`ROLES`**: Defines roles that can be assigned to users.
- **`PERMISSIONS`**: Defines individual permissions within different platform modules.
- **`USER_ROLES`**: Connects users with their assigned roles.
- **`ROLE_PERMISSIONS`**: Connects roles with the permissions they grant.
- **`NOTIFICATIONS`**: Stores notifications associated with roles.
- **`ACTIVITY_LOGS`**: Records user actions performed within the platform.

### Design Decisions

#### 1. Separation of `USERS` and `MEMBER_PROFILES`

Account information and additional member information are stored separately.

#### 2. Role-Based Access Control (RBAC)

The system uses roles and permissions instead of assigning every permission directly to an individual user.

The relationship between users and roles is many-to-many through `USER_ROLES`. Similarly, roles and permissions are connected through `ROLE_PERMISSIONS`.

#### 3. Separation of roles and permissions

A role represents a collection of responsibilities, while a permission represents a specific action that can be authorized.

#### 4. Notifications and activity logs

Notifications communicate information to users, while activity logs provide a record of actions performed in the platform.

---

## 4. Module 02 - Recruitment & Applications

This module manages the recruitment process and applications submitted by candidates.

### Main Tables

- **`POSITIONS`**: Stores the available departments or positions displayed on the recruitment section.
- **`POSITION_QUESTIONS`**: Stores the questions associated with each position.
- **`APPLICATIONS`**: Stores candidate applications and their review status.
- **`APPLICATION_ANSWERS`**: Stores answers submitted for individual application questions.

### Design Decisions

#### 1. Dynamic application questions

Questions are stored in `POSITION_QUESTIONS` instead of being hardcoded into the application structure.

Each position can have its own questions, question types, required status, options, and display order.

The question types include:

- Short text
- Long text
- Choice
- Multiple choice
- Yes/no
- File upload

#### 2. Separation of applications and answers

`APPLICATIONS` represents the application itself, while `APPLICATION_ANSWERS` stores the candidate's responses.

#### 3. File upload support

`APPLICATION_ANSWERS` includes `answer_file_url` for answers that contain uploaded files.

The database stores the file reference, while the actual file can be handled by the application's file-storage system.

#### 4. Application status tracking

Each application has a status: `pending`, `approved`, `rejected`.

The `reviewed_by` and `reviewed_at` fields record who reviewed the application and when the review occurred.

#### 5. Duplicate application prevention

A unique constraint on `(user_id, position_id)` prevents the same user from having multiple application records for the same position.

---

## 5. Module 03 - Events & Registrations

This module manages AFS events and participant registration.

### Main Tables

- **`EVENTS`**: Stores event details, including title, description, dates, times, location, capacity, price, cover image, and publication status.
- **`EVENT_REGISTRATIONS`**: Stores participant information and registration records.
- **`EVENT_REGISTRATION_REMINDERS`**: Records reminders sent for individual registrations.

### Design Decisions

#### 1. Separation of events and registrations

An event is stored independently from its participants.

One event can have multiple registrations, while each registration belongs to one event.

#### 2. Participant information

`EVENT_REGISTRATIONS` stores participant information directly, including name, email, phone number, age, city, education, and organization, and this structure does not require participants to have an existing member account to register.

#### 3. QR ticket validation

Each registration has a `unique_token` field.

This provides a unique identifier that can be used by the ticketing and QR check-in system to identify and validate a registration.

The `checked_in_at` field records when the participant was checked in.

#### 4. Registration reminders

`EVENT_REGISTRATION_REMINDERS` stores reminder records separately.

The unique constraint on `(registration_id, reminder_key)` prevents the same reminder type from being recorded more than once for a registration.

#### 5. Registration status and ticket delivery

The registration status currently supports `pending` and `issued`.

The `ticket_sent_at` field separately records when the ticket was sent.

---

## 6. Module 04 - Content & Media Management

This module manages the content displayed on the public AFS website.

### Main Tables

- **`ARTICLE_CATEGORIES`**: Defines categories for articles.
- **`ARTICLES`**: Stores articles, their content, authors, categories, publication status, and related information.
- **`GALLERY_CATEGORIES`**: Defines categories used to organize gallery content.
- **`GALLERY_PHOTOS`**: Stores photo metadata and references to uploaded images.
- **`GALLERY_VIDEOS`**: Stores video metadata and references to video content.

### Design Decisions

#### 1. Separation of articles and categories

Articles reference `ARTICLE_CATEGORIES` instead of storing category names directly.

This makes category management centralized and allows multiple articles to belong to the same category.

#### 2. Separate photo and video tables

Photos and videos are stored in different tables because they have different attributes.

For example, photos have captions and display ordering, while videos can have thumbnails, durations, and publication dates.

#### 3. Event association

Gallery photos and videos can optionally reference an event.

This allows media to be associated with a specific event while still supporting general gallery content.

#### 4. Visibility management

Gallery records include `is_visible`, allowing administrators to control whether media appears publicly without necessarily deleting the record.

---

## 7. Module 05 - Community & Engagement

This module manages interactions between AFS and external individuals or organizations.

### Main Tables

- **`DONATIONS`**: Stores donation information, donor contact details, donation type, amount or goods description, delivery method, and processing status.
- **`PARTNERS`**: Stores information about AFS partners and their public visibility.
- **`PARTNER_REQUESTS`**: Stores requests submitted by organizations interested in collaborating with AFS.

### Design Decisions

#### 1. Different donation types

The `donation_type` field distinguishes between cash and goods donations.

The `amount` field stores monetary values, while `goods_description` describes donated items.

The `delivery_method` field supports drop-off and pickup.

#### 2. Donation processing

The donation status tracks the processing stage: `new`, `contacted`, `confirmed`, `received`, or `declined`.

The `handled_by` field optionally links a donation to the user responsible for handling it.

#### 3. Separation of partners and partner requests

`PARTNERS` represents existing partners, while `PARTNER_REQUESTS` represents incoming collaboration requests.

This distinction allows an organization to submit a request without automatically becoming an official partner.

#### 4. Partnership request tracking

Each request has an organization type, contact information, offer type, message, and processing status.

The optional `partner_id` allows a request to be associated with an existing partner when applicable.

---

## 8. Module 06 - Website CMS & Configuration

This module supports the management of website content and configuration.

### Main Tables

- **`STATS`**: Stores statistics displayed on the website.
- **`PAGE_SECTIONS`**: Stores editable website section content, including titles, body text, images, and display order.
- **`SITE_SETTINGS`**: Stores configurable website settings as key-value entries.
- **`TRANSLATIONS`**: Stores translated values associated with different entities and fields.

### Design Decisions

#### 1. Editable page sections

`PAGE_SECTIONS` allows administrators to update selected website content without changing the frontend source code for every content update.

The combination of `page` and `section_key` identifies a section within a page.

A unique constraint on `(page, section_key)` prevents duplicate section identifiers for the same page.

#### 2. Centralized website settings

`SITE_SETTINGS` uses `setting_key` and `setting_value` to store configurable values.

This avoids creating a separate table for every simple website setting.

> [!WARNING]
> Sensitive credentials and API secrets should not be stored in this table.

#### 3. Translation management

`TRANSLATIONS` uses `entity_type`, `entity_id`, `language`, and `field_name` to identify which content field a translation belongs to.

The supported languages are Arabic, French, and English.

This design supports translations across different types of content without requiring separate translation columns in every content table.

#### 4. Website statistics

`STATS` stores manually managed statistics and their display order.

---

## 9. Important Implementation Considerations

The DBML describes the logical database design. Some implementation details must still be handled during backend and database development.

- **Foreign key deletion rules:** Define whether related records should be restricted from deletion, deleted together, or have their references set to `NULL`. Historical applications and event registrations should be protected against accidental deletion.
- **File storage:** Uploaded files and media should be stored in an appropriate file-storage system. The database stores their references.
- **RBAC enforcement:** Permissions must be checked by the backend when users access protected operations.
- **Sensitive information:** Member profile information, especially `CIN`, requires appropriate access restrictions and protection.
- **Translation validation:** `TRANSLATIONS` uses a polymorphic relationship. The backend must validate that the referenced entity exists because `entity_id` does not have a conventional foreign key to every possible content table.
- **Conditional validation:** Donation fields should be validated according to `donation_type`. For example, cash donations require an appropriate monetary amount, while goods donations require a goods description.
- **Database migrations:** Structural changes after implementation should be managed through controlled database migrations.

---

## Conclusion

The AFS database is organized around the main functional requirements of the public website and internal member platform.

Its modular structure separates identity management, recruitment, events, content, community engagement, and website configuration.

The design uses relational relationships, junction tables, enumerations, and constraints to organize information and support data consistency.

The database diagram serves as the foundation for the next development stage: implementing the database, developing the backend, and connecting the frontend to the application services.

---

## Reference Files

- [`AFS_Database.dbml`](./AFS_Database.dbml) – Editable database model.
- [View ERD on dbdiagram.io](https://dbdiagram.io/d/6aed0e5a7ded3580fac3f724) – Interactive entity-relationship diagram.

---

**Document Status:** Initial architecture and design decisions documentation.
