-- Create database and table
CREATE DATABASE IF NOT EXISTS infura_io;

USE infura_io;

CREATE TABLE IF NOT EXISTS Bonds (
    id INT AUTO_INCREAMENT PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    contract_address VARCHAR(255) NOT NULL,
    date_time DATETIME NOT NULL,
    bonus DECIMAL(10, 2) NOT NULL,
    min_price DECIMAL(18, 2) NOT NULL,
    max_price DECIMAL(18, 2) NOT NULL,
    max_buy DECIMAL(18, 2) NOT NULL
);
