CREATE DATABASE IF NOT EXISTS lost_found_db;

USE lost_found_db;


CREATE TABLE IF NOT EXISTS users (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    role ENUM('user','admin')
        DEFAULT 'user',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS items (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    item_type ENUM('lost','found')
        NOT NULL,

    item_name VARCHAR(150)
        NOT NULL,

    category VARCHAR(100),

    brand VARCHAR(100),

    color VARCHAR(80),

    location VARCHAR(200),

    item_date DATE,

    description TEXT,

    image VARCHAR(255),

    status ENUM(
        'active',
        'matched',
        'closed'
    )
    DEFAULT 'active',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS matches (

    id INT AUTO_INCREMENT PRIMARY KEY,

    lost_item_id INT NOT NULL,

    found_item_id INT NOT NULL,

    score DECIMAL(5,2) NOT NULL,

    status ENUM(
        'pending',
        'verified',
        'rejected'
    )
    DEFAULT 'pending',

    created_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_match (
        lost_item_id,
        found_item_id
    ),

    FOREIGN KEY (lost_item_id)
        REFERENCES items(id)
        ON DELETE CASCADE,

    FOREIGN KEY (found_item_id)
        REFERENCES items(id)
        ON DELETE CASCADE
);