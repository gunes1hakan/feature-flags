CREATE DATABASE IF NOT EXISTS feature_flags;

CREATE USER IF NOT EXISTS 'ff_user'@'%' IDENTIFIED BY 'ff_pass_123';
GRANT ALL PRIVILEGES ON feature_flags.* TO 'ff_user'@'%';

CREATE USER IF NOT EXISTS 'ff_user'@'localhost' IDENTIFIED BY 'ff_pass_123';
GRANT ALL PRIVILEGES ON feature_flags.* TO 'ff_user'@'localhost';

FLUSH PRIVILEGES;
