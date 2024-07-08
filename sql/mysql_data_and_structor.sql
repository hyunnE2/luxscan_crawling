USE luxscan_crawling_data;


DROP TABLE IF EXISTS `brand`;
CREATE TABLE `brand` (
  `b_id` int NOT NULL AUTO_INCREMENT,
  `b_name` varchar(50) DEFAULT NULL,
  `b_update_at` datetime DEFAULT NULL,
  PRIMARY KEY (`b_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `brand`(`b_id`, `b_name`) VALUES (1,'Bottega Veneta'),(2,'Adidas'),(3,'Dior'),(4,'Gucci'),(5,'Hermes'),(6,'Burberry'),(7,'Balenciaga'),(8,'Jordan'),(9,'Celine'),(10,'Stone Island'),(11,'Moncler'),(12,'Miu Miu'),(13,'Prada'),(14,'Louis Vuitton'),(15,'Chan'),(16,'Maison Kitsune'),(17,'Supreme'),(18,'Converse'),(19,'Chanel'),(20,'Carhartt'),(21,'C.P. Company'),(22,'Maison Margiela'),(23,'Saint Laurent'),(24,'Human Made'),(25,'AMI'),(26,'Chloe'),(27,'Vivienne Westwood'),(28,'Lego'),(29,'Thom Browne'),(30,'Essentials'),(31,'Jacquemus'),(32,'Loewe'),(33,'A.P.C.'),(34,'Arc\'teryx'),(35,'Matin Kim'),(36,'Stussy'),(37,'Fendi'),(38,'Isabel Marant'),(39,'Asics'),(40,'BAPE'),(41,'Vans'),(42,'Ganni'),(43,'Diesel'),(44,'Bearbrick'),(45,'Mihara Yasuhiro'),(46,'New Balance'),(47,'Lemaire'),(48,'Lacoste'),(49,'Ferragamo'),(50,'Acne Studios'),(51,'Kapital'),(52,'Apple'),(53,'Canada Goose'),(54,'Goyard'),(55,'Crocs'),(56,'Malbon Golf'),(57,'Ader Error'),(58,'IAB Studio'),(59,'Wooyoungmi'),(60,'Casetify'),(61,'Porter'),(62,'J.Lindeberg'),(63,'Nike'),(64,'Auralee'),(65,'Helinox'),(66,'Marni'),(67,'Max Mara'),(68,'Head'),(69,'Emis'),(70,'Kenzo'),(71,'Covernat'),(72,'Off-White'),(73,'The North Face'),(74,'COS'),(75,'Dunst'),(76,'Gentle Monster'),(77,'Hoka'),(78,'G/Fore'),(79,'Barbour'),(80,'Cav Empt'),(81,'Golden Goose'),(82,'Michael Kors'),(83,'Courreges'),(84,'Hysteric Glamour'),(85,'Rolex'),(86,'Casio'),(87,'Montblanc'),(88,'Coach'),(89,'Mulberry'),(90,'Chrome Hearts'),(91,'Mackage'),(92,'Corteiz'),(93,'Autry'),(94,'Citizen'),(95,'Alexander McQueen'),(96,'Kith'),(97,'Mischief'),(98,'Givenchy'),(99,'Dr. Martens'),(100,'Howlin'),(101,'Camper'),(102,'Birkenstock'),(103,'Jil Sander'),(104,'Hunter'),(105,'Moose Knuckles'),(106,'Longchamp'),(107,'Montbell'),(108,'Clarks'),(109,'Juun.J'),(110,'Cartier'),(111,'Bally'),(112,'Jansport'),(113,'Loro Piana'),(114,'Glowny'),(115,'Bohemian Seoul'),(116,'Comme des Garcons'),(117,'Aime Leon Dore'),(118,'Bao Bao Issey Miyake'),(119,'Kaikai Kiki'),(120,'Danton'),(121,'Denim Tears'),(122,'Homme Plisse Issey Miyake'),(123,'Emporio Armani'),(124,'NanAMIca'),(125,'Comfort'),(126,'CDG'),(127,'Helen KAMInski'),(128,'Girl'),(129,'Mizuno'),(130,'Klattermusen'),(131,'Ciota'),(132,'Ancellm'),(133,'Keen'),(134,'HAMIlton'),(135,'Calvin Klein'),(136,'Marc Jacobs'),(137,'Gallery Dept.'),(138,'Meta'),(139,'Jo Malone'),(140,'Leopold'),(141,'Diptyque'),(142,'Add'),(143,'Chocolate'),(144,'Magliano'),(145,'Logitech'),(146,'Deus Ex Machina'),(147,'Kaws'),(148,'Deinet'),(149,'And Wander'),(150,'Fragment'),(151,'Hai'),(152,'Khy'),(153,'Drew House'),(154,'Fjallraven'),(155,'Alo Yoga'),(156,'Darkr8m Studio'),(157,'Fear of God'),(158,'msgm'),(159,'MSGM'),(160,'Kangol'),(161,'Crystal Haze'),(162,'Jellycat'),(163,'Dragon Diffusion'),(164,'Duvetica'),(165,'Ienki Ienki'),(166,'Byredo'),(167,'Fossil'),(168,'Aviemuah'),(169,'Goldwin'),(170,'Beams'),(171,'Alexander Wang'),(172,'Cayl'),(173,'Dolce & Gabbana'),(174,'Dada'),(175,'Haag'),(176,'Le Labo'),(177,'47 Brand'),(178,'Hidden NY'),(179,'Andersen Andersen'),(180,'Cardinal Red'),(181,'Kakazzy'),(182,'Bandai'),(183,'Delvaux'),(184,'Fullcount'),(185,'Dyson'),(186,'Merrell'),(187,'Fred'),(188,'Hyke'),(189,'Columbia'),(190,'Lululemon'),(191,'Maje'),(192,'Brunello Cucinelli'),(193,'Alaia'),(194,'MM6'),(195,'Axel Arigato'),(196,'Achilles'),(197,'Balmain'),(198,'Moon Boot'),(199,'Ennoy'),(200,'Black Diamond'),(201,'DAMIani'),(202,'Graphpaper'),(203,'H&M'),(204,'Champion'),(205,'GR10K'),(206,'Acqua Di Parma'),(207,'Bode'),(208,'Daniel Arsham'),(209,'Herno'),(210,'Iro'),(211,'Melissa'),(212,'Buly 1803'),(213,'Creed'),(214,'Drole de Monsieur'),(215,'Marine Serre'),(216,'Moorer'),(217,'Jaded London'),(218,'Meduse'),(219,'Megahouse'),(220,'Aritzia'),(221,'Farfromwhat'),(222,'House of Sunny'),(223,'1017 Alyx 9SM'),(224,'Cactus Plant Flea Market'),(225,'Dickies'),(226,'Hereu'),(227,'Marithe Francois Girbaud'),(228,'Corsair'),(229,'Dareu'),(230,'Estee Lauder'),(231,'Hilleberg'),(232,'Levi\'s'),(233,'Atelier Choux'),(234,'Charles Jeffrey Loverboy'),(235,'Drogheria Crivellini'),(236,'Marshall'),(237,'Anti Social Social Club'),(238,'Coperni'),(239,'Engineered Garments'),(240,'Golden Dew'),(241,'Ecco'),(242,'Beats'),(243,'Mitchell & Ness'),(244,'Cow Books'),(245,'Kinchi'),(246,'Charles & Keith'),(247,'Cosymosy'),(248,'Aesop'),(249,'Flos'),(250,'MLB'),(251,'Moonstar'),(252,'Blizzard'),(253,'California General Store'),(254,'Goal Studio'),(255,'Hugo Boss'),(256,'Marimekko'),(257,'Ambush'),(258,'Bang & Olufsen'),(259,'Grailz'),(260,'JBL'),(261,'Babymetalclub'),(262,'BOSE'),(263,'Hobonichi'),(264,'Jimmy Choo'),(265,'Lawn Chair'),(266,'All Saints'),(267,'Bensimon'),(268,'Blue Bottle'),(269,'Facade Pattern'),(270,'Grove'),(271,'Harley of Scotland'),(272,'Etro'),(273,'Barrie'),(274,'BDNS'),(275,'Christian Louboutin'),(276,'District Vision'),(277,'Eastpak'),(278,'Ends and Means'),(279,'Fujifilm'),(280,'Island Slipper'),(281,'LE SSERAFIM'),(282,'Farven'),(283,'Fila'),(284,'JW Anderson'),(285,'Lowa'),(286,'Monamhee'),(287,'A Cold Wall'),(288,'Cumulus'),(289,'Feathered Friends'),(290,'Baracuta'),(291,'Bon Ton Toys'),(292,'Bulgari'),(293,'Hourglass'),(294,'MM6 Maison Margiela'),(295,'Blunt'),(296,'Comoli'),(297,'Fashy'),(298,'Memo'),(299,'Mark & Lona'),(300,'Martine Rose'),(301,'Blumarine'),(302,'Coleman'),(303,'J.L-A.L'),(304,'Akikoaoki'),(305,'Cueren'),(306,'Daiwa Pier39'),(307,'Insilence'),(308,'JJJJound'),(309,'MJD'),(310,'Filson'),(311,'Giorgio Armani'),(312,'Guizio'),(313,'Helikon Tex'),(314,'Kilian'),(315,'Travis Scott'),(316,'Merci'),(317,'Common Projects'),(318,'Helsport'),(319,'Microsoft'),(320,'longines'),(321,'Aeae'),(322,'Alden'),(323,'Asus'),(324,'Carol Shoppe'),(325,'Fottsfotts'),(326,'Junya Watanabe'),(327,'Malin+Goetz'),(328,'Minitmute'),(329,'Berluti'),(330,'Chaumet'),(331,'DJI'),(332,'Foreo'),(333,'Horlisun'),(334,'Leica'),(335,'Marsell'),(336,'A.Presse'),(337,'Aeyde'),(338,'Breitling'),(339,'Buccellati'),(340,'Globe'),(341,'Harman Kardon'),(342,'I Am Gia'),(343,'Maison Francis Kurkdjian'),(344,'MSR'),(345,'Audemars Piguet'),(346,'AQ'),(347,'Duno'),(348,'Vanessa Bruno'),(349,'Balmuda'),(350,'Blitzway'),(351,'d\'Alba'),(352,'Anta'),(353,'Giarite'),(354,'Gregory'),(355,'Hunza G'),(356,'IDEA'),(357,'Kiko Kostadinov'),(358,'Marmot'),(359,'& Other Stories'),(360,'Ae Synctx'),(361,'AMIacalva'),(362,'Biotherm Homme'),(363,'Camber USA'),(364,'Church\'s'),(365,'Guerlain'),(366,'Leey'),(367,'Manolo Blahnik'),(368,'Alighieri'),(369,'Audio-Technica'),(370,'Ben Davis'),(371,'Bugaboo'),(372,'By Far'),(373,'Chopard'),(374,'Glynit'),(375,'Lancome'),(376,'Avavav'),(377,'Belstaff'),(378,'Canon'),(379,'Discovery Expedition'),(380,'EOW'),(381,'Freak\'s Store'),(382,'Hot Toys'),(383,'Keds'),(384,'Knwls'),(385,'Massimo Dutti'),(386,'032c'),(387,'Laarvee'),(388,'LOW CLASSIC'),(389,'Marysia'),(390,'MSCHF'),(391,'Nanga'),(392,'C.P.'),(393,'Athleta'),(394,'AMD'),(395,'Botanize'),(396,'Boucheron'),(397,'Callaway'),(398,'Carne Bollente'),(399,'Evisu'),(400,'Godashin'),(401,'Hogan'),(402,'Khakis'),(403,'Ancuta Sarca'),(404,'BeyerdynAMIc'),(405,'Buttero'),(406,'Destree'),(407,'ETCE'),(408,'Mou'),(409,'AOP'),(410,'Kipling'),(411,'Andar'),(412,'Annika Inez'),(413,'Bunzaburo'),(414,'Castore'),(415,'Guidi'),(416,'Hakusan Megane'),(417,'HGBB Studio'),(418,'Jichoi'),(419,'Korean Air'),(420,'La Mer'),(421,'Lanvin'),(422,'Creature'),(423,'Magaret Howell'),(424,'Taylormade'),(425,'Bonjour Diary'),(426,'Denon'),(427,'Fidan Novruzova'),(428,'Giuseppe Zanotti'),(429,'Grip Swany'),(430,'IKEA'),(431,'Luar'),(432,'Baccarat'),(433,'Manduka'),(434,'Medicube'),(435,'Swarovski'),(436,'Aula'),(437,'Wacko Maria'),(438,'EA7'),(439,'GoPro'),(440,'Kiehl\'s'),(441,'Kijima Takayuki'),(442,'Balansa'),(443,'CCS Toys'),(444,'Cole Haan'),(445,'Denver & Liely'),(446,'HUF'),(447,'Joopiter'),(448,'LG'),(449,'LOTS YOU'),(450,'Youth'),(451,'Winning'),(452,'Tissot'),(453,'Tory Burch'),(454,'Tiffany & Co.'),(455,'A Twosome Place'),(456,'Y-3'),(457,'AAPE'),(458,'Bait'),(459,'Bravest Studios'),(460,'Carrots'),(461,'Foce'),(462,'Jolielaide'),(463,'Ki-No'),(464,'Advisory Board Crystals'),(465,'Mercer'),(466,'Military Surplus'),(467,'Mmo Garden'),(468,'Lemaire'),(469,'Rick Owens'),(470,'feragamo'),(471,'Van Cleef & Arpels'),(472,'Yeezy'),(473,'Porta'),(474,'Artue'),(475,'Suicoke'),(476,'Brooks'),(477,'Glossier'),(478,'Hot Wheels'),(479,'Joan Cornella'),(480,'Homer'),(481,'London Bagel Museum'),(482,'LP & CD'),(483,'Toei Studio'),(484,'WD'),(485,'Pony'),(486,'Spyder'),(487,'GCDS'),(488,'Birthdaysuit'),(489,'Palace'),(490,'Nars'),(491,'National Geographic');


DROP TABLE IF EXISTS `category`;
CREATE TABLE `category` (
  `c_id` int NOT NULL AUTO_INCREMENT,
  `c_name` varchar(50) DEFAULT NULL,
  `c_is_men` tinyint DEFAULT '0',
  `c_is_woman` tinyint DEFAULT '0',
  PRIMARY KEY (`c_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `category` VALUES (1,'스니커즈',1,1),(20,'패딩',1,1),(21,'코트',1,1),(22,'자켓',1,1),(23,'후드',1,0),(24,'스웨트셔츠',1,1),(25,'니트',1,1),(26,'긴팔 티셔츠',1,1),(27,'반팔 티셔츠',1,1),(28,'셔츠',1,1),(29,'바지',0,1),(30,'반바지',0,1),(35,'부츠',1,1),(37,'샌들/슬리퍼',1,1),(50,'스커트',0,1),(52,'벨트',1,1),(53,'기타 주얼리',1,1),(55,'데비/레이스업',1,1),(57,'스카프',1,1),(59,'아이웨어',1,1),(62,'힐/펌프스',0,1),(69,'로퍼',1,1),(70,'플랫',0,1),(71,'기타 신발',1,1),(73,'기타 아우터',1,1),(74,'후드 집업',1,0),(75,'가디건',1,1),(76,'슬리브리스',1,1),(77,'원피스',0,1),(78,'기타 상의',1,1),(81,'미니백',1,1),(82,'백팩',1,1),(83,'크로스백',1,1),(84,'숄더백',1,1),(85,'더플백',1,1),(86,'클러치',1,1),(87,'토트백',1,1),(89,'캐리어',1,1),(90,'기타 가방',1,1),(95,'반 지갑',1,0),(96,'장지갑',1,0),(97,'카드 지갑',1,0),(98,'체인 지갑',1,1),(99,'기타 지갑',1,0),(100,'귀걸이',1,1),(101,'목걸이',1,1),(102,'팔찌',1,1),(103,'비니',1,1),(104,'버킷 햇',1,1),(105,'볼캡',1,1),(106,'기타 모자',1,1),(107,'머플러',1,1),(108,'키링',1,1),(109,'넥타이',1,0),(110,'장갑',1,1),(111,'기타 패션잡화',1,1),(142,'반지',1,1),(148,'양말',1,1);


DROP TABLE IF EXISTS `config`;
CREATE TABLE `config` (
  `cfg_key` varchar(255) NOT NULL,
  `cfg_value` text NOT NULL,
  index config_cfg_index_key (cfg_key)
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

INSERT INTO `market` VALUES (1,'kream');


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
  `psh_id` int NOT NULL AUTO_INCREMENT,
  `p_id` int DEFAULT NULL,
  `psh_option` varchar(50) DEFAULT NULL,
  `psh_datetime` datetime DEFAULT NULL,
  `psh_price` int DEFAULT NULL,
  `psh_is_quickly` tinyint DEFAULT NULL,
  PRIMARY KEY (`psh_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


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