

DROP TABLE IF EXISTS `price_by_option_of_product`;
CREATE TABLE `price_by_option_of_product` (
	`pboop_id` INT NOT NULL AUTO_INCREMENT,
	`p_id` INT DEFAULT NULL,
	`pboop_option` VARCHAR(20) DEFAULT NULL,
	`pboop_price` INT,
	`pboop_quick_price` INT,
	`pboop_datetime` DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (`pboop_id`),
  UNIQUE KEY `pboop_unique_key` (`p_id`,`pboop_option`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;