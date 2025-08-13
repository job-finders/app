# Encryptor Documentation

## Overview

The `Encryptor` class provides password hashing and comparison functionality using Flask-Bcrypt.

## Purpose

-   To securely hash passwords for storage.
-   To compare a given password against a stored hash.

## Dependencies

-   Flask: Used for application context.
-   Flask-Bcrypt: Used for password hashing.

## Methods

### `__init__(self)`

-   **Description:** Initializes the `Encryptor` class.
    -   Initializes `_bcrypt` to None.
-   **Parameters:** None
-   **Returns:** None

### `init_app(self, app: Flask)`

-   **Description:** Initializes the Flask-Bcrypt extension.
-   **Parameters:**
    -   `app` (Flask): The Flask application instance.
-   **Returns:** None
-   **Details:**
    -   Initializes the Flask-Bcrypt extension for the given app.

### `create_hash(self, password: str) -> str`

-   **Description:** Generates a password hash.
-   **Parameters:**
    -   `password` (str): The password to hash.
-   **Returns:** A string representing the password hash.
-   **Details:**
    -   Uses `bcrypt.generate_password_hash` to generate the hash.
    -   Decodes the hash to a UTF-8 string.

### `compare_hashes(self, hash: str, password: str)`

-   **Description:** Compares a password against a stored hash.
-   **Parameters:**
    -   `hash` (str): The stored password hash.
    -   `password` (str): The password to compare against the hash.
-   **Returns:** A boolean indicating whether the password matches the hash.
-   **Details:**
    -   Uses `bcrypt.check_password_hash` to compare the password against the hash.

## Input Validation

-   The controller relies on Flask-Bcrypt for input validation.

## Error Handling

-   No explicit error handling is used, relies on Flask-Bcrypt.

## Notes

-   This class provides basic password hashing and comparison functionality.
-   Ensure that Flask-Bcrypt is properly configured in the Flask application.