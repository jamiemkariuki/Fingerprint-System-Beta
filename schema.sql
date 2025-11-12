-- MySQL schema for Fingerprint System
-- Run as a user with privileges to create database/objects

CREATE DATABASE IF NOT EXISTS `FingerprintDB` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `FingerprintDB`;

-- Admins table
CREATE TABLE IF NOT EXISTS `Admins` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_admin_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Teachers table
CREATE TABLE IF NOT EXISTS `Teachers` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `username` VARCHAR(64) NOT NULL,
  `email` VARCHAR(128) NOT NULL,
  `class` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `fingerprint_id` INT UNSIGNED NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_teacher_username` (`username`),
  UNIQUE KEY `uniq_teacher_email` (`email`),
  UNIQUE KEY `uniq_teacher_fingerprint_id` (`fingerprint_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Users (students) table
CREATE TABLE IF NOT EXISTS `Users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `class` VARCHAR(64) NOT NULL,
  `fingerprint_id` INT UNSIGNED NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_users_class` (`class`),
  UNIQUE KEY `uniq_user_fingerprint_id` (`fingerprint_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Fingerprint logs
CREATE TABLE IF NOT EXISTS `FingerprintLogs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `person_type` ENUM('student','teacher') NOT NULL,
  `person_id` INT UNSIGNED NOT NULL,
  `timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_logs_person_day` (`person_type`, `person_id`, `timestamp` )
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Settings table
CREATE TABLE IF NOT EXISTS `Settings` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `key` VARCHAR(255) NOT NULL,
  `value` TEXT,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_setting_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Default settings
INSERT INTO `Settings` (`key`, `value`) VALUES ('send_days', '1,2,3,4,5') ON DUPLICATE KEY UPDATE `key`=`key`;
INSERT INTO `Settings` (`key`, `value`) VALUES ('fingerprint_listener_enabled', '1') ON DUPLICATE KEY UPDATE `key`=`key`;
  

-- Optional: seed initial admin (change password after hashing externally if desired)
-- INSERT INTO `Admins` (`username`, `password_hash`) VALUES ('admin', '<bcrypt-hash-here>');