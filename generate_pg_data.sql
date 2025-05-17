-- Create payments table
DROP TABLE IF EXISTS payments;

CREATE TABLE payments (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    country VARCHAR(2) NOT NULL,
    shipping_country VARCHAR(2) NOT NULL,
    ts TIMESTAMP NOT NULL,
    authorized BOOLEAN NOT NULL,
    fraud_label INTEGER NOT NULL
);

-- Create indexes for better performance
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_country ON payments(country);
CREATE INDEX idx_payments_ts ON payments(ts);

-- Insert sample data (10 legitimate transactions)
INSERT INTO payments (user_id, amount, country, shipping_country, ts, authorized, fraud_label) VALUES
    (1, 120.50, 'US', 'US', now() - interval '5 days', true, 0),
    (2, 75.25, 'CA', 'CA', now() - interval '10 days', true, 0),
    (3, 200.00, 'UK', 'UK', now() - interval '15 days', true, 0),
    (4, 50.99, 'FR', 'FR', now() - interval '20 days', true, 0),
    (5, 300.75, 'DE', 'DE', now() - interval '25 days', true, 0),
    (6, 99.99, 'US', 'US', now() - interval '30 days', true, 0),
    (7, 150.00, 'CA', 'CA', now() - interval '35 days', true, 0),
    (8, 180.25, 'UK', 'UK', now() - interval '40 days', true, 0),
    (9, 45.50, 'FR', 'FR', now() - interval '45 days', true, 0),
    (10, 250.00, 'DE', 'DE', now() - interval '50 days', true, 0);

-- Insert sample data (5 fraudulent transactions with patterns)
INSERT INTO payments (user_id, amount, country, shipping_country, ts, authorized, fraud_label) VALUES
    (11, 750.00, 'NG', 'US', now() - interval '7 days', false, 1),  -- High-risk country + mismatch
    (12, 1200.50, 'US', 'ZA', now() - interval '12 days', false, 1), -- High amount + shipping to high-risk
    (13, 500.00, 'NG', 'NG', now() - interval '18 days', false, 1),  -- High-risk country
    (14, 850.75, 'IN', 'UK', now() - interval '22 days', false, 1),  -- High-risk country + mismatch
    (15, 1500.00, 'US', 'US', now() - interval '28 days', false, 1); -- Very high amount

-- Generate more data with a loop (approximately 500 random transactions)
DO $$
DECLARE
    user_id_var INTEGER;
    amount_var DECIMAL(10, 2);
    country_var VARCHAR(2);
    shipping_country_var VARCHAR(2);
    ts_var TIMESTAMP;
    authorized_var BOOLEAN;
    fraud_label_var INTEGER;
    countries VARCHAR(2)[] := ARRAY['US', 'CA', 'UK', 'FR', 'DE', 'NG', 'ZA', 'IN', 'CN', 'JP', 'AU', 'BR', 'MX'];
    high_risk_countries VARCHAR(2)[] := ARRAY['NG', 'ZA', 'IN'];
    days_ago INTEGER;
    is_fraud BOOLEAN;
    country_mismatch BOOLEAN;
    is_high_risk BOOLEAN;
BEGIN
    FOR i IN 1..500 LOOP
        -- Select random user ID from 1 to 100
        user_id_var := floor(random() * 100) + 1;
        
        -- Days ago (0 to 90 days)
        days_ago := floor(random() * 90);
        ts_var := now() - (days_ago || ' days')::INTERVAL;
        
        -- Determine if this will be a fraudulent transaction (approximately 5% fraud rate)
        is_fraud := random() < 0.05;
        
        -- Determine if transaction is from a high-risk country
        is_high_risk := random() < 0.2;
        
        -- Determine country
        IF is_high_risk THEN
            country_var := high_risk_countries[floor(random() * array_length(high_risk_countries, 1)) + 1];
        ELSE
            country_var := countries[floor(random() * array_length(countries, 1)) + 1];
        END IF;
        
        -- Determine if shipping country matches billing country (85% match, 15% mismatch)
        country_mismatch := random() < 0.15;
        
        IF country_mismatch THEN
            shipping_country_var := countries[floor(random() * array_length(countries, 1)) + 1];
        ELSE
            shipping_country_var := country_var;
        END IF;
        
        -- Generate amount (higher for fraudulent transactions)
        IF is_fraud THEN
            amount_var := (random() * 1500) + 300; -- $300 to $1800
        ELSE
            -- 10% chance of high-value legitimate transaction
            IF random() < 0.1 THEN
                amount_var := (random() * 800) + 200; -- $200 to $1000
            ELSE
                amount_var := (random() * 290) + 10; -- $10 to $300
            END IF;
        END IF;
        
        -- Round amount to 2 decimal places
        amount_var := round(amount_var::numeric, 2);
        
        -- Authorization is usually successful unless fraud
        IF is_fraud THEN
            authorized_var := random() > 0.9; -- 90% of fraud is unauthorized
        ELSE
            authorized_var := random() > 0.02; -- 98% of legitimate is authorized
        END IF;
        
        -- Increase fraud probability based on risk factors
        IF NOT is_fraud THEN
            -- If transaction has fraud characteristics, re-evaluate fraud label
            IF (country_var = ANY(high_risk_countries) AND amount_var > 200) OR
               (country_mismatch AND amount_var > 250) OR
               (amount_var > 1000) THEN
                is_fraud := random() < 0.3; -- 30% chance to convert to fraud
            END IF;
        END IF;
        
        -- Set fraud label
        fraud_label_var := CASE WHEN is_fraud THEN 1 ELSE 0 END;
        
        -- Insert the data
        INSERT INTO payments (user_id, amount, country, shipping_country, ts, authorized, fraud_label)
        VALUES (user_id_var, amount_var, country_var, shipping_country_var, ts_var, authorized_var, fraud_label_var);
    END LOOP;
END $$;

-- Create a view that calculates some fraud statistics
CREATE OR REPLACE VIEW fraud_statistics AS
SELECT
    COUNT(*) AS total_transactions,
    SUM(amount) AS total_amount,
    SUM(CASE WHEN fraud_label = 1 THEN 1 ELSE 0 END) AS fraud_count,
    SUM(CASE WHEN fraud_label = 1 THEN amount ELSE 0 END) AS fraud_amount,
    ROUND(SUM(CASE WHEN fraud_label = 1 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100, 2) AS fraud_percent
FROM payments;

-- Display some statistics about the data
SELECT * FROM fraud_statistics;
SELECT COUNT(*) AS legitimate_transactions FROM payments WHERE fraud_label = 0;
SELECT COUNT(*) AS fraudulent_transactions FROM payments WHERE fraud_label = 1;
SELECT country, COUNT(*) FROM payments GROUP BY country ORDER BY COUNT(*) DESC;
SELECT 
    COUNT(*) AS country_mismatch_count, 
    ROUND(AVG(amount)::NUMERIC, 2) AS avg_amount,
    SUM(CASE WHEN fraud_label = 1 THEN 1 ELSE 0 END) AS fraud_count
FROM payments 
WHERE country != shipping_country;
