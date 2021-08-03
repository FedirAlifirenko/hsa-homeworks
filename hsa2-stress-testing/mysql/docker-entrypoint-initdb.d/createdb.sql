CREATE DATABASE IF NOT EXISTS `test-db` ;
GRANT ALL ON `test-db`.* TO 'test-user'@'%' ;
FLUSH PRIVILEGES ;
