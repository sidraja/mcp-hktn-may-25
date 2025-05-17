DROP TABLE IF EXISTS user_velocity;

CREATE TABLE user_velocity (
    user_id UInt32,
    tx_last_24h UInt16,
    first_seen_days UInt16
) ENGINE = MergeTree() ORDER BY user_id;

INSERT INTO user_velocity (user_id, tx_last_24h, first_seen_days) VALUES
    (1, 3, 120),
    (2, 2, 85),
    (3, 5, 210),
    (4, 1, 45),
    (5, 4, 150),
    (6, 2, 90),
    (7, 3, 180),
    (8, 6, 220),
    (9, 1, 60),
    (10, 4, 145),
    (11, 12, 5),
    (12, 8, 10),
    (13, 15, 3),
    (14, 10, 7),
    (15, 20, 2);

INSERT INTO user_velocity (user_id, tx_last_24h, first_seen_days)
SELECT 
    number + 16 AS user_id,
    if(rand() % 10 < 3, 
       rand() % 5 + 1,
       if(rand() % 10 < 1, 
          rand() % 15 + 10,
          rand() % 5 + 5)
    ) AS tx_last_24h,
    if(rand() % 10 < 3,
       rand() % 30 + 1,
       rand() % 700 + 30)
    AS first_seen_days
FROM system.numbers
WHERE number < 85;

SELECT 
    count() AS total_users,
    avg(tx_last_24h) AS avg_transactions_24h,
    min(tx_last_24h) AS min_transactions_24h,
    max(tx_last_24h) AS max_transactions_24h
FROM user_velocity;
