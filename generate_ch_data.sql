-- Create user_velocity table
DROP TABLE IF EXISTS user_velocity;

CREATE TABLE user_velocity (
    user_id UInt32,
    tx_last_24h UInt16,
    first_seen_days UInt16
) ENGINE = MergeTree() ORDER BY user_id;

-- Insert initial user velocity data for the sample users
INSERT INTO user_velocity (user_id, tx_last_24h, first_seen_days) VALUES
    (1, 3, 120),    -- Established user with moderate activity
    (2, 2, 85),     -- Established user with low activity
    (3, 5, 210),    -- Established user with high activity
    (4, 1, 45),     -- Newer user with low activity
    (5, 4, 150),    -- Established user with moderate activity
    (6, 2, 90),     -- Established user with low activity
    (7, 3, 180),    -- Established user with moderate activity
    (8, 6, 220),    -- Established user with high activity
    (9, 1, 60),     -- Newer user with low activity
    (10, 4, 145),   -- Established user with moderate activity
    (11, 12, 5),    -- New user with very high activity (suspicious)
    (12, 8, 10),    -- New user with high activity (suspicious)
    (13, 15, 3),    -- New user with very high activity (suspicious)
    (14, 10, 7),    -- New user with high activity (suspicious)
    (15, 20, 2);    -- New user with extremely high activity (suspicious)

-- Generate additional user velocity data for the remaining users
INSERT INTO user_velocity (user_id, tx_last_24h, first_seen_days)
SELECT 
    number + 16 AS user_id,
    if(rand() % 10 < 3, 
       rand() % 5 + 1,    -- 30% of users have 1-5 transactions (normal)
       if(rand() % 10 < 1, 
          rand() % 15 + 10, -- 10% of users have 10-25 transactions (suspicious)
          rand() % 5 + 5)   -- 60% of users have 5-10 transactions (moderate)
    ) AS tx_last_24h,
    if(rand() % 10 < 3,
       rand() % 30 + 1,    -- 30% are new users (1-30 days)
       rand() % 700 + 30)  -- 70% are established users (30-730 days)
    AS first_seen_days
FROM system.numbers
WHERE number < 85;  -- Generate for users 16-100

-- Display some statistics
SELECT 
    count() AS total_users,
    avg(tx_last_24h) AS avg_transactions_24h,
    min(tx_last_24h) AS min_transactions_24h,
    max(tx_last_24h) AS max_transactions_24h
FROM user_velocity;

-- Count of new vs established users
SELECT
    countIf(first_seen_days < 30) AS new_users,
    countIf(first_seen_days >= 30) AS established_users
FROM user_velocity;

-- High velocity users (potential fraud indicators)
SELECT
    user_id,
    tx_last_24h,
    first_seen_days
FROM user_velocity
WHERE tx_last_24h > 10
ORDER BY tx_last_24h DESC;
