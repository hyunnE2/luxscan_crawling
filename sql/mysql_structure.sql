-- MySQL dump 10.13  Distrib 8.0.34, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: test
-- ------------------------------------------------------
-- Server version	8.0.35
DROP DATABASE IF EXISTS test;
create database test DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `brand`;
CREATE TABLE `brand` (
  `b_id` int NOT NULL AUTO_INCREMENT,
  `b_name` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`b_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `category`;
CREATE TABLE `category` (
  `c_id` int NOT NULL AUTO_INCREMENT,
  `c_name` varchar(50) DEFAULT NULL,
  `c_is_men` tinyint DEFAULT '0',
  `c_is_woman` tinyint DEFAULT '0',
  PRIMARY KEY (`c_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `config`;
CREATE TABLE `config` (
  `cfg_key` varchar(255) NOT NULL,
  `cfg_value` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `crawling_product_list`;
CREATE TABLE `crawling_product_list` (
  `cpl_id` int NOT NULL AUTO_INCREMENT,
  `p_id` int DEFAULT NULL,
  PRIMARY KEY (`cpl_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `market`;
CREATE TABLE `market` (
  `m_id` int NOT NULL AUTO_INCREMENT,
  `m_name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`m_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `product`;
CREATE TABLE `product` (
  `p_id` int NOT NULL AUTO_INCREMENT,
  `m_id` int DEFAULT NULL,
  `b_id` int DEFAULT NULL,
  `p_name` varchar(255) DEFAULT NULL,
  `p_name_kr` varchar(255) DEFAULT NULL,
  `p_price` decimal(10,0) DEFAULT '0',
  `p_count` int DEFAULT '0',
  `p_option` text,
  `p_url` varchar(255) DEFAULT NULL,
  `p_img_url` varchar(255) DEFAULT NULL,
  `p_last_crawling_datetime` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`p_id`),
  UNIQUE KEY `p_url_unique` (`p_url`),
  KEY `p_url` (`p_url`) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `product_sell_history`;
CREATE TABLE `product_sell_history` (
  `psh_id` int NOT NULL,
  `p_id` int DEFAULT NULL,
  `psh_option` varchar(50) DEFAULT NULL,
  `psh_datetime` datetime DEFAULT NULL,
  `psh_price` int DEFAULT NULL,
  `psh_is_quickly` tinyint DEFAULT '0',
  PRIMARY KEY (`psh_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


DROP TABLE IF EXISTS `price_by_option_of_product`;
CREATE TABLE `price_by_option_of_product` (
	`pbsop_id` INT NOT NULL AUTO_INCREMENT,
	`p_id` INT DEFAULT NULL,
	`pbsop_option` VARCHAR(20) DEFAULT NULL,
	`pbsop_price` INT,
	`pbsop_quick_price` INT,
	`pbsop_datetime` DATETIME DEFAULT CURRENT_TIMESTAMP,
	 PRIMARY KEY (`pbsop_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;