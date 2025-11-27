-- Adminer 5.4.1 MariaDB 11.8.3-MariaDB-log dump

SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

SET NAMES utf8mb4;

DROP TABLE IF EXISTS `bitacora`;
CREATE TABLE `bitacora` (
  `idBitacora` int(11) NOT NULL AUTO_INCREMENT,
  `idPaciente` int(11) DEFAULT NULL,
  `fecha` date NOT NULL,
  `horaInicio` varchar(20) NOT NULL,
  `horaFin` varchar(20) NOT NULL,
  `drenajeInicial` decimal(10,2) DEFAULT NULL,
  `ufTotal` decimal(10,2) DEFAULT NULL,
  `tiempoMedioPerm` decimal(10,2) DEFAULT NULL,
  `liquidoIngerido` decimal(10,2) DEFAULT NULL,
  `cantidadOrina` decimal(10,2) DEFAULT NULL,
  `glucosa` decimal(10,2) DEFAULT NULL,
  `presionArterial` varchar(20) DEFAULT NULL,
  `fechaCreacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `fechaActualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`idBitacora`),
  KEY `idPaciente` (`idPaciente`),
  CONSTRAINT `bitacora_ibfk_2` FOREIGN KEY (`idPaciente`) REFERENCES `pacientes` (`idPaciente`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `bitacora` (`idBitacora`, `idPaciente`, `fecha`, `horaInicio`, `horaFin`, `drenajeInicial`, `ufTotal`, `tiempoMedioPerm`, `liquidoIngerido`, `cantidadOrina`, `glucosa`, `presionArterial`, `fechaCreacion`, `fechaActualizacion`) VALUES
(2,	2,	'2025-11-02',	'07:15:00',	'12:05:00',	1150.00,	400.10,	44.00,	550.00,	300.00,	112.00,	'120/80',	'2025-11-25 04:22:52',	'2025-11-26 05:16:43'),
(3,	2,	'2025-11-03',	'07:10:00',	'12:10:00',	1180.90,	420.00,	43.50,	580.00,	320.00,	109.90,	'116/74',	'2025-11-25 04:22:52',	'2025-11-26 05:16:43'),
(4,	2,	'2025-11-26',	'07:20:00',	'12:15:00',	1200.00,	395.30,	41.20,	500.00,	280.00,	115.20,	'120/30',	'2025-11-25 04:22:52',	'2025-11-26 05:16:43'),
(5,	2,	'2025-11-05',	'07:05:00',	'12:00:00',	1130.70,	410.40,	45.10,	650.00,	330.00,	107.80,	'117/75',	'2025-11-25 04:22:52',	'2025-11-26 05:16:43'),
(20,	1,	'2025-10-24',	'21:14',	'10:00',	1500.00,	500.00,	1.03,	1500.00,	500.00,	93.00,	'180/90',	'2025-11-26 02:14:30',	'2025-11-26 05:16:52'),
(21,	1,	'2025-10-10',	'20:24',	'20:24',	789.00,	789.00,	8.99,	778.00,	678.00,	23.00,	'180/90',	'2025-11-26 02:24:46',	'2025-11-26 05:16:52'),
(22,	1,	'2025-11-01',	'08:00',	'21:00',	1230.00,	232.00,	231.00,	213.00,	321.00,	123.00,	'120/30',	'2025-11-26 05:01:03',	'2025-11-26 05:16:52');

DROP TABLE IF EXISTS `pacientes`;
CREATE TABLE `pacientes` (
  `idPaciente` int(11) NOT NULL AUTO_INCREMENT,
  `nombreCompleto` varchar(255) NOT NULL,
  `edad` int(11) DEFAULT NULL,
  `sexo` char(1) DEFAULT NULL,
  `curp` varchar(18) DEFAULT NULL,
  `domicilio` text DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `emergencia` varchar(20) DEFAULT NULL,
  `seguroMedico` varchar(255) DEFAULT NULL,
  `fechaRegistro` datetime DEFAULT current_timestamp(),
  `idUsuario` int(11) DEFAULT NULL,
  PRIMARY KEY (`idPaciente`),
  KEY `idx_nombre` (`nombreCompleto`),
  KEY `idx_curp` (`curp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `pacientes` (`idPaciente`, `nombreCompleto`, `edad`, `sexo`, `curp`, `domicilio`, `telefono`, `emergencia`, `seguroMedico`, `fechaRegistro`, `idUsuario`) VALUES
(1,	'María Guadalupe Torres Hernández',	52,	'F',	'TOHM690325MCLRRN07',	'Calle Nogales #214, Col. Doctores, Piedras Negras, Coahuila, México',	'8781452398',	'8781125476',	'IMSS',	'2025-11-25 05:59:47',	4),
(2,	'Maria de los Angeles Treviño Rodriguez',	55,	'F',	'TERA020270',	'Av. Progreso #1519 Col. Buena Vista Sur',	'8781328934',	'Gilberto Treviño Lop',	'23005493',	'2025-11-26 00:14:48',	1);

DROP TABLE IF EXISTS `usuario`;
CREATE TABLE `usuario` (
  `idUsuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `tipo_usuario` varchar(10) NOT NULL,
  PRIMARY KEY (`idUsuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `usuario` (`idUsuario`, `nombre`, `contrasena`, `tipo_usuario`) VALUES
(1,	'Maria',	'020270',	'2'),
(3,	'Rene',	'12345',	'1'),
(4,	'María Guadalupe',	'54321',	'2');

-- 2025-11-27 01:45:15 UTC
