CREATE DATABASE smart_garden;
USE smart_garden;

CREATE TABLE sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    reg_limit INT
);

CREATE TABLE readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    moisture INT,
    pump_state VARCHAR(10),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);