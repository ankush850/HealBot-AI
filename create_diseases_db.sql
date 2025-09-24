-- Enable foreign key support for data integrity
PRAGMA foreign_keys = ON;

-- Drop existing tables to make the script re-runnable
DROP TABLE IF EXISTS disease_symptoms;
DROP TABLE IF EXISTS disease_prevention;
DROP TABLE IF EXISTS diseases;
DROP TABLE IF EXISTS symptoms;
DROP TABLE IF EXISTS preventive_measures;
DROP TABLE IF EXISTS treatments;

-- Create the main 'diseases' table
CREATE TABLE diseases (
    disease_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    treatment_id INTEGER,
    FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id)
);

-- Create a table for all possible symptoms
CREATE TABLE symptoms (
    symptom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Create a table for all possible preventive measures
CREATE TABLE preventive_measures (
    measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Create a table for common treatments
CREATE TABLE treatments (
    treatment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL
);

-- Create a linking table for the many-to-many relationship between diseases and symptoms
CREATE TABLE disease_symptoms (
    disease_id INTEGER,
    symptom_id INTEGER,
    PRIMARY KEY (disease_id, symptom_id),
    FOREIGN KEY (disease_id) REFERENCES diseases(disease_id),
    FOREIGN KEY (symptom_id) REFERENCES symptoms(symptom_id)
);

-- Create a linking table for the many-to-many relationship between diseases and prevention
CREATE TABLE disease_prevention (
    disease_id INTEGER,
    measure_id INTEGER,
    PRIMARY KEY (disease_id, measure_id),
    FOREIGN KEY (disease_id) REFERENCES diseases(disease_id),
    FOREIGN KEY (measure_id) REFERENCES preventive_measures(measure_id)
);

-- Insert data into the tables
INSERT INTO treatments (description) VALUES
('Rest, hydration, and over-the-counter pain relievers. Medical consultation is advised.'),
('Antibiotics prescribed by a doctor.'),
('Antiviral medication prescribed by a doctor.'),
('Rehydration salts, fluids, and medical care for severe cases.'),
('Blood sugar management through diet, exercise, and medication.'),
('Lifestyle changes (diet, exercise) and prescribed medication.'),
('A multi-drug regimen over several months prescribed and monitored by a doctor.'),
('Specialized medical care to manage symptoms and prevent complications.');

INSERT INTO diseases (name, description, treatment_id) VALUES
('Dengue', 'A mosquito-borne viral infection causing flu-like illness, which can develop into a severe form.', 8),
('Malaria', 'A life-threatening disease caused by parasites that are transmitted to people through the bites of infected female Anopheles mosquitoes.', 8),
('Typhoid', 'A bacterial infection that can lead to a high fever, diarrhea, and vomiting. It is caused by the bacteria Salmonella typhi.', 2),
('Common Cold', 'A mild viral infection of the nose and throat.', 1),
('Influenza (Flu)', 'A contagious respiratory illness caused by influenza viruses.', 3),
('COVID-19', 'A contagious disease caused by the SARS-CoV-2 virus, affecting the respiratory system.', 3),
('Type 2 Diabetes', 'A chronic condition that affects the way the body processes blood sugar (glucose).', 5),
('Hypertension', 'A condition in which the force of the blood against the artery walls is too high, also known as high blood pressure.', 6),
('Tuberculosis (TB)', 'A potentially serious infectious disease that mainly affects the lungs.', 7);

INSERT INTO symptoms (name) VALUES
('Fever'), ('Headache'), ('Rash'), ('Muscle and Joint Pain'), ('Nausea'), ('Vomiting'), ('Chills'), ('Fatigue'),
('Cough'), ('Sore Throat'), ('Runny Nose'), ('Shortness of Breath'), ('Increased Thirst'), ('Frequent Urination'), ('Blurred Vision');

INSERT INTO preventive_measures (name) VALUES
('Mosquito Control (nets, repellents, eliminating stagnant water)'),
('Vaccination'),
('Frequent Hand Washing'),
('Maintain a Healthy Diet'),
('Regular Physical Exercise'),
('Avoid Touching Face'),
('Wear Masks in crowded places'),
('Ensure Clean Food and Water');

-- Link diseases to their symptoms
INSERT INTO disease_symptoms (disease_id, symptom_id) VALUES
-- Dengue
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
-- Malaria
(2, 1), (2, 2), (2, 7), (2, 4),
-- Typhoid
(3, 1), (3, 2), (3, 8), (3, 5), (3, 6),
-- Common Cold
(4, 9), (4, 10), (4, 11),
-- Influenza
(5, 1), (5, 4), (5, 8), (5, 9), (5, 10),
-- COVID-19
(6, 1), (6, 9), (6, 8), (6, 12),
-- Type 2 Diabetes
(7, 13), (7, 14), (7, 15), (7, 8),
-- Hypertension
(8, 2), (8, 12),
-- Tuberculosis
(9, 1), (9, 7), (9, 9), (9, 8);

-- Link diseases to their preventive measures
INSERT INTO disease_prevention (disease_id, measure_id) VALUES
(1, 1),
(2, 1),
(3, 8), (3, 2),
(4, 3), (4, 6),
(5, 2), (5, 3),
(6, 2), (6, 3), (6, 7),
(7, 4), (7, 5),
(8, 4), (8, 5),
(9, 2);