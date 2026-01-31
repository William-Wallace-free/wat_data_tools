CREATE TABLE IF NOT EXISTS wat_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_id VARCHAR(50),
    wafer_id VARCHAR(50),
    x_index INT,
    y_index INT,
    param_name VARCHAR(50),
    value FLOAT,
    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert dummy data
INSERT INTO wat_data (lot_id, wafer_id, x_index, y_index, param_name, value) VALUES 
('L01', 'W01', 0, 0, 'Vth', 0.75),
('L01', 'W01', 1, 0, 'Vth', 0.76),
('L01', 'W01', 0, 1, 'Vth', 0.74),
('L01', 'W01', 1, 1, 'Vth', 0.80);
