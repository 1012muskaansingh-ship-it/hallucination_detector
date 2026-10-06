-- Phase 1: ECU Telemetry & Sensor Logic Ground Truth Graph G = (V, E)

DROP TABLE IF EXISTS ecu_pathways;
DROP TABLE IF EXISTS logic_rules;
DROP TABLE IF EXISTS telemetry_nodes;

-- V: The Vertices (Vehicle Components & Sensors)
CREATE TABLE telemetry_nodes (
    node_id SERIAL PRIMARY KEY,
    component_name VARCHAR(255) UNIQUE NOT NULL,
    subsystem_category VARCHAR(100) NOT NULL -- e.g., 'Braking', 'Powertrain', 'Thermals'
);

-- P: The Predicates (Physical & Electronic Relationships)
CREATE TABLE logic_rules (
    rule_id SERIAL PRIMARY KEY,
    relation_type VARCHAR(100) UNIQUE NOT NULL
);

-- E: The Edges (Verified Valid Pathways)
CREATE TABLE ecu_pathways (
    pathway_id SERIAL PRIMARY KEY,
    source_node_id INT REFERENCES telemetry_nodes(node_id) ON DELETE CASCADE,
    rule_id INT REFERENCES logic_rules(rule_id) ON DELETE CASCADE,
    target_node_id INT REFERENCES telemetry_nodes(node_id) ON DELETE CASCADE,
    UNIQUE(source_node_id, rule_id, target_node_id)
);
---
-- Seed Vertices (V)
INSERT INTO telemetry_nodes (node_id, component_name, subsystem_category) VALUES 
(1, 'Brake Bias Dial', 'Braking'),
(2, 'Front Master Cylinder', 'Braking'),
(3, 'High Voltage Accumulator', 'Powertrain'),
(4, 'Powertrain ECU', 'Electronics'),
(5, 'Accumulator Cooling Fans', 'Thermals');

-- Seed Predicates (P)
INSERT INTO logic_rules (rule_id, relation_type) VALUES 
(1, 'MODULATES_PRESSURE_IN'),
(2, 'READS_THERMAL_DATA_FROM'),
(3, 'ACTIVATES');

-- Seed Edges (E): The mathematically valid physical pathways
INSERT INTO ecu_pathways (source_node_id, rule_id, target_node_id) VALUES 
-- Braking Subgraph
(1, 1, 2), -- Brake Bias Dial MODULATES_PRESSURE_IN Front Master Cylinder

-- Powertrain Thermal Subgraph
(4, 2, 3), -- Powertrain ECU READS_THERMAL_DATA_FROM High Voltage Accumulator
(4, 3, 5); -- Powertrain ECU ACTIVATES Accumulator Cooling Fans