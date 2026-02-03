# Query Engine Architecture

## Module: Backend Development - Advanced Node.js

## 1. Project Objective

In this module, my goal was to transition from a basic CRUD application to a Production-Grade Architecture. I moved away from "fat controllers" to a layered approach, implementing a dynamic Query Engine capable of handling complex filtering, sorting, and pagination without hardcoding individual routes.

## 2. Architechture

### A. The Layered Architecture (Separation of Concerns)

To ensure scalability and maintainability, I restructured the application into three distinct layers:

Controller Layer: Strictly handles HTTP requests/responses. It does not contain business logic.

Service Layer: The "brain" of the application. It handles the logic (filtering, soft deletes) and communicates with the database.

Data Access Layer (Repository/Model): Manages the direct interaction with MongoDB.

### B. The Advanced Query Engine

Instead of writing separate endpoints for every filter (e.g., /products/cheap, /products/expensive), I implemented a dynamic translator.

Concept: The engine intercepts the URL query string, parses special operators (like gte for "greater than"), and maps them to MongoDB operators ($gte).

Benefit: This allows the frontend to construct complex queries on the fly without requiring backend code changes.

### C. Soft Deletes vs. Hard Deletes

I chose to implement Soft Deletes for data safety.

Hard Delete: Physically removing data (DELETE FROM...). This is risky and non-recoverable.

Soft Delete (My Implementation): I introduced an isDeleted boolean flag. When a user "deletes" an item, the system simply hides it by setting this flag to true. This allows for data recovery and audit trails.

### D. Centralized Error Handling

I replaced scattered try/catch blocks with a global error middleware. This ensures that every error—whether a database failure or a validation error—returns a consistent JSON structure (success, message, code) to the client.


![SS1](day3/AfterDeletion.png)
![SS1](day3/Deleted_sucessfully.png)